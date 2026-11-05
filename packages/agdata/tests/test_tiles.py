"""Web map tiles (`agdata.tiles`): each pixel's cell, and values packed into colors and back."""

import io

import numpy as np
from PIL import Image

from agdata import tiles
from agdata.grid import NDFD, Window

# About Wisconsin's southwest: 40 × 60 cells
WINDOW = Window(j0=880, j1=920, i0=1380, i1=1440)


def _a_tile(z: int) -> tuple[int, int]:
    lat, lon = NDFD.window_latlon(WINDOW)
    return tiles._tile_of(float(lon.mean()), float(lat.mean()), z)


def test_each_pixel_takes_the_cell_under_it():
    x, y = _a_tile(8)
    cells = tiles.index(WINDOW, 8, x, y)
    assert cells is not None and (cells >= 0).any()
    west, south, east, north = tiles.tile_bounds(8, x, y)
    lat, lon = NDFD.window_latlon(WINDOW)
    _, cols = np.divmod(np.flatnonzero(cells >= 0), tiles.SIZE)
    # A pixel's longitude is linear across the tile; its cell's center is within half a cell (~1.25 km) of it
    pixel_lon = west + (cols + 0.5) / tiles.SIZE * (east - west)
    cell = cells[cells >= 0]
    assert np.abs(lon.ravel()[cell] - pixel_lon).max() < 0.03
    assert south <= lat.ravel()[cell].min() + 0.03 and lat.ravel()[cell].max() - 0.03 <= north
    assert tiles.index(WINDOW, 8, x + 20, y) is None  # far east of the window


def test_values_come_back_from_the_png_to_their_step():
    rng = np.random.default_rng(1)
    values = np.round(rng.uniform(-40, 4000, WINDOW.shape), 1)
    values[3, 4] = np.nan
    x, y = _a_tile(7)
    cells = tiles.index(WINDOW, 7, x, y)
    assert cells is not None
    rgba = np.asarray(Image.open(io.BytesIO(tiles.png(tiles.data_tile(values, cells, step=0.1)))))
    back = tiles.decode(rgba, step=0.1).ravel()
    expected = np.where(cells >= 0, values.ravel()[np.clip(cells, 0, None)], np.nan)
    np.testing.assert_allclose(back, expected, atol=1e-6)
    assert (rgba[..., 3].ravel()[np.isnan(expected)] == 0).all()  # missing and outside are transparent


def test_maplibre_factors_decode_the_same():
    f = tiles.Encoding(step=0.5, unit="degF_day").factors
    r, g, b = 128, 1, 3  # code 2^23 + 259
    assert r * f["redFactor"] + g * f["greenFactor"] + b * f["blueFactor"] + f["baseShift"] == 259 * 0.5
    assert tiles.codes(np.array([1e12, -1e12]), 0.1).tolist() == [tiles.TOP, 1]  # clipped, never "missing"
