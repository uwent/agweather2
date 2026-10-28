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
