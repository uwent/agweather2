"""Map images rendered with matplotlib (PLAN.md Phase 5 G, D60): legends for colored tiles, and static maps.

Drawn with matplotlib's Agg backend only (no display, no GDAL). Values arrive in the stored unit; `shown` converts
a stored value to the unit a reader asked for (`units=`), which the labels use, while colors follow the stored
values (a palette's domain is in the stored unit).
"""

import io
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from agdata import palettes
from agdata.grid import NDFD, Window
from agdata.palettes import Palette

DPI = 100
FONT = "DejaVu Sans"
# A first or last day within bounds (D78): cells where the window has values but no such day, and where it has none.
# Both gray, a light and a darker shade, so neither reads as a color of the scale
NONE_COLOR, NO_DATA_COLOR = "#dedede", "#a3a3a3"
EMPTY = ((0, NONE_COLOR, "None"), (-1, NO_DATA_COLOR, "No data"))  # (state, color, label)
EPOCH = date(1970, 1, 1)


def colormap(p: Palette) -> LinearSegmentedColormap | ListedColormap:
    if p.kind == "categorical":
        return ListedColormap(list(p.colors), name=p.id)
    return LinearSegmentedColormap.from_list(p.id, list(p.colors))


def legend_png(
    p: Palette,
    domain: tuple[float, float],
    title: str,
    unit_label: str,
    shown: Callable[[np.ndarray], np.ndarray],
    categories: Sequence[str] | None = None,
    width: int = 320,
    dates: bool = False,
    empties: Sequence[int] = (),
    middle: float | None = None,
) -> bytes:
    """A legend: a color bar over the domain with round ticks in the shown unit (a conversion that's linear, as
    every unit's is) or dates (`dates`: values are days since 1970-01-01), or one swatch per category; then a
    swatch for each empty state on the map (`empties`: 0 none, −1 no data). A long title wraps. `middle`: the value
    at the palette's middle color (`palettes.position`), ticked."""
    if categories is not None:
        return _categories_png(p, categories, title, width)
    lines = textwrap.wrap(f"{title} ({unit_label})" if unit_label else title, width=width // 7)
    extra = 0.22 if empties else 0.0
    height = 0.62 + 0.15 * len(lines) + extra
    fig = Figure(figsize=(width / DPI, height), dpi=DPI)
    bar = fig.add_axes((0.04, (0.32 + extra) / height, 0.92, 0.18 / height))
    _colorbar(bar, p, domain, ticks(domain, shown, dates=dates, middle=middle), middle)
    if empties:
        _empty_swatches(fig, empties, 0.04, 0.12 / height, 0.13 / height)
    fig.text(0.04, 1 - 0.08 / height, "\n".join(lines), fontsize=8.5, family=FONT, va="top", linespacing=1.3)
    return _png(fig)


def _empty_swatches(fig: Figure, empties: Sequence[int], left: float, bottom: float, height: float) -> None:
    """A gray swatch and its label for each empty state shown (`EMPTY`), side by side from `left`."""
    width = height * fig.get_figheight() / fig.get_figwidth() * 1.6
    x = left
    for state, color, label in EMPTY:
        if state not in empties:
            continue
        ax = fig.add_axes((x, bottom, width, height))
        ax.set_facecolor(color)
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_linewidth(0.5)
        fig.text(x + width * 1.3, bottom + height / 2, label, fontsize=8, family=FONT, va="center")
        x += width * 1.3 + 0.012 * len(label) + 0.04


def date_ticks(lo: float, hi: float) -> list[float]:
    """Round dates between `lo` and `hi` (days since 1970-01-01): month starts, with the 15ths over a short range,
    or every few days over a few weeks; about three to seven of them."""
    first, last = EPOCH + timedelta(days=int(np.ceil(lo))), EPOCH + timedelta(days=int(np.floor(hi)))
    if last < first:
        return [float(lo)]
    days = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    for keep in (lambda d: d.day == 1, lambda d: d.day in (1, 15)):
        found = [d for d in days if keep(d)]
        if len(found) >= 3:
            while len(found) > 7:
                found = found[::2]
            return [float((d - EPOCH).days) for d in found]
    every = max(1, len(days) // 5)
    return [float((d - EPOCH).days) for d in days[::every]]


def date_label(value: float) -> str:
    """Days since 1970-01-01 as "Oct 1"."""
    day = EPOCH + timedelta(days=round(value))
    return f"{day:%b} {day.day}"


@dataclass(frozen=True, kw_only=True)
class Ticks:
    """A legend's ticks (stored values, rising) and their labels ("" for a tick left unlabelled to fit)."""

    values: list[float]
    labels: list[str]


MAX_LABELS = 8  # on a color bar; more ticks than this are labelled every few
MAX_LEVELS = 100  # isolines a map may draw (`isolines=N` over its values' range)


def ticks(
    domain: tuple[float, float],
    shown: Callable[[np.ndarray], np.ndarray],
    dates: bool = False,
    middle: float | None = None,
    every: float | None = None,
) -> Ticks:
    """Round values over `domain` (stored) in the shown unit, or dates: about five (MaxNLocator), or every multiple
    of `every` (shown units; days for dates), plus `middle`. Labels are thinned to MAX_LABELS, the middle always
    labelled and its near neighbours not, so labels don't overlap."""
    lo, hi = domain
    if dates:
        if every is None:
            found = date_ticks(lo, hi)
        else:
            start = float(np.ceil(lo))
            found = [start + k * every for k in range(int((hi - start) // every) + 1)]
        values: list[float] = sorted({*found, *([middle] if middle is not None else [])})
        return _thinned(values, [date_label(v) for v in values], domain, middle)
    a, b = (float(v) for v in shown(np.array([lo, hi])))
    if a == b:
        return Ticks(values=[lo], labels=[_number(a)])
    low, high = min(a, b), max(a, b)
    if every is None:
        found = [t for t in MaxNLocator(nbins=5).tick_values(low, high) if low <= t <= high]
    else:
        k0, k1 = int(np.ceil(low / every - 1e-9)), int(np.floor(high / every + 1e-9))
        found = [k * every for k in range(k0, k1 + 1)]
    marks = {round(t, 9) for t in found}
    if middle is not None:
        marks.add(round(float(shown(np.array([middle]))[0]), 9))
    shown_ticks = sorted(marks, key=lambda t: lo + (t - a) / (b - a) * (hi - lo))
    values = [lo + (t - a) / (b - a) * (hi - lo) for t in shown_ticks]
    return _thinned(values, [_number(t) for t in shown_ticks], domain, middle)


def _thinned(values: list[float], labels: list[str], domain: tuple[float, float], middle: float | None) -> Ticks:
    lo, hi = domain
    span = (hi - lo) or 1.0
    every = max(1, int(np.ceil(len(values) / MAX_LABELS)))
    at_middle = int(np.argmin([abs(v - middle) for v in values])) if middle is not None and values else None
    out = []
    for k, (value, label) in enumerate(zip(values, labels, strict=True)):
        near_middle = at_middle is not None and k != at_middle and abs(value - values[at_middle]) < 0.07 * span
        off_beat = k != at_middle and (k - (at_middle or 0)) % every
        out.append("" if near_middle or off_beat else label)
    return Ticks(values=values, labels=out)


def _colorbar(ax, p: Palette, domain: tuple[float, float], marks: Ticks, middle: float | None = None) -> None:
    """A horizontal color bar over the domain, colored as the map is (`palettes.position`, with its middle), with
    `marks`."""
    lo, hi = domain
    along = palettes.position(np.linspace(lo, hi, 512), domain, middle)
    ax.imshow(along[None], aspect="auto", cmap=colormap(p), extent=(lo, hi, 0, 1), vmin=0, vmax=1)
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_linewidth(0.5)
    ax.set_xlim(lo, hi)
    ax.set_xticks(marks.values)
    ax.set_xticklabels(marks.labels, fontsize=8, family=FONT)


def _swatches(fig: Figure, p: Palette, categories: Sequence[str], box: tuple[float, float, float, float]) -> None:
    """The categories side by side in `box` (left, bottom, width, height in figure fractions)."""
    left, bottom, width, height = box
    each = width / len(categories)
    for k, name in enumerate(categories):
        ax = fig.add_axes((left + k * each, bottom, height * fig.get_figheight() / fig.get_figwidth(), height))
        ax.set_facecolor(p.colors[k] if k < len(p.colors) else "#ffffff")
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_linewidth(0.5)
        fig.text(
            left + k * each + height * 1.4 * fig.get_figheight() / fig.get_figwidth(),
            bottom + height / 2,
            name,
            fontsize=8,
            family=FONT,
            va="center",
        )


def _categories_png(p: Palette, categories: Sequence[str], title: str, width: int) -> bytes:
    rows = len(categories)
    fig = Figure(figsize=(width / DPI, (0.36 + 0.2 * rows)), dpi=DPI)
    fig.text(
        0.04,
        1 - 0.14 / (0.36 + 0.2 * rows),
        textwrap.shorten(title, width=width // 6),
        fontsize=8.5,
        family=FONT,
        va="center",
    )
    height = 0.2 / (0.36 + 0.2 * rows)
    for k, name in enumerate(categories):
        y = 1 - (0.3 + 0.2 * (k + 1)) / (0.36 + 0.2 * rows)
        ax = fig.add_axes((0.04, y + height * 0.15, 0.06, height * 0.7))
        ax.set_facecolor(p.colors[k] if k < len(p.colors) else "#ffffff")
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_linewidth(0.5)
        fig.text(0.13, y + height / 2, name, fontsize=8, family=FONT, va="center")
    return _png(fig)


def _number(v: float) -> str:
    """A tick label: no more decimals than it needs."""
    if abs(v) >= 100 or v == round(v):
        return f"{v:,.0f}"
    return f"{v:,.1f}" if abs(v) >= 1 else f"{v:,.2f}"


def _png(fig: Figure) -> bytes:
    out = io.BytesIO()
    fig.savefig(out, format="png", dpi=DPI, facecolor="white")
    return out.getvalue()


# --- Static maps ---------------------------------------------------------------------------------------------------

OUTLINES = Path(__file__).parent / "data" / "outlines.npz"  # `scripts/make_outlines.py`


@dataclass(frozen=True, kw_only=True)
class Rings:
    """Outline rings on the grid: fractional (j, i) vertices, where each ring starts, and each ring's box."""

    j: np.ndarray
    i: np.ndarray
    starts: np.ndarray
    boxes: np.ndarray  # (rings, 4): j min, j max, i min, i max


@cache
def outlines(kind: str) -> Rings:
    """States' or counties' outlines on the NDFD grid (projected once, ~0.1 s)."""
    with np.load(OUTLINES) as f:
        lat, lon, starts = f[f"{kind}_lat"], f[f"{kind}_lon"], f[f"{kind}_starts"]
    j, i = NDFD.fractional_index(lat.astype(float), lon.astype(float))
    ends = np.append(starts[1:], lat.size)
    boxes = np.array(
        [[j[a:b].min(), j[a:b].max(), i[a:b].min(), i[a:b].max()] for a, b in zip(starts, ends, strict=True)]
    )
    return Rings(j=j, i=i, starts=starts, boxes=boxes)


def _draw_outlines(ax, kind: str, window: Window, width: float, color: str) -> None:
    rings = outlines(kind)
    j0, j1, i0, i1 = window.j0 - 0.5, window.j1 - 0.5, window.i0 - 0.5, window.i1 - 0.5
    b = rings.boxes
    seen = np.flatnonzero((b[:, 1] >= j0) & (b[:, 0] <= j1) & (b[:, 3] >= i0) & (b[:, 2] <= i1))
    ends = np.append(rings.starts[1:], rings.j.size)
    lines = [np.column_stack([rings.i[rings.starts[k] : ends[k]], rings.j[rings.starts[k] : ends[k]]]) for k in seen]
    ax.add_collection(LineCollection(lines, colors=color, linewidths=width))


Isolines = Literal["auto"] | float | None  # at the legend's ticks, every N in the shown unit, or none


def map_png(
    values: np.ndarray,
    window: Window,
    p: Palette,
    domain: tuple[float, float],
    title: str,
    subtitle: str,
    unit_label: str,
    shown: Callable[[np.ndarray], np.ndarray],
    categories: Sequence[str] | None = None,
    caption: Sequence[str] = (),
    credit: str = "AgWeather, UW–Madison · agweather.cals.wisc.edu",
    width: int = 800,
    dates: bool = False,
    states: np.ndarray | None = None,
    middle: float | None = None,
    isolines: Isolines = None,
) -> bytes:
    """A map of `values` (y, x) over `window` (south row first; NaN blank), with county and state outlines, a frame
    with a latitude-longitude graticule, a title and a subtitle (what and when; each wraps), a legend, a caption (the
    data sources, the days estimated or missing) and a credit line. `dates`: values are days since 1970-01-01, ticked
    as dates. `states` (y, x): 1 where a value was found, 0 none (light gray), −1 no data (darker gray), NaN blank
    (`EMPTY`). `middle`: the value at the palette's middle color (`palettes.position`). `isolines`: lines at the
    legend's ticks (`auto`) or every N in the shown unit (days for dates), whose multiples the legend then ticks; a
    middle gets a heavier line."""
    rows, cols = window.shape
    inches = width / DPI
    LEFT, RIGHT = 0.55, 0.2  # inches beside the map: the latitude labels, and a margin
    map_w = inches - LEFT - RIGHT
    map_h = map_w * rows / cols
    title_lines = textwrap.wrap(title, width=int(inches * 8.3)) or [""]
    subtitle_lines = textwrap.wrap(subtitle, width=int(inches * 14))
    caption_lines = [line for part in caption for line in textwrap.wrap(part, width=int(inches * 15.5))]
    TITLE, SUB, CAPTION = 0.25, 0.19, 0.16  # line heights, inches
    LABELS = 0.22  # the longitude labels under the map
    head = 0.18 + TITLE * len(title_lines) + SUB * len(subtitle_lines) + 0.08
    legend = 0.6
    foot = legend + CAPTION * len(caption_lines) + 0.3
    height = head + map_h + LABELS + foot
    fig = Figure(figsize=(inches, height), dpi=DPI)
    ax = fig.add_axes((LEFT / inches, (foot + LABELS) / height, map_w / inches, map_h / height))
    extent = (window.i0 - 0.5, window.i1 - 0.5, window.j0 - 0.5, window.j1 - 0.5)
    shown_values = np.ma.masked_invalid(values)
    if p.kind == "categorical":
        ax.imshow(
            shown_values,
            origin="lower",
            extent=extent,
            cmap=colormap(p),
            vmin=-0.5,
            vmax=len(p.colors) - 0.5,
            interpolation="nearest",
        )
    else:
        along = np.ma.masked_invalid(palettes.position(values, domain, middle))
        ax.imshow(along, origin="lower", extent=extent, cmap=colormap(p), vmin=0, vmax=1, interpolation="nearest")
    empties: list[int] = []
    if states is not None:
        for state, color, _ in EMPTY:
            where = states == state
            if where.any():
                empties.append(state)
                ax.imshow(
                    np.ma.masked_where(~where, np.zeros(where.shape)),
                    origin="lower",
                    extent=extent,
                    cmap=ListedColormap([color]),
                    interpolation="nearest",
                )
    _graticule(ax, window, extent, cells_per_inch=cols / map_w)
    _draw_outlines(ax, "counties", window, 0.25, "#9a9a9a")
    _draw_outlines(ax, "states", window, 0.8, "#333333")
    marks = ticks(domain, shown, dates=dates, middle=middle, every=isolines if isinstance(isolines, float) else None)
    if isolines is not None and categories is None:
        _isolines(ax, values, extent, domain, shown, dates, middle, isolines, marks)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_linewidth(1.2)
        side.set_color("#222222")
    y = 0.18 + TITLE / 2
    for line in title_lines:
        fig.text(0.025, 1 - y / height, line, fontsize=13, family=FONT, weight="bold", va="center")
        y += TITLE
    y += (SUB - TITLE) / 2
    for line in subtitle_lines:
        fig.text(0.025, 1 - y / height, line, fontsize=9.5, family=FONT, va="center", color="#444444")
        y += SUB
    top = foot - 0.1  # the legend's band, under the map
    if categories is not None:
        _swatches(fig, p, categories, (0.025, (top - 0.33) / height, 0.95, 0.2 / height))
    else:
        _colorbar(fig.add_axes((0.025, (top - 0.25) / height, 0.5, 0.17 / height)), p, domain, marks, middle)
        fig.text(0.54, (top - 0.165) / height, unit_label, fontsize=8.5, family=FONT, va="center")
        if empties:
            _empty_swatches(fig, empties, 0.6 if unit_label else 0.56, (top - 0.25) / height, 0.17 / height)
    y = top - legend
    for line in caption_lines:
        fig.text(0.025, (y - CAPTION / 2 + 0.06) / height, line, fontsize=8, family=FONT, va="center", color="#444444")
        y -= CAPTION
    fig.text(0.975, 0.14 / height, credit, fontsize=7.5, family=FONT, ha="right", color="#666666")
    return _png(fig)


# --- Isolines -------------------------------------------------------------------------------------------------------

SMOOTH_CELLS = 2.0  # the Gaussian's sigma before contouring, in cells: 2.5 km noise would draw every hollow
ISOLINE_COLOR = "#1a1a1a"


def isoline_levels(
    values: np.ndarray,
    domain: tuple[float, float],
    shown: Callable[[np.ndarray], np.ndarray],
    dates: bool,
    middle: float | None,
    isolines: "Literal['auto'] | float",
) -> list[float]:
    """The values (stored) isolines are drawn at: the legend's ticks (`auto`), or every N of the shown unit over the
    values' range; inside the values' range either way, so every level has a line."""
    known = values[np.isfinite(values)]
    if not known.size:
        return []
    low, high = float(known.min()), float(known.max())
    if isolines == "auto":
        found = ticks(domain, shown, dates=dates, middle=middle).values
    else:
        found = ticks((low, high), shown, dates=dates, middle=middle, every=float(isolines)).values
    return [v for v in found if low < v < high]


def smoothed(values: np.ndarray, sigma: float = SMOOTH_CELLS) -> np.ndarray:
    """A Gaussian smoothing that leaves missing cells out of their neighbours' means (normalized convolution) and
    keeps them missing."""
    known = np.isfinite(values)
    radius = int(np.ceil(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    total = np.where(known, values, 0.0).astype(np.float64)
    weight = known.astype(np.float64)
    for axis in (0, 1):
        total = _convolve(total, kernel, axis)
        weight = _convolve(weight, kernel, axis)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = total / weight
    return np.where(known, out, np.nan)


def _convolve(a: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    """`a` convolved with a symmetric 1-D `kernel` along `axis`, zero past the edges."""
    radius = kernel.size // 2
    pad = [(0, 0), (0, 0)]
    pad[axis] = (radius, radius)
    padded = np.pad(a, pad)
    out = np.zeros_like(a)
    n = a.shape[axis]
    for k, w in enumerate(kernel):
        out += w * (padded[k : k + n] if axis == 0 else padded[:, k : k + n])
    return out


def _isolines(
    ax,
    values: np.ndarray,
    extent: tuple[float, float, float, float],
    domain: tuple[float, float],
    shown: Callable[[np.ndarray], np.ndarray],
    dates: bool,
    middle: float | None,
    isolines: "Literal['auto'] | float",
    marks: Ticks,
) -> None:
    levels = isoline_levels(values, domain, shown, dates, middle, isolines)
    if not levels:
        return
    field = np.ma.masked_invalid(smoothed(values))

    def label(v: float) -> str:
        return date_label(v) if dates else _number(round(float(shown(np.array([v]))[0]), 6))

    plain = [v for v in levels if middle is None or abs(v - middle) > 1e-9]
    heavy = [v for v in levels if middle is not None and abs(v - middle) <= 1e-9]
    for group, width in ((plain, 0.5), (heavy, 1.3)):
        if not group:
            continue
        lines = ax.contour(
            field,
            levels=group,
            origin="lower",
            extent=extent,
            colors=ISOLINE_COLOR,
            linewidths=width,
            linestyles="solid",  # matplotlib dashes levels below 0 by default, and levels are in the stored unit
            zorder=3,
        )
        ax.clabel(lines, fmt=label, fontsize=6.5, inline=True, inline_spacing=2)


# --- Frame and graticule ----------------------------------------------------------------------------------------------

GRATICULE_COLOR = "#b0b0b0"


def graticule_step(lat_span: float) -> float:
    """Degrees between graticule lines: 1° over a state or more, finer over a county."""
    return 1.0 if lat_span > 2.5 else 0.5 if lat_span > 1.0 else 0.25


def _degrees(v: float, positive: str, negative: str) -> str:
    return f"{abs(v):g}°{positive if v >= 0 else negative}"


def _graticule(ax, window: Window, extent: tuple[float, float, float, float], cells_per_inch: float) -> None:
    """Latitude and longitude lines (thin, light, under the outlines), labelled where they leave the frame's left and
    bottom edges. The grid is Lambert conformal, so the lines are projected polylines and curve."""
    lat, lon = NDFD.window_latlon(window)
    lat_lo, lat_hi = float(np.min(lat)), float(np.max(lat))
    lon_lo, lon_hi = float(np.min(lon)), float(np.max(lon))
    step = graticule_step(lat_hi - lat_lo)
    x0, _, y0, _ = extent
    pad = 0.06 * cells_per_inch  # labels this far from the frame
    style = {"fontsize": 7.5, "family": FONT, "color": "#333333", "clip_on": False}
    for parallel in np.arange(np.floor(lat_lo / step) * step, lat_hi + step, step):
        lons = np.linspace(lon_lo - 2, lon_hi + 2, 400)
        j, i = NDFD.fractional_index(np.full(lons.shape, parallel), lons)
        ax.plot(i, j, color=GRATICULE_COLOR, linewidth=0.4, zorder=2)
        crossing = _crossing(i, j, x0)
        if crossing is not None and extent[2] <= crossing <= extent[3]:
            ax.text(x0 - pad, crossing, _degrees(float(parallel), "N", "S"), ha="right", va="center", **style)
    for meridian in np.arange(np.floor(lon_lo / step) * step, lon_hi + step, step):
        lats = np.linspace(lat_lo - 2, lat_hi + 2, 400)
        j, i = NDFD.fractional_index(lats, np.full(lats.shape, meridian))
        ax.plot(i, j, color=GRATICULE_COLOR, linewidth=0.4, zorder=2)
        crossing = _crossing(j, i, y0)
        if crossing is not None and extent[0] <= crossing <= extent[1]:
            ax.text(crossing, y0 - pad, _degrees(float(meridian), "E", "W"), ha="center", va="top", **style)


def _crossing(along: np.ndarray, other: np.ndarray, at: float) -> float | None:
    """Where a polyline (`along`, `other`) crosses `along == at`: `other` there, by linear interpolation; None if it
    doesn't."""
    side = np.sign(along - at)
    k = np.flatnonzero(side[:-1] * side[1:] <= 0)
    if not k.size:
        return None
    a = int(k[0])
    if along[a + 1] == along[a]:
        return float(other[a])
    f = (at - along[a]) / (along[a + 1] - along[a])
    return float(other[a] + f * (other[a + 1] - other[a]))
