import json
from pathlib import Path

import numpy as np
import pytest

from agdata.grid import BOXES, NDFD, Box, Window, parse_box, service_window

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ndfd_points.json").read_text())


def test_cell_centers_match_the_grib_grid():
    points = FIXTURE["points"]
    assert (FIXTURE["ny"], FIXTURE["nx"]) == (NDFD.ny, NDFD.nx)
    lat, lon = NDFD.latlon([p["j"] for p in points], [p["i"] for p in points])
    np.testing.assert_allclose(lat, [p["lat"] for p in points], atol=1e-5)
    np.testing.assert_allclose(lon, [p["lon"] for p in points], atol=1e-5)


def test_cell_of_inverts_latlon():
    for p in FIXTURE["points"]:
        assert NDFD.cell_of(p["lat"], p["lon"]) == (p["j"], p["i"])


def test_points_off_the_grid():
    assert NDFD.cell_of(10.0, -95.0) is None
    assert NDFD.cell_of(43.07, -89.40) is not None  # Madison


def test_older_urma_grids_are_aligned_subwindows():
    # Before 2017-05-01 URMA used a 2145-column grid; the 2017-18 precip files a 2145 x 1377 one. Both start here
    assert NDFD.offset_of(20.191999, 238.445999) == (0, 200)
    with pytest.raises(ValueError):
        NDFD.offset_of(20.2, 238.5)


def test_wisconsin_window_covers_the_state_and_fits_older_grids():
    window = service_window("wisconsin")
    box = BOXES["wisconsin"]
    assert box
    lat, _lon = NDFD.window_latlon(window)
    # Every corner of the box is inside the window
    for corner in [(box.south, box.west), (box.south, box.east), (box.north, box.west), (box.north, box.east)]:
        cell = NDFD.cell_of(*corner)
        assert cell and window.contains(*cell)
    assert lat.shape == window.shape
    assert 200 < window.shape[0] < 300 and 200 < window.shape[1] < 300
    # Inside the 2145 x 1377 grid of the 2017-18 precip files (columns 200 on, rows 0-1376)
    assert window.i0 >= 200 and window.j1 <= 1377


def test_presets_and_explicit_boxes():
    assert service_window("conus") == NDFD.window
    assert parse_box(" Wisconsin ") == BOXES["wisconsin"]
    assert parse_box("40,-95,45,-85") == Box(40, -95, 45, -85)
    um = service_window("upper_midwest")
    wi = service_window("wisconsin")
    assert um.j0 <= wi.j0 and um.i0 <= wi.i0 and um.j1 >= wi.j1 and um.i1 >= wi.i1
    with pytest.raises(ValueError):
        parse_box("iowa")
    with pytest.raises(ValueError):
        parse_box("45,-95,40,-85")


def test_window_local_indices():
    window = Window(10, 20, 30, 40)
    assert window.shape == (10, 10)
    assert window.local(10, 39) == (0, 9)
    with pytest.raises(IndexError):
        window.local(20, 30)
