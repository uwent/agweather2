from collections.abc import Callable

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
