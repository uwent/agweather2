"""Past years laid out for points (agdata.pastyears; D63's projection)."""

import fcntl
import os
import shutil
import threading
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


def test_a_projections_stamp_follows_what_the_reader_reads(two_years):
    """A year with a copy is stamped by it (written to the daily store, it reads and stamps the same until rebuilt);
    a year without one, or a read the copy can't serve, by its hours."""
    from agdata import series

    cell = [(WINDOW.j0 + 1, WINDOW.i0 + 2)]
    assert pastyears.stamp(two_years, 2024, NAMES, cell) is None
    without = series.past_years_stamp(two_years, cells=cell, years=[2023, 2024], names=NAMES)
    pastyears.build(two_years, 2024)
    built = pastyears.stamp(two_years, 2024, NAMES, cell)
    assert built is not None
    with_copy = series.past_years_stamp(two_years, cells=cell, years=[2023, 2024], names=NAMES)
    assert with_copy != without and with_copy.split(";")[0] == without.split(";")[0]  # 2023 still by its hours
    assert pastyears.stamp(two_years, 2024, ["not_a_variable"], cell) is None
    assert pastyears.stamp(two_years, 2024, NAMES, [(WINDOW.j0 - 5, WINDOW.i0)]) is None
    pastyears.build(two_years, 2024)  # rebuilt from the same data: the same values, the same stamp
    assert pastyears.stamp(two_years, 2024, NAMES, cell) == built
    store = GridStore.open(two_years, DAILY, 2024, [DAILY_VARIABLES["air_temperature_min"]])
    store.write(date(2024, 1, 5), {"air_temperature_min": np.full((1, *WINDOW.shape), 3.0)}, source="derived")
    assert pastyears.stamp(two_years, 2024, NAMES, cell) == built  # the reader still reads the copy
    pastyears.build(two_years, 2024)
    assert pastyears.stamp(two_years, 2024, NAMES, cell) != built


def test_years_without_a_complete_copy_or_cells_outside_it_read_nothing(two_years):
    pastyears.build(two_years, 2024)
    reader = pastyears.Reader(two_years)
    assert reader.read(WINDOW.j0, WINDOW.i0, date(2023, 12, 30), date(2024, 1, 2), NAMES) is None  # 2023 has none
    assert reader.read(WINDOW.j0 - 5, WINDOW.i0, date(2024, 1, 2), date(2024, 1, 3), NAMES) is None  # off the window
    assert reader.read(WINDOW.j0, WINDOW.i0, date(2024, 1, 2), date(2024, 1, 3), ["not_a_variable"]) is None
    (pastyears.PAST.path(two_years, 2023).with_name("2023.zarr.part")).mkdir(parents=True)  # a build that crashed
    assert pastyears.status(two_years, 2023) == "missing"


def test_a_copy_read_while_its_replacement_is_swapped_in_reads_as_missing(two_years):
    pastyears.build(two_years, 2024)
    path = pastyears.PAST.path(two_years, 2024)
    (path / "zarr.json").unlink()  # what a reader saw mid-swap before builds swapped by renames
    assert pastyears.status(two_years, 2024) == "missing"
    assert pastyears.Reader(two_years).read(WINDOW.j0, WINDOW.i0, date(2024, 1, 2), date(2024, 1, 3), NAMES) is None
    pastyears.build(two_years, 2024)  # a rebuild replaces it whole, leaving nothing beside it
    assert pastyears.status(two_years, 2024) is None
    assert sorted(p.name for p in path.parent.iterdir()) == ["2024.zarr"]


def test_a_copy_marked_complete_without_its_array_is_incomplete_and_reads_nothing(two_years):
    """What two builds at once left of 2017's copy on dev (2026-11-09): the projection's read raised KeyError."""
    pastyears.build(two_years, 2024)
    path = pastyears.PAST.path(two_years, 2024)
    (path / "values" / "zarr.json").unlink()
    assert pastyears.status(two_years, 2024) == "incomplete"
    assert pastyears.stale_years(two_years, before=2025)[2024] == "incomplete"
    assert pastyears.Reader(two_years).read(WINDOW.j0, WINDOW.i0, date(2024, 1, 2), date(2024, 1, 3), NAMES) is None


def test_builds_take_turns(two_years):
    """A build waits while another holds the copies' folder, then builds whole."""
    folder = pastyears.PAST.path(two_years, 2024).parent
    folder.mkdir(parents=True, exist_ok=True)
    held = os.open(folder, os.O_RDONLY)
    fcntl.flock(held, fcntl.LOCK_EX)
    builder = threading.Thread(target=pastyears.build, kwargs={"data_dir": two_years, "year": 2024})
    builder.start()
    builder.join(timeout=1)
    assert builder.is_alive() and pastyears.status(two_years, 2024) == "missing"
    os.close(held)
    builder.join(timeout=60)
    assert not builder.is_alive() and pastyears.status(two_years, 2024) is None
