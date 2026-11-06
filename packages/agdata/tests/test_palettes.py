"""Map palettes (`agdata.palettes`): readable by lightness, distinct under color-vision deficiencies, and colored as
their domains say."""

import numpy as np
import pytest

from agdata import palettes
from agdata.layers import LAYERS

# Machado, Oliveira and Fernandes (2009), full severity, on linear RGB
CVD = {
    "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritanopia": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}
MIN_CATEGORY_DELTA = 15.0  # CIE76 ΔE between any two levels, for every vision
# Neighbouring colors of a sequential palette (CIEDE2000; Ben, 2026-11-06: YlOrRd's uneven steps read poorly): the
# smallest step, and the largest no more than this many times it. One-hue ramps can't reach it over nine colors; these
# are kept where the hue itself says what's mapped
MIN_STEP, MAX_STEP_RATIO = 7.5, 2.5
CONTRAST_EXCEPTIONS = {"PuBu": "snow reads as white to blue", "Greys": "cloud cover reads as clear to gray"}
# Palettes some use assigns (the rest are choices a reader can pick, `colorblind_safe` False)
ASSIGNED = sorted({use.palette for use in palettes.USES.values()})
ASSIGNED_OF = {
    kind: [palettes.PALETTES[i] for i in ASSIGNED if palettes.PALETTES[i].kind == kind]
    for kind in ("sequential", "diverging", "categorical")
}


def _linear(colors: tuple[str, ...]) -> np.ndarray:
    c = np.array([palettes.rgb(h) for h in colors], dtype=float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lab(linear: np.ndarray) -> np.ndarray:
    xyz = (
        np.clip(linear, 0, 1)
        @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
        / np.array([0.95047, 1.0, 1.08883])
    )
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def _visions(colors) -> dict[str, np.ndarray]:
    linear = _linear(colors)
    return {"normal": _lab(linear)} | {name: _lab(linear @ np.array(m).T) for name, m in CVD.items()}


@pytest.mark.parametrize("p", ASSIGNED_OF["sequential"], ids=lambda p: p.id)
def test_a_sequential_palette_changes_lightness_steadily(p):
    lightness = np.diff(_lab(_linear(p.colors))[:, 0])
    assert (lightness > 0).all() or (lightness < 0).all(), p.id


@pytest.mark.parametrize("p", ASSIGNED_OF["diverging"], ids=lambda p: p.id)
def test_a_diverging_palette_is_lightest_in_the_middle(p):
    lightness = _lab(_linear(p.colors))[:, 0]
    top = int(np.argmax(lightness))
    assert 0 < top < len(lightness) - 1, p.id
    assert (np.diff(lightness[: top + 1]) > 0).all() and (np.diff(lightness[top:]) < 0).all(), p.id


@pytest.mark.parametrize("p", ASSIGNED_OF["categorical"], ids=lambda p: p.id)
def test_levels_stay_distinct_under_color_vision_deficiencies(p):
    for vision, lab in _visions(p.colors).items():
        for a in range(len(lab)):
            for b in range(a + 1, len(lab)):
                delta = float(np.linalg.norm(lab[a] - lab[b]))
                assert delta >= MIN_CATEGORY_DELTA, f"{p.id} levels {a} and {b} under {vision}: ΔE {delta:.1f}"


def test_every_layer_and_output_has_a_use_whose_palette_exists():
    for layer in LAYERS.values():
        for name in [layer.use, *(o.use for o in layer.outputs)]:
            assert palettes.USES[name].palette in palettes.PALETTES, (layer.id, name)


def test_palettes_assigned_are_colorblind_safe_and_named_low_to_high():
    assert all(palettes.PALETTES[i].colorblind_safe for i in ASSIGNED)
    offered = [p.id for p in palettes.PALETTES.values() if not p.colorblind_safe]
    assert offered == ["rainbow", "GnYlRd"] and not set(offered) & set(ASSIGNED)
    # A name lists its colors low to high: blue first for temperature, as ColorBrewer's RdYlBu reversed
    assert palettes.PALETTES["BuYlRd"].colors[0] == "#313695" and "reversed" in palettes.PALETTES["BuYlRd"].source


def _de2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """CIEDE2000 (Sharma, Wu and Dalal 2005)."""
    (l1, a1, b1), (l2, a2, b2) = lab1, lab2
    c_mean = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    g = 0.5 * (1 - np.sqrt(c_mean**7 / (c_mean**7 + 25**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dh = 0.0 if c1p * c2p == 0 else (h2p - h1p + 180) % 360 - 180
    dl, dc, dhh = l2 - l1, c2p - c1p, 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh / 2))
    l_mean, c_mean_p = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_mean = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        h_mean = (h1p + h2p) / 2
    else:
        h_mean = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    t = (
        1
        - 0.17 * np.cos(np.radians(h_mean - 30))
        + 0.24 * np.cos(np.radians(2 * h_mean))
        + 0.32 * np.cos(np.radians(3 * h_mean + 6))
        - 0.20 * np.cos(np.radians(4 * h_mean - 63))
    )
    rt = (
        -np.sin(np.radians(60 * np.exp(-(((h_mean - 275) / 25) ** 2))))
        * 2
        * np.sqrt(c_mean_p**7 / (c_mean_p**7 + 25**7))
    )
    sl = 1 + 0.015 * (l_mean - 50) ** 2 / np.sqrt(20 + (l_mean - 50) ** 2)
    sc, sh = 1 + 0.045 * c_mean_p, 1 + 0.015 * c_mean_p * t
    return float(np.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dhh / sh) ** 2 + rt * (dc / sc) * (dhh / sh)))


def test_de2000_matches_sharmas_published_pair():
    assert _de2000(np.array([50.0, 2.6772, -79.7751]), np.array([50.0, 0.0, -82.7485])) == pytest.approx(
        2.0425, abs=1e-4
    )


@pytest.mark.parametrize("p", ASSIGNED_OF["sequential"], ids=lambda p: p.id)
def test_a_sequential_palettes_steps_are_distinct_and_even(p):
    lab = _lab(_linear(p.colors))
    steps = np.array([_de2000(lab[k], lab[k + 1]) for k in range(len(lab) - 1)])
    if p.id in CONTRAST_EXCEPTIONS:
        return
    assert steps.min() >= MIN_STEP, f"{p.id}: smallest step {steps.min():.1f}"
    assert steps.max() <= MAX_STEP_RATIO * steps.min(), f"{p.id}: steps {np.round(steps, 1).tolist()}"


def test_colors_follow_the_domain():
    p = palettes.PALETTES["YlGnBu"]
    rgba = palettes.colorize(np.array([0.0, 100.0, 50.0, np.nan, 500.0]), p, (0, 100))
    assert tuple(rgba[0, :3]) == palettes.rgb(p.colors[0]) and tuple(rgba[1, :3]) == palettes.rgb(p.colors[-1])
    assert tuple(rgba[2, :3]) == palettes.rgb(p.colors[4]) and rgba[3, 3] == 0 and tuple(rgba[4]) == tuple(rgba[1])
    risk = palettes.colorize(np.array([0.0, 3.0, 7.0]), palettes.PALETTES["BuYlRd_4"], (0, 3))
    assert tuple(risk[1, :3]) == palettes.rgb("#a50026") and risk[2, 3] == 0
    assert palettes.auto_domain(np.array([3.0, 870.0, 1234.0, np.nan])) == (0.0, 1250.0)
    assert palettes.auto_domain(np.array([-3.2, 1.1]), centered=True) == (-3.25, 3.25)
