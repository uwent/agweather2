"""Color palettes for maps (PLAN.md Phase 5 G2; Ben, 2026-11-05 and 11-06): defined here, served to the frontend.

Two tables, kept apart so a palette can be reused, changed or offered to a reader on its own (Ben, 2026-11-06):

- `PALETTES`: each palette by the name of its colors **from low to high** (`BuYlRd`: blue, yellow, red), with where
  it comes from (`source`). Ramps are sampled at import from matplotlib's colormaps: ColorBrewer's schemes (designed
  for maps, Harrower and Brewer 2003; matplotlib carries their published colors, which come back exactly) and
  matplotlib's perceptual ones. Only colors chosen one by one are written as hex: categorical levels and other
  services' palettes. ColorBrewer publishes some schemes the other way round (RdYlBu starts at red), so a name here can
  be a ColorBrewer scheme sampled in reverse, and the source says so.
- Any palette runs high to low with `palette(id, reverse=True)`, whose id ends `_r` (matplotlib's convention), and
  `palette("BrBG_r")` gives it back. `/palettes` lists the palettes low to high; the reversed ones aren't listed.
- `USES`: what each kind of map uses (`temperature`, `precipitation`, `degree_days`, …): its palette, its default
  domain for a day and an hour, whether it's reversed, and whether its values are bounded (a percentage) or centered
  on zero (an anomaly). Layers and model outputs name a use (`agdata.layers`), never a palette.

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

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from matplotlib import colormaps
from matplotlib.colors import to_hex

Kind = Literal["sequential", "diverging", "categorical", "cyclic"]


REVERSED = "_r"  # a palette's id with this suffix is the palette reversed (matplotlib's convention)
_REVERSED_TEXT = ", reversed"


@dataclass(frozen=True, kw_only=True)
class Palette:
    id: str  # its colors from low to high
    kind: Kind
    colors: tuple[str, ...]  # low to high (a categorical palette's, level by level)
    description: str  # what its hues are
    source: str  # where the colors come from
    colorblind_safe: bool = True

    def reversed(self) -> "Palette":
        """The palette high to low, its id with `_r` added (or taken off: reversing twice gives it back)."""
        if self.id.endswith(REVERSED):
            id, description = self.id.removesuffix(REVERSED), self.description.removesuffix(_REVERSED_TEXT)
        else:
            id, description = self.id + REVERSED, self.description + _REVERSED_TEXT
        return replace(self, id=id, colors=self.colors[::-1], description=description)


def _sampled(
    *,
    id: str,
    kind: Kind,
    scheme: str,
    description: str,
    n: int = 9,
    start: float = 0.0,
    stop: float = 1.0,
    reverse: bool = False,
) -> Palette:
    """`n` colors of one of matplotlib's colormaps (its ColorBrewer schemes are ColorBrewer's published colors) from
    `start` to `stop` of the way along it, reversed where ColorBrewer's order runs high to low."""
    cmap = colormaps[scheme].resampled(10001)  # fine enough that ColorBrewer's classes come back exactly
    at = np.linspace(0, 1, n, endpoint=False) if kind == "cyclic" else np.linspace(start, stop, n)
    colors = tuple(to_hex(cmap(float(x))) for x in at)
    by = "ColorBrewer" if scheme in _COLORBREWER else "matplotlib"
    part = f", from {start:g}" if start else ""
    part += f" to {stop:g}" if stop != 1 else ""
    p = Palette(id=id, kind=kind, colors=colors, description=description, source=f"{by} {scheme}{part}")
    if reverse:  # sampled high to low, named and kept low to high
        p = replace(p, colors=p.colors[::-1], source=f"{p.source}, reversed")
    return p


def _listed(*, id: str, kind: Kind, colors: list[str], description: str, source: str, safe: bool = True) -> Palette:
    """Colors chosen one by one rather than sampled: categorical levels, and other services' palettes."""
    return Palette(id=id, kind=kind, colors=tuple(colors), description=description, source=source, colorblind_safe=safe)


_COLORBREWER = {"RdYlBu", "BrBG", "YlGnBu", "YlOrBr", "PuBu", "Greys", "Greens", "RdPu"}

_ALL = [
    _sampled(
        id="BuYlRd",
        kind="diverging",
        scheme="RdYlBu",
        n=11,
        reverse=True,
        description="Blue through pale yellow to red",
    ),
    _sampled(id="BrBG", kind="diverging", scheme="BrBG", description="Brown through white to blue-green"),
    _sampled(id="YlGnBu", kind="sequential", scheme="YlGnBu", start=0.2, description="Light yellow-green to deep blue"),
    _sampled(
        id="YlOrBr",
        kind="sequential",
        scheme="YlOrBr",
        start=0.25,
        description="Pale yellow through orange to brown",
    ),
    _sampled(id="PuBu", kind="sequential", scheme="PuBu", start=0.25, description="Pale lavender to deep blue"),
    _sampled(id="Greys", kind="sequential", scheme="Greys", start=0.1, stop=0.85, description="Light to dark gray"),
    _sampled(id="Greens", kind="sequential", scheme="Greens", description="Pale to deep green"),
    _sampled(id="RdPu", kind="sequential", scheme="RdPu", description="Pale pink to deep purple"),
    _sampled(id="viridis", kind="sequential", scheme="viridis", description="Dark purple through teal to yellow"),
    _sampled(
        id="inferno",
        kind="sequential",
        scheme="inferno",
        start=0.15,
        description="Dark purple through red and orange to pale yellow",
    ),
    _sampled(
        id="magma",
        kind="sequential",
        scheme="magma",
        start=0.15,
        description="Dark purple through pink to pale yellow",
    ),
    _sampled(
        id="twilight",
        kind="cyclic",
        scheme="twilight",
        n=12,
        description="Around the compass, back to where it started",
    ),
    # Levels picked from ColorBrewer RdYlBu's 11 classes for distinct lightness under color-vision deficiencies
    _listed(
        id="BuYlRd_3",
        kind="categorical",
        colors=["#4575b4", "#fee090", "#d73027"],
        description="Blue, yellow, red",
        source="ColorBrewer RdYlBu, 3 of its 11 classes",
    ),
    _listed(
        id="BuYlRd_4",
        kind="categorical",
        colors=["#4575b4", "#fee090", "#f46d43", "#a50026"],
        description="Blue, yellow, orange, dark red",
        source="ColorBrewer RdYlBu, 4 of its 11 classes",
    ),
    _listed(
        id="BuYlRd_5",
        kind="categorical",
        colors=["#4575b4", "#abd9e9", "#fee090", "#f46d43", "#a50026"],
        description="Blue, light blue, yellow, orange, dark red",
        source="ColorBrewer RdYlBu, 5 of its 11 classes",
    ),
    _listed(
        id="GyOrRd_3",
        kind="categorical",
        colors=["#d9d9d9", "#fdae61", "#d73027"],
        description="Gray, orange, red",
        source="ColorBrewer Greys and RdYlBu",
    ),
    # Offered to readers, assigned to nothing: neither is ordered by lightness, so neither is color-blind safe
    _listed(
        id="rainbow",
        kind="sequential",
        colors=[
            "#a100c7",
            "#6e00dc",
            "#1f3dfa",
            "#00c7c7",
            "#00d18c",
            "#a1e633",
            "#e6dc33",
            "#f08229",
            "#f00000",
            "#dc0063",
        ],
        description="Violet through blue, green, yellow and orange to crimson",
        source="AgWeather v1's maps (gnuplot)",
        safe=False,
    ),
    _listed(
        id="GnYlRd",
        kind="sequential",
        colors=["#00cc00", "#ffd700", "#cc0000"],
        description="Green through gold to red",
        source="VDIFN's spectral maps",
        safe=False,
    ),
]
PALETTES: dict[str, Palette] = {p.id: p for p in _ALL}


def palette(id: str, reverse: bool = False) -> Palette:
    """A palette by id, high to low with `reverse` (an id ending `_r` is reversed too, so a reversed palette's id
    comes back to it)."""
    if id not in PALETTES and id.endswith(REVERSED):
        id, reverse = id.removesuffix(REVERSED), not reverse
    p = PALETTES[id]
    return p.reversed() if reverse else p


Domain = tuple[float, float]


@dataclass(frozen=True, kw_only=True)
class Use:
    """What a kind of map uses: its palette and default domains in the stored unit (None: from the data)."""

    palette: str
    reverse: bool = False  # the palette high to low (its id `_r`)
    day: Domain | None = None  # a day's value
    hour: Domain | None = None  # an hour's (default: the day's)
    bounded: bool = False  # values have the same range whatever the layer (percentages, compass degrees)
    centered: bool = False  # a domain from the data is symmetric around zero (an anomaly)


USES: dict[str, Use] = {
    "temperature": Use(palette="BuYlRd", day=(-30, 40)),
    "soil_temperature": Use(palette="BuYlRd", day=(-15, 35)),
    "dew_point_depression": Use(palette="BrBG", reverse=True, day=(0, 20)),
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


def use_palette(use_id: str) -> Palette:
    """The palette a use's maps take, reversed if the use says so."""
    use = USES[use_id]
    return palette(use.palette, reverse=use.reverse)


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
    p = use_palette(use_id)
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
