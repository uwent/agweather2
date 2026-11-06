"""Color palettes for maps (PLAN.md Phase 5 G2; Ben, 2026-11-05 and 11-06): defined here, served to the frontend.

Two tables, kept apart so a palette can be reused, changed or offered to a reader on its own (Ben, 2026-11-06):

- `PALETTES`: each palette by the name of its colors **from low to high** (`BuYlRd`: blue, yellow, red), with where
  it comes from (`source`: ColorBrewer's schemes, designed for maps, Harrower and Brewer 2003, or matplotlib's
  perceptual ones, sampled once into hex here). ColorBrewer publishes some schemes the other way round (RdYlBu starts
  at red), so a name here can be a ColorBrewer scheme reversed, and the source says so.
- `USES`: what each kind of map uses (`temperature`, `precipitation`, `degree_days`, …): its palette, its default
  domain for a day and an hour, and whether its values are bounded (a percentage) or centered on zero (an anomaly).
  Layers and model outputs name a use (`agdata.layers`), never a palette.

Kinds: `sequential` (low to high, lightness changing steadily, so a reader with any color vision can order them),
`diverging` (two halves around a light middle), `categorical` (one color per level, each pair distinct under the
common color-vision deficiencies), `cyclic` (wraps around: wind direction).

Every palette a use assigns is checked by `tests/test_palettes.py`: lightness, distinct levels, and for sequential
ones the contrast between neighbouring colors (CIEDE2000; YlOrRd's uneven steps fail it), with snow's white-to-blue
and cloud cover's grays as named exceptions. Palettes no use assigns (`colorblind_safe=False`: v1's rainbow, VDIFN's
green-to-red) are there for the frontend to offer a reader who wants them.

A map's `Scale` is its palette and the domain its ends stand for, in the stored unit: the use's default where values
have a natural range (a day's temperature, humidity, hours in a day, a risk level), else None, from the map's own
values (`auto_domain`): running totals, ranges reduced by `stat`, and model outputs grow through a season. A request
can choose (`scale=`, `api.layermaps`).
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

Kind = Literal["sequential", "diverging", "categorical", "cyclic"]


@dataclass(frozen=True, kw_only=True)
class Palette:
    id: str  # its colors from low to high
    kind: Kind
    colors: tuple[str, ...]  # low to high (a categorical palette's, level by level)
    description: str  # what its hues are
    source: str  # where the colors come from
    colorblind_safe: bool = True


def _p(id: str, kind: Kind, colors: list[str], description: str, source: str, safe: bool = True) -> Palette:
    return Palette(id=id, kind=kind, colors=tuple(colors), description=description, source=source, colorblind_safe=safe)


_RDYLBU = [
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
]
_BRBG = ["#543005", "#995d13", "#cfa256", "#f1dfb3", "#f4f5f5", "#b4e2db", "#58b0a7", "#0c7169", "#003c30"]
_VIRIDIS = ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21918c", "#28ae80", "#5ec962", "#addc30", "#fde725"]

_ALL = [
    _p("BuYlRd", "diverging", _RDYLBU, "Blue through pale yellow to red", "ColorBrewer RdYlBu, reversed"),
    _p("BrBG", "diverging", _BRBG, "Brown through white to blue-green", "ColorBrewer BrBG"),
    _p("BGBr", "diverging", _BRBG[::-1], "Blue-green through white to brown", "ColorBrewer BrBG, reversed"),
    _p(
        "YlGnBu",
        "sequential",
        ["#d6efb3", "#abdeb7", "#73c8bd", "#40b5c4", "#2498c1", "#2072b1", "#234da0", "#1f2f87", "#081d58"],
        "Light yellow-green to deep blue",
        "ColorBrewer YlGnBu, from 0.2",
    ),
    _p(
        "YlOrBr",
        "sequential",
        ["#fee390", "#fecb5f", "#feae3b", "#f98e23", "#eb6f14", "#d35406", "#b13f03", "#8b3005", "#662506"],
        "Pale yellow through orange to brown",
        "ColorBrewer YlOrBr, from 0.25",
    ),
    _p(
        "PuBu",
        "sequential",
        ["#d0d1e6", "#b0c2de", "#8cb3d5", "#63a2cb", "#358fc0", "#1077b4", "#04649e", "#03517e", "#023858"],
        "Pale lavender to deep blue",
        "ColorBrewer PuBu, from 0.25",
    ),
    _p(
        "Greys",
        "sequential",
        ["#f3f3f3", "#e4e4e4", "#d1d1d1", "#bbbbbb", "#9e9e9e", "#838383", "#696969", "#505050", "#2e2e2e"],
        "Light to dark gray",
        "ColorBrewer Greys",
    ),
    _p(
        "Greens",
        "sequential",
        ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a0d99b", "#73c476", "#40aa5d", "#228a44", "#006c2c", "#00441b"],
        "Pale to deep green",
        "ColorBrewer Greens",
    ),
    _p(
        "RdPu",
        "sequential",
        ["#fff7f3", "#fde0dd", "#fcc5c0", "#fa9eb5", "#f767a1", "#dc3397", "#ad017e", "#790177", "#49006a"],
        "Pale pink to deep purple",
        "ColorBrewer RdPu",
    ),
    _p("viridis", "sequential", _VIRIDIS, "Dark purple through teal to yellow", "matplotlib viridis"),
    _p(
        "inferno",
        "sequential",
        ["#2b0b57", "#59106e", "#84206b", "#b0315b", "#d54a41", "#f06f20", "#fc9f07", "#f7d340", "#fcffa4"],
        "Dark purple through red and orange to pale yellow",
        "matplotlib inferno, from 0.15",
    ),
    _p(
        "magma",
        "sequential",
        ["#251255", "#52137c", "#7c2382", "#aa337d", "#d5446d", "#f4675c", "#fd9a6a", "#fecc8f", "#fcfdbf"],
        "Dark purple through pink to pale yellow",
        "matplotlib magma, from 0.15",
    ),
    _p(
        "twilight",
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
        "Around the compass, back to where it started",
        "matplotlib twilight",
    ),
    _p("BuYlRd_3", "categorical", ["#4575b4", "#fee090", "#d73027"], "Blue, yellow, red", "ColorBrewer RdYlBu, 3"),
    _p(
        "BuYlRd_4",
        "categorical",
        ["#4575b4", "#fee090", "#f46d43", "#a50026"],
        "Blue, yellow, orange, dark red",
        "ColorBrewer RdYlBu",
    ),
    _p(
        "BuYlRd_5",
        "categorical",
        ["#4575b4", "#abd9e9", "#fee090", "#f46d43", "#a50026"],
        "Blue, light blue, yellow, orange, dark red",
        "ColorBrewer RdYlBu",
    ),
    _p("GyOrRd_3", "categorical", ["#d9d9d9", "#fdae61", "#d73027"], "Gray, orange, red", "ColorBrewer RdYlBu's"),
    # Offered to readers, assigned to nothing: neither is ordered by lightness, so neither is color-blind safe
    _p(
        "rainbow",
        "sequential",
        ["#a100c7", "#6e00dc", "#1f3dfa", "#00c7c7", "#00d18c", "#a1e633", "#e6dc33", "#f08229", "#f00000", "#dc0063"],
        "Violet through blue, green, yellow and orange to crimson",
        "AgWeather v1's maps (gnuplot)",
        safe=False,
    ),
    _p(
        "GnYlRd",
        "sequential",
        ["#00cc00", "#ffd700", "#cc0000"],
        "Green through gold to red",
        "VDIFN's spectral maps",
        safe=False,
    ),
]
PALETTES: dict[str, Palette] = {p.id: p for p in _ALL}


def palette(id: str) -> Palette:
    return PALETTES[id]


Domain = tuple[float, float]


@dataclass(frozen=True, kw_only=True)
class Use:
    """What a kind of map uses: its palette and default domains in the stored unit (None: from the data)."""

    palette: str
    day: Domain | None = None  # a day's value
    hour: Domain | None = None  # an hour's (default: the day's)
    bounded: bool = False  # values have the same range whatever the layer (percentages, compass degrees)
    centered: bool = False  # a domain from the data is symmetric around zero (an anomaly)


USES: dict[str, Use] = {
    "temperature": Use(palette="BuYlRd", day=(-30, 40)),
    "soil_temperature": Use(palette="BuYlRd", day=(-15, 35)),
    "dew_point_depression": Use(palette="BGBr", day=(0, 20)),
    "humidity": Use(palette="BrBG", day=(0, 100), bounded=True),
    "precipitation": Use(palette="YlGnBu", day=(0, 50), hour=(0, 25)),
    "snow": Use(palette="PuBu", day=(0, 100)),
    "evapotranspiration": Use(palette="YlOrBr", day=(0, 8), hour=(0, 1)),
    "radiation": Use(palette="inferno", day=(0, 32), hour=(0, 1000)),
    "wind": Use(palette="RdPu", day=(0, 12), hour=(0, 15)),
    "direction": Use(palette="twilight", day=(0, 360), bounded=True),
    "pressure": Use(palette="viridis"),
    "cloud": Use(palette="Greys", day=(0, 100), bounded=True),
    "hours": Use(palette="Greens", day=(0, 24)),
    "degree_days": Use(palette="BuYlRd", day=(0, 40)),
    "risk_value": Use(palette="viridis"),  # insects' activity (Ben, 2026-11-06)
    "chance": Use(palette="magma", day=(0, 100), bounded=True),
    "crop_stage": Use(palette="viridis"),
    "risk_3": Use(palette="BuYlRd_3"),
    "risk_4": Use(palette="BuYlRd_4"),
    "risk_5": Use(palette="BuYlRd_5"),
    "susceptibility": Use(palette="GyOrRd_3"),
    "default": Use(palette="viridis"),
}


@dataclass(frozen=True, kw_only=True)
class Scale:
    """A map's colors: its palette and the domain its ends stand for, in the stored unit (None: from the data)."""

    palette: Palette
    domain: Domain | None
    centered: bool = False


def scale_for(use_id: str, time_axis: str, running: bool) -> Scale:
    """A layer's (or a model output's) scale: `running` is a running total, a reduced range or a model output that
    grows through its season, whose domain comes from the data unless the use's values are bounded."""
    use = USES[use_id]
    p = PALETTES[use.palette]
    if p.kind == "categorical":
        return Scale(palette=p, domain=(0, len(p.colors) - 1))
    if running and not use.bounded:
        return Scale(palette=p, domain=None, centered=use.centered)
    domain = use.hour if time_axis == "hour" and use.hour is not None else use.day
    return Scale(palette=p, domain=domain, centered=use.centered)


def auto_domain(values: np.ndarray, centered: bool = False) -> tuple[float, float]:
    """A domain from a map's values: its 2nd to 98th percentile widened to a round step (a quarter of the span's
    power of ten), symmetric around zero for a centered use (an anomaly); (0, 1) with no values."""
    known = values[np.isfinite(values)]
    if not known.size:
        return (0.0, 1.0)
    lo, hi = (float(v) for v in np.percentile(known, [2, 98]))
    if centered:
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
