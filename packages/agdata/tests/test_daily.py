from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import daily
from agdata.catalog import VARIABLES
from agdata.daily import cell_timezones, open_or_create_daily, rollup_days
from agdata.grid import Window
from agdata.store import HOURLY, GridStore
from agdata.timezones import day_bounds

WINDOW = Window(900, 902, 1400, 1403)  # 2 x 3 cells near Madison
HOUR = timedelta(hours=1)


@pytest.fixture(autouse=True)
def two_zones(monkeypatch):
    """Column 0 is Eastern time, the rest Central."""
    index = np.ones(WINDOW.shape, dtype=np.uint8)
    index[:, 0] = 0
    monkeypatch.setattr(daily, "window_timezones", lambda window: (["America/Detroit", "America/Chicago"], index))


def hourly_store(tmp_path, year, start, hours, temperature=None, precip=1.0):
    """Hours from `start`: temperature counts up 0.1 °C an hour from 0 at `start` unless given; precip 1 mm."""
    store = GridStore.create(tmp_path, HOURLY, year, WINDOW, VARIABLES.values())
    n = np.arange(hours, dtype=float)
    temps = (n * 0.1 if temperature is None else np.full(hours, temperature))[:, None, None]
    store.write(start, {"air_temperature": np.broadcast_to(temps, (hours, *WINDOW.shape))}, source="test")
    store.write(start, {"precipitation": np.full((hours, *WINDOW.shape), precip)}, source="test")
    return store


def read(tmp_path, name, day):
    store = open_or_create_daily(tmp_path, day.year, WINDOW)
    return store.read_block(name, store.index_of(day))


def test_day_bounds_follow_daylight_saving():
    assert day_bounds(date(2025, 7, 1), "America/Chicago") == (
        datetime(2025, 7, 1, 6, tzinfo=UTC),
        datetime(2025, 7, 2, 5, tzinfo=UTC),
    )
    for day, zone, hours in [
        (date(2025, 3, 9), "America/Chicago", 23),
        (date(2025, 11, 2), "America/Chicago", 25),
        (date(2025, 1, 15), "America/Detroit", 24),
    ]:
        begin, end = day_bounds(day, zone)
        assert (end - begin) // HOUR + 1 == hours


def test_each_cell_uses_its_own_local_day(tmp_path):
    start = datetime(2025, 7, 1, tzinfo=UTC)
    hourly_store(tmp_path, 2025, start, 72)
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 1))
    low = read(tmp_path, "air_temperature_min", date(2025, 7, 1))
    high = read(tmp_path, "air_temperature_max", date(2025, 7, 1))
    # Eastern (UTC-4) hours end 05:00Z .. 04:00Z; Central (UTC-5) 06:00Z .. 05:00Z
    np.testing.assert_allclose(low[:, 0], 0.5)
    np.testing.assert_allclose(high[:, 0], 2.8)
    np.testing.assert_allclose(low[:, 1:], 0.6)
    np.testing.assert_allclose(high[:, 1:], 2.9)
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 7, 1)), 24)


def test_daylight_saving_days_sum_23_and_25_hours(tmp_path):
    hourly_store(tmp_path, 2025, datetime(2025, 1, 1, tzinfo=UTC), 8760, temperature=5.0)
    rollup_days(tmp_path, WINDOW, date(2025, 3, 9), date(2025, 3, 9))
    rollup_days(tmp_path, WINDOW, date(2025, 11, 2), date(2025, 11, 2))
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 3, 9)), 23)
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 11, 2)), 25)


def test_incomplete_days_are_missing(tmp_path):
    start = datetime(2025, 7, 1, 6, tzinfo=UTC)  # the Central day's first hour
    store = hourly_store(tmp_path, 2025, start - timedelta(days=1), 96, temperature=20.0)
    store.write(start, {"air_temperature": np.full((4, *WINDOW.shape), np.nan)}, source="test")  # 20 hours left
    store.write(start + 10 * HOUR, {"precipitation": np.full((1, *WINDOW.shape), np.nan)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 2))
    np.testing.assert_allclose(read(tmp_path, "air_temperature_mean", date(2025, 7, 1))[:, 1:], 20)
    assert np.isnan(read(tmp_path, "precipitation_sum", date(2025, 7, 1))).all()  # one hour short
    store.write(start + 4 * HOUR, {"air_temperature": np.full((1, *WINDOW.shape), np.nan)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 1))
    assert np.isnan(read(tmp_path, "air_temperature_mean", date(2025, 7, 1))[:, 1:]).all()  # 19 hours
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 7, 2)), 24)


def test_local_new_years_eve_reads_the_next_years_hours(tmp_path):
    hourly_store(tmp_path, 2025, datetime(2025, 12, 31, tzinfo=UTC), 24)
    rollup_days(tmp_path, WINDOW, date(2025, 12, 31), date(2025, 12, 31))
    assert np.isnan(read(tmp_path, "precipitation_sum", date(2025, 12, 31))).all()  # 2026's hours missing
    hourly_store(tmp_path, 2026, datetime(2026, 1, 1, tzinfo=UTC), 24)
    rollup_days(tmp_path, WINDOW, date(2025, 12, 31), date(2026, 1, 1))
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 12, 31)), 24)
    assert read(tmp_path, "precipitation_sum", date(2026, 1, 1)).shape == WINDOW.shape


def test_the_store_keeps_the_time_zones(tmp_path):
    zones, index = cell_timezones(open_or_create_daily(tmp_path, 2025, WINDOW))
    assert zones == ["America/Detroit", "America/Chicago"]
    assert index[:, 0].tolist() == [0, 0]


def test_a_day_missing_et0_hours_gets_an_estimate_beside_the_raw_total(tmp_path):
    start = datetime(2025, 7, 1, tzinfo=UTC)
    store = hourly_store(tmp_path, 2025, start, 96, temperature=25.0)
    shape = (96, *WINDOW.shape)
    store.write(
        start,
        {
            "dew_point": np.full(shape, 15.0),
            "wind_speed": np.full(shape, 3.0),
            "surface_pressure": np.full(shape, 98.5),
            "shortwave_radiation": np.full(shape, 0.0),  # stays dark, so the missing hour's ET0 is small
            "et0": np.full(shape, 0.1),
        },
        source="test",
    )
    store.write(start + 30 * HOUR, {"et0": np.full((1, *WINDOW.shape), np.nan)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 2))
    assert np.isnan(read(tmp_path, "et0_sum", date(2025, 7, 2))[:, 1:]).all()  # the hour is in Central Jul 2
    estimate = read(tmp_path, "et0_sum_estimate", date(2025, 7, 2))[:, 1:]
    assert np.all((estimate > 2.3) & (estimate < 2.6))  # 23 × 0.1 plus the estimated hour
    np.testing.assert_allclose(read(tmp_path, "et0_sum", date(2025, 7, 1))[:, 1:], 2.4)
    assert np.isnan(read(tmp_path, "et0_sum_estimate", date(2025, 7, 1))).all()  # only where the raw is missing


def test_grid_features_match_the_point_path(tmp_path):
    from zoneinfo import ZoneInfo

    from agmodels import features
    from agmodels.weather import relative_humidity_percent

    start = datetime(2025, 7, 1, tzinfo=UTC)
    n = 96
    hour = np.arange(n)
    temperature = np.round(20 + 8 * np.sin(2 * np.pi * (hour - 15) / 24), 1)  # a daily cycle, at stored precision
    dew_point = 17 + 0 * hour  # humid at night, dry by day
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())
    grid = (n, *WINDOW.shape)
    store.write(start, {"air_temperature": np.broadcast_to(temperature[:, None, None], grid)}, source="test")
    store.write(start, {"dew_point": np.broadcast_to(dew_point[:, None, None], grid)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 3))

    # The point path over the same hours, as a Central cell sees them
    local = np.array(
        [(start + k * HOUR).astimezone(ZoneInfo("America/Chicago")).replace(tzinfo=None) for k in range(n)],
        dtype="datetime64[h]",
    )
    rh = relative_humidity_percent(temperature, dew_point)
    days, point = features.daily_features(local, temperature, rh, np.zeros(n))
    for day in (date(2025, 7, 2), date(2025, 7, 3)):
        k = [str(d) for d in days].index(str(day))
        for name in (
            "hours_rh_over_90",
            "hours_temperature_over_20c",
            "hours_rh_over_80_from_8pm",
            "hours_rh_over_90_night",
            "temperature_mean_rh_over_80_from_8pm",
        ):
            grid_value = read(tmp_path, name, day)[:, 1:]  # Central columns
            np.testing.assert_allclose(grid_value, point[name][k], atol=0.05, err_msg=f"{name} {day}")
    assert read(tmp_path, "hours_rh_over_80_from_8pm", date(2025, 7, 2))[0, 1] > 0  # the test has humid hours


def test_a_store_from_before_new_features_opens_with_them_stale(tmp_path):
    from dataclasses import replace

    from agdata.catalog import DAILY_FEATURES, DAILY_VARIABLES
    from agdata.store import DAILY

    old = [v for name, v in DAILY_VARIABLES.items() if name not in DAILY_FEATURES]
    GridStore.create(tmp_path, DAILY, 2025, WINDOW, old)
    store = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values(), add_missing=True)
    assert store.stale == set(DAILY_FEATURES)
    store.mark_current(DAILY_FEATURES)
    assert GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values()).stale == set()
    bumped = [replace(v, version=2) if v.name == "hours_rh_over_90" else v for v in DAILY_VARIABLES.values()]
    assert GridStore.open(tmp_path, DAILY, 2025, bumped).stale == {"hours_rh_over_90"}
