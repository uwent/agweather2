"""Map images rendered with matplotlib (PLAN.md Phase 5 G, D60): legends for colored tiles, and static maps.

Drawn with matplotlib's Agg backend only (no display, no GDAL). Values arrive in the stored unit; `shown` converts
a stored value to the unit a reader asked for (`units=`), which the labels use, while colors follow the stored
values (a palette's domain is in the stored unit).
"""

import io
import textwrap
from collections.abc import Callable, Sequence

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

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
    bar = 0.18 / height
    ax = fig.add_axes((0.04, 0.32 / height, 0.92, bar))
    lo, hi = domain
    ax.imshow(np.linspace(lo, hi, 256)[None], aspect="auto", cmap=colormap(p), extent=(lo, hi, 0, 1), vmin=lo, vmax=hi)
    ax.set_yticks([])
    a, b = (float(v) for v in shown(np.array([lo, hi])))
    ticks = [t for t in MaxNLocator(nbins=5).tick_values(min(a, b), max(a, b)) if min(a, b) <= t <= max(a, b)]
    ax.set_xticks([lo + (t - a) / (b - a) * (hi - lo) for t in ticks] if b != a else [lo])
    ax.set_xticklabels([_number(t) for t in ticks] if b != a else [_number(a)], fontsize=8, family=FONT)
    fig.text(0.04, 1 - 0.08 / height, "\n".join(lines), fontsize=8.5, family=FONT, va="top", linespacing=1.3)
    for side in ax.spines.values():
        side.set_linewidth(0.5)
    return _png(fig)


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
