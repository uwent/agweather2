"""gridMET's adapter (`agdata.sources.gridmet`): cropping a file as received, reading it into our units, and the
B-spline to our grid with the coast rule. The fixtures are gridMET's own 2020 files cropped at Lake Michigan's shore
(`fixtures/make_gridmet.py`)."""

from datetime import date
from pathlib import Path

import h5py
import numpy as np
import pytest

from agdata.coast import water
from agdata.grid import NDFD, Box, LatLonGrid, Window
from agdata.sources import gridmet

FIXTURES = Path(__file__).parent / "fixtures" / "gridmet"
TMMX = FIXTURES / "tmmx_2020.nc"
PR = FIXTURES / "pr_2020.nc"
SHORE = NDFD.window_for(Box(south=43.72, west=-87.88, north=43.84, east=-87.72))  # 8 × 7 cells, 4 on the lake


def raw(path: Path) -> tuple[np.ndarray, dict, np.ndarray, np.ndarray]:
    with h5py.File(path) as f:
        data = gridmet._dataset(f, gridmet._data_variable(f))
        return np.asarray(data[()]), dict(data.attrs), gridmet._array(f, "lat"), gridmet._array(f, "lon")


def test_fetch_keeps_the_box_as_received(tmp_path):
    dest = tmp_path / "tmmx" / "2020.nc"
    box = Box(south=43.7, west=-87.9, north=43.9, east=-87.6)
    size = gridmet.fetch(str(TMMX), dest, box)
    assert size == dest.stat().st_size and gridmet.kept(dest)
    assert not dest.with_name("2020.nc.part").exists()
    values, attrs, lat, _ = raw(dest)
    whole, whole_attrs, whole_lat, whole_lon = raw(TMMX)
    rows = (whole_lat >= box.south) & (whole_lat <= box.north)
    cols = (whole_lon >= box.west) & (whole_lon <= box.east)
    assert values.dtype == whole.dtype == np.uint16
    np.testing.assert_array_equal(values, whole[:, rows][:, :, cols])
    np.testing.assert_array_equal(lat, whole_lat[rows])
    for key in ("scale_factor", "add_offset", "_FillValue", "units"):
        np.testing.assert_array_equal(np.asarray(attrs[key]), np.asarray(whole_attrs[key]))
    with h5py.File(dest) as f:
        assert f.attrs["agweather_source"] == str(TMMX)


def test_fetch_refuses_a_box_outside_the_file(tmp_path):
    with pytest.raises(ValueError, match="covers none"):
        gridmet.fetch(str(TMMX), tmp_path / "x.nc", Box(south=30, west=-100, north=31, east=-99))
    assert not (tmp_path / "x.nc").exists()


def test_kept_tells_netcdf4_from_the_subsetting_services_netcdf3(tmp_path):
    old = tmp_path / "old.nc"
    old.write_bytes(b"CDF\x01" + bytes(100))
    assert not gridmet.kept(old)
    assert not gridmet.kept(tmp_path / "none.nc")
    assert gridmet.kept(TMMX)


def test_read_unpacks_into_our_units_south_to_north():
    values, attrs, lat, _ = raw(TMMX)
    year = gridmet.read(TMMX, "tmmx")
    assert year.days == [date(2020, 1, d) for d in range(1, 6)]
    assert lat[0] > lat[-1] and year.grid.first_lat == pytest.approx(lat[-1], abs=1e-6)  # flipped
    fill = np.asarray(attrs["_FillValue"]).ravel()[0]
    expected = values.astype(np.float64) * float(attrs["scale_factor"][0]) + float(attrs["add_offset"][0]) - 273.15
    expected[values == fill] = np.nan
    np.testing.assert_allclose(year.values, expected[:, ::-1], atol=1e-4)
    assert np.isnan(year.values).any() and (np.isnan(year.values) == (values[:, ::-1] == fill)).all()  # the lake
    rain = gridmet.read(PR, "pr")
    assert rain.source.daily == "precipitation_sum" and np.nanmin(rain.values) >= 0  # mm as gridMET gives them


def test_regrid_is_exact_on_a_linear_field():
    window = Window(j0=1000, j1=1010, i0=1400, i1=1412)  # inland Wisconsin, no water
    box = gridmet.extent(window)
    lat = np.arange(np.floor(box.south * 24), np.ceil(box.north * 24) + 1) / 24
    lon = np.arange(np.floor(box.west * 24), np.ceil(box.east * 24) + 1) / 24
    grid = LatLonGrid(name="t", first_lat=lat[0], first_lon=lon[0], step=gridmet.STEP, ny=lat.size, nx=lon.size)
    jj, ii = np.meshgrid(np.arange(lat.size), np.arange(lon.size), indexing="ij")
    field = (2.0 * jj + 0.5 * ii + 3.0).astype(np.float32)
    year = gridmet.Year(source=gridmet.BY_NAME["tmmx"], days=[date(2001, 1, 1)], values=field[None], grid=grid)
    got = gridmet.regrid(year, window)[0]
    cell_lat, cell_lon = NDFD.window_latlon(window)
    fj, fi = grid.fractional_index(cell_lat, cell_lon)
    np.testing.assert_allclose(got, 2.0 * fj + 0.5 * fi + 3.0, atol=1e-4)


def test_regrid_leaves_our_water_missing_and_fills_the_shore_from_land():
    year = gridmet.read(TMMX, "tmmx")
    got = gridmet.regrid(year, SHORE)
    on_water = water(SHORE)
    assert on_water.any() and (~on_water).any()
    assert np.isnan(got[:, on_water]).all()
    assert np.isfinite(got[:, ~on_water]).all()
    land = year.values[0][np.isfinite(year.values[0])]
    assert land.min() - 1e-4 <= np.nanmin(got[0]) and np.nanmax(got[0]) <= land.max() + 1e-4  # positive weights


def test_a_missing_day_at_a_point_renormalizes_its_neighbours():
    year = gridmet.read(TMMX, "tmmx")
    values = year.values.copy()
    land = np.flatnonzero(np.isfinite(values[1]).ravel())
    values[1].ravel()[land[::3]] = np.nan  # a third of the land points missing on one day
    holed = gridmet.Year(source=year.source, days=year.days, values=values, grid=year.grid)
    got = gridmet.regrid(holed, SHORE)
    assert np.isfinite(got[1][~water(SHORE)]).all()
    np.testing.assert_allclose(got[0], gridmet.regrid(year, SHORE)[0], atol=1e-5)  # other days unchanged


def test_extent_covers_the_windows_curved_edges():
    window = Window(j0=900, j1=1100, i0=1350, i1=1600)
    box = gridmet.extent(window, margin=0.0)
    lat, lon = NDFD.window_latlon(window)
    assert box.south == pytest.approx(lat.min()) and box.east == pytest.approx(lon.max())
    wider = gridmet.extent(window)
    assert wider.south == pytest.approx(box.south - gridmet.MARGIN)
