"""Counts of days or hours within bounds (D75, `api.counts`): on maps (`count=days_above_86`) and at points
(`/weather/totals?count=air_temperature_max:days_above_86`, with `interval=month`). The fixture archive's July 2025
days are 15 °C ± 6 (highs 21 °C, 69.8 °F) and its forecast 25 °C ± 6; the projection archive adds July and August of
2023 (12 °C, with an 11-day hole) and 2024 (18 °C)."""

import numpy as np
import pytest

from api import counts
from api.errors import ApiError
from api.tests.fixture_archive import POINT

LAT, LNG = POINT


def grid(client, layer, **params):
    return client.get(f"/api/v2/grids/{layer}", params)


def totals(client, *count, **params):
    return client.get("/api/v2/weather/totals", {"lat": LAT, "lng": LNG, "count": list(count), **params})


# --- Parsing -------------------------------------------------------------------------------------------------------


def test_a_count_names_its_axis_and_bounds():
    above = counts.parse("days_above_93.2")
    assert (above.axis, above.low, above.high, above.name) == ("days", 93.2, None, "days_above_93p2")
    below = counts.parse("Hours_Below_-2p2")
    assert (below.axis, below.low, below.high, below.name) == ("hours", None, -2.2, "hours_below_-2p2")
    between = counts.parse("days_between_50_86")
    assert (between.low, between.high) == (50, 86)
    assert between.words("degF") == "days between 50 and 86 °F" and above.words("degF") == "days at or above 93.2 °F"
    assert counts.parse("days_above_90").words("percent") == "days at or above 90%"


@pytest.mark.parametrize("text", ["above_86", "days_over_86", "days_above_", "days_between_50", "weeks_above_1"])
def test_a_count_that_cant_be_read_says_how_to_write_one(text):
    with pytest.raises(ApiError) as caught:
        counts.parse(text)
    assert caught.value.code == "invalid" and "days_above_86" in caught.value.message


def test_bounds_out_of_order_and_the_wrong_axis_are_refused():
    with pytest.raises(ApiError) as caught:
        counts.parse("days_between_86_50")
    assert caught.value.code == "out_of_order" and "days_between_50_86" in caught.value.message
    with pytest.raises(ApiError) as caught:
        counts.check_axis(counts.parse("hours_above_86"), "day", "Air temperature, daily maximum")
    assert "count=days_above_86" in caught.value.message


def test_bounds_go_to_the_stored_unit_inclusive_of_float_noise():
    low, high = counts.parse("days_between_50_86").bounds("degF", "degC", 0.1)
    assert low == pytest.approx(10 - 0.025) and high == pytest.approx(30 + 0.025)
    values = np.array([[30.0], [30.1], [np.nan], [9.9]], dtype=np.float32)
    found, missing = counts.count_within(values, low, high)
    assert found.tolist() == [1.0] and missing.tolist() == [1]  # 30.0 counts; 30.1 and 9.9 are outside
    found, missing = counts.count_within(np.full((3, 1), np.nan), low, high)
    assert np.isnan(found[0]) and missing[0] == 3


# --- Maps ----------------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_map_counts_days_with_the_bound_included(client, archive):
    on = grid(client, "air_temperature_max", start="2025-07-02", end="2025-07-09", count="days_above_69.8").json()
    assert set(on["data"]["air_temperature_max"]) == {8} and set(on["data"]["missing_days"]) == {0}
    assert on["meta"]["request"]["count"] == "days_above_69p8" and on["meta"]["request"]["stat"] == "count"
    assert on["meta"]["units"]["air_temperature_max"] == "d"
    off = grid(client, "air_temperature_max", start="2025-07-02", end="2025-07-09", count="days_above_70").json()
    assert set(off["data"]["air_temperature_max"]) == {0}
    metric = grid(
        client, "air_temperature_max", start="2025-07-02", end="2025-07-09", count="days_below_21", units="metric"
    )
    assert set(metric.json()["data"]["air_temperature_max"]) == {8}  # 21 °C


@pytest.mark.django_db
def test_a_maps_missing_days_are_counted_not_assumed(client, archive):
    data = grid(client, "air_temperature_max", start="2025-07-20", end="2025-07-23", count="days_above_0").json()[
        "data"
    ]
    assert set(data["missing_days"]) == {3} and set(data["air_temperature_max"]) == {1}  # the run's last whole day


@pytest.mark.django_db
def test_hourly_and_degree_day_maps_count_too(client, archive):
    span = {"start": "2025-07-05T00:00Z", "end": "2025-07-05T23:00Z"}
    each = grid(client, "air_temperature_hourly", **span).json()["data"]["air_temperature_hourly"]
    at_first_cell = each[:: len(each) // 24]  # the hours of one cell (every cell has the same)
    hours = grid(client, "air_temperature_hourly", count="hours_above_60.8", **span).json()["data"]
    expected = sum(t >= 60.8 for t in at_first_cell)
    assert set(hours["air_temperature_hourly"]) == {expected} and 0 < expected < 24
    assert set(hours["missing_hours"]) == {0}
    dd = grid(
        client, "degree_days", dd="sine_50_86", start="2025-07-02", end="2025-07-09", count="days_above_1"
    ).json()["data"]
    assert set(dd["degree_days"]) == {8} and set(dd["estimated_days"]) == {0}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("layer", "params", "param"),
    [
        ("air_temperature_max", {"stat": "count"}, "count"),
        ("air_temperature_max", {"stat": "sum", "count": "days_above_86"}, "count"),
        ("air_temperature_max", {"count": "hours_above_86"}, "count"),
        ("air_temperature_hourly", {"start": "2025-07-05T00:00Z", "count": "days_above_86"}, "count"),
        ("precipitation_total", {"count": "days_above_1"}, "count"),
        ("air_temperature_max", {"count": "days_above"}, "count"),
    ],
)
def test_counts_that_dont_apply_are_refused(client, archive, layer, params, param):
    response = grid(client, layer, **params)
    assert response.status_code == 422 and response.json()["errors"][0]["param"] == param


@pytest.mark.django_db
def test_a_count_map_is_titled_with_what_it_counts(client, archive):
    params = {"time": "2025-07-02..2025-07-09", "count": "days_above_69.8"}
    tile_json = client.get("/api/v2/tiles/air_temperature_max.json", params).json()
    assert tile_json["name"] == "Air temperature, daily maximum, days at or above 69.8 °F"
    image = client.get(
        "/api/v2/maps/air_temperature_max.png", {"days": "5", "end": "2025-07-09", "count": "days_above_60"}
    )
    assert image.status_code == 200 and image["Content-Type"] == "image/png"


# --- Points --------------------------------------------------------------------------------------------------------


def test_a_points_counts_match_its_days_and_hours(client, archive):
    window = {"start": "2025-07-08", "end": "2025-07-12"}
    body = totals(client, "air_temperature_max:days_above_80", "air_temperature:hours_between_60_80", **window).json()
    data = body["data"]
    assert list(data) == [
        "days",
        "forecast_days",
        "air_temperature_max_days_above_80",
        "air_temperature_max_days_above_80_missing_days",
        "air_temperature_hours_between_60_80",
        "air_temperature_hours_between_60_80_missing_hours",
    ]  # only the counts when vars is left out
    daily = client.get("/api/v2/weather/daily", {"lat": LAT, "lng": LNG, "vars": "air_temperature_max", **window})
    highs = daily.json()["data"]["air_temperature_max"]
    assert data["air_temperature_max_days_above_80"] == [sum(h >= 80 for h in highs)] == [3]  # the forecast's days
    hourly = client.get(
        "/api/v2/weather/hourly",
        {"lat": LAT, "lng": LNG, "start": "2025-07-08T06:00Z", "end": "2025-07-13T06:00Z", "vars": "air_temperature"},
    ).json()["data"]["air_temperature"]
    expected = sum(
        t is not None and 60 <= t <= 80 for t in hourly[1:]
    )  # hours ending 07Z Jul 8 .. 06Z Jul 13 (CST days)
    assert data["air_temperature_hours_between_60_80"] == [expected]
    assert body["meta"]["request"]["count"] == [
        "air_temperature_max:days_above_80",
        "air_temperature:hours_between_60_80",
    ]


def test_counts_by_month_count_missing_days_with_a_warning(client, projection_archive):
    body = totals(
        client,
        "air_temperature_min:days_below_50,air_temperature_max:days_above_70",
        start="2023-07-01",
        end="2023-08-31",
        interval="month",
        vars="precipitation_sum",
    ).json()
    data = body["data"]
    assert data["month"] == ["2023-07", "2023-08"] and data["days"] == [31, 31]
    missing = data["air_temperature_min_days_below_50_missing_days"]
    assert missing[0] >= 3 and missing[1] >= 6  # the hole: July 28 to August 7
    assert data["precipitation_sum_missing_days"] == missing
    assert [c + m for c, m in zip(data["air_temperature_min_days_below_50"], missing, strict=True)] == [
        31,
        31,
    ]  # 6 °C lows
    assert data["air_temperature_max_days_above_70"] == [0, 0]  # highs of 18 °C
    assert any("air_temperature_min_days_below_50" in w for w in body["meta"]["warnings"])


def test_a_count_of_the_wrong_kind_is_refused(client, archive):
    wrong = totals(client, "air_temperature:days_above_86")
    assert wrong.status_code == 422 and "air_temperature:hours_above_86" in wrong.json()["errors"][0]["message"]
    unknown = totals(client, "air_temp:days_above_86")
    assert unknown.json()["errors"][0]["code"] == "unknown_variable"
    bare = totals(client, "days_above_86")
    assert bare.json()["errors"][0]["code"] == "invalid"
