"""Rolling windows at points and on maps (D81, PLAN.md Phase 6 D0) on the fixture archive: observed July 1–10 2025
(each day's maximum 21 °C, 2.4 mm of rain), then an NBM run to July 20 (31 °C)."""

import pytest

from agdata.grid import NDFD
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
OTHER_CELL = tuple(round(float(v), 4) for v in NDFD.latlon(901, 1402))


def get(client, path, **params):
    return client.get(f"/api/v2/{path}", {"lat": LAT, "lng": LNG, **params})


def daily(client, **params):
    response = get(client, "weather/daily", vars="air_temperature_max,precipitation_sum", **params)
    assert response.status_code == 200, response.json()
    return response.json()


def test_a_trailing_window_reads_the_days_before_start(client, archive):
    body = daily(client, start="2025-07-08", end="2025-07-09", roll="3,7")
    data = body["data"]
    assert data["date"] == ["2025-07-08", "2025-07-09"]  # the rows asked for, not the lead-in
    assert data["air_temperature_max_3d"] == [69.8, 69.8] and data["air_temperature_max_7d"] == [69.8, 69.8]
    assert data["precipitation_sum_3d"] == [0.2835, 0.2835]  # a sum by default: 7.2 mm
    roll = body["meta"]["summary"]["roll"]
    assert roll["columns"]["precipitation_sum_3d"] == {"of": "precipitation_sum", "stat": "sum", "days": 3}
    assert roll["columns"]["air_temperature_max_7d"]["stat"] == "mean"
    assert body["meta"]["request"]["roll"] == [3, 7] and body["meta"]["request"]["roll_align"] == "trailing"
    assert body["meta"]["units"]["air_temperature_max_3d"] == "°F"


def test_windows_past_the_series_end_are_empty_unless_partial(client, archive):
    """The forecast's last whole day is July 20, so a centered window on it reaches past the series' end."""
    data = daily(client, start="2025-07-18", roll="3", roll_align="centered")["data"]
    assert data["date"] == ["2025-07-18", "2025-07-19", "2025-07-20"]
    assert data["air_temperature_max_3d"] == [87.8, 87.8, None]
    body = daily(client, start="2025-07-18", roll="3", roll_align="centered", roll_partial="true")
    assert body["data"]["air_temperature_max_3d"] == [87.8, 87.8, 87.8]
    assert body["data"]["precipitation_sum_3d"] == [0.2835, 0.2835, 0.189]  # a clipped sum is over fewer days
    assert body["meta"]["summary"]["roll"]["windows"][0]["clipped"] == ["2025-07-20"]


def test_days_without_data_are_a_gap_not_an_end(client, archive):
    """June 29 and 30 are in the fixture's store without values: a gap, so coverage applies even with partial."""
    data = daily(client, start="2025-07-01", end="2025-07-03", roll="3", roll_partial="true")["data"]
    assert data["air_temperature_max_3d"] == [None, None, 69.8]


def test_a_centered_window_reaches_into_the_forecast(client, archive):
    body = daily(client, start="2025-07-08", end="2025-07-09", roll="5", roll_align="centered")
    data = body["data"]
    assert data["air_temperature_max_5d"] == [73.4, 77.0]  # July 10 is partly forecast, its maximum 87.8 °F
    note = body["meta"]["summary"]["roll"]["windows"][0]
    assert note["forecast_from"] == "2025-07-08"  # its window holds July 10, partly forecast
    # Without the forecast, the series ends July 9, so a centered window there has no value unless clipped
    data = daily(client, start="2025-07-08", end="2025-07-09", roll="5", roll_align="centered", forecast="false")[
        "data"
    ]
    assert data["air_temperature_max_5d"] == [None, None]
    data = daily(
        client,
        start="2025-07-08",
        end="2025-07-09",
        roll="5",
        roll_align="centered",
        forecast="false",
        roll_partial="true",
    )["data"]
    assert data["air_temperature_max_5d"] == [69.8, 69.8]


def test_coverage_and_zoo_s_any_value(client, archive):
    """July 2's 7-day window holds two days with data (June's have none): empty at 75%, a value at 0, as zoo's
    `na.rm = TRUE`."""
    body = daily(client, date="2025-07-02", roll="7")
    assert body["data"]["air_temperature_max_7d"] == [None]
    assert any("7-day" in w and "roll_coverage" in w for w in body["meta"]["warnings"])
    body = daily(client, date="2025-07-02", roll="7", roll_coverage="0")
    assert body["data"]["air_temperature_max_7d"] == [69.8]
    assert daily(client, date="2025-07-02", roll="7", roll_coverage="25")["data"]["air_temperature_max_7d"] == [69.8]


def test_other_statistics_and_their_checks(client, archive):
    data = daily(client, start="2025-07-08", end="2025-07-10", roll="3", roll_stat="min")["data"]
    assert data["air_temperature_max_3d"] == [69.8, 69.8, 69.8]
    data = daily(client, start="2025-07-10", end="2025-07-12", roll="3", roll_stat="max")["data"]
    assert data["air_temperature_max_3d"] == [87.8, 87.8, 87.8]
    data = daily(client, start="2025-07-10", end="2025-07-12", roll="3", roll_stat="mean")["data"]
    assert data["precipitation_sum_3d"][0] == 0.0945
    response = get(client, "weather/daily", vars="air_temperature_max", roll="3", roll_stat="sum")
    assert response.status_code == 422 and response.json()["errors"][0]["param"] == "roll_stat"
    for bad in ("1", "abc", "7,7", "400"):
        response = get(client, "weather/daily", roll=bad)
        assert response.status_code == 422 and response.json()["errors"][0]["param"] == "roll", bad
    response = get(client, "weather/daily", roll="7", roll_coverage="120")
    assert response.json()["errors"][0]["param"] == "roll_coverage"


def test_several_points_note_each(client, archive):
    response = client.get(
        "/api/v2/weather/daily",
        {
            "points": f"{LAT},{LNG};{OTHER_CELL[0]},{OTHER_CELL[1]}",
            "start": "2025-07-08",
            "end": "2025-07-09",
            "roll": "3",
            "vars": "air_temperature_max",
        },
    )
    body = response.json()
    assert body["data"]["air_temperature_max_3d"] == [69.8] * 4
    assert [n["point"] for n in body["meta"]["summary"]["roll"]["windows"]] == [0, 1]


def test_a_lead_in_before_the_archive_s_first_year_stays_in_the_archive(client, archive):
    """January 2's 7-day window reaches into 2024, which the fixture archive lacks: the read starts January 1
    rather than going to Open-Meteo (the network is blocked in tests, so that would fail)."""
    body = daily(client, start="2025-01-02", end="2025-01-03", roll="7")
    assert body["data"]["air_temperature_max_7d"] == [None, None]
    assert "open-meteo" not in body["meta"]["sources"]


def test_degree_days_roll_as_a_sum_of_each_days(client, archive):
    plain = get(client, "degree-days", start="2025-07-06", end="2025-07-09", dd="sine_50").json()["data"]
    body = get(client, "degree-days", start="2025-07-08", end="2025-07-09", dd="sine_50", roll="3").json()
    week = body["data"]["dd_sine_50_3d"]
    assert week == pytest.approx([sum(plain["dd_sine_50"][0:3]), sum(plain["dd_sine_50"][1:4])], abs=0.11)
    assert body["data"]["date"] == ["2025-07-08", "2025-07-09"]
    assert body["meta"]["summary"]["roll"]["columns"]["dd_sine_50_3d"]["stat"] == "sum"
    assert body["meta"]["summary"]["days_returned"] == 2  # the lead-in isn't counted
    mean = get(client, "degree-days", start="2025-07-08", end="2025-07-09", dd="sine_50", roll="3", roll_stat="mean")
    assert mean.json()["data"]["dd_sine_50_3d"] == pytest.approx([w / 3 for w in week], abs=0.11)
    refused = get(client, "degree-days", dd="sine_50", roll="7", projection="true")
    assert refused.status_code == 422 and refused.json()["errors"][0]["param"] == "roll"


# --- Maps ------------------------------------------------------------------------------------------------------


def grid(client, layer, **params):
    return client.get(f"/api/v2/grids/{layer}", {"cells": "true", **params})


def test_a_map_s_window_is_a_range_ending_on_its_date(client, archive):
    body = grid(client, "air_temperature_max", date="2025-07-08", roll="3").json()
    assert set(body["data"]["air_temperature_max"]) == {69.8}
    request = body["meta"]["request"]
    assert (request["date"], request["roll"], request["start"], request["end"]) == (
        "2025-07-08",
        3,
        "2025-07-06",
        "2025-07-08",
    )
    assert request["stat"] == "mean" and request["roll_align"] == "trailing"
    rain = grid(client, "precipitation_sum", date="2025-07-08", roll="3").json()
    assert rain["meta"]["request"]["stat"] == "sum" and set(rain["data"]["precipitation_sum"]) == {0.2835}
    hot = grid(client, "air_temperature_max", date="2025-07-12", roll="5", count="days_above_80").json()
    assert set(hot["data"]["air_temperature_max"]) == {3}  # July 10–12 at 87.8 °F


def test_a_cell_s_window_matches_the_point_s(client, archive):
    params = {"roll": "5", "roll_align": "centered"}
    point = get(client, "weather/daily", date="2025-07-09", vars="air_temperature_max", **params).json()
    cells = grid(client, "air_temperature_max", date="2025-07-09", **params).json()["data"]
    k = next(n for n, (j, i) in enumerate(zip(cells["j"], cells["i"], strict=True)) if (j, i) == (900, 1401))
    assert cells["air_temperature_max"][k] == point["data"]["air_temperature_max_5d"][0] == 77.0


def test_a_map_s_window_past_the_data_is_empty_unless_partial(client, archive):
    """The forecast's days run to July 21; a centered window on it reaches July 22."""
    body = grid(client, "air_temperature_max", date="2025-07-21", roll="3", roll_align="centered").json()
    assert set(body["data"]["air_temperature_max"]) == {None}
    assert any("roll_partial" in w for w in body["meta"]["warnings"])
    again = grid(client, "air_temperature_max", date="2025-07-21", roll="3", roll_align="centered").json()
    assert again["meta"]["warnings"] == body["meta"]["warnings"]  # kept with the map, not lost on a cache hit
    body = grid(client, "air_temperature_max", date="2025-07-21", roll="3", roll_align="centered", roll_partial="true")
    assert None not in body.json()["data"]["air_temperature_max"]


def test_a_map_s_window_is_checked(client, archive):
    for params, param in (
        ({"start": "2025-07-01"}, "start"),
        ({"first": "frost"}, "first"),
        ({"roll": "1"}, "roll"),
        ({"roll_coverage": "101"}, "roll_coverage"),
    ):
        response = grid(client, "air_temperature_max", date="2025-07-08", **({"roll": "3"} | params))
        assert response.status_code == 422 and response.json()["errors"][0]["param"] == param, params
    hourly = grid(client, "air_temperature_hourly", time="2025-07-08T12", roll="3")
    assert hourly.status_code == 422 and hourly.json()["errors"][0]["param"] == "roll"
    total = grid(client, "dd_modified_50_86", date="2025-07-08", roll="3")
    assert total.status_code == 422 and total.json()["errors"][0]["param"] == "roll"
    summary = client.get(
        "/api/v2/summaries/air_temperature_max", {"date": "2025-07-08", "roll": "3", "interval": "month"}
    )
    assert summary.status_code == 422 and summary.json()["errors"][0]["param"] == "interval"


@pytest.mark.django_db
def test_tiles_and_images_take_a_window(client, archive):
    from agdata import tiles
    from api import layermaps, maptitles
    from api.tests.fixture_archive import NOW

    x, y = tiles.tile_of(LNG, LAT, 8)
    tile = client.get(f"/api/v2/tiles/air_temperature_max/2025-07-08/8/{x}/{y}.png", {"roll": "3"})
    assert tile.status_code == 200
    ranged = client.get(f"/api/v2/tiles/air_temperature_max/2025-07-01..2025-07-08/8/{x}/{y}.png", {"roll": "3"})
    assert ranged.status_code == 422 and ranged.json()["errors"][0]["param"] == "roll"
    image = client.get("/api/v2/maps/precipitation_sum.png", {"date": "2025-07-08", "roll": "7"})
    assert image.status_code == 200
    assert "precipitation_sum_sum_2025-07-02_2025-07-08" in image["Content-Disposition"]
    query = layermaps.LayerQuery(date="2025-07-08", roll=14)
    a = layermaps.ask(tile.wsgi_request, "air_temperature_max", query, "us", NOW)
    assert maptitles.title(a, "us") == "Air temperature, 14-day mean daily maximum"
    assert maptitles.subtitle(a).startswith("14 days ending Jul 8, 2025 (Jun 25 – Jul 8, 2025)")
    rain = layermaps.ask(
        tile.wsgi_request, "precipitation_sum", layermaps.LayerQuery(date="2025-07-08", roll=7), "us", NOW
    )
    assert maptitles.title(rain, "us") == "Precipitation, 7-day total"
