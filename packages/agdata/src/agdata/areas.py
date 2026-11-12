"""The area around a point: the grid cells within a radius, averaged into one series (Ben, 2026-11-10).

A point's weather is its one 2.5 km cell's, which near a lake or a city can differ a good deal from the farms a few
miles away (Madison's isthmus cell had a frost-free season 35 days longer than a cell 8 miles northwest, over
2016–2025). An `Area` is every cell whose center lies within `radius_km` of the point (always the point's own),
weighted `equal` or `center` (a Gaussian with σ = radius / 2, cut off at the radius), clipped to the archive's
window. A read of an area (`agdata.series`) reads each of its cells and averages them step by step before anything
is computed from them, so days, degree days, frost and models come from the area's weather.

The average skips cells without a value at a step and is missing only where none has one. Nothing is masked by
hand: air and wind keep the cells over water (a lake's air moves inland, as Door County's cherries show), and soil
and snow are already missing over the Great Lakes (`agdata.coast`, D79), so their averages are over land alone.
Wind direction is averaged as unit vectors.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from agdata.grid import NDFD, Window

Weighting = Literal["equal", "center"]
MAX_RADIUS_KM = 16.0934  # 10 miles: well under a county (Wisconsin's average ~750 sq mi, ~27 miles across)
EARTH_KM = 6371.0
CIRCULAR = {"wind_direction"}  # averaged as unit vectors (degrees)
Cell = tuple[int, int]


@dataclass(frozen=True, kw_only=True)
class Area:
    """Cells around a point and their weights (summing to 1), the point's own cell first unless `land_only` left
    it out."""

    center: Cell  # the point's own cell, in `cells` or not
    cells: tuple[Cell, ...]
    weights: tuple[float, ...]
    radius_km: float
    weighting: Weighting


def around(
    lat: float,
    lng: float,
    radius_km: float,
    weighting: Weighting = "equal",
    window: Window | None = None,
    keep: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None,
) -> Area | None:
    """The cells whose centers lie within `radius_km` of (lat, lng), inside `window` if given, and for which `keep`
    (grid indices j, i → bool) is true if given (`land_only`: no cell all water, the point's own included); None
    off the grid or where no cell is left."""
    if not 0 < radius_km <= MAX_RADIUS_KM + 1e-6:
        raise ValueError(f"a radius is over 0 and at most {MAX_RADIUS_KM} km, not {radius_km}")
    center = NDFD.cell_of(lat, lng)
    if center is None:
        return None
    reach = math.ceil(radius_km / 2.5) + 1
    js = np.arange(center[0] - reach, center[0] + reach + 1)
    is_ = np.arange(center[1] - reach, center[1] + reach + 1)
    jj, ii = np.meshgrid(js, is_, indexing="ij")
    clat, clng = NDFD.latlon(jj, ii)
    d = _km(lat, lng, np.asarray(clat), np.asarray(clng))
    inside = d <= radius_km
    inside[reach, reach] = True  # the point's own cell, whatever its center's distance
    if window is not None:
        inside &= (jj >= window.j0) & (jj < window.j1) & (ii >= window.i0) & (ii < window.i1)
    if keep is not None:
        inside &= keep(jj, ii)
    if not inside.any():
        return None
    order = np.argsort(np.where(inside, d, np.inf).ravel(), kind="stable")
    own = reach * len(is_) + reach
    first = [own] if inside[reach, reach] else []
    picked = first + [int(k) for k in order if inside.ravel()[k] and k != own]
    dist = d.ravel()[picked]
    if weighting == "center":
        sigma = radius_km / 2
        w = np.exp(-(dist**2) / (2 * sigma**2))
    else:
        w = np.ones(len(picked))
    w = w / w.sum()
    cells = tuple((int(jj.ravel()[k]), int(ii.ravel()[k])) for k in picked)
    return Area(
        center=(int(center[0]), int(center[1])),
        cells=cells,
        weights=tuple(float(x) for x in w),
        radius_km=radius_km,
        weighting=weighting,
    )


def _km(lat: float, lng: float, lats: np.ndarray, lngs: np.ndarray) -> np.ndarray:
    p1, p2 = math.radians(lat), np.radians(lats)
    dp, dl = p2 - p1, np.radians(lngs - lng)
    a = np.sin(dp / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


Place = Cell | Area


def cells_of(places: Sequence[Place]) -> list[Cell]:
    """Every cell the places read, each once, in order."""
    return list(dict.fromkeys(c for p in places for c in (p.cells if isinstance(p, Area) else (p,))))


def combine(values: np.ndarray, cells: Sequence[Cell], places: Sequence[Place], name: str = "") -> np.ndarray:
    """Steps × `cells` (as `cells_of` gave them) → steps × `places`: a cell's own column, or an area's weighted
    mean over its cells with a value at each step (missing where none has one)."""
    column = {c: k for k, c in enumerate(cells)}
    out = np.full((values.shape[0], len(places)), np.nan)
    for p, place in enumerate(places):
        if not isinstance(place, Area):
            out[:, p] = values[:, column[place]]
            continue
        own = values[:, [column[c] for c in place.cells]]
        w = np.asarray(place.weights)[None, :]
        known = np.isfinite(own)
        weight = np.where(known, w, 0.0).sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            if name in CIRCULAR:
                rad = np.radians(np.where(known, own, 0.0))
                x = (np.cos(rad) * np.where(known, w, 0.0)).sum(axis=1)
                y = (np.sin(rad) * np.where(known, w, 0.0)).sum(axis=1)
                mean = np.degrees(np.arctan2(y, x)) % 360
            else:
                mean = np.where(known, own * w, 0.0).sum(axis=1) / weight
        out[:, p] = np.where(weight > 0, mean, np.nan)
    return out
