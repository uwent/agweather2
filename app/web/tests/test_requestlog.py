"""The development request log (`web.requestlog`) and the API root's redirect."""

import asyncio
import logging

from django.http import HttpResponse
from django.test import RequestFactory

from web import requestlog


def test_a_request_is_one_line_with_its_status_and_time():
    request = RequestFactory().get("/api/v2/status", {"lat": "43"})
    assert requestlog.line(request, 200, 61.4) == "GET /api/v2/status?lat=43 200 OK in 61 ms"
    assert requestlog.line(request, 404, 2.25) == "GET /api/v2/status?lat=43 404 Not Found in 2.2 ms"
    long = RequestFactory().get("/api/v2/weather/daily", {"points": "43,-89;" * 60})
    assert len(requestlog.line(long, 200, 5).split(" ")[1]) == requestlog.LONGEST_PATH


def test_the_middleware_logs_each_request_when_on(settings, caplog):
    settings.REQUEST_LOG = True
    caplog.set_level(logging.INFO, logger="agweather.requests")

    async def answer(request):
        return HttpResponse(status=201)

    response = asyncio.run(requestlog.RequestLogMiddleware(answer)(RequestFactory().post("/sites")))
    assert response.status_code == 201
    assert [r.getMessage().split(" in ")[0] for r in caplog.records] == ["POST /sites 201 Created"]


def test_the_api_root_redirects_to_its_docs(client):
    response = client.get("/api/v2/")
    assert response.status_code == 302 and response["Location"] == "/api/v2/docs"
    assert client.get("/api/v2/docs").status_code == 200
    assert client.get("/api/v2/nothing-here").json()["errors"][0]["code"] == "not_found"
