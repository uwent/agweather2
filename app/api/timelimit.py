"""A time limit on API requests (Phase 6, step 1): an answer by `API_TIME_LIMIT` seconds, whatever the request.

Nothing else bounds a request: uvicorn has no request timeout, and Caddy's (`infra/Caddyfile`) is only the outer
bound. Some requests have hung without ever answering (2026-11-07), and a client waiting forever learns nothing.

Views are sync, so Django runs them on a thread, and a thread can't be stopped. Cancelling the await doesn't help
either: asgiref's `sync_to_async`, cancelled, waits for its thread to finish before it gives up, so a plain
`asyncio.wait_for` would answer only when the hang ended. Instead the rest of the chain runs as a task of its own;
past the limit the client gets a 503 `timeout` envelope at once, and the task is left to finish in the background
with its answer dropped. What it holds is safe to leave: API code never takes the archive's write lock, and the map
caches' locks are held only around dictionary updates. The rate limit sits inside, so the client is still charged
the request's whole time when it finishes.

To find a hang, the log gets the request's path and query and the stack of the thread running it at the moment the
limit passed (`TimingMiddleware` records which thread that is), then the total time once it finishes.
"""

import asyncio
import logging
import sys
import time
import traceback
from collections.abc import Awaitable, Callable

from asgiref.sync import markcoroutinefunction
from django.conf import settings
from django.http import HttpRequest, HttpResponse

from api import envelope

logger = logging.getLogger(__name__)

RETRY_AFTER_SECONDS = 120
# Frames of Django's middleware plumbing, left out of the logged stack (each middleware adds two)
_PLUMBING = ("django/core/handlers/", "django/utils/deprecation.py")
# Requests answered with a timeout whose work is still running: kept so the tasks aren't collected, and counted in
# the log so a pile-up shows
_overrunning: set[asyncio.Task] = set()


def overrunning() -> int:
    """How many requests past the limit are still running."""
    return len(_overrunning)


def message(limit: float) -> str:
    seconds = f"{limit:g} seconds" if limit != 1 else "1 second"
    return (
        f"This request took longer than {seconds}, so we stopped waiting for it. Please try again in a few minutes; "
        "a request for a smaller area or a shorter period may help."
    )


class TimeLimitMiddleware:
    """First in `MIDDLEWARE`: an API request still running after `API_TIME_LIMIT` seconds is answered with a 503
    (None turns the limit off, as it is under pytest unless a test sets it). Async only: production runs under ASGI."""

    async_capable = True
    sync_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], Awaitable[HttpResponse]]):
        self.get_response = get_response
        markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        limit = settings.API_TIME_LIMIT
        if limit is None or not request.path.startswith("/api/"):
            return await self.get_response(request)
        started = time.perf_counter()
        task = asyncio.ensure_future(self.get_response(request))
        try:
            done, _ = await asyncio.wait({task}, timeout=limit)
        except asyncio.CancelledError:  # the client went away
            task.cancel()
            raise
        if done:
            return task.result()
        _overran(request, task, started, limit)
        response = envelope.error_response(
            request, [{"code": "timeout", "param": None, "message": message(limit)}], status=503
        )
        response["Retry-After"] = str(RETRY_AFTER_SECONDS)
        return response


def _overran(request: HttpRequest, task: asyncio.Task, started: float, limit: float) -> None:
    """Log where the request is stuck, and again when it finishes."""
    where = request.get_full_path()
    ident = getattr(request, "api_thread", None)
    frame = sys._current_frames().get(ident) if ident is not None else None
    frames = traceback.format_stack(frame) if frame is not None else ["(the thread isn't known)\n"]
    stack = "".join(f for f in frames if not any(part in f for part in _PLUMBING))
    _overrunning.add(task)
    logger.warning(
        "API request over its %gs limit, answered with a timeout (%d now running past the limit): %s\n"
        "Its thread is at:\n%s",
        limit,
        len(_overrunning),
        where,
        stack.rstrip(),
    )

    def finished(task: asyncio.Task) -> None:
        _overrunning.discard(task)
        seconds = time.perf_counter() - started
        if task.cancelled():
            logger.warning("API request past its limit was cancelled after %.1fs: %s", seconds, where)
            return
        failure = task.exception()
        if failure is not None:
            logger.warning("API request past its limit failed after %.1fs: %s", seconds, where, exc_info=failure)
        else:
            logger.warning("API request past its limit finished after %.1fs: %s", seconds, where)

    task.add_done_callback(finished)
