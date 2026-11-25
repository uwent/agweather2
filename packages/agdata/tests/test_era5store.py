"""ERA5-Land kept as received (D79, `agdata.era5store`)."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
import zarr

from agdata import era5store
from agdata.grid import LatLonGrid
from agdata.sources.era5land import Native

GRID = LatLonGrid(name="ERA5-Land 0.1°", first_lat=42.0, first_lon=-90.0, step=0.1, ny=3, nx=4)
HOUR = timedelta(hours=1)


def native(first: datetime, n: int, grid: LatLonGrid = GRID) -> Native:
    times = [first + k * HOUR for k in range(n)]
    base = np.arange(n, dtype=np.float32)[:, None, None] + np.zeros((1, grid.ny, grid.nx), dtype=np.float32)
    return Native(
        times=times, grid=grid, values={"stl1": base + 270, "stl2": base + 271, "stl3": base + 272, "sde": base / 100}
    )


def test_hours_come_back_as_written_across_a_new_year(tmp_path):
    first = datetime(2025, 12, 31, 20, tzinfo=UTC)
    assert era5store.write(tmp_path, native(first, 8)) == 8
    assert era5store.years(tmp_path) == [2025, 2026]
    back = era5store.read(tmp_path, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 5, tzinfo=UTC))
    assert back is not None and back.grid == GRID
    np.testing.assert_array_equal(back.values["stl1"][:4, 0, 0], [274, 275, 276, 277])
    assert np.isnan(back.values["sde"][4:]).all()  # never written
    held = era5store.written_hours(tmp_path, 2025)
    assert held.sum() == 4 and held[-4:].all()


def test_a_store_keeps_its_grid(tmp_path):
    era5store.write(tmp_path, native(datetime(2025, 7, 1, tzinfo=UTC), 2))
    other = LatLonGrid(name="ERA5-Land 0.1°", first_lat=42.1, first_lon=-90.0, step=0.1, ny=3, nx=4)
    with pytest.raises(ValueError, match="new store"):
        era5store.write(tmp_path, native(datetime(2025, 7, 2, tzinfo=UTC), 2, other))
    assert era5store.read(tmp_path, datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 7, 1, 1, tzinfo=UTC)) is None


def with_moisture(hours: Native, water: float) -> Native:
    shape = hours.values["stl1"].shape
    moisture = {name: np.full(shape, water, dtype=np.float32) for name in ("swvl1", "swvl2", "swvl3")}
    return Native(times=hours.times, grid=hours.grid, values=hours.values | moisture)


def test_a_store_from_before_soil_moisture_gains_it_and_a_file_without_it_leaves_it_alone(tmp_path):
    first = datetime(2025, 7, 1, tzinfo=UTC)
    era5store.write(tmp_path, native(first, 4))
    group = zarr.open_group(era5store.path(tmp_path, 2025), mode="r+")
    for name in ("swvl1", "swvl2", "swvl3"):
        del group[name]  # as a store made before soil moisture was asked for
    old = era5store.read(tmp_path, first, first + 3 * HOUR)
    assert old is not None and set(old.values) == {"stl1", "stl2", "stl3", "sde"}

    era5store.write(tmp_path, with_moisture(native(first, 2), 0.31))  # a month downloaded again
    era5store.write(tmp_path, native(first, 4))  # an older file written over it: no soil moisture in it
    back = era5store.read(tmp_path, first, first + 3 * HOUR)
    assert back is not None
    np.testing.assert_allclose(back.values["swvl2"][:, 0, 0], [0.31, 0.31, np.nan, np.nan])
    assert zarr.open_group(era5store.path(tmp_path, 2025), mode="r")["swvl1"].attrs["units"] == "m3 m-3"
