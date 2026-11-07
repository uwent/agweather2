"""Weather at points (PLAN.md Phase 5 C) on the fixture archive: observed July 1–10 2025 at 15 °C ± 6 and 0.1 mm an
hour, then an NBM run at 25 °C ± 6 to July 21 13Z."""

from datetime import date, timedelta

import numpy as np
import pytest
import requests

from agdata.grid import NDFD
from agdata.series import DailySeries, Forecast
from api import points
from api.routes import weather
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
OTHER = tuple(round(float(v), 4) for v in NDFD.latlon(901, 1402))
DULUTH = (46.79, -92.1)  # on the grid, outside the test box


def get(client, path, http_headers=None, **params):
    return client.get(f"/api/v2/{path}", {"lat": LAT, "lng": LNG, **params}, headers=http_headers)


def test_daily_weather_runs_through_the_forecast_with_each_days_kind(client, archive):
    body = get(client, "weather/daily", start="2025-07-08", end="2025-07-12").json()
    data = body["data"]
    assert data["date"] == ["2025-07-08", "2025-07-09", "2025-07-10", "2025-07-11", "2025-07-12"]
    assert data["kind"] == ["observed", "observed", "partial", "forecast", "forecast"]
    assert data["air_temperature_max"][0] == 69.8 and data["air_temperature_max"][-1] == 87.8  # 21 and 31 °C
    assert data["precipitation_sum"][0] == 0.0945  # 2.4 mm
    assert body["meta"]["sources"] == ["urma", "nbm"]
    assert body["meta"]["summary"]["days_forecast"] == 3 and body["meta"]["summary"]["days_requested"] == 5
    assert "nbm-max v1" in body["meta"]["summary"]["corrections"]


def test_a_default_end_stops_at_the_forecasts_last_day_and_forecast_false_at_the_last_observed(client, archive):
    body = get(client, "weather/daily", start="2025-07-08").json()
    assert body["data"]["date"][-1] == "2025-07-20"  # July 21 isn't whole: the run ends at 13Z
    assert body["meta"]["request"]["end"] == "2025-07-20"
    body = get(client, "weather/daily", start="2025-07-08", forecast="false").json()
    assert body["data"]["date"] == ["2025-07-08", "2025-07-09"] and body["meta"]["request"]["forecast"] is False


def test_daily_weather_at_several_points_is_one_long_table(client, archive):
    response = client.get(
        "/api/v2/weather/daily",
        {"points": f"{LAT},{LNG};{OTHER[0]},{OTHER[1]}", "start": "2025-07-08", "end": "2025-07-09"},
    )
    data = response.json()["data"]
    assert data["point"] == [0, 0, 1, 1] and data["date"] == ["2025-07-08", "2025-07-09"] * 2
    assert len(response.json()["meta"]["locations"]) == 2


def test_archive_answers_revalidate_to_a_304(client, archive):
    response = get(client, "weather/daily", start="2025-07-08", end="2025-07-09")
    etag = response["ETag"]
    again = get(client, "weather/daily", start="2025-07-08", end="2025-07-09", http_headers={"If-None-Match": etag})
    assert again.status_code == 304


def _open_meteo_days(lat, lng, first, last, names, now, zone=None):
    n = (last - first).days + 1
    return DailySeries(
        dates=[first + timedelta(days=k) for k in range(n)],
        values={name: np.full(n, 10.0) for name in names},
        kinds=["observed"] * n,
        forecast=Forecast(path=None, reason="openmeteo"),
        zone="America/Chicago",
    )


def test_a_point_outside_the_box_reads_open_meteo_and_has_no_etag(client, archive, monkeypatch):
    monkeypatch.setattr(points.openmeteo, "point_days", _open_meteo_days)
    response = client.get(
        "/api/v2/weather/daily", {"lat": DULUTH[0], "lng": DULUTH[1], "start": "2025-07-08", "end": "2025-07-09"}
    )
    body = response.json()
    assert body["meta"]["sources"] == ["openmeteo"] and body["meta"]["location"]["in_box"] is False
    assert body["data"]["air_temperature_max"] == [50.0, 50.0]
    assert "ETag" not in response  # computed each time from the cache


def test_points_inside_and_outside_the_box_keep_their_order(client, archive, monkeypatch):
    monkeypatch.setattr(points.openmeteo, "point_days", _open_meteo_days)
    asked = f"{LAT},{LNG};{DULUTH[0]},{DULUTH[1]};{OTHER[0]},{OTHER[1]}"
    body = client.get("/api/v2/weather/daily", {"points": asked, "start": "2025-07-08", "end": "2025-07-09"}).json()
    data = body["data"]
    assert data["point"] == [0, 0, 1, 1, 2, 2]
    assert data["air_temperature_max"][2:4] == [50.0, 50.0]  # Open-Meteo's, in its place
    assert data["air_temperature_max"][:2] == data["air_temperature_max"][4:] == [69.8, 69.8]  # the archive's
    assert [loc["in_box"] for loc in body["meta"]["locations"]] == [True, False, True]


@pytest.mark.django_db
def test_open_meteo_unreachable_is_a_503_that_says_so(client, archive, monkeypatch):
    def down(*args, **kwargs):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr("agdata.sources.openmeteo.fetch", down)
    response = client.get(
        "/api/v2/weather/daily", {"lat": DULUTH[0], "lng": DULUTH[1], "start": "2025-07-08", "end": "2025-07-09"}
    )
    assert response.status_code == 503 and response["Retry-After"] == "300"
    error = response.json()["errors"][0]
    assert error["code"] == "weather_unavailable" and "Open-Meteo" in error["message"]


def test_points_outside_the_archive_are_capped(client, archive, monkeypatch):
    monkeypatch.setattr(points.openmeteo, "point_days", _open_meteo_days)
    many = ";".join(f"{45 + k / 10},-92.1" for k in range(weather.MAX_OUTSIDE + 1))
    response = client.get("/api/v2/weather/daily", {"points": many, "start": "2025-07-08", "end": "2025-07-09"})
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "too_many"


def test_too_many_days_is_refused(client, archive):
    response = get(client, "weather/daily", start="2010-01-01", end="2025-07-09")
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "too_large"


def test_hourly_weather_with_local_times(client, archive):
    body = get(
        client, "weather/hourly", start="2025-07-10T14:00Z", end="2025-07-10T16:00Z", vars="air_temperature", tz="local"
    ).json()
    data = body["data"]
    assert data["time"] == ["2025-07-10T14:00Z", "2025-07-10T15:00Z", "2025-07-10T16:00Z"]
    assert data["local_time"] == ["2025-07-10T09:00-05:00", "2025-07-10T10:00-05:00", "2025-07-10T11:00-05:00"]
    assert data["kind"] == ["observed", "observed", "forecast"]
    assert body["meta"]["units"] == {"air_temperature": "°F"}
    assert body["meta"]["summary"]["hours_forecast"] == 1


def test_hours_must_be_on_the_hour_and_a_zone_is_honoured(client, archive):
    response = get(client, "weather/hourly", start="2025-07-10T14:30Z", end="2025-07-10T16:00Z")
    assert response.status_code == 422 and response.json()["errors"][0]["param"] == "start"
    body = get(client, "weather/hourly", start="2025-07-10T09:00-05:00", end="2025-07-10T09:00-05:00").json()
    assert body["data"]["time"] == ["2025-07-10T14:00Z"] and body["meta"]["request"]["start"] == "2025-07-10T14:00Z"


def test_totals_over_a_window(client, archive):
    body = get(client, "weather/totals", start="2025-07-02", end="2025-07-09", vars="precipitation_sum,et0_sum").json()
    data = body["data"]
    assert data["days"] == [8] and data["forecast_days"] == [0]
    assert data["precipitation_sum"] == [0.7559]  # 8 days × 2.4 mm = 19.2 mm
    assert data["precipitation_sum_missing_days"] == [0] and data["et0_sum_estimated_days"] == [0]
    assert body["meta"]["units"]["precipitation_sum"] == "in"
    response = get(client, "weather/totals", vars="air_temperature_max")
    assert response.status_code == 422 and "precipitation_sum" in response.json()["errors"][0]["message"]


def test_a_window_total_estimates_short_gaps_but_never_rain():
    et0 = np.array([2.0, np.nan, np.nan, 4.0, np.nan])
    assert weather.window_total(et0, "et0_sum", "estimate") == (12.0, 2, 1)  # 2 + 2.67 + 3.33 + 4; the end stays
    assert weather.window_total(et0, "et0_sum", "missing") == (6.0, 0, 3)
    rain = np.array([1.0, np.nan, 2.0])
    assert weather.window_total(rain, "precipitation_sum", "estimate") == (3.0, 0, 1)  # missing counted as none
    total, _, missing = weather.window_total(np.full(3, np.nan), "precipitation_sum", "estimate")
    assert np.isnan(total) and missing == 3


@pytest.mark.parametrize("path", ["weather/daily", "weather/totals", "degree-days?dd=sine_50", "freeze"])
def test_every_point_endpoint_offers_csv(client, archive, path):
    base, _, query = path.partition("?")
    params = dict(p.split("=") for p in query.split("&") if p)
    response = get(client, base, start="2025-07-08", end="2025-07-09", format="csv", **params)
    assert response.status_code == 200 and response["Content-Type"].startswith("text/csv")


def test_default_dates_start_on_january_1(client, archive):
    body = get(client, "weather/daily", forecast="false").json()
    assert body["meta"]["request"]["start"] == "2025-01-01"
    # The fixture's hours begin July 1: earlier days are the archive's (its year's store exists) but missing, not 0
    assert body["data"]["kind"][0] == "observed" and body["data"]["air_temperature_max"][0] is None
    assert body["meta"]["summary"]["missing"]["air_temperature_max"] == 181
    assert date.fromisoformat(body["data"]["date"][-1]) == date(2025, 7, 9)


def test_day_basis_says_whose_clock_makes_the_days(client, archive):
    central = get(client, "weather/daily", start="2025-07-08", end="2025-07-09")
    local = get(client, "weather/daily", start="2025-07-08", end="2025-07-09", day_basis="local")
    # Inside the box a point takes the grid's days by default, so it agrees with its map (D74)
    where = central.json()["meta"]["location"]
    assert where["day_basis"] == "central" and where["days"].startswith("Midnight to midnight CST all year")
    assert "day_basis" not in central.json()["meta"]["request"]
    where = local.json()["meta"]["location"]
    assert where["day_basis"] == "local" and "CDT (05:00 to 05:00 UTC) in daylight time" in where["days"]
    assert local.json()["meta"]["request"]["day_basis"] == "local" and local["ETag"] != central["ETag"]

    def error(path, **params):
        return get(client, path, **params).json()["errors"][0]

    assert error("weather/hourly", day_basis="central")["code"] == "not_applicable"  # hours aren't days
    assert error("weather/daily", day_basis="solar")["param"] == "day_basis"
    # Maps use grid days everywhere: central is accepted and local refused, saying why
    tilejson = client.get("/api/v2/tiles/air_temperature_max.json", {"day_basis": "central"})
    assert tilejson.status_code == 200
    refused = client.get("/api/v2/tiles/air_temperature_max.json", {"day_basis": "local"}).json()["errors"][0]
    assert refused["code"] == "not_applicable" and "Central Standard Time" in refused["message"]


def test_a_point_outside_the_box_takes_its_own_days(client, archive, monkeypatch):
    monkeypatch.setattr(points.openmeteo, "point_days", _open_meteo_days)
    body = client.get("/api/v2/weather/daily", {"lat": DULUTH[0], "lng": DULUTH[1], "start": "2025-07-08"}).json()
    assert body["meta"]["location"]["day_basis"] == "local" and body["meta"]["location"]["days"].startswith(
        "Midnight to midnight local time: CST (06:00 to 06:00 UTC)"
    )


def test_water_balance_is_rain_less_et0_on_each_day(client, archive):
    names = "water_balance,precipitation_sum,et0_sum"
    body = get(client, "weather/daily", start="2025-07-08", end="2025-07-12", vars=names, units="metric").json()
    data = body["data"]
    for balance, rain, et0 in zip(data["water_balance"], data["precipitation_sum"], data["et0_sum"], strict=True):
        assert balance == pytest.approx(rain - et0, abs=0.02)  # each column rounded to its own precision
    assert data["water_balance"][0] == 0.0  # the archive's 2.4 mm of rain and of ET0
    assert body["meta"]["units"]["water_balance"] == "mm"
    alone = get(client, "weather/daily", start="2025-07-08", end="2025-07-12", vars="water_balance").json()
    assert list(alone["data"]) == ["date", "kind", "water_balance"] and alone["meta"]["units"]["water_balance"] == "in"


def test_a_water_balance_total_sums_the_days_it_has_and_counts_the_rest(client, archive):
    window = {"start": "2025-07-08", "end": "2025-07-23", "units": "metric"}  # the run's hours end July 21 13Z
    daily = get(client, "weather/daily", vars="water_balance", **window).json()["data"]["water_balance"]
    body = get(client, "weather/totals", vars="water_balance", **window).json()
    known = [v for v in daily if v is not None]
    missing = 16 - len(known)
    assert missing > 0 and body["data"]["water_balance"] == [pytest.approx(sum(known), abs=0.05)]
    assert body["data"]["water_balance_missing_days"] == [missing]
    assert body["data"]["water_balance_estimated_days"] == [0]  # never estimated (D75)
    assert any(w.startswith(f"Water balance is missing on {missing} days") for w in body["meta"]["warnings"])
