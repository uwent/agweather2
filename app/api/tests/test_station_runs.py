"""Models on weather sent with the request (PLAN.md Phase 5 D step 5, D58), on the fixture archive: observed hours
July 1–10, 2025 (to 15Z on the 10th), then the forecast."""

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from agdata import series
from api.tests.fixture_archive import CELL, NOW, POINT

LAT, LNG = POINT
HOUR = timedelta(hours=1)
FIRST = datetime(2025, 7, 1, 6, tzinfo=UTC)  # 1 am CDT, the first local day's first hour (hour ending)
LAST = datetime(2025, 7, 10, 5, tzinfo=UTC)  # midnight CDT, closing July 9


def archive_hours(archive, names, first=FIRST, last=LAST) -> dict:
    """The archive's hours at the fixture cell, as a station would send them (metric)."""
    frame = series.point_hours(archive, *CELL, first, last, names, now=NOW)
    block: dict = {"time": [t.strftime("%Y-%m-%dT%H:%MZ") for t in frame.times]}
    for name in names:
        block[name] = [None if not np.isfinite(v) else round(float(v), 3) for v in frame.values[name]]
    return block


def post(client, path, body, **query):
    url = f"/api/v2/{path}" + ("?" + "&".join(f"{k}={v}" for k, v in query.items()) if query else "")
    return client.post(url, json.dumps(body), content_type="application/json")


def body_for(hourly=None, daily=None, **rest):
    return {"location": {"lat": LAT, "lng": LNG}, "units": "metric", "hourly": hourly, "daily": daily, **rest}


def test_a_stations_hours_give_what_the_archive_gives(client, archive):
    hourly = archive_hours(archive, ["air_temperature"])
    sent = post(
        client,
        "models/early-blight-pdays/run",
        body_for(hourly=hourly, start="2025-07-02", end="2025-07-09", options={"biofix": "2025-07-02"}),
    ).json()
    ours = client.get(
        "/api/v2/models/early-blight-pdays/run",
        {"lat": LAT, "lng": LNG, "start": "2025-07-02", "end": "2025-07-09", "biofix": "2025-07-02", "units": "metric"},
    ).json()
    assert sent["data"]["pdays_total"] == pytest.approx(ours["data"]["pdays_total"], abs=0.01)
    assert sent["data"]["kind"] == ["provided"] * 8
    assert sent["meta"]["summary"]["days_provided"] == 8 and sent["meta"]["sources"] == ["provided"]
    assert sent["meta"]["units"]["air_temperature_min"] == "°C"  # the body's units


def test_rh_without_dew_point_gets_one_and_humid_hours_count_at_90(client, archive):
    hourly = archive_hours(archive, ["air_temperature", "relative_humidity"])
    body = post(client, "models/late-blight-dsv/run", body_for(hourly=hourly, start="2025-07-02", end="2025-07-09"))
    assert body.status_code == 200, body.json()
    meta = body.json()["meta"]
    assert any("We computed dew point from the relative humidity" in w for w in meta["warnings"])
    # Every hour at 89% RH: under the station's 90%, though D50 would count it on gridded RH
    times = hourly["time"]
    humid = {"time": times, "air_temperature": [15.0] * len(times), "relative_humidity": [89.0] * len(times)}
    dsv = post(client, "models/late-blight-dsv/run", body_for(hourly=humid, start="2025-07-02", end="2025-07-09"))
    assert dsv.json()["data"]["hours_rh_over_90_from_8pm"] == [0] * 8


def test_inputs_that_cannot_be_made_are_named_with_their_hourly_sources(client, archive):
    hourly = archive_hours(archive, ["air_temperature"])
    response = post(client, "models/late-blight-dsv/run", body_for(hourly=hourly, start="2025-07-02", end="2025-07-09"))
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert (
        error["code"] == "missing_inputs"
        and "hours_rh_over_90_from_8pm (hourly: air_temperature, dew_point)" in error["message"]
    )
    filled = post(
        client, "models/late-blight-dsv/run", body_for(hourly=hourly, start="2025-07-02", end="2025-07-09", fill="grid")
    ).json()
    assert set(filled["data"]["kind"]) == {"grid"}  # each day took the humid hours from the archive
    assert any("fill=grid" in w for w in filled["meta"]["warnings"]) and "urma" in filled["meta"]["sources"]


def test_a_csv_of_daily_values(client, archive):
    csv = "date,air_temperature_min,air_temperature_max\n" + "\n".join(f"2025-07-0{d},50,70" for d in range(2, 10))
    response = client.post(
        f"/api/v2/models/early-blight-pdays/run?lat={LAT}&lng={LNG}&biofix=2025-07-02", csv, content_type="text/csv"
    )
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    assert data["kind"] == ["provided"] * 8 and data["air_temperature_min"] == [50] * 8  # °F, the default units


def test_a_gap_the_model_bridges_is_estimated_and_out_of_range_values_are_dropped(client, archive):
    days = [f"2025-07-0{d}" for d in range(2, 10)]
    lows = [10.0, 10.0, None, 10.0, 10.0, 10.0, 10.0, 10.0]
    highs = [20.0] * 5 + [99.0] + [20.0] * 2  # 99 °C: past the catalog's range
    body = post(
        client,
        "models/early-blight-pdays/run",
        body_for(daily={"date": days, "air_temperature_min": lows, "air_temperature_max": highs}),
    ).json()
    assert body["data"]["kind"][2] == "estimated" and body["data"]["kind"][5] == "estimated"
    assert any(w.startswith("1 day of air_temperature_m") for w in body["meta"]["warnings"])
    assert body["meta"]["summary"]["days_estimated"] == 2
    assert body["data"]["air_temperature_max_estimated"][5] is True  # and its input column says which
    assert body["meta"]["summary"]["estimated_by_input"] == {"air_temperature_max": 1, "air_temperature_min": 1}


def test_extend_runs_on_with_our_weather_after_the_stations_last_day(client, archive):
    hourly = archive_hours(archive, ["air_temperature"], last=datetime(2025, 7, 6, 5, tzinfo=UTC))  # to July 5
    body = post(
        client,
        "models/early-blight-pdays/run",
        body_for(hourly=hourly, start="2025-07-02", extend="forecast", options={"biofix": "2025-07-02"}),
    ).json()
    kinds = body["data"]["kind"]
    assert kinds[:4] == ["provided"] * 4 and kinds[4] == "grid" and kinds[-1] == "forecast"
    assert body["meta"]["summary"]["days_forecast"] > 5


def test_several_models_on_posted_weather(client, archive):
    hourly = archive_hours(archive, ["air_temperature", "dew_point"])
    body = post(
        client,
        "models/run",
        body_for(hourly=hourly, start="2025-07-02", end="2025-07-09", models=["early-blight-pdays", "late-blight-dsv"]),
    ).json()
    assert list(body["data"]) == ["early-blight-pdays", "late-blight-dsv"]
    assert body["data"]["late-blight-dsv"]["data"]["kind"] == ["provided"] * 8


def test_bad_bodies(client, archive):
    assert post(client, "models/tar-spot/run", {"hourly": {"time": []}}).json()["errors"][0]["param"] == "location"
    naive = body_for(hourly={"time": ["2025-07-02T05:00"], "air_temperature": [10]})
    assert "needs a time zone" in post(client, "models/tar-spot/run", naive).json()["errors"][0]["message"]
    unknown = body_for(hourly={"time": ["2025-07-02T05:00Z"], "leaf_wetness": [1]})
    assert post(client, "models/tar-spot/run", unknown).json()["errors"][0]["code"] == "unknown_variable"
    uneven = body_for(hourly={"time": ["2025-07-02T05:00Z"], "air_temperature": [1, 2]})
    assert post(client, "models/tar-spot/run", uneven).status_code == 422


def test_several_models_skip_those_the_station_cannot_run(client, archive):
    hourly = archive_hours(archive, ["air_temperature"])
    body = post(
        client, "models/run", body_for(hourly=hourly, start="2025-07-02", end="2025-07-09", models="all")
    ).json()
    assert "early-blight-pdays" in body["data"] and "late-blight-dsv" not in body["data"]
    assert "hours_rh_over_90_from_8pm" in body["meta"]["summary"]["skipped"]["late-blight-dsv"]
    nothing = post(
        client,
        "models/run",
        body_for(hourly={"time": hourly["time"], "precipitation": [0.0] * len(hourly["time"])}, models=["tar-spot"]),
    )
    assert nothing.status_code == 422 and nothing.json()["errors"][0]["code"] == "missing_inputs"


def test_a_stations_hours_in_unix_time_give_what_iso_times_give(client, archive):
    # Wisconet sends Unix time: seconds as JSON numbers, and milliseconds should read the same
    iso = archive_hours(archive, ["air_temperature"])
    seconds = [int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()) for t in iso["time"]]
    request = {"start": "2025-07-02", "end": "2025-07-09", "options": {"biofix": "2025-07-02"}}
    by_iso = post(client, "models/early-blight-pdays/run", body_for(hourly=iso, **request)).json()
    for times in (seconds, [s * 1000 for s in seconds], [str(s) for s in seconds]):
        sent = post(client, "models/early-blight-pdays/run", body_for(hourly={**iso, "time": times}, **request)).json()
        assert sent["data"]["pdays_total"] == by_iso["data"]["pdays_total"]
