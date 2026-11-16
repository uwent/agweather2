"""The time limit on API requests (`api.timelimit`): past it, a 503 envelope at once, and the stuck thread's stack in
the log."""

import asyncio
import logging
import time
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test.client import AsyncClient

from api import timelimit

pytestmark = pytest.mark.urls("api.tests.routes")


def _get(path: str, settings, limit: float) -> tuple[float, Any]:
    """The response to an async GET (as under uvicorn) with a time limit, and the seconds it took to arrive. A first
    request without the limit warms the process (its first request imports the routes), and the event loop then
    waits for a request past the limit to finish, as a server's would."""

    async def go():
        await AsyncClient().get("/api/test/sleep")
        settings.API_TIME_LIMIT = limit
        started = time.perf_counter()
        response = await AsyncClient().get(path)
        seconds = time.perf_counter() - started
        for _ in range(100):
            if not timelimit.overrunning():
                break
            await asyncio.sleep(0.05)
        return seconds, response

    return asyncio.run(go())


def test_a_request_past_the_limit_is_answered_at_once_and_its_stack_logged(settings, caplog):
    caplog.set_level(logging.WARNING, logger="api.timelimit")
    seconds, response = _get("/api/test/sleep?seconds=1.5", settings, limit=0.2)
    assert seconds < 1.0  # not when the sleep ends
    assert response.status_code == 503
    assert response["Retry-After"] == str(timelimit.RETRY_AFTER_SECONDS)
    assert response["Cache-Control"] == "no-store"
    body = response.json()
    assert body["errors"] == [{"code": "timeout", "param": None, "message": timelimit.message(0.2)}]
    assert body["meta"]["request"] == {"seconds": "1.5"}
    over, finished = (r.getMessage() for r in caplog.records if r.name == "api.timelimit")
    assert "over its 0.2s limit" in over and "/api/test/sleep?seconds=1.5" in over
    assert "in sleep" in over and "time.sleep(seconds)" in over  # where the thread is stuck
    assert "deprecation.py" not in over  # without Django's middleware plumbing
    assert "finished after 1." in finished
    assert timelimit.overrunning() == 0


def test_a_request_within_the_limit_is_untouched(settings, caplog):
    _, response = _get("/api/test/sleep?seconds=0.05", settings, limit=5)
    assert response.status_code == 200
    assert response.json()["data"] == {"slept": 0.05}
    assert not caplog.records


def test_the_limit_is_off_under_tests_and_leaves_other_paths_alone(settings):
    assert settings.API_TIME_LIMIT is None
    settings.API_TIME_LIMIT = 0.05
    request = HttpRequest()
    request.path = "/admin/"

    async def slow(request: HttpRequest) -> HttpResponse:
        await asyncio.sleep(0.2)
        return HttpResponse("answered")

    assert asyncio.run(timelimit.TimeLimitMiddleware(slow)(request)).content == b"answered"


def test_the_message_reads_as_public_text():
    assert timelimit.message(30).startswith("This request took longer than 30 seconds, so we stopped waiting for it.")
    assert "1 second," in timelimit.message(1)
