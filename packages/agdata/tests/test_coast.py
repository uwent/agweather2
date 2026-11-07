"""The coast rule for soil and snow on the 2.5 km grid (D79, `agdata.coast`): our own water mask, land-only
neighbours, and the nearest land point within 20 km."""

import numpy as np

from agdata import coast
from agdata.grid import NDFD, Window


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
