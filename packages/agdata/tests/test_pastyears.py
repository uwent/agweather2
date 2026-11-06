"""Past years laid out for points (agdata.pastyears; D63's projection)."""

import shutil
from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata import pastyears
from agdata.catalog import DAILY_VARIABLES
from agdata.store import DAILY, GridStore
from agdata.testing import WINDOW

NAMES = ["air_temperature_min", "air_temperature_max", "precipitation_sum", "hours_rh_over_90"]


@pytest.fixture(scope="module")
def built(tmp_path_factory, fx_module):
    root = tmp_path_factory.mktemp("two-years")
    fx_module.archive(root, datetime(2023, 12, 20, tzinfo=UTC), datetime(2024, 1, 15, tzinfo=UTC), warm=10)
    return root


@pytest.fixture
def two_years(built, tmp_path):
    """The archive's hours Dec 20, 2023 to Jan 15, 2024, rolled up: a copy each test may change (~10 s to build)."""
    return shutil.copytree(built, tmp_path / "archive")


def daily_values(data_dir, j, i, first: date, last: date, name: str) -> np.ndarray:
    out = []
    for year in range(first.year, last.year + 1):
        store = GridStore.open(data_dir, DAILY, year, [DAILY_VARIABLES[name]])
        a = max(first, date(year, 1, 1))
        b = min(last, date(year, 12, 31))
        out.append(store.read_point(name, j, i, store.index_of(a), store.index_of(b) + 1))
    return np.concatenate(out)


def test_a_copy_reads_what_the_daily_store_holds_across_years(two_years):
    assert pastyears.stale_years(two_years, before=2025) == {2023: "missing", 2024: "missing"}
    for year in (2023, 2024):
        pastyears.build(two_years, year)
    assert pastyears.stale_years(two_years, before=2025) == {}
    j, i = WINDOW.j0 + 1, WINDOW.i0 + 2
    found = pastyears.Reader(two_years).read(j, i, date(2023, 12, 25), date(2024, 1, 10), NAMES)
    assert found is not None
    for name in NAMES:
        np.testing.assert_array_equal(
            found[name], daily_values(two_years, j, i, date(2023, 12, 25), date(2024, 1, 10), name)
        )
    assert np.isfinite(found["air_temperature_min"]).all()


def test_a_copy_goes_stale_when_its_daily_store_is_written(two_years):
    pastyears.build(two_years, 2024)
    store = GridStore.open(two_years, DAILY, 2024, [DAILY_VARIABLES["air_temperature_min"]])
    store.write(date(2024, 1, 5), {"air_temperature_min": np.full((1, *WINDOW.shape), 3.0)}, source="derived")
    assert pastyears.status(two_years, 2024) == pastyears.OUT_OF_DATE_DATA


def test_years_without_a_complete_copy_or_cells_outside_it_read_nothing(two_years):
    pastyears.build(two_years, 2024)
    reader = pastyears.Reader(two_years)
    assert reader.read(WINDOW.j0, WINDOW.i0, date(2023, 12, 30), date(2024, 1, 2), NAMES) is None  # 2023 has none
    assert reader.read(WINDOW.j0 - 5, WINDOW.i0, date(2024, 1, 2), date(2024, 1, 3), NAMES) is None  # off the window
    assert reader.read(WINDOW.j0, WINDOW.i0, date(2024, 1, 2), date(2024, 1, 3), ["not_a_variable"]) is None
    (pastyears.PAST.path(two_years, 2023).with_name("2023.zarr.part")).mkdir(parents=True)  # a build that crashed
    assert pastyears.status(two_years, 2023) == "missing"
