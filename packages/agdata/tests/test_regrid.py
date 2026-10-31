import numpy as np
import pytest

from agdata.grid import NDFD, LatLonGrid, Window, service_window
from agdata.regrid import bilinear_weights, regrid
from agdata.sources.hrrr import HRRR_GRID


def test_a_linear_field_regrids_exactly():
    # A field linear in the source grid's projected x and y is reproduced exactly by bilinear interpolation
    jj, ii = np.mgrid[0 : HRRR_GRID.ny, 0 : HRRR_GRID.nx]
    field = 2.0 * jj + 0.5 * ii
    window = service_window("wisconsin")
    out = regrid(field, HRRR_GRID, window)
    lat, lon = NDFD.window_latlon(window)
    fj, fi = HRRR_GRID.fractional_index(lat, lon)
    np.testing.assert_allclose(out, 2.0 * fj + 0.5 * fi, atol=1e-9)


def test_missing_neighbors_and_cells_outside_the_source_are_nan():
    window = Window(j0=800, j1=810, i0=1400, i1=1410)
    field = np.ones((HRRR_GRID.ny, HRRR_GRID.nx))
    w = bilinear_weights(HRRR_GRID, window)
    field[w.j0[1, 1], w.i0[1, 1]] = np.nan
    out = regrid(field, HRRR_GRID, window)
    # Neighboring 2.5 km cells can share a 3 km source corner, so check a cell well away from it
    assert np.isnan(out[1, 1]) and np.isfinite(out[9, 9])
    # NDFD's far northwest corner is beyond HRRR's grid
    corner = regrid(np.ones((HRRR_GRID.ny, HRRR_GRID.nx)), HRRR_GRID, Window(j0=1590, j1=1597, i0=0, i1=5))
    assert np.isnan(corner).all()


def test_shape_is_checked():
    with pytest.raises(ValueError):
        regrid(np.ones((10, 10)), HRRR_GRID, Window(j0=0, j1=2, i0=0, i1=2))


def test_a_latlon_field_linear_in_degrees_regrids_exactly():
    source = LatLonGrid(name="0.1°", first_lat=41.0, first_lon=-93.5, step=0.1, ny=30, nx=40)
    jj, ii = np.mgrid[0 : source.ny, 0 : source.nx]
    lat_of, lon_of = source.first_lat + 0.1 * jj, source.first_lon + 0.1 * ii
    window = Window(j0=850, j1=870, i0=1400, i1=1420)
    out = regrid(3.0 * lat_of - 2.0 * lon_of, source, window)
    lat, lon = NDFD.window_latlon(window)
    np.testing.assert_allclose(out, 3.0 * lat - 2.0 * lon, atol=1e-9)
