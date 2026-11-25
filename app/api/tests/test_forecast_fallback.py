"""Open-Meteo's forecast for points in the box while ours is stale (D114), on the fixture archive with its clock 14
hours past the run's cycle: observed to 15Z on July 10, 2025, and Open-Meteo's recorded answers for July 4-22 at the
point's cell (`fixtures/make_fallback_fixtures.py`) served for the forecast endpoint. No network."""

import json
from datetime import timedelta
from pathlib import Path

import pytest
import requests

from agdata.sources import openmeteo as source
from api import points
from api.tests.fixture_archive import CYCLE, NOW, POINT

LAT, LNG = POINT
STALE_NOW = CYCLE + timedelta(hours=14)  # 03Z July 11: the run is past MAX_RUN_AGE
FIXTURES = Path(__file__).parent / "fixtures"
pytestmark = pytest.mark.django_db  # the cell cache


@pytest.fixture
def stale(archive, settings, monkeypatch):
    """The fixture archive with its clock past the run's 12 hours, the fallback on, and Open-Meteo's answers from
    the recordings; the calls made are listed."""
    monkeypatch.setattr("api.clock.now", lambda: STALE_NOW)
    settings.OPEN_METEO_FALLBACK = True
    calls = []

    def get(session, address, params, timeout=None, tries=None, **_):  # `report=` too, after D115
        calls.append((address, params["models"], params["start_date"], params["end_date"]))
        return json.loads((FIXTURES / f"fallback_{params['models']}.json").read_text())

    monkeypatch.setattr(source, "_get", get)
    return calls


@pytest.fixture
def unreachable(stale, monkeypatch):
    """Open-Meteo refusing every connection, at once (no pause between tries)."""

    def get(session, address, params, timeout=None, tries=None, **_):  # `report=` too, after D115
        stale.append((address, params["models"]))
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(source, "_get", get)
    return stale


def daily(client, **params):
    return client.get("/api/v2/weather/daily", {"lat": LAT, "lng": LNG, "start": "2025-07-08", **params})


def test_a_stale_run_gives_way_to_open_meteo_for_a_point_in_the_box(client, stale):
    response = daily(client, end="2025-07-14")
    assert response.status_code == 200 and "ETag" not in response  # the cache refetches on a timer, as outside
    body = response.json()
    data, meta = body["data"], body["meta"]
    assert data["kind"] == ["observed", "observed", "partial", "forecast", "forecast", "forecast", "forecast"]
    assert all(v is not None for v in data["air_temperature_max"])
    assert meta["sources"] == ["urma", "openmeteo"]
    assert meta["warnings"] == [points.STALE_FALLBACK]
    assert not any(c.startswith("nbm") for c in meta["summary"]["corrections"])  # the run's aren't applied
    assert {model for _, model, *_ in stale} == {"ncep_nbm_conus", "best_match", "ecmwf_ifs"}
    assert {(first, last) for *_, first, last in stale} == {("2025-07-04", "2025-07-22")}  # the forecast span only
    asked = len(stale)
    daily(client, end="2025-07-14")
    assert len(stale) == asked  # the second request reads the cell cache


def test_the_fallbacks_observed_days_are_the_archives(client, stale, archive, monkeypatch, settings):
    settings.OPEN_METEO_FALLBACK = False
    before = daily(client, end="2025-07-09").json()["data"]
    settings.OPEN_METEO_FALLBACK = True
    after = daily(client, end="2025-07-09").json()["data"]
    assert before == after and stale == []  # days all observed: nothing asked of Open-Meteo


def test_with_the_fallback_off_a_stale_run_ends_the_series_as_before(client, stale, settings):
    settings.OPEN_METEO_FALLBACK = False
    response = daily(client, end="2025-07-14")
    body = response.json()
    assert body["data"]["kind"][-1] is None and body["data"]["air_temperature_max"][-1] is None
    assert body["meta"]["warnings"] == [points.STALE] and "ETag" in response and stale == []


def test_when_open_meteo_cannot_be_reached_the_series_ends_with_the_observed_days(client, unreachable):
    response = daily(client)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["date"][-1] == "2025-07-09"  # the last whole observed day
    assert body["meta"]["warnings"] == [points.STALE_UNAVAILABLE]
    assert body["meta"]["sources"] == ["urma"]


def test_after_one_failure_the_requests_other_points_do_not_wait_on_open_meteo(client, unreachable):
    other = (POINT[0] + 0.02, POINT[1] + 0.02)  # another cell of the box
    response = client.get(
        "/api/v2/weather/daily", {"points": f"{LAT},{LNG};{other[0]},{other[1]}", "start": "2025-07-08"}
    )
    assert response.status_code == 200
    assert len(unreachable) == 1  # the first point's first call; the second point's skipped (tries are inside _get)
    assert response.json()["meta"]["warnings"] == [points.STALE_UNAVAILABLE]


def test_a_projection_at_several_points_shares_one_budget_for_open_meteo(client, unreachable):
    """Each point of a projection ran on its own budget, so an unreachable Open-Meteo cost every point its own
    tries; the points share the request's (D114)."""
    other = (POINT[0] + 0.02, POINT[1] + 0.02)
    response = client.get(
        "/api/v2/models/early-blight-pdays/run",
        {"points": f"{LAT},{LNG};{other[0]},{other[1]}", "biofix": "2025-07-02", "projection": "true"},
    )
    assert response.status_code == 200, response.json()
    assert len(unreachable) == 1  # the first point's first call; the second point's skipped


def test_hourly_weather_runs_through_open_meteos_hours(client, stale):
    response = client.get(
        "/api/v2/weather/hourly",
        {"lat": LAT, "lng": LNG, "start": "2025-07-10T12:00Z", "end": "2025-07-11T12:00Z", "vars": "air_temperature"},
    )
    body = response.json()
    assert "ETag" not in response
    kinds = body["data"]["kind"]
    assert kinds[:4] == ["observed"] * 4 and set(kinds[4:]) == {"forecast"}  # 16Z on: the ingest lag included
    assert all(v is not None for v in body["data"]["air_temperature"])
    assert body["meta"]["sources"] == ["urma", "openmeteo"] and body["meta"]["warnings"] == [points.STALE_FALLBACK]


def test_degree_days_run_through_open_meteos_days(client, stale):
    body = client.get(
        "/api/v2/degree-days", {"lat": LAT, "lng": LNG, "dd": "sine_50", "start": "2025-07-07", "end": "2025-07-14"}
    ).json()
    assert body["data"]["kind"][-1] == "forecast" and body["data"]["dd_sine_50_cum"][-1] is not None
    assert body["meta"]["warnings"] == [points.STALE_FALLBACK]


def test_a_model_runs_on_open_meteos_forecast(client, stale):
    response = client.get(
        "/api/v2/models/early-blight-pdays/run",
        {"lat": LAT, "lng": LNG, "biofix": "2025-07-02", "end": "2025-07-14"},
    )
    assert response.status_code == 200 and "ETag" not in response
    body = response.json()
    assert body["data"]["kind"][-1] == "forecast" and body["data"]["pdays"][-1] is not None
    assert points.STALE_FALLBACK in body["meta"]["warnings"]
    assert "openmeteo" in body["meta"]["sources"]


def test_a_fresh_run_never_asks_open_meteo(client, archive, settings, monkeypatch):
    settings.OPEN_METEO_FALLBACK = True
    monkeypatch.setattr(source, "_get", lambda *a, **k: pytest.fail("asked Open-Meteo with a fresh run"))
    assert archive and CYCLE + timedelta(hours=12) > NOW
    body = daily(client, end="2025-07-14").json()
    assert body["meta"]["sources"] == ["urma", "nbm"] and body["meta"]["warnings"] == []


def test_status_says_points_use_open_meteo(client, stale):
    forecast = client.get("/api/v2/status").json()["data"]["forecast"]
    assert forecast["reason"] == "stale" and forecast["fallback"] == "openmeteo"


def test_forecast_warnings_say_once_what_each_series_forecast_was():
    from agdata.series import Forecast

    fallback = Forecast(path=None, reason="stale", fallback="openmeteo")
    down = Forecast(path=None, reason="stale", fallback="unavailable")
    soil = Forecast(path=Path("run"), soil_unavailable=True)
    found = points.forecast_warnings([fallback, fallback, down, soil, None], forecast_asked=True)
    assert found == [points.STALE_FALLBACK, points.STALE_UNAVAILABLE, points.SOIL_UNAVAILABLE]
    assert points.forecast_warnings([fallback], forecast_asked=False) == []
