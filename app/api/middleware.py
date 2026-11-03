"""Marks when a request arrived, for the API's `compute_ms` and `Server-Timing` (`api.envelope`)."""

import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class TimingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.api_started = time.perf_counter()  # pyright: ignore[reportAttributeAccessIssue]
        return self.get_response(request)
