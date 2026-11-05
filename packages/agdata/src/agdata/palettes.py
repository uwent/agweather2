"""Color palettes for maps (PLAN.md Phase 5 G2; Ben, 2026-11-05: defined here, served to the frontend).

One source of colors for the frontend's maps (through `/palettes` and each layer's `palette` and `domain`), the
colored tiles, legends and static map images. Hues have a connection to what's mapped: blue to red for temperature,
greens to deep blue for rain, brown (dry) to teal (humid) for humidity, yellow to dark red for heat accumulated,
yellow to brown for water lost (ET), white to blue for snow. Ramps come from ColorBrewer's schemes (designed for
maps; Harrower and Brewer 2003) and matplotlib's perceptual ones, sampled once into hex here.

- `sequential`: low to high, lightness changing steadily (a reader with any color vision can order them);
- `diverging`: two sequential halves around a middle (an anomaly, or wet against dry);
- `categorical`: one color per level (risk levels), each pair distinct under the common color-vision deficiencies;
- `cyclic`: wraps around (wind direction).

Risk levels use ColorBrewer's red-yellow-blue (colorblind-safe) rather than its red-yellow-green, whose dark green
and red have the same lightness. `tests/test_palettes.py` checks each palette's lightness and distinctness.

A layer's `Scale` is its palette and its domain in the stored unit: fixed where values have a natural range (a day's
temperature, humidity, hours in a day, a risk level), else None, taken from the map's own values (`auto_domain`):
running totals, ranges reduced by `stat`, and model outputs grow through a season.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

Kind = Literal["sequential", "diverging", "categorical", "cyclic"]


@dataclass(frozen=True, kw_only=True)
class Palette:
    id: str
    kind: Kind
    colors: tuple[str, ...]  # low to high (a categorical palette's, level by level)
    description: str


def _p(id: str, kind: Kind, colors: list[str], description: str) -> Palette:
    return Palette(id=id, kind=kind, colors=tuple(colors), description=description)


_ALL = [
    _p(
        "temperature",
        "diverging",
        [
            "#313695",
            "#4574b3",
            "#74add1",
            "#aad8e9",
            "#e0f3f8",
            "#feffc0",
            "#fee090",
            "#fdad60",
            "#f46d43",
            "#d62f27",
            "#a50026",
        ],
        "Cold blue through pale yellow to hot red (ColorBrewer RdYlBu)",
    ),
    _p(
        "dew_point_depression",
        "diverging",
        ["#003c30", "#0c7169", "#58b0a7", "#b4e2db", "#f4f5f5", "#f1dfb3", "#cfa256", "#995d13", "#543005"],
        "Humid teal (air near saturation) to dry brown (ColorBrewer BrBG, reversed)",
    ),
    _p(
        "humidity",
        "diverging",
        ["#543005", "#995d13", "#cfa256", "#f1dfb3", "#f4f5f5", "#b4e2db", "#58b0a7", "#0c7169", "#003c30"],
        "Dry brown to humid teal (ColorBrewer BrBG)",
    ),
    _p(
        "precipitation",
        "sequential",
        ["#f1faba", "#d3eeb3", "#9cd8b8", "#5fc1c0", "#33a7c2", "#1f82b9", "#2355a4", "#21318d", "#081d58"],
        "Light green to deep blue as rain grows (ColorBrewer YlGnBu)",
    ),
    _p(
        "snow",
        "sequential",
        ["#d9e8f5", "#c4daee", "#a3cce3", "#77b5d9", "#529dcc", "#3383be", "#1967ad", "#084c95", "#08306b"],
        "Pale to deep blue (ColorBrewer Blues)",
    ),
    _p(
        "evapotranspiration",
        "sequential",
        ["#fff9c5", "#fee99e", "#fed069", "#feae3b", "#f78921", "#e2650f", "#c14702", "#933204", "#662506"],
        "Yellow to brown as water is lost (ColorBrewer YlOrBr)",
    ),
    _p(
        "radiation",
        "sequential",
        ["#ffffcc", "#ffefa5", "#fedd7f", "#febe59", "#fd9c42", "#fc6c33", "#f23924", "#d7121f", "#b00026"],
        "Pale yellow to deep orange-red as sunlight grows (ColorBrewer YlOrRd)",
    ),
    _p(
        "degree_days",
        "sequential",
        ["#fff8bb", "#ffe691", "#fece6a", "#fea948", "#fd8038", "#f84628", "#df171d", "#b90026", "#800026"],
        "Yellow to dark red as heat accumulates (ColorBrewer YlOrRd)",
    ),
    _p(
        "wind",
        "sequential",
        ["#ebe9f3", "#d9d9ea", "#bfc0de", "#a5a2cd", "#8c88bf", "#7669af", "#63449d", "#51218c", "#3f007d"],
        "Pale to deep purple (ColorBrewer Purples)",
    ),
    _p(
        "pressure",
        "sequential",
        ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21918c", "#28ae80", "#5ec962", "#addc30", "#fde725"],
        "Low to high pressure (viridis)",
    ),
    _p(
        "cloud",
        "sequential",
        ["#f3f3f3", "#e4e4e4", "#d1d1d1", "#bbbbbb", "#9e9e9e", "#838383", "#696969", "#505050", "#2e2e2e"],
        "Clear (light) to overcast (gray) (ColorBrewer Greys)",
    ),
    _p(
        "direction",
        "cyclic",
        [
            "#e2d9e2",
            "#b3c6ce",
            "#7ba1c2",
            "#6276ba",
            "#5e43a5",
            "#4e186f",
            "#2f1436",
            "#581647",
            "#8e2c50",
            "#b25652",
            "#c6896c",
            "#d4bcac",
        ],
        "Wind direction around the compass (twilight)",
    ),
    _p(
        "hours",
        "sequential",
        ["#e9f7fa", "#d4efec", "#ade0d4", "#7fcdb6", "#57ba92", "#38a367", "#1c8540", "#00682a", "#00441b"],
        "Few to many hours (ColorBrewer BuGn)",
    ),
    _p(
        "risk_value",
        "sequential",
        ["#fff1a9", "#fedf83", "#fec15d", "#fd9f44", "#fd7435", "#f43e26", "#db141e", "#b60026", "#800026"],
        "Low to high pest activity (ColorBrewer YlOrRd)",
    ),
    _p(
        "chance",
        "sequential",
        ["#e5eff6", "#c9dbea", "#abc5df", "#95a8d0", "#8c85be", "#8b5eab", "#873696", "#7b0d76", "#4d004b"],
        "Unlikely to likely (ColorBrewer BuPu)",
    ),
    _p(
        "crop_stage",
        "sequential",
        ["#f1fab5", "#d7efa2", "#b2df90", "#84cb7e", "#56b568", "#339951", "#187b3f", "#006335", "#004529"],
        "Early to late crop stages, light to deep green (ColorBrewer YlGn)",
    ),
    _p(
        "default",
        "sequential",
        ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21918c", "#28ae80", "#5ec962", "#addc30", "#fde725"],
        "Low to high (viridis)",
    ),
    _p("risk_3", "categorical", ["#4575b4", "#fee090", "#d73027"], "Low, medium, high risk (ColorBrewer RdYlBu)"),
    _p(
        "risk_4",
        "categorical",
        ["#4575b4", "#fee090", "#f46d43", "#a50026"],
        "Four risk levels, low to very high (ColorBrewer RdYlBu)",
    ),
    _p(
        "risk_5",
        "categorical",
        ["#4575b4", "#abd9e9", "#fee090", "#f46d43", "#a50026"],
        "Five risk levels, very low to very high (ColorBrewer RdYlBu)",
    ),
    _p(
        "susceptibility",
        "categorical",
        ["#d9d9d9", "#fdae61", "#d73027"],
        "Crop not susceptible (gray), near its susceptible stages (orange), susceptible (red)",
    ),
]
PALETTES: dict[str, Palette] = {p.id: p for p in _ALL}
ALIASES = {"soil_temperature": "temperature"}  # the same colors over its own domain


def palette(id: str) -> Palette:
    return PALETTES[ALIASES.get(id, id)]


@dataclass(frozen=True, kw_only=True)
class Scale:
    """A map's colors: its palette and the domain its ends stand for, in the stored unit (None: from the data)."""

    palette: Palette
    domain: tuple[float, float] | None


# Fixed domains in stored units, by palette and time axis ("day" a day's value, "hour" an hour's); a palette not
# listed, a running total, a reduced range and a model output take theirs from the data
_DOMAINS: dict[tuple[str, str], tuple[float, float]] = {
    ("temperature", "day"): (-30, 40),
    ("temperature", "hour"): (-30, 40),
    ("soil_temperature", "day"): (-15, 35),
    ("soil_temperature", "hour"): (-15, 35),
    ("dew_point_depression", "day"): (0, 20),
    ("humidity", "day"): (0, 100),
    ("humidity", "hour"): (0, 100),
    ("wind", "day"): (0, 12),
    ("wind", "hour"): (0, 15),
    ("cloud", "day"): (0, 100),
    ("cloud", "hour"): (0, 100),
    ("precipitation", "day"): (0, 50),
    ("precipitation", "hour"): (0, 25),
    ("snow", "day"): (0, 100),
    ("snow", "hour"): (0, 100),
    ("evapotranspiration", "day"): (0, 8),
    ("evapotranspiration", "hour"): (0, 1),
    ("radiation", "day"): (0, 32),
    ("radiation", "hour"): (0, 1000),
    ("hours", "day"): (0, 24),
    ("degree_days", "day"): (0, 40),
    ("direction", "day"): (0, 360),
    ("direction", "hour"): (0, 360),
    ("chance", "day"): (0, 100),
}


# Palettes whose values are bounded whatever the layer (percentages, degrees of the compass): always their domain
_BOUNDED = {"chance", "humidity", "cloud", "direction"}


def scale_for(palette_id: str, time_axis: str, running: bool) -> Scale:
    """A layer's (or a model output's) scale: `running` is a running total, a reduced range or a model output that
    grows through its season, whose domain comes from the data unless the palette's values are bounded."""
    p = palette(palette_id)
    if p.kind == "categorical":
        return Scale(palette=p, domain=(0, len(p.colors) - 1))
    if running and palette_id not in _BOUNDED:
        return Scale(palette=p, domain=None)
    return Scale(palette=p, domain=_DOMAINS.get((palette_id, time_axis)) or _DOMAINS.get((palette_id, "day")))


def auto_domain(values: np.ndarray, diverging: bool = False) -> tuple[float, float]:
    """A domain from a map's values: its 2nd to 98th percentile widened to a round step (a quarter of the span's
    power of ten), symmetric around zero for a diverging palette; (0, 1) with no values."""
    known = values[np.isfinite(values)]
    if not known.size:
        return (0.0, 1.0)
    lo, hi = (float(v) for v in np.percentile(known, [2, 98]))
    if diverging:
        top = max(abs(lo), abs(hi)) or 1.0
        top = _round(top, _step(top), up=True)
        return (-top, top)
    if hi <= lo:
        hi = lo + 1.0
    step = _step(hi - lo)
    return (_round(lo, step, up=False), _round(hi, step, up=True))


def _step(span: float) -> float:
    return float(10 ** np.floor(np.log10(span)) / 4)


def _round(v: float, step: float, up: bool) -> float:
    return float((np.ceil if up else np.floor)(v / step) * step) + 0.0


def rgb(color: str) -> tuple[int, int, int]:
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def colorize(values: np.ndarray, p: Palette, domain: tuple[float, float]) -> np.ndarray:
    """RGBA (…, 4) uint8 for values: a categorical palette by level (rounded; outside its levels transparent), others
    interpolated along the ramp over `domain` (clipped); missing transparent."""
    colors = np.array([rgb(c) for c in p.colors], dtype=float)
    out = np.zeros((*values.shape, 4), dtype=np.uint8)
    known = np.isfinite(values)
    if p.kind == "categorical":
        level = np.where(known, np.rint(values), -1).astype(int)
        shown = (level >= 0) & (level < len(colors))
        out[shown, :3] = colors[level[shown]].astype(np.uint8)
        out[shown, 3] = 255
        return out
    lo, hi = domain
    span = hi - lo or 1.0
    t = np.clip((np.where(known, values, lo) - lo) / span, 0, 1) * (len(colors) - 1)
    k = np.minimum(np.floor(t).astype(int), len(colors) - 2)
    f = (t - k)[..., None]
    mixed = colors[k] * (1 - f) + colors[k + 1] * f
    out[known, :3] = np.rint(mixed[known]).astype(np.uint8)
    out[known, 3] = 255
    return out
