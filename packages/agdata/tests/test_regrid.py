import numpy as np
import pytest

from agdata.grid import NDFD, Window, service_window
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
