"""Winter chill at points (`GET /chill`, D76) and the heat stress features (D77) on the fixture archive: July 1–10,
2025 at 15 °C ± 6, so some hours fall in Utah's best range and few are cold enough for chill hours."""

from datetime import date

import numpy as np
import pytest

from agdata import chillseason
from agdata.timezones import GRID_ZONE, day_bounds
from agmodels import chill, livestock
from agmodels.weather import relative_humidity_percent
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
DAYS = {"start": "2025-07-02", "end": "2025-07-08"}


def get(client, **params):
    return client.get("/api/v2/chill", {"lat": LAT, "lng": LNG, **params})


def hours_of(client, first: date, last: date) -> np.ndarray:
    """The point's hourly temperature (°C) over grid days first..last, as /weather/hourly gives it."""
    start, end = day_bounds(first, GRID_ZONE)[0], day_bounds(last, GRID_ZONE)[1]
    body = client.get(
        "/api/v2/weather/hourly",
        {
            "lat": LAT,
            "lng": LNG,
            "start": start.strftime("%Y-%m-%dT%H:%MZ"),
            "end": end.strftime("%Y-%m-%dT%H:%MZ"),
            "vars": "air_temperature",
            "units": "metric",
        },
    )
    return np.array(body.json()["data"]["air_temperature"], dtype=float)


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["dynamic", "utah", "hours"])
def test_each_method_totals_the_hours(client, archive, method):
    body = get(client, method=method, **DAYS).json()
    data = body["data"]
    assert data["date"][0] == "2025-07-02" and data["date"][-1] == "2025-07-08" and len(data["chill"]) == 7
    t = hours_of(client, date(2025, 7, 2), date(2025, 7, 8))
    expected = {
        "dynamic": chill.dynamic(t)[0].sum(),
        "utah": chill.utah_weights(t).sum(),
        "hours": float(((np.round(t, 2) >= 0) & (np.round(t, 2) <= 7.2)).sum()),
    }[method]
    assert data["chill_total"][-1] == pytest.approx(expected, abs=0.01)
    assert data["chill_total"][-1] == pytest.approx(sum(data["chill"]), abs=0.05)
    assert body["meta"]["units"]["chill"] == {"dynamic": "CP", "utah": "CU", "hours": "h"}[method]
    assert data["missing_hours"] == [0] * 7 and data["kind"] == ["observed"] * 7


@pytest.mark.django_db
def test_chill_hours_between_other_bounds_and_in_metric(client, archive):
    t = hours_of(client, date(2025, 7, 2), date(2025, 7, 8))
    us = get(client, method="hours", bounds="50,60", **DAYS).json()
    metric = get(client, method="hours", bounds="10,15.56", units="metric", **DAYS).json()
    expected = float(((np.round(t, 2) >= 10) & (np.round(t, 2) <= 15.56)).sum())
    assert us["data"]["chill_total"][-1] == expected == metric["data"]["chill_total"][-1] and expected > 0
    assert us["meta"]["request"]["bounds"] == [50, 60]


def test_the_default_start_is_the_october_1_before_the_end():
    assert chillseason.season_start(date(2025, 7, 8)) == date(2024, 10, 1)
    assert chillseason.season_start(date(2025, 10, 1)) == date(2025, 10, 1)
    assert chillseason.season_end(date(2025, 10, 1)) == date(2026, 9, 30)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("params", "param"),
    [
        ({"method": "utah", "bounds": "32,45"}, "bounds"),
        ({"method": "hours", "bounds": "45,32"}, "bounds"),
        ({"method": "hours", "bounds": "45"}, "bounds"),
        ({"method": "hours", "bounds": "32,500"}, "bounds"),
        ({"method": "portions"}, "method"),
        ({"start": "2025-07-08", "end": "2025-07-02"}, "start"),
        ({"start": "2020-01-01", "end": "2025-07-02"}, "start"),
    ],
)
def test_requests_chill_refuses(client, archive, params, param):
    response = get(client, **params)
    assert response.status_code == 422 and response.json()["errors"][0]["param"] == param


@pytest.mark.django_db
def test_heat_stress_and_chill_features_follow_their_hours(client, archive):
    names = "thi_max,thi_min,hours_thi_over_68,cci_max,chill_hours,utah_chill_units"
    body = client.get(
        "/api/v2/weather/daily",
        {"lat": LAT, "lng": LNG, "date": "2025-07-05", "vars": names, "units": "metric"},
    ).json()["data"]
    start, end = day_bounds(date(2025, 7, 5), GRID_ZONE)
    hourly = client.get(
        "/api/v2/weather/hourly",
        {
            "lat": LAT,
            "lng": LNG,
            "start": start.strftime("%Y-%m-%dT%H:%MZ"),
            "end": end.strftime("%Y-%m-%dT%H:%MZ"),
            "vars": "air_temperature,dew_point,relative_humidity,wind_speed,shortwave_radiation,thi",
            "units": "metric",
            "wind_speed": "m_s",  # metric shows km/h
        },
    ).json()["data"]
    t = np.array(hourly["air_temperature"])
    # The daily features take RH from temperature and dew point, as ingest makes the stored hourly RH (the fixture's
    # stored RH is a flat 75%, so hourly THI is checked against that)
    index = livestock.thi(t, relative_humidity_percent(t, np.array(hourly["dew_point"])))
    assert body["thi_max"][0] == pytest.approx(index.max(), abs=0.15)
    rh = relative_humidity_percent(t, np.array(hourly["dew_point"]))
    comfort = livestock.cci(t, rh, np.array(hourly["wind_speed"]), np.array(hourly["shortwave_radiation"]))
    assert body["cci_max"][0] == pytest.approx(comfort.max(), abs=0.15)
    assert body["thi_min"][0] == pytest.approx(index.min(), abs=0.15)
    assert body["hours_thi_over_68"][0] == int((index >= 68).sum())
    assert hourly["thi"] == pytest.approx(list(livestock.thi(t, np.array(hourly["relative_humidity"]))), abs=0.15)
    assert body["chill_hours"][0] == chill.chill_hours(t) and body["utah_chill_units"][0] == chill.utah_units(t)
