"""Errors as the API reports them (docs/api.md, "The envelope"): `{meta, errors: [{code, param, message}]}` with a
4xx or 5xx status, in place of Ninja's `{"detail": …}`. `install(api)` registers a handler for each kind."""

import logging
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError
from ninja.errors import ValidationError as NinjaValidationError


class ApiError(Exception):
    """A request the API can't answer as asked: `code` is a stable machine name (`out_of_range`, `unknown_variable`),
    `param` the query parameter at fault, if one is."""

    def __init__(self, code: str, message: str, param: str | None = None, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.param, self.status = code, message, param, status

    def item(self) -> dict[str, Any]:
        return {"code": self.code, "param": self.param, "message": self.message}


def install(api: NinjaAPI) -> None:
    from api import envelope  # which raises ApiError

    @api.exception_handler(ApiError)
    def api_error(request: HttpRequest, exc: ApiError) -> HttpResponse:
        return envelope.error_response(request, [exc.item()], status=exc.status)

    @api.exception_handler(NinjaValidationError)
    def invalid(request: HttpRequest, exc: NinjaValidationError) -> HttpResponse:
        return envelope.error_response(request, [_validation_item(e) for e in exc.errors], status=422)

    @api.exception_handler(Http404)
    def not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
        message = str(exc) or f"nothing at {request.path}"
        return envelope.error_response(request, [{"code": "not_found", "param": None, "message": message}], 404)

    @api.exception_handler(HttpError)
    def http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        item = {"code": _CODES.get(exc.status_code, "error"), "param": None, "message": exc.message}
        return envelope.error_response(request, [item], status=exc.status_code)

    @api.exception_handler(AuthenticationError)
    def unauthorized(request: HttpRequest, exc: AuthenticationError) -> HttpResponse:
        item = {"code": "unauthorized", "param": None, "message": "this endpoint needs credentials"}
        return envelope.error_response(request, [item], status=401)

    @api.exception_handler(Exception)
    def unexpected(request: HttpRequest, exc: Exception) -> HttpResponse:
        # Logged with the traceback, as Django logs an unhandled error; the client gets the envelope without internals
        logging.getLogger("django.request").error("API error at %s", request.path, exc_info=exc)
        item = {"code": "internal_error", "param": None, "message": "something went wrong on our side; it's logged"}
        return envelope.error_response(request, [item], status=500)


_CODES = {400: "bad_request", 403: "forbidden", 404: "not_found", 405: "method_not_allowed", 429: "rate_limited"}


def _validation_item(error: dict[str, Any]) -> dict[str, Any]:
    """One of Pydantic's errors, as Ninja passes them on: `loc` is ("query", "lat") or ("query", "<schema>", "lat"),
    and a model-level check has no field (its message names the parameters)."""
    loc = [str(part) for part in error.get("loc", ()) if part not in ("query", "path", "body", "header")]
    param = loc[-1] if loc else None
    if param is not None and param.endswith("Query"):  # a whole query schema's own check
        param = None
    code = str(error.get("type", "invalid"))
    message = str(error.get("msg", "invalid value"))
    message = message.removeprefix("Value error, ")
    if code in ("value_error", "assertion_error"):
        code = "invalid"
    ctx = error.get("ctx") or {}
    if "param" in ctx:  # our own checks name the parameter they're about (`params.fail`)
        param = ctx["param"]
    return {"code": code, "param": param, "message": message}
