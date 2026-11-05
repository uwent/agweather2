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


@pytest.mark.parametrize("p", [p for p in palettes.PALETTES.values() if p.kind == "sequential"], ids=lambda p: p.id)
def test_a_sequential_palette_changes_lightness_steadily(p):
    lightness = np.diff(_lab(_linear(p.colors))[:, 0])
    assert (lightness > 0).all() or (lightness < 0).all(), p.id


@pytest.mark.parametrize("p", [p for p in palettes.PALETTES.values() if p.kind == "diverging"], ids=lambda p: p.id)
def test_a_diverging_palette_is_lightest_in_the_middle(p):
    lightness = _lab(_linear(p.colors))[:, 0]
    top = int(np.argmax(lightness))
    assert 0 < top < len(lightness) - 1, p.id
    assert (np.diff(lightness[: top + 1]) > 0).all() and (np.diff(lightness[top:]) < 0).all(), p.id


@pytest.mark.parametrize("p", [p for p in palettes.PALETTES.values() if p.kind == "categorical"], ids=lambda p: p.id)
def test_levels_stay_distinct_under_color_vision_deficiencies(p):
    for vision, lab in _visions(p.colors).items():
        for a in range(len(lab)):
            for b in range(a + 1, len(lab)):
                delta = float(np.linalg.norm(lab[a] - lab[b]))
                assert delta >= MIN_CATEGORY_DELTA, f"{p.id} levels {a} and {b} under {vision}: ΔE {delta:.1f}"


def test_every_layer_and_output_has_a_palette():
    for layer in LAYERS.values():
        for name in [layer.palette, *(o.palette for o in layer.outputs)]:
            assert palettes.palette(name).id, (layer.id, name)


def test_colors_follow_the_domain():
    p = palettes.PALETTES["degree_days"]
    rgba = palettes.colorize(np.array([0.0, 100.0, 50.0, np.nan, 500.0]), p, (0, 100))
    assert tuple(rgba[0, :3]) == palettes.rgb(p.colors[0]) and tuple(rgba[1, :3]) == palettes.rgb(p.colors[-1])
    assert tuple(rgba[2, :3]) == palettes.rgb(p.colors[4]) and rgba[3, 3] == 0 and tuple(rgba[4]) == tuple(rgba[1])
    risk = palettes.colorize(np.array([0.0, 3.0, 7.0]), palettes.PALETTES["risk_4"], (0, 3))
    assert tuple(risk[1, :3]) == palettes.rgb("#a50026") and risk[2, 3] == 0
    assert palettes.auto_domain(np.array([3.0, 870.0, 1234.0, np.nan])) == (0.0, 1250.0)
    assert palettes.auto_domain(np.array([-3.2, 1.1]), diverging=True) == (-3.25, 3.25)
