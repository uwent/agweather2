"""Map images' drawing pieces (`agdata.mapimage`, Phase 6 H): ticks, isolines, the graticule, and a scale's middle
(`palettes.position`)."""

import io

import numpy as np
from PIL import Image

from agdata import mapimage, palettes
from agdata.grid import NDFD, Window


def fahrenheit(v):
    return np.asarray(v) * 1.8 + 32


def test_a_middle_pins_the_palettes_middle_and_stretches_each_half():
    np.testing.assert_allclose(palettes.position(np.array([0.0, 5.0, 10.0]), (0, 10)), [0, 0.5, 1])
    pinned = palettes.position(np.array([-10.0, 0.0, 15.0, 30.0, 99.0, np.nan]), (-10, 30), middle=0.0)
    np.testing.assert_allclose(pinned[:5], [0, 0.5, 0.75, 1, 1])
    assert np.isnan(pinned[5])
    one_side = palettes.position(np.array([5.0, 10.0]), (5, 10), middle=5.0)  # every value above the middle
    np.testing.assert_allclose(one_side, [0.5, 1])
    colors = palettes.colorize(np.array([0.0]), palettes.PALETTES["BuYlRd"], (-10, 30), middle=0.0)
    middle_color = palettes.PALETTES["BuYlRd"].colors[5]  # the 6th of 11: the pale middle
    assert tuple(colors[0, :3]) == palettes.rgb(middle_color)


def test_ticks_every_n_in_the_shown_unit_with_the_middle_labelled():
    domain = (-20.0, 20.0)  # °C: -4 to 68 °F
    marks = mapimage.ticks(domain, fahrenheit, middle=0.0, every=5)
    shown = fahrenheit(np.array(marks.values))
    np.testing.assert_allclose(shown, sorted({*range(0, 70, 5), 32}))  # -4 to 68 °F: every 5, and the middle
    labelled = [label for label in marks.labels if label]
    assert "32" in labelled and len(labelled) <= mapimage.MAX_LABELS + 1
    assert "30" not in labelled and "35" not in labelled  # beside the middle's label, left off
    auto = mapimage.ticks(domain, fahrenheit)
    assert 3 <= len(auto.values) <= 7 and all(auto.labels)


def test_isolines_fall_inside_the_values_and_smoothing_keeps_gaps():
    values = np.add.outer(np.linspace(0, 10, 40), np.zeros(30))  # rising south to north, °C
    values[5:8, 5:8] = np.nan
    levels = mapimage.isoline_levels(values, (0, 10), fahrenheit, False, None, 4.0)
    assert levels and all(0 < v < 10 for v in levels)
    np.testing.assert_allclose(fahrenheit(np.array(levels)) % 4, 0, atol=1e-9)
    auto = mapimage.isoline_levels(values, (0, 10), fahrenheit, False, None, "auto")
    assert set(auto) <= set(mapimage.ticks((0, 10), fahrenheit).values)
    smooth = mapimage.smoothed(values)
    assert np.isnan(smooth[5:8, 5:8]).all() and np.isfinite(smooth[10:, :]).all()
    np.testing.assert_allclose(smooth[20, 15], values[20, 15], atol=1e-6)  # a linear field keeps its value inside


def test_the_graticule_steps_by_the_maps_extent_and_finds_its_crossings():
    assert mapimage.graticule_step(5.0) == 1.0 and mapimage.graticule_step(1.5) == 0.5
    assert mapimage.graticule_step(0.6) == 0.25
    assert mapimage._crossing(np.array([0.0, 2.0, 4.0]), np.array([10.0, 20.0, 30.0]), 3.0) == 25.0
    assert mapimage._crossing(np.array([0.0, 1.0]), np.array([0.0, 1.0]), 5.0) is None
    assert mapimage._degrees(-89.5, "E", "W") == "89.5°W" and mapimage._degrees(44.0, "N", "S") == "44°N"


def test_a_map_draws_with_a_middle_isolines_and_its_graticule():
    j, i = NDFD.cell_of(43.07, -89.40) or (0, 0)
    window = Window(j0=j - 30, j1=j + 30, i0=i - 30, i1=i + 30)
    lat, _ = NDFD.window_latlon(window)
    values = (np.asarray(lat) - 43.0) * 10.0  # °C, rising northward through freezing
    png = mapimage.map_png(
        values,
        window,
        palettes.PALETTES["BuYlRd"],
        (-10.0, 10.0),
        "Test",
        "A day",
        "°F",
        fahrenheit,
        middle=0.0,
        isolines=5.0,
    )
    image = Image.open(io.BytesIO(png))
    assert image.size[0] == 800
