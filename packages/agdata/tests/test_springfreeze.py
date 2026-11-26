"""The area-wide normal freeze dates (`agdata.springfreeze`, D127)."""

import math

import numpy as np
import pytest

from agdata import springfreeze
from agdata.grid import NDFD, Window
from agdata.springfreeze import RADIUS_KM, SIGMA_KM, kernel, smooth


def test_the_kernel_is_areas_center_weighting_cut_at_the_radius():
    """A Gaussian with σ = radius / 2 (`agdata.areas`' `center`), zero past RADIUS_KM, by the grid's spacing."""
    k = kernel()
    r = k.shape[0] // 2
    km = NDFD.dx / 1000
    assert k.shape == (2 * r + 1, 2 * r + 1) and r == math.floor(RADIUS_KM / km) == 19
    assert k[r, r] == 1.0 and SIGMA_KM == RADIUS_KM / 2
    assert k[r, r + 10] == pytest.approx(math.exp(-((10 * km) ** 2) / (2 * SIGMA_KM**2)))
    assert k[r + 14, r + 14] == 0.0  # 50.3 km away
    assert k[r + 13, r + 13] > 0  # 46.7 km
    np.testing.assert_array_equal(k, k.T)
    np.testing.assert_array_equal(k, k[::-1])


def _direct(values: np.ndarray, land: np.ndarray) -> np.ndarray:
    """The weighted mean cell by cell, as a reference for `smooth`'s FFT."""
    k = kernel()
    r = k.shape[0] // 2
    use = land & np.isfinite(values)
    out = np.full(values.shape, np.nan)
    for y in range(values.shape[0]):
        for x in range(values.shape[1]):
            if not np.isfinite(values[y, x]):
                continue
            total = weight = 0.0
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < values.shape[0] and 0 <= xx < values.shape[1] and use[yy, xx]:
                        total += k[r + dy, r + dx] * values[yy, xx]
                        weight += k[r + dy, r + dx]
            if weight > 0:
                out[y, x] = total / weight
    return out


def test_smoothing_is_the_weighted_mean_over_land_with_a_value():
    rng = np.random.default_rng(3)
    values = 100 + 20 * rng.random((30, 45))
    values[:4, :] = np.nan  # past the coverage
    values[20, 30] = np.nan
    land = np.ones(values.shape, dtype=bool)
    land[10:14, 5:12] = False  # a lake
    found = smooth(values, land)
    np.testing.assert_allclose(found, _direct(values, land), atol=1e-9)
    assert np.isnan(found[:4]).all() and np.isnan(found[20, 30])  # missing where the cell's own is
    assert np.isfinite(found[10:14, 5:12]).all()  # a lake cell takes the land around it


def test_missing_cells_and_water_dont_pull_the_mean():
    """An even field stays even to the coverage's edge, and a lake's late dates don't move the shore's."""
    values = np.full((40, 40), 110.0)
    values[:, :8] = np.nan  # past the coverage
    land = np.ones(values.shape, dtype=bool)
    land[15:25, 25:35] = False
    values[15:25, 25:35] = 150.0  # the lake's own dates
    found = smooth(values, land)
    np.testing.assert_allclose(found[:, 8:], 110.0)
    assert np.isnan(found[:, :8]).all()


def test_a_frost_pocket_is_averaged_away():
    values = np.full((41, 41), 110.0)
    values[20, 20] = 130.0  # three weeks later than the farms around it
    found = smooth(values, np.ones(values.shape, dtype=bool))
    assert found[20, 20] < 110.2


def test_a_point_reads_its_map_cell(tmp_path):
    """`at` gives exactly `within`'s value for the cell, whatever window the map was read over; NaN past the normals'
    area and everywhere before they're built."""
    from agdata.testing import freeze_normal

    window = Window(j0=1000, j1=1030, i0=1400, i1=1440)
    assert np.isnan(springfreeze.within(tmp_path, springfreeze.SPRING_28, window)).all()
    rng = np.random.default_rng(5)
    slots = np.round(100 + 30 * rng.random(window.shape))
    slots[:, :3] = np.nan
    freeze_normal(tmp_path, window, slots)
    part = Window(j0=1010, j1=1050, i0=1395, i1=1420)  # reaching past the store
    found = springfreeze.within(tmp_path, springfreeze.SPRING_28, part)
    assert np.isnan(found[20:]).all() and np.isnan(found[:, :8]).all() and np.isfinite(found[:20, 8:]).all()
    for y, x in ((0, 8), (7, 12), (19, 24)):
        j, i = part.j0 + y, part.i0 + x
        assert springfreeze.at(tmp_path, springfreeze.SPRING_28, j, i) == found[y, x]
    assert np.nanstd(found) < np.nanstd(slots) / 3  # the noise averaged out
