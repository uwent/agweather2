import numpy as np
import pytest

from agdata.grid import NDFD, Window
from agdata.regrid import latlon_index

WINDOW = Window(j0=900, j1=940, i0=1440, i1=1480)  # ~100 km square in southern Wisconsin


def _cells():
    jj, ii = np.mgrid[WINDOW.j0 : WINDOW.j1, WINDOW.i0 : WINDOW.i1]
    return (jj * 10_000 + ii).astype(float)[None]  # each cell's value names it


def _bounds():
    lat, lon = NDFD.window_latlon(WINDOW)
    return float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())


def test_points_sit_on_multiples_of_the_step():
    index = latlon_index(WINDOW, *_bounds(), 0.1, "nearest")
    assert np.allclose(index.lats * 10, np.round(index.lats * 10)) and index.lats[0] >= _bounds()[0]
    assert (np.diff(index.lons) > 0).all()


def test_nearest_takes_the_cell_under_each_point():
    index = latlon_index(WINDOW, *_bounds(), 0.05, "nearest")
    out = index.resample(_cells())[0]
    for r, c in [(0, 0), (3, 5), (len(index.lats) - 1, len(index.lons) - 1)]:
        cell = NDFD.cell_of(float(index.lats[r]), float(index.lons[c]))
        if cell is not None and WINDOW.contains(*cell):
            assert out[r, c] == cell[0] * 10_000 + cell[1]
        else:
            assert np.isnan(out[r, c])


def test_mean_averages_the_cells_within_half_a_step():
    index = latlon_index(WINDOW, *_bounds(), 0.1, "mean")
    values = np.ones((1, *WINDOW.shape))
    values[0, :5] = 3.0
    values[0, 5, 5] = np.nan  # left out, not counted
    out = index.resample(values)[0]
    lat, lon = NDFD.window_latlon(WINDOW)
    r, c = 2, 2
    inside = (np.abs(lat - index.lats[r]) <= 0.05) & (np.abs(lon - index.lons[c]) <= 0.05) & np.isfinite(values[0])
    assert out[r, c] == pytest.approx(values[0][inside].mean())


def test_steps_finer_than_the_grid_are_refused():
    with pytest.raises(ValueError, match="finer"):
        latlon_index(WINDOW, *_bounds(), 0.01, "nearest")
