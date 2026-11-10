"""The coast rule for soil and snow on the 2.5 km grid (D79, `agdata.coast`): our own water mask, land-only
neighbours by the cubic B-spline, and the nearest land point within 40 km."""

import numpy as np

from agdata import coast
from agdata.grid import NDFD, LatLonGrid, Window
from agdata.sources import era5land


def cell(lat, lon):
    found = NDFD.cell_of(lat, lon)
    assert found is not None
    return found


def is_water(lat, lon) -> bool:
    j, i = cell(lat, lon)
    return bool(coast.water(Window(j0=j, j1=j + 1, i0=i, i1=i + 1))[0, 0])


def test_the_water_mask_is_the_great_lakes_and_not_the_islands():
    assert is_water(43.0, -87.5) and is_water(44.9, -87.8)  # Lake Michigan off Milwaukee; Green Bay
    assert is_water(47.5, -88.0)  # Lake Superior
    assert not is_water(43.07, -89.40)  # Madison
    assert not is_water(45.38, -86.92)  # Washington Island
    assert not is_water(46.80, -90.72)  # Madeline Island, the Apostles
    assert not is_water(44.02, -88.42)  # Lake Winnebago: no wave height, counted as land


def test_a_land_cell_without_land_neighbours_takes_the_nearest_land_within_40_km():
    j, i = cell(45.38, -86.92)  # Washington Island, among water cells of the source
    window = Window(j0=j - 1, j1=j + 2, i0=i - 1, i1=i + 2)
    lat, lon = NDFD.window_latlon(window)
    shape = (4, *window.shape)
    none = coast.Weights(cells=np.zeros(shape, dtype=np.int64), weights=np.zeros(shape))
    points = np.array([10, 11])  # one 10 km away, one 60 km
    point_lat = np.array([float(lat[1, 1]) + 0.09, float(lat[1, 1]) + 0.54])
    point_lon = np.array([float(lon[1, 1]), float(lon[1, 1])])
    weights, nearest = coast.finish(none, window, points, point_lat, point_lon)
    on_water = coast.water(window)
    land = ~on_water
    assert nearest[land].all() and not nearest[on_water].any()
    assert (weights.cells[0][land] == 10).all() and (weights.weights[0][land] == 1).all()
    values = np.array([[5.0], [7.0]])  # (points, hours) for points 10 and 11
    out = weights.apply(values, needed=np.array([10, 11]))[0]
    assert (out[land] == 5.0).all() and np.isnan(out[on_water]).all()
    far, nearest = coast.finish(none, window, points[1:], point_lat[1:], point_lon[1:])
    assert not nearest.any() and (far.weights == 0).all()  # 60 km: too far, missing


def test_land_only_weights_renormalize_over_the_land_neighbours():
    cells = np.array([0, 1, 2, 3])[:, None, None]
    weights = coast.Weights(cells=cells, weights=np.full((4, 1, 1), 0.25))
    kept = coast.land_only(weights, np.array([True, True, False, False])[:, None, None])
    out = kept.apply(np.array([[1.0], [3.0], [100.0], [100.0]]), needed=np.arange(4))
    assert out[0, 0, 0] == 2.0 and kept.needed.tolist() == [0, 1]


def test_the_b_spline_weights_are_positive_sum_to_one_and_keep_a_linear_field():
    t = np.linspace(0, 1, 101)[:-1]
    w = coast.bspline(t)
    assert (w >= 0).all() and (w[:3] > 0).all()  # only the far point gets nothing, and only at t = 0
    np.testing.assert_allclose(w.sum(axis=0), 1.0)
    np.testing.assert_allclose((w * np.array(coast.KERNEL_OFFSETS)[:, None]).sum(axis=0), t)  # a linear field


def window_grid(window: Window, values) -> tuple[LatLonGrid, era5land.LandMask]:
    """A 0.1° grid around the window, all land, its fraction from `values`' shape."""
    lat, lon = NDFD.window_latlon(window)
    south, west = np.floor(float(lat.min()) * 10) / 10 - 0.3, np.floor(float(lon.min()) * 10) / 10 - 0.3
    grid = LatLonGrid(name="test", first_lat=south, first_lon=west, step=0.1, ny=values.shape[0], nx=values.shape[1])
    return grid, era5land.LandMask(grid=grid, fraction=np.ones(values.shape))


def derived(window: Window, grid: LatLonGrid, land: era5land.LandMask, values: np.ndarray) -> np.ndarray:
    weights = era5land.coast_weights(grid, window, land)
    flat = values.reshape(-1)[weights.needed][:, None]
    return weights.apply(flat, needed=weights.needed)[0]


def test_a_lone_extreme_point_stays_within_its_neighbours_and_has_no_creases():
    j, i = cell(43.07, -89.40)  # Madison
    window = Window(j0=j, j1=j + 40, i0=i, i1=i + 40)  # ~100 km
    values = np.zeros((24, 24))
    grid, land = window_grid(window, values)
    lat, lon = NDFD.window_latlon(window)
    fj, fi = grid.fractional_index(lat, lon)
    pj, pi = round(float(fj[20, 20])), round(float(fi[20, 20]))
    values[pj, pi] = 10.0  # one warm 0.1° point among zeros, under the window's middle
    out = derived(window, grid, land, values)
    assert np.isfinite(out).all()
    assert out.min() >= 0.0 and out.max() <= 10.0  # positive weights: no overshoot below or above
    assert 3.0 < out.max() < 6.0  # softened, as an area's mean: the B-spline's own peak is (2/3)² × 10 ≈ 4.4
    # Smooth: no crease along the source's cell lines, where bilinear's slope jumps. The largest change in slope
    # between neighbouring cells, against bilinear's
    tent = np.clip(1 - np.abs(fj - pj), 0, None) * np.clip(1 - np.abs(fi - pi), 0, None) * 10.0

    def kink(field):
        return np.abs(np.diff(field, n=2, axis=1)).max()

    assert kink(out) < kink(tent) / 2


def test_water_neighbours_dropped_from_the_b_spline_cannot_push_a_value_past_the_land_ones():
    j, i = cell(43.07, -89.40)
    window = Window(j0=j, j1=j + 20, i0=i, i1=i + 20)
    rng = np.random.default_rng(0)
    values = rng.uniform(-5.0, 5.0, (12, 12))
    grid, land = window_grid(window, values)
    fraction = (rng.uniform(size=values.shape) > 0.4).astype(float)  # a ragged shore
    land = era5land.LandMask(grid=grid, fraction=fraction)
    values = np.where(fraction >= 0.5, values, 99.0)  # the lake's value on water points
    out = derived(window, grid, land, values)
    assert np.nanmax(out) <= 5.0 and np.nanmin(out) >= -5.0
