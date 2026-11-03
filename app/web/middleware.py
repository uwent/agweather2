from collections.abc import Callable

import inertia.middleware
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from inertia import always, share

from web.inertia import pop_errors
from web.props import AppInfo, SharedProps


class SharedPropsMiddleware:
    """Shares `SharedProps` and the last form's `errors` with every Inertia page."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        shared = SharedProps(app=AppInfo(version=settings.APP_VERSION, service_box=settings.SERVICE_BOX))
        share(request, **shared.model_dump(mode="json"), errors=always(lambda: pop_errors(request)))
        return self.get_response(request)


class InertiaMiddleware(inertia.middleware.InertiaMiddleware):
    """inertia-django's middleware, except for the public API: it sets a CSRF cookie and `Vary: Cookie` on every
    response, which would stop shared caches (Caddy, PLAN.md Phase 5 G) storing API answers that depend on neither."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/api/"):
            return self.get_response(request)
        return super().__call__(request)
