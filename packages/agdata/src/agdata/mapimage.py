"""Map images rendered with matplotlib (PLAN.md Phase 5 G, D60): legends for colored tiles, and static maps.

Drawn with matplotlib's Agg backend only (no display, no GDAL). Values arrive in the stored unit; `shown` converts
a stored value to the unit a reader asked for (`units=`), which the labels use, while colors follow the stored
values (a palette's domain is in the stored unit).
"""

import io
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from agdata.grid import NDFD, Window
from agdata.palettes import Palette

DPI = 100
FONT = "DejaVu Sans"


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
) -> bytes:
    """A legend: a color bar over the domain with round ticks in the shown unit (a conversion that's linear, as
    every unit's is), or one swatch per category. A long title wraps."""
    if categories is not None:
        return _categories_png(p, categories, title, width)
    lines = textwrap.wrap(f"{title} ({unit_label})" if unit_label else title, width=width // 7)
    height = 0.62 + 0.15 * len(lines)
    fig = Figure(figsize=(width / DPI, height), dpi=DPI)
    _colorbar(fig.add_axes((0.04, 0.32 / height, 0.92, 0.18 / height)), p, domain, shown)
    fig.text(0.04, 1 - 0.08 / height, "\n".join(lines), fontsize=8.5, family=FONT, va="top", linespacing=1.3)
    return _png(fig)


def _colorbar(ax, p: Palette, domain: tuple[float, float], shown: Callable[[np.ndarray], np.ndarray]) -> None:
    """A horizontal color bar over the domain, ticked at round numbers of the shown unit."""
    lo, hi = domain
    ax.imshow(np.linspace(lo, hi, 256)[None], aspect="auto", cmap=colormap(p), extent=(lo, hi, 0, 1), vmin=lo, vmax=hi)
    ax.set_yticks([])
    a, b = (float(v) for v in shown(np.array([lo, hi])))
    ticks = [t for t in MaxNLocator(nbins=5).tick_values(min(a, b), max(a, b)) if min(a, b) <= t <= max(a, b)]
    ax.set_xticks([lo + (t - a) / (b - a) * (hi - lo) for t in ticks] if b != a else [lo])
    ax.set_xticklabels([_number(t) for t in ticks] if b != a else [_number(a)], fontsize=8, family=FONT)
    for side in ax.spines.values():
        side.set_linewidth(0.5)


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
) -> bytes:
    """A map of `values` (y, x) over `window` (south row first; NaN blank), with county and state outlines, a
    title and a subtitle (what and when; each wraps), a legend, a caption (the data sources, the days combined) and
    a credit line."""
    rows, cols = window.shape
    inches = width / DPI
    map_w = inches - 0.4
    map_h = map_w * rows / cols
    title_lines = textwrap.wrap(title, width=int(inches * 9.5)) or [""]
    subtitle_lines = textwrap.wrap(subtitle, width=int(inches * 14))
    caption_lines = [line for part in caption for line in textwrap.wrap(part, width=int(inches * 15.5))]
    TITLE, SUB, CAPTION = 0.25, 0.19, 0.16  # line heights, inches
    head = 0.18 + TITLE * len(title_lines) + SUB * len(subtitle_lines) + 0.08
    legend = 0.6
    foot = legend + CAPTION * len(caption_lines) + 0.3
    height = head + map_h + foot
    fig = Figure(figsize=(inches, height), dpi=DPI)
    ax = fig.add_axes((0.2 / inches, foot / height, map_w / inches, map_h / height))
    extent = (window.i0 - 0.5, window.i1 - 0.5, window.j0 - 0.5, window.j1 - 0.5)
    lo, hi = domain
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
        ax.imshow(
            shown_values, origin="lower", extent=extent, cmap=colormap(p), vmin=lo, vmax=hi, interpolation="nearest"
        )
    _draw_outlines(ax, "counties", window, 0.25, "#9a9a9a")
    _draw_outlines(ax, "states", window, 0.8, "#333333")
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()
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
        _colorbar(fig.add_axes((0.025, (top - 0.25) / height, 0.5, 0.17 / height)), p, domain, shown)
        fig.text(0.54, (top - 0.165) / height, unit_label, fontsize=8.5, family=FONT, va="center")
    y = top - legend
    for line in caption_lines:
        fig.text(0.025, (y - CAPTION / 2 + 0.06) / height, line, fontsize=8, family=FONT, va="center", color="#444444")
        y -= CAPTION
    fig.text(0.975, 0.14 / height, credit, fontsize=7.5, family=FONT, ha="right", color="#666666")
    return _png(fig)
