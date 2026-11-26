"""Models on weather sent with the request (Phase 5 D step 5, D58), on the fixture archive: observed hours
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
    assert dsv.json()["data"]["hours_rh_over_90_from_6pm"] == [0] * 8


def test_inputs_that_cannot_be_made_are_named_with_their_hourly_sources(client, archive):
    hourly = archive_hours(archive, ["air_temperature"])
    response = post(client, "models/late-blight-dsv/run", body_for(hourly=hourly, start="2025-07-02", end="2025-07-09"))
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert (
        error["code"] == "missing_inputs"
        and "'hours_rh_over_90_from_6pm' (hourly: 'air_temperature', 'dew_point')" in error["message"]
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
    assert any(w.startswith("1 day of 'air_temperature_m") for w in body["meta"]["warnings"])
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
    assert "hours_rh_over_90_from_6pm" in body["meta"]["summary"]["skipped"]["late-blight-dsv"]
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


def test_posted_hours_roll_up_on_the_days_asked_for(client, archive):
    hourly = archive_hours(archive, ["air_temperature"])
    body = body_for(hourly=hourly, start="2025-07-02", end="2025-07-09")
    central = post(client, "models/early-blight-pdays/run", body).json()["meta"]
    assert central["location"]["day_basis"] == "central" and "day_basis" not in central["request"]
    local = post(client, "models/early-blight-pdays/run", body | {"day_basis": "local"}).json()["meta"]
    assert local["location"]["day_basis"] == "local" and local["request"]["day_basis"] == "local"
    refused = post(client, "models/early-blight-pdays/run", body | {"day_basis": "solar"}).json()["errors"][0]
    assert refused["param"] == "day_basis" and refused["code"] == "invalid"


def _season_body() -> dict:
    """Daily weather from January 1 (a model counting from then needs it): 5–20 °C, about 1,650 degree days by July."""
    first = datetime(2025, 1, 1, tzinfo=UTC)
    days = [(first + timedelta(days=k)).strftime("%Y-%m-%d") for k in range(190)]  # to July 9
    return body_for(
        daily={"date": days, "air_temperature_min": [5.0] * 190, "air_temperature_max": [20.0] * 190},
        start="2025-07-01",
    )


def test_a_model_reads_the_places_normal_and_warns_without_it(client, archive, monkeypatch):
    """European corn borer's one flight where the 30-year normal by August 1 is below 1,500 (part H, round 2): the
    fixture has no 30-year normal maps, so two flights and a warning; given one at the cell, one flight."""
    from agdata import normals
    from agmodels.insects.european_corn_borer import ONE_FLIGHT_NORMAL

    without = post(client, "models/european-corn-borer/run", _season_body()).json()
    assert without["data"]["one_flight"] == [0] * 9
    assert ONE_FLIGHT_NORMAL.missing in without["meta"]["warnings"]
    monkeypatch.setattr(
        normals,
        "read_place_normals",
        lambda data_dir, wanted, window: {n: np.full(window.shape, 1400.0) for n in wanted},
    )
    north = post(client, "models/european-corn-borer/run", _season_body()).json()
    assert north["data"]["one_flight"] == [1] * 9
    assert north["data"][ONE_FLIGHT_NORMAL.key] == [pytest.approx(1400 / 1.8, abs=0.01)] * 9  # metric: °C·d
    assert ONE_FLIGHT_NORMAL.missing not in north["meta"]["warnings"]
    assert north["data"]["activity_adult_flight"] != without["data"]["activity_adult_flight"]


def test_a_fixed_biofix_is_refused_in_a_posted_run(client, archive):
    """Western bean cutworm always counts from March 1: another date is refused in the API's words, and March 1
    itself is the same run (the runner refuses any other, `runner.check_biofix`)."""
    refused = post(client, "models/western-bean-cutworm/run", _season_body() | {"options": {"biofix": "2025-04-01"}})
    error = refused.json()["errors"][0]
    assert refused.status_code == 422 and (error["code"], error["param"]) == ("not_applicable", "biofix")
    assert (
        error["message"]
        == "The Western bean cutworm model always counts from March 1, so it doesn't take a biofix date. Leave out 'biofix'."
    )
    same = post(client, "models/western-bean-cutworm/run", _season_body() | {"options": {"biofix": "2025-03-01"}})
    plain = post(client, "models/western-bean-cutworm/run", _season_body())
    assert same.status_code == 200 and same.json()["data"] == plain.json()["data"]


def test_a_models_setting_beside_options_is_refused_not_ignored(client, archive):
    """A top-level `"biofix"` in a JSON body was ignored without a word (only `options.biofix` is read): refused, saying
    where it goes; any other unknown field is refused naming the fields taken."""
    for path in ("models/early-blight-pdays/run", "models/run"):
        refused = post(client, path, _june(range(0), biofix="2025-06-01"))
        error = refused.json()["errors"][0]
        assert refused.status_code == 422 and (error["code"], error["param"]) == ("unknown_parameter", "biofix")
        assert (
            error["message"]
            == """Put 'biofix' inside 'options', such as '"options": {"biofix": "2025-06-01"}': in a JSON body, a model's settings go there."""
        )
    typo = post(client, "models/early-blight-pdays/run", _june(range(0), dialy={})).json()["errors"][0]
    assert typo["param"] == "dialy" and "Did you mean 'daily'?" in typo["message"] and "'models'" not in typo["message"]
    several = post(
        client, "models/run", _june(range(0), models=["early-blight-pdays"], options={"biofix": "2025-06-01"})
    )
    assert several.status_code == 200, several.json()


def _june(hole: range, **rest) -> dict:
    """June 1–25, 2025 at 10–25 °C, without the days in `hole` (day numbers)."""
    days = [f"2025-06-{d:02d}" for d in range(1, 26)]
    lows = [None if d in hole else 10.0 for d in range(1, 26)]
    highs = [None if d in hole else 25.0 for d in range(1, 26)]
    return body_for(daily={"date": days, "air_temperature_min": lows, "air_temperature_max": highs}, **rest)


def test_days_missing_past_the_fill_are_flagged_and_warned(client, archive):
    """D56: a 10-day hole is longer than the fill's 7 days, so the running total adds nothing for it."""
    body = post(client, "models/early-blight-pdays/run", _june(range(5, 15), options={"biofix": "2025-06-01"})).json()
    data = body["data"]
    assert data["air_temperature_max_missing"] == [5 <= d < 15 for d in range(1, 26)]
    assert data["air_temperature_min_missing"] == data["air_temperature_max_missing"]
    assert "air_temperature_max_estimated" not in data
    assert body["meta"]["summary"]["missing_by_input"] == {"air_temperature_min": 10, "air_temperature_max": 10}
    warning = next(w for w in body["meta"]["warnings"] if "gaps longer than the 7 days" in w)
    assert warning == (
        "The weather data have 10 days of 'air_temperature_min' and 'air_temperature_max' missing, in gaps longer than the 7 days we fill with estimates, so the model's running totals add nothing for those days and may run behind. Its results after them may be late. The columns ending in '_missing' mark the days shown."
    )


def test_a_short_hole_is_estimated_and_not_warned(client, archive):
    body = post(client, "models/early-blight-pdays/run", _june(range(5, 10), options={"biofix": "2025-06-01"})).json()
    data = body["data"]
    assert sum(data["air_temperature_max_estimated"]) == 5
    assert "air_temperature_max_missing" not in data and "missing_by_input" not in body["meta"]["summary"]
    assert not any("gaps longer than" in w for w in body["meta"]["warnings"])


def test_days_missing_before_the_first_day_shown_still_warn(client, archive):
    """The hole is before `start`: no row shows it, but the totals from the biofix rest on it."""
    body = post(
        client,
        "models/early-blight-pdays/run",
        _june(range(5, 15), start="2025-06-20", options={"biofix": "2025-06-01"}),
    ).json()
    assert body["data"]["date"][0] == "2025-06-20" and "air_temperature_max_missing" not in body["data"]
    assert body["meta"]["summary"]["missing_by_input"] == {"air_temperature_min": 10, "air_temperature_max": 10}
    assert any("gaps longer than the 7 days" in w for w in body["meta"]["warnings"])


def test_days_missing_at_the_end_are_flagged_but_not_warned(client, archive):
    """Days after the last day with data aren't a gap the totals fall behind on."""
    body = post(
        client,
        "models/early-blight-pdays/run",
        _june(range(16, 26), end="2025-06-25", options={"biofix": "2025-06-01"}),
    ).json()
    assert "missing_by_input" not in body["meta"]["summary"]
    assert not any("gaps longer than" in w for w in body["meta"]["warnings"])
