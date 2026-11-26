"""Events on model results (Phase 6 step 3, `api.modelevents`): `first=`, `last=` and `since=` at points
(`/models/{id}/run`'s `meta.summary.events`, and `milestones` without a projection) and on model maps. The fixture
archive is observed July 1–10, 2025 (to 15Z on the 10th), then forecast to about July 21; days before July 1 have
no data."""

import json

import pytest

from agdata.grid import NDFD
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
BLIGHT = {"biofix": "2025-07-02"}


def run(client, model_id, **params):
    response = client.get(f"/api/v2/models/{model_id}/run", {"lat": LAT, "lng": LNG, **params})
    assert response.status_code == 200, response.json()
    return response.json()


def first_row(data, column, test):
    """The first row's date where `test(value)`, or None."""
    return next((d for d, v in zip(data["date"], data[column], strict=True) if v is not None and test(v)), None)


def last_row(data, column, test):
    found = [d for d, v in zip(data["date"], data[column], strict=True) if v is not None and test(v)]
    return found[-1] if found else None


# --- At points --------------------------------------------------------------------------------------------------


def test_events_at_a_point_are_the_days_in_its_rows(client, archive):
    body = run(
        client,
        "early-blight-pdays",
        **BLIGHT,
        units="metric",
        first="high,pdays_total:above_50",
        last="pdays:above_0",
        since="very_low",
    )
    data, summary = body["data"], body["meta"]["summary"]
    high, total, last, since = summary["events"]
    assert high == {
        "event": "first=high",
        "kind": "first",
        "output": "risk_level",
        "date": None,
        "day_kind": None,
        "before_start": False,
        "missing_days": 0,
    }
    expected = first_row(data, "pdays_total", lambda v: v >= 50)
    assert expected is not None and total["date"] == expected and total["output"] == "pdays_total"
    assert total["day_kind"] == data["kind"][data["date"].index(expected)]
    assert last["date"] == last_row(data, "pdays", lambda v: v >= 0) == data["date"][-1]  # through the forecast
    assert last["day_kind"] == "forecast"
    # Days since are counted to today (the clock's July 10), not to the forecast's end
    assert since["days"] == 0 and since["kind"] == "since" and "date" not in since
    assert body["meta"]["request"]["first"] == ["high", "pdays_total:above_50"]
    assert body["meta"]["request"]["since"] == ["very_low"]


def test_bounds_are_in_the_units_asked_for(client, archive):
    metric = run(client, "black-cutworm", first="dd_total:above_100", units="metric")
    us = run(client, "black-cutworm", first="dd_total:above_180")  # 100 °C·d is 180 °F·d
    found = metric["meta"]["summary"]["events"][0]["date"]
    assert found is not None and found == us["meta"]["summary"]["events"][0]["date"]
    assert found == first_row(us["data"], "dd_total", lambda v: v >= 180)


def test_an_insects_risk_by_number_and_a_crops_stage_by_code(client, archive):
    body = run(client, "black-cutworm", first="above_1")
    assert body["meta"]["summary"]["events"][0]["date"] == first_row(body["data"], "risk_level", lambda v: v >= 1)
    corn = run(client, "corn-stages", planting_date="2025-07-01", first="V2,r1")
    v2, r1 = corn["meta"]["summary"]["events"]
    assert v2["output"] == "stage" and v2["date"] == first_row(corn["data"], "stage_code", lambda v: v == "V2")
    assert r1["date"] is None  # not by the forecast's end
    milestones = {m["name"]: m for m in corn["meta"]["summary"]["milestones"]}
    assert milestones["V2"]["date"] == v2["date"] and milestones["V2"]["what"] == "stage"
    assert milestones["V2"]["day_kind"] == "forecast" and milestones["R1"]["date"] is None


def test_milestones_without_a_projection(client, archive):
    body = run(client, "early-blight-pdays", **BLIGHT, start="2025-07-05")
    milestones = body["meta"]["summary"]["milestones"]
    assert [m["name"] for m in milestones] == ["Low", "Moderate", "High", "Very high"]
    assert all(set(m) == {"what", "name", "date", "day_kind", "before_start"} for m in milestones)
    # A day found on the first row, after the biofix, may have come earlier
    body = run(client, "early-blight-pdays", **BLIGHT, start="2025-07-05", first="pdays_total:above_1")
    event = body["meta"]["summary"]["events"][0]
    assert event["date"] == "2025-07-05" and event["before_start"] is True


def test_each_option_set_and_each_point_has_its_own(client, archive):
    body = run(client, "white-mold", irrigation="all", first="above_0", start="2025-07-05", end="2025-07-09")
    events = body["meta"]["summary"]["events"]
    assert len(events) == 2 and all(len(found) == 1 for found in events)
    other = ",".join(str(round(float(v), 4)) for v in NDFD.latlon(901, 1402))
    several = client.get(
        "/api/v2/models/black-cutworm/run", {"points": f"{LAT},{LNG};{other}", "first": "above_1"}
    ).json()
    points = several["meta"]["summary"]["points"]
    assert [p["events"][0]["event"] for p in points] == ["first=above_1", "first=above_1"]
    assert all("milestones" in p for p in points) and "events" not in several["meta"]["summary"]


@pytest.mark.parametrize(
    ("value", "words"),
    [
        ("stage:above_1", "has no result named 'stage'"),
        ("sometime", "We can't read"),
        ("frost", "is a temperature"),
        ("between_3_1", "'between_1_3'"),
    ],
)
def test_events_that_cannot_be_read(client, archive, value, words):
    response = client.get("/api/v2/models/seedcorn-maggot/run", {"lat": LAT, "lng": LNG, "first": value})
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["param"] == "first" and words in error["message"]


def test_events_on_posted_weather(client, archive):
    csv = "date,air_temperature_min,air_temperature_max\n" + "\n".join(f"2025-07-0{d},50,70" for d in range(2, 10))
    response = client.post(
        f"/api/v2/models/early-blight-pdays/run?lat={LAT}&lng={LNG}&biofix=2025-07-02&first=pdays_total:above_20",
        csv,
        content_type="text/csv",
    )
    assert response.status_code == 200, response.json()
    body = response.json()
    event = body["meta"]["summary"]["events"][0]
    assert event["date"] == first_row(body["data"], "pdays_total", lambda v: v >= 20)
    assert event["day_kind"] == "provided" and body["meta"]["request"]["first"] == ["pdays_total:above_20"]
    several = client.post(
        "/api/v2/models/run",
        json.dumps({"location": {"lat": LAT, "lng": LNG}, "daily": {"date": ["2025-07-02"]}, "first": "high"}),
        content_type="application/json",
    )
    assert several.status_code == 422 and several.json()["errors"][0]["param"] == "first"


def test_a_projected_first_day_across_past_years(client, projection_archive):
    params = {"lat": LAT, "lng": LNG, "biofix": "2025-07-02", "end": "2025-08-20", "projection": "true"}
    body = client.get(
        "/api/v2/models/early-blight-pdays/run", {**params, "first": "pdays_total:above_150,pdays_total:above_1"}
    ).json()
    later, now = body["meta"]["summary"]["events"]
    assert later["date"] is None  # not by the forecast's end...
    projected = later["projection"]
    assert projected["of"] == 2 and projected["reached"] == 2  # ...but in both past years' paths
    assert projected["p10"] <= projected["p50"] <= projected["p90"]
    assert now["date"] == "2025-07-02" and now["projection"]["p50"] == "2025-07-02"  # every path shares it
    assert "milestones" not in body["meta"]["summary"]  # they're in the projection's


# --- On maps ----------------------------------------------------------------------------------------------------


def grid(client, layer, **params):
    return client.get(f"/api/v2/grids/{layer}", {"format": "json", **params})


def test_a_model_map_finds_the_first_day_through_the_forecast(client, archive):
    body = grid(client, "black-cutworm", first="above_1").json()
    request = body["meta"]["request"]
    assert request["start"] == "2025-04-15" and request["output"] == "risk_level"  # its season's start
    assert request["end"] > "2025-07-10"  # through the forecast
    days = grid(client, "black-cutworm", start="2025-07-01", end=request["end"]).json()["data"]
    expected = first_row(days, "black-cutworm", lambda v: v >= 1)
    assert expected is not None and set(body["data"]["black-cutworm"]) == {expected}
    assert all(body["data"]["found"])
    # Days since are counted to the last observed day
    since = grid(client, "black-cutworm", since="above_0").json()["meta"]["request"]
    assert since["end"] == "2025-07-09"


def test_a_named_level_and_another_output(client, archive):
    body = grid(client, "tar-spot", first="low", planting="none").json()
    assert body["meta"]["request"]["start"] == "2025-07-01"  # the model's season
    days = grid(client, "tar-spot", planting="none", start="2025-07-01", end=body["meta"]["request"]["end"]).json()
    expected = first_row(days["data"], "tar-spot", lambda v: v >= 1)
    assert set(body["data"]["tar-spot"]) == {expected}
    total = grid(client, "black-cutworm", output="dd_total", first="above_100", units="metric").json()["data"]
    us = grid(client, "black-cutworm", output="dd_total", first="above_180").json()["data"]
    assert total["black-cutworm"] == us["black-cutworm"]


def test_a_model_events_map_title_and_image(client, archive):
    from api import maptitles

    response = client.get("/api/v2/maps/tar-spot.png", {"first": "high", "planting": "none"})
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    assert maptitles  # the title is checked through the TileJSON below
    tilejson = client.get("/api/v2/tiles/tar-spot.json", {"first": "high", "planting": "none"}).json()
    assert tilejson["name"].endswith("first day at High risk or higher")


@pytest.mark.parametrize(
    ("layer", "params", "param", "words"),
    [
        ("black-cutworm", {"first": "dd_total:above_10"}, "first", "Give 'output=dd_total' and 'first=above_10'"),
        ("potato-volunteer", {"first": "high"}, "first", "counted over a season"),
        ("black-cutworm", {"first": "frost"}, "first", "is a temperature"),
        ("corn-stages", {"first": "R9", "planting": "mid"}, "first", "such as 'first=v1'"),
        ("black-cutworm", {"first": "high", "date": "2025-07-05"}, "date", "looks over a range of days"),
    ],
)
def test_model_map_events_that_do_not_apply(client, archive, layer, params, param, words):
    response = grid(client, layer, **params)
    assert response.status_code == 422, response.json()
    error = response.json()["errors"][0]
    assert error["param"] == param and words in error["message"], error
