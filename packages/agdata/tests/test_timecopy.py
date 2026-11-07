"""The season-read copy of daily min and max (`agdata.timecopy`): kept by the rollup, read for a season over the map,
and never wrong when it's behind (days rewritten after it, a year rolled up before it, a stale variable)."""

import shutil
from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata import series, testing, timecopy
from agdata.catalog import DAILY_VARIABLES
from agdata.store import DAILY, GridStore

FIRST, LAST = date(2025, 7, 2), date(2025, 7, 9)  # the fixture's whole observed days
NOW = datetime(2025, 7, 10, 16, tzinfo=UTC)


@pytest.fixture(scope="module")
def built(tmp_path_factory, fx_module):
    path = tmp_path_factory.mktemp("timecopy")
    fx_module.archive(path, datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 10, 15, tzinfo=UTC))
    return path


@pytest.fixture
def world(built, tmp_path):
    """A copy of the archive for each test: they rewrite it."""
    shutil.copytree(built, tmp_path / "archive")
    return tmp_path / "archive"


def _daily(path) -> GridStore:
    return GridStore.open(path, DAILY, 2025, [DAILY_VARIABLES[name] for name in timecopy.NAMES])


def _season(path, name: str) -> np.ndarray:
    return series.grid_days(path, DAILY, name, FIRST, LAST, testing.WINDOW, NOW).values


def test_the_rollup_keeps_a_copy_with_the_daily_stores_values(world):
    daily = _daily(world)
    copy = GridStore.open(world, timecopy.COPY, 2025, timecopy.variables())
    t0, t1 = daily.index_of(FIRST), daily.index_of(LAST) + 1
    for name in timecopy.NAMES:
        np.testing.assert_array_equal(copy.read_packed(name, t0, t1), daily.read_packed(name, t0, t1))
    assert timecopy.behind(world, 2025) == 0


def test_a_season_reads_the_same_from_the_copy(world, monkeypatch):
    found = _season(world, "air_temperature_max")
    monkeypatch.setattr(timecopy, "MIN_DAYS", 10_000)  # every read from the daily store
    np.testing.assert_array_equal(found, _season(world, "air_temperature_max"))
    assert np.isfinite(found).all()


def test_days_rewritten_after_the_copy_come_from_the_daily_store(world):
    daily = _daily(world)
    day = date(2025, 7, 5)
    changed = np.full((1, *testing.WINDOW.shape), 40.0)
    daily.write(day, {"air_temperature_max": changed}, source="urma")  # the copy isn't told
    assert timecopy.behind(world, 2025) == 1
    found = _season(world, "air_temperature_max")
    assert np.allclose(found[(day - FIRST).days], 40.0)
    assert not np.allclose(found[0], 40.0)  # the others from the copy, as before
    assert timecopy.fill(world, 2025) == 1 and timecopy.behind(world, 2025) == 0
    copy = GridStore.open(world, timecopy.COPY, 2025, timecopy.variables())
    t = copy.index_of(day)
    assert np.allclose(copy.read_steps("air_temperature_max", t, t + 1), 40.0)


def test_a_year_rolled_up_before_the_copy_reads_the_daily_store_until_filled(world):
    expected = _season(world, "air_temperature_min")
    shutil.rmtree(timecopy.COPY.path(world, 2025))
    assert timecopy.behind(world, 2025) > 0
    np.testing.assert_array_equal(_season(world, "air_temperature_min"), expected)
    timecopy.fill(world, 2025)
    assert timecopy.behind(world, 2025) == 0
    np.testing.assert_array_equal(_season(world, "air_temperature_min"), expected)


def test_a_variable_stale_in_the_daily_store_is_read_from_it(world):
    copy = GridStore.open(world, timecopy.COPY, 2025, timecopy.variables())
    t0 = copy.index_of(FIRST)
    copy.write(FIRST, {"air_temperature_min": np.full((8, *testing.WINDOW.shape), -30.0)}, source="derived")
    assert np.allclose(copy.read_steps("air_temperature_min", t0, t0 + 1), -30.0)  # a copy that's now wrong
    daily = _daily(world)
    daily._array("air_temperature_min").attrs["version"] = 0  # written by older code: stale (D29)
    found = series.grid_days(world, DAILY, "air_temperature_min", FIRST, LAST, testing.WINDOW, NOW)
    assert found.stale.all() and not np.isclose(found.values, -30.0).any()  # the daily store's, flagged stale
