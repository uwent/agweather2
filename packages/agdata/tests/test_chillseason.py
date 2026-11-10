"""Chill portions on the grid (agdata.chillseason, D76): the Dynamic model's running total from October 1."""

import shutil
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import chillseason
from agdata.catalog import CUMULATIVE_VARIABLES, VARIABLES
from agdata.daily import _HourlyReader
from agdata.store import CUMULATIVE, HOURLY, GridStore
from agdata.testing import WINDOW
from agdata.timezones import GRID_ZONE, day_bounds
from agmodels import chill

FIRST, LAST = datetime(2025, 9, 20, tzinfo=UTC), datetime(2025, 10, 25, 23, tzinfo=UTC)


@pytest.fixture(scope="module")
def built(tmp_path_factory, fx_module):
    """Hours September 20 to October 25, 2025 at 6 °C ± 6 (chill most hours), rolled up."""
    root = tmp_path_factory.mktemp("chill")
    fx_module.archive(root, FIRST, LAST, warm=6)
    return root


@pytest.fixture
def archive(built, tmp_path):
    return shutil.copytree(built, tmp_path / "archive")


def stored(data_dir, name: str, first: date, last: date) -> np.ndarray:
    store = GridStore.open(data_dir, CUMULATIVE, first.year, CUMULATIVE_VARIABLES.values(), add_missing=True)
    return store.read_steps(name, store.index_of(first), store.index_of(last) + 1)


def direct(data_dir, first: date, last: date) -> np.ndarray:
    """agmodels.chill.dynamic on the archive's hours of first..last, each day's running total."""
    begin = day_bounds(first, GRID_ZONE)[0]
    hours = _HourlyReader(data_dir).read(
        "air_temperature", begin, begin + timedelta(days=(last - first).days + 1), WINDOW
    )
    portions, _, _ = chill.dynamic(hours)
    return np.cumsum(portions.reshape(-1, 24, *WINDOW.shape).sum(axis=1), axis=0)


def test_a_season_starts_on_october_1_and_matches_the_model(built):
    october = stored(built, "chill_portions", date(2025, 10, 1), date(2025, 10, 24))
    expected = direct(built, date(2025, 10, 1), date(2025, 10, 24))
    np.testing.assert_allclose(october, expected, atol=0.01)  # stored at 0.01
    assert october[-1].min() > 5
    assert (stored(built, "chill_missing_hours", date(2025, 10, 1), date(2025, 10, 24)) == 0).all()
    # The season before: nothing rolled up before September 21, so its missing hours count back to October 1, 2024
    september = stored(built, "chill_missing_hours", date(2025, 9, 21), date(2025, 9, 21))
    assert (september == 24 * (date(2025, 9, 21) - date(2024, 10, 1)).days).all()


def test_an_update_from_a_later_day_carries_the_state_on(archive):
    before = stored(archive, "chill_portions", date(2025, 10, 1), date(2025, 10, 24))
    chillseason.update(archive, WINDOW, date(2025, 10, 12), date(2025, 10, 12))  # and the days written after it
    after = stored(archive, "chill_portions", date(2025, 10, 1), date(2025, 10, 24))
    np.testing.assert_allclose(after, before, atol=0.011)  # the state read back at 0.001


def test_missing_hours_hold_the_state_and_are_counted(archive):
    store = GridStore.open(archive, HOURLY, 2025, VARIABLES.values())
    gap = datetime(2025, 10, 10, 12, tzinfo=UTC)
    store.write(gap, {"air_temperature": np.full((5, *WINDOW.shape), np.nan)}, source="urma")
    chillseason.update(archive, WINDOW, date(2025, 10, 10), date(2025, 10, 10))
    missing = stored(archive, "chill_missing_hours", date(2025, 10, 9), date(2025, 10, 11))
    assert (missing[0] == 0).all() and (missing[1] == 5).all() and (missing[2] == 5).all()
    portions = stored(archive, "chill_portions", date(2025, 10, 24), date(2025, 10, 24))[0]
    assert np.isfinite(portions).all()


def test_a_forecast_run_carries_on_from_the_archive_or_writes_nothing(archive, tmp_path):
    run = tmp_path / "run"
    shutil.copytree(archive, run)
    assert chillseason.update(run, WINDOW, date(2025, 10, 20), date(2025, 10, 24), base_dir=archive) is not None
    np.testing.assert_allclose(
        stored(run, "chill_portions", date(2025, 10, 20), date(2025, 10, 24)),
        stored(archive, "chill_portions", date(2025, 10, 20), date(2025, 10, 24)),
        atol=0.011,
    )
    empty = tmp_path / "empty"
    empty.mkdir()
    assert chillseason.update(run, WINDOW, date(2025, 10, 20), date(2025, 10, 24), base_dir=empty) is None
