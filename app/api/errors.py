"""Errors as the API reports them (docs/api.md, "The envelope"): `{meta, errors: [{code, param, message}]}` with a
4xx or 5xx status, in place of Ninja's `{"detail": …}`. `install(api)` registers a handler for each kind."""

import logging
from datetime import UTC, date, datetime
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError
from ninja.errors import ValidationError as NinjaValidationError


def day_text(day: date) -> str:
    """A date as public text says it: "July 8, 2025"."""
    return f"{day:%B} {day.day}, {day.year}"


def counted(n: int, noun: str) -> str:
    """ "1 day", "3 days", "1,200 grid cells" (`noun` singular; an s for more than one)."""
    return f"{n:,} {noun}" if n == 1 else f"{n:,} {noun}s"


def hour_text(when: datetime) -> str:
    """A UTC hour as public text says it: "3 p.m. UTC, July 8, 2025" (midnight and noon by name)."""
    when = when.astimezone(UTC)
    if not when.minute and when.hour in (0, 12):
        clock = "midnight" if when.hour == 0 else "noon"
    else:
        minutes = f":{when.minute:02d}" if when.minute else ""
        clock = f"{when.hour % 12 or 12}{minutes} {'a.m.' if when.hour < 12 else 'p.m.'}"
    return f"{clock} UTC, {day_text(when.date())}"


class ApiError(Exception):
    """A request the API can't answer as asked: `code` is a stable machine name (`out_of_range`, `unknown_variable`),
    `param` the query parameter at fault, if one is."""

    def __init__(self, code: str, message: str, param: str | None = None, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.param, self.status = code, message, param, status

    def item(self) -> dict[str, Any]:
        return {"code": self.code, "param": self.param, "message": self.message}


INTERNAL_ERROR = (
    "Something went wrong on our side while answering this request. We've recorded the problem; please try again "
    "later, and contact us if it continues."
)
# Points outside the service box, or before the archive, are read from Open-Meteo in the request
OPEN_METEO_DOWN = (
    "We couldn't reach Open-Meteo, which supplies the weather for this location (outside our area or before our "
    "records begin). Please try again in a few minutes."
)


def install(api: NinjaAPI) -> None:
    from api import envelope  # which raises ApiError
    from ops import openmeteo

    @api.exception_handler(ApiError)
    def api_error(request: HttpRequest, exc: ApiError) -> HttpResponse:
        return envelope.error_response(request, [exc.item()], status=exc.status)

    @api.exception_handler(NinjaValidationError)
    def invalid(request: HttpRequest, exc: NinjaValidationError) -> HttpResponse:
        return envelope.error_response(request, [_validation_item(e) for e in exc.errors], status=422)

    @api.exception_handler(Http404)
    def not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
        message = str(exc) or f"There's nothing at {request.path}. The API's endpoints are listed at /api/v2/docs."
        return envelope.error_response(request, [{"code": "not_found", "param": None, "message": message}], 404)

    @api.exception_handler(HttpError)
    def http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        item = {"code": _CODES.get(exc.status_code, "error"), "param": None, "message": exc.message}
        return envelope.error_response(request, [item], status=exc.status_code)

    @api.exception_handler(AuthenticationError)
    def unauthorized(request: HttpRequest, exc: AuthenticationError) -> HttpResponse:
        item = {"code": "unauthorized", "param": None, "message": "This request needs you to sign in."}
        return envelope.error_response(request, [item], status=401)

    @api.exception_handler(openmeteo.Unavailable)
    def weather_unavailable(request: HttpRequest, exc: openmeteo.Unavailable) -> HttpResponse:
        logging.getLogger(__name__).warning("Open-Meteo unavailable at %s: %s", request.path, exc)
        item = {"code": "weather_unavailable", "param": None, "message": OPEN_METEO_DOWN}
        response = envelope.error_response(request, [item], status=503)
        response["Retry-After"] = "300"
        return response

    @api.exception_handler(Exception)
    def unexpected(request: HttpRequest, exc: Exception) -> HttpResponse:
        # Logged with the traceback, as Django logs an unhandled error; the client gets the envelope without internals
        logging.getLogger("django.request").error("API error at %s", request.path, exc_info=exc)
        item = {"code": "internal_error", "param": None, "message": INTERNAL_ERROR}
        return envelope.error_response(request, [item], status=500)


# Pydantic's checks of a value's type, as public text says them
_TYPES = {
    "float_parsing": "must be a number",
    "float_type": "must be a number",
    "int_parsing": "must be a whole number",
    "int_type": "must be a whole number",
    "int_from_float": "must be a whole number",
    "bool_parsing": "must be true or false",
    "date_parsing": "must be a date, as YYYY-MM-DD",
    "date_from_datetime_parsing": "must be a date, as YYYY-MM-DD",
    "datetime_parsing": "must be a time, as 2025-07-08T15:00Z",
    "datetime_from_date_parsing": "must be a time, as 2025-07-08T15:00Z",
    "missing": "is required",
}


def _pydantic_message(param: str | None, code: str, message: str) -> str:
    """Pydantic's own message for a value of the wrong type ("Input should be a valid number…") as a sentence that
    names the parameter."""
    named = f"The value of {param}" if param else "A value"
    if code in _TYPES:
        return f"{named} {_TYPES[code]}."
    text = message[0].lower() + message[1:] if message else "isn't valid"
    text = text.removeprefix("input ").removeprefix("value ")
    return f"{named} {text.rstrip('.')}."


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
    if code not in ("value_error", "assertion_error") and "param" not in (error.get("ctx") or {}):
        message = _pydantic_message(param, code, message)
    if code in ("value_error", "assertion_error"):
        code = "invalid"
    ctx = error.get("ctx") or {}
    if "param" in ctx:  # our own checks name the parameter they're about (`params.fail`)
        param = ctx["param"]
    return {"code": code, "param": param, "message": message}
