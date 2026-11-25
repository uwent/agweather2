from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import inertia.middleware
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from inertia import always, share

from agdata.timezones import GRID_ZONE
from web.inertia import pop_errors
from web.props import AppInfo, SharedProps
from web.status import data_status


def grid_today() -> date:
    """Today on the grid's clock: days run midnight to midnight CST all year (D74), so a page's "today" is the
    archive's, not the server's or the reader's."""
    return datetime.now(UTC).astimezone(ZoneInfo(GRID_ZONE)).date()


class SharedPropsMiddleware:
    """Shares `SharedProps` and the last form's `errors` with every Inertia page."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        shared = SharedProps(
            app=AppInfo(version=settings.APP_VERSION, service_box=settings.SERVICE_BOX), today=grid_today(), status=None
        )
        share(
            request,
            **shared.model_dump(mode="json", exclude={"status"}),
            # Read only when a page renders (inertia-django calls a callable prop), and kept a few seconds (web.status)
            status=_status_json,
            errors=always(lambda: pop_errors(request)),
        )
        return self.get_response(request)


def _status_json() -> dict | None:
    found = data_status()
    return None if found is None else found.model_dump(mode="json")


class InertiaMiddleware(inertia.middleware.InertiaMiddleware):
    """inertia-django's middleware, except for the public API: it sets a CSRF cookie and `Vary: Cookie` on every
    response, which would stop shared caches (Caddy, Phase 5 G) storing API answers that depend on neither."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/api/"):
            return self.get_response(request)
        return super().__call__(request)
