"""The first or last day within bounds, and the days since the last (D78, `api.events`): parsing, the finder, on
maps (`first=frost` on `/grids`, tiles and `/maps`) and at points (`/weather/totals?first=air_temperature_min:frost`).
The fixture archive's July 2025 days are 15 °C ± 6 from July 1 (observed to July 10 15Z, the clock's day) and its
forecast 25 °C ± 6."""

from datetime import date
from unittest import mock

import numpy as np
import pytest

from agdata import mapimage, tiles
from api import events
from api.errors import ApiError
from api.routes import maps
from api.tests.fixture_archive import POINT

LAT, LNG = POINT


def grid(client, layer, **params):
    return client.get(f"/api/v2/grids/{layer}", params)


def grid_min(client, start, end):
    """The map's daily minimum (°C) at its first cell, by day (the cells are alike; the test archive's daily store
    starts July 2, while points compute July 1 from the hours)."""
    body = grid(client, "air_temperature_min", start=start, end=end, units="metric").json()["data"]
    seen: dict[date, float] = {}
    for day, value in zip(body["date"], body["air_temperature_min"], strict=True):
        seen.setdefault(date.fromisoformat(day), np.nan if value is None else value)
    return list(seen), np.array(list(seen.values()), dtype=float)


def daily_min(client, start, end, units="metric"):
    """The point's daily minimum from `/weather/daily` (the cells are alike), as floats with NaN for missing."""
    body = client.get(
        "/api/v2/weather/daily",
        {"lat": LAT, "lng": LNG, "start": start, "end": end, "vars": "air_temperature_min", "units": units},
    ).json()["data"]
    values = [np.nan if v is None else v for v in body["air_temperature_min"]]
    return [date.fromisoformat(d) for d in body["date"]], np.array(values, dtype=float)


# --- Parsing and finding -------------------------------------------------------------------------------------------


def test_an_event_is_a_named_temperature_or_bounds():
    frost = events.parse(kind="first", text="Hard_Freeze")
    assert (frost.low, frost.high, frost.named, frost.name, frost.unit) == (
        None,
        28.0,
        "hard_freeze",
        "hard_freeze",
        "degF",
    )
    above = events.parse(kind="last", text="above_50.5")
    assert (above.low, above.high, above.named, above.name, above.unit) == (50.5, None, None, "above_50p5", None)
    between = events.parse(kind="since", text="between_50_86")
    assert (between.low, between.high) == (50, 86)
    assert frost.words("degF") == "first hard freeze (28 °F)" and frost.words("degC") == "first hard freeze (-2.2 °C)"
    assert above.words("degF") == "last day at or above 50.5 °F"
    assert events.parse(kind="since", text="frost").words("degF") == "days since the last frost (32 °F)"
    assert (frost.unit_out, events.parse(kind="since", text="frost").unit_out) == ("date", "day")


@pytest.mark.parametrize(
    ("text", "said"),
    [("days_below_32", "first=below_32"), ("chilly", "frost"), ("between_86_50", "between_50_86")],
)
def test_an_event_that_cant_be_read_says_how_to_write_one(text, said):
    with pytest.raises(ApiError) as caught:
        events.parse(kind="first", text=text)
    assert said in caught.value.message and caught.value.param == "first"


def test_one_event_a_map():
    assert events.asked(first=None, last=None, since=None) is None
    with pytest.raises(ApiError) as caught:
        events.asked(first="frost", last="frost", since=None)
    assert caught.value.code == "conflict" and caught.value.param == "last"


def test_a_cold_events_window_starts_the_previous_july_1_and_others_january_1():
    frost = events.parse(kind="first", text="frost")
    assert frost.default_start(date(2026, 5, 15)) == date(2025, 7, 1)
    assert frost.default_start(date(2026, 7, 1)) == date(2026, 7, 1)
    assert frost.default_start(date(2026, 11, 7)) == date(2026, 7, 1)
    assert events.parse(kind="first", text="above_50").default_start(date(2026, 5, 15)) == date(2026, 1, 1)
    assert events.parse(kind="first", text="between_40_50").default_start(date(2026, 5, 15)) == date(2026, 1, 1)


def test_the_finder_tells_a_day_from_none_and_from_no_data():
    days = np.array(
        [
            [1.0, 5.0, np.nan, np.nan],
            [-1.0, 6.0, 2.0, np.nan],
            [np.nan, 7.0, np.nan, np.nan],
            [-2.0, 8.0, -0.5, np.nan],
            [3.0, 9.0, np.nan, np.nan],
        ]
    )  # days × cells: a cell with two freezes and a gap, one with none, one with one late, one with no data
    start = date(2026, 10, 1)
    epoch = (start - events.EPOCH).days
    value, found, missing = events.find(days, low=None, high=0.0, kind="first", first_day=start)
    assert value[0] == epoch + 1 and value[2] == epoch + 3 and np.isnan(value[1]) and np.isnan(value[3])
    assert found[:3].tolist() == [1, 0, 1] and np.isnan(found[3]) and missing.tolist() == [1, 0, 3, 5]
    value, _, _ = events.find(days, low=None, high=0.0, kind="last", first_day=start)
    assert value[0] == epoch + 3 and events.to_date(value[0]) == date(2026, 10, 4)
    value, _, _ = events.find(days, low=None, high=0.0, kind="since", first_day=start)
    assert value[0] == 1 and value[2] == 1 and np.isnan(value[1])
    value, _, _ = events.find(days, low=6.0, high=8.0, kind="first", first_day=start)  # between, inclusive
    assert value[1] == epoch + 1


def test_date_ticks_fall_on_round_dates():
    def as_days(day):
        return float((day - events.EPOCH).days)

    ticks = mapimage.date_ticks(as_days(date(2026, 9, 10)), as_days(date(2026, 11, 20)))
    assert [mapimage.date_label(t) for t in ticks] == ["Sep 15", "Oct 1", "Oct 15", "Nov 1", "Nov 15"]
    ticks = mapimage.date_ticks(as_days(date(2026, 1, 1)), as_days(date(2026, 12, 31)))
    assert [mapimage.date_label(t) for t in ticks] == ["Jan 1", "Mar 1", "May 1", "Jul 1", "Sep 1", "Nov 1"]
    assert len(mapimage.date_ticks(as_days(date(2026, 10, 3)), as_days(date(2026, 10, 12)))) >= 3


def test_a_data_tile_marks_none_apart_from_missing():
    values = np.array([[20000.0, np.nan, np.nan]])
    states = np.array([[1.0, 0.0, -1.0]])
    cells = np.full(tiles.SIZE * tiles.SIZE, -1, dtype=np.int32)
    cells[:3] = [0, 1, 2]
    rgba = tiles.data_tile(values, cells, 1, states).reshape(-1, 4)[:3]
    assert rgba[1].tolist() == [0, 0, tiles.NONE, 255] and rgba[2, 3] == 0  # none: code 1; no data: transparent
    decoded = tiles.decode(rgba, 1)
    assert decoded[0] == 20000 and np.isnan(decoded[1]) and np.isnan(decoded[2])


# --- Maps ----------------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_map_finds_the_first_and_last_day_and_the_days_since(client, archive):
    dates, lows = grid_min(client, "2025-07-01", "2025-07-09")
    bound = float(np.nanmax(lows))  # every day with data is at or below it: the bound is included
    hits = [d for d, v in zip(dates, lows, strict=True) if v <= bound]
    params = {"end": "2025-07-09", "units": "metric"}
    first = grid(client, "air_temperature_min", first=f"below_{bound:g}", **params).json()
    assert set(first["data"]["air_temperature_min"]) == {hits[0].isoformat()}
    assert set(first["data"]["found"]) == {True} and set(first["data"]["missing_days"]) == {len(dates) - len(hits)}
    assert first["meta"]["request"]["start"] == "2025-07-01" and first["meta"]["request"]["first"] == f"below_{bound:g}"
    last = grid(client, "air_temperature_min", last=f"below_{bound:g}", **params).json()
    assert set(last["data"]["air_temperature_min"]) == {hits[-1].isoformat()}
    since = grid(client, "air_temperature_min", since=f"below_{bound:g}", **params).json()
    assert set(since["data"]["air_temperature_min"]) == {(date(2025, 7, 9) - hits[-1]).days}
    none = grid(client, "air_temperature_min", first=f"below_{bound - 1:g}", **params).json()
    assert set(none["data"]["air_temperature_min"]) == {None} and set(none["data"]["found"]) == {False}
    early = grid(client, "air_temperature_min", first="frost", start="2025-06-01", end="2025-06-20").json()
    assert set(early["data"]["found"]) == {None} and set(early["data"]["missing_days"]) == {20}  # before the archive


@pytest.mark.django_db
def test_a_warm_events_window_starts_january_1(client, archive):
    body = grid(client, "air_temperature_min", first="above_32", end="2025-07-09").json()
    assert body["meta"]["request"]["start"] == "2025-01-01"
    assert set(body["data"]["air_temperature_min"]) == {"2025-07-02"}  # the daily store's first day


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("layer", "params", "code", "param"),
    [
        ("precipitation_sum", {"first": "frost"}, "invalid", "first"),  # not a temperature
        ("air_temperature_hourly", {"first": "above_50"}, "invalid", "first"),
        ("precipitation_total", {"first": "above_1"}, "invalid", "first"),
        ("air_temperature_min", {"first": "frost", "last": "frost"}, "conflict", "last"),
        ("air_temperature_min", {"first": "frost", "stat": "sum"}, "conflict", "first"),
        ("air_temperature_min", {"first": "frost", "count": "days_below_32"}, "conflict", "first"),
        ("air_temperature_min", {"first": "frost", "date": "2025-07-08"}, "invalid", "date"),
        ("air_temperature_min", {"stat": "first"}, "missing", "first"),
    ],
)
def test_events_that_dont_apply_are_refused(client, archive, layer, params, code, param):
    error = grid(client, layer, **params).json()["errors"][0]
    assert (error["code"], error["param"]) == (code, param)


@pytest.mark.django_db
def test_a_map_image_draws_dates_and_the_empty_states(client, archive):
    with mock.patch.object(maps.mapimage, "map_png", return_value=b"png") as drawn:
        response = client.get("/api/v2/maps/air_temperature_min.png", {"first": "frost", "end": "2025-07-09"})
    assert response.status_code == 200
    args, kwargs = drawn.call_args
    assert args[4] == "Air temperature, daily minimum, first frost (32 °F)"
    assert args[5] == "Jul 1 – Jul 9, 2025 (9 days)"
    assert kwargs["dates"] is True and set(np.unique(kwargs["states"])) == {0.0}  # July: no frost anywhere


@pytest.mark.django_db
def test_a_maps_bounds_in_other_units_are_another_map(client, archive):
    """The kept maps are keyed by the bounds as resolved: 15 means °C with units=metric and °F without."""
    seen = []
    with mock.patch.object(maps.mapimage, "map_png", side_effect=lambda *a, **k: seen.append(a[0]) or b"png"):
        for units in ("metric", "us"):
            client.get(
                "/api/v2/maps/air_temperature_min.png", {"count": "days_above_15", "end": "2025-07-09", "units": units}
            )
    assert not np.array_equal(seen[0], seen[1], equal_nan=True)


@pytest.mark.django_db
def test_tiles_carry_none_and_describe_dates(client, archive):
    described = client.get("/api/v2/tiles/air_temperature_min.json", {"first": "frost", "time": "2025-07-09"}).json()
    assert described["encoding"]["unit"] == "date" and described["encoding"]["none"].startswith("code 1")
    assert described["request"]["start"] == "2025-07-01" and described["request"]["end"] == "2025-07-09"
    legend = client.get("/api/v2/tiles/air_temperature_min/legend.png", {"first": "frost", "time": "2025-07-09"})
    assert legend.status_code == 200 and legend["Content-Type"] == "image/png"


@pytest.mark.django_db
def test_a_netcdf_holds_dates_as_cf_days(client, archive, tmp_path):
    import xarray as xr

    body = grid(client, "air_temperature_min", first="above_32", end="2025-07-09", format="netcdf").content
    (tmp_path / "f.nc").write_bytes(body)
    with xr.open_dataset(tmp_path / "f.nc") as ds:
        found = ds["air_temperature_min"].values
    assert found.dtype.kind == "M" and set(found.ravel().astype("datetime64[D]").astype(str)) == {"2025-07-02"}


# --- Points --------------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_totals_find_days_at_points(client, archive):
    dates, lows = daily_min(client, "2025-07-01", "2025-07-09", units="us")
    bound = float(np.nanmax(lows))
    hits = [d for d, v in zip(dates, lows, strict=True) if v <= bound]
    body = client.get(
        "/api/v2/weather/totals",
        {
            "lat": LAT,
            "lng": LNG,
            "end": "2025-07-09",
            "first": f"air_temperature_min:below_{bound}",
            "last": [f"air_temperature_min:below_{bound}", "air_temperature_min:frost"],
            "since": f"air_temperature_min:below_{bound}",
        },
    ).json()
    data, name = body["data"], f"air_temperature_min_{{}}_below_{f'{bound:g}'.replace('.', 'p')}"
    assert data[name.format("first")] == [hits[0].isoformat()] and data[name.format("last")] == [hits[-1].isoformat()]
    assert data[name.format("since")] == [(date(2025, 7, 9) - hits[-1]).days]
    assert data["air_temperature_min_last_frost"] == [None] and data["air_temperature_min_last_frost_missing_days"] == [
        0
    ]
    assert body["meta"]["request"]["event_start"]["air_temperature_min_last_frost"] == "2025-07-01"
    assert list(data) == ["days", "forecast_days", *(k for k in data if k.startswith("air_temperature_min_"))]


@pytest.mark.django_db
def test_totals_refuse_an_hourly_variable_or_frost_on_rain(client, archive):
    for param, value in (("first", "air_temperature:above_50"), ("last", "precipitation_sum:frost"), ("since", "x")):
        error = client.get("/api/v2/weather/totals", {"lat": LAT, "lng": LNG, param: value}).json()["errors"][0]
        assert error["param"] == param
