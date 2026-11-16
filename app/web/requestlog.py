"""One line per request in the development log, as Rails writes it: "GET /api/v2/status 200 OK in 12 ms".

uvicorn's access log has no timing, so `bin/dev` turns it off (`--no-access-log` in `Procfile.dev`) and this takes its
place. On by default in development only (`REQUEST_LOG`); production's requests are timed by Caddy's log and the
API's `Server-Timing` header. Static files never reach Django's middleware, so they aren't logged.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from http import HTTPStatus

from asgiref.sync import markcoroutinefunction
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("agweather.requests")
LONGEST_PATH = 200  # characters of the path and query shown; a long query is cut with an ellipsis


class RequestLogMiddleware:
    """First in `MIDDLEWARE`, so its time covers everything Django does with the request."""

    async_capable = True
    sync_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], Awaitable[HttpResponse]]):
        if not settings.REQUEST_LOG:
            raise MiddlewareNotUsed
        self.get_response = get_response
        markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        started = time.perf_counter()
        response = await self.get_response(request)
        logger.info(line(request, response.status_code, (time.perf_counter() - started) * 1000))
        return response


def line(request: HttpRequest, status: int, ms: float) -> str:
    where = request.get_full_path()
    if len(where) > LONGEST_PATH:
        where = where[: LONGEST_PATH - 1] + "…"
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = ""
    took = f"{ms:.0f} ms" if ms >= 10 else f"{ms:.1f} ms"
    return f"{request.method} {where} {status} {phrase} in {took}".replace("  ", " ")
