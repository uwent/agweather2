"""Marks when a request arrived, for the API's `compute_ms` and `Server-Timing` (`api.envelope`), and the thread
running it, for the stack `api.timelimit` logs when it runs past the limit."""

import threading
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class TimingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.api_started = time.perf_counter()  # pyright: ignore[reportAttributeAccessIssue]
        request.api_thread = threading.get_ident()  # pyright: ignore[reportAttributeAccessIssue]
        return self.get_response(request)
