"""Coarse land-only fields on the 2.5 km grid at the coast: soil temperature and snow depth (D79).

ERA5-Land (0.1°) and IFS (~9 km) give soil over water too, but there it's the lake's temperature, and a cell that's
partly water is a blend of soil and lake by its land fraction (checked over Door County, July and January 2025:
open water +2.5 °C in mid-January, land −5.6 °C, mixed cells between). So a 2.5 km cell takes its value from the
source's land points only (fraction ≥ 0.5), wherever its own center is:

- Its interpolation neighbours that are land, their weights renormalized (`Weights`, `land_only`). The neighbours
  are the source's 4 × 4 points around the cell, weighted by the cubic B-spline (`bspline`): every weight is
  positive, so a cell's value stays within its neighbours' and dropping water ones can't blow it up (an
  interpolating cubic such as Catmull-Rom has negative weights, and masked it reached −136 °C); the result is
  smooth across the source's cell lines, where bilinear's slope jumps and its creases and squares show on a map.
  It's an approximation, not an interpolation: a source point's own value is softened toward its neighbours' (a
  lone warm 0.1° cell by about a degree), which suits values that are each an area's mean. A field linear in the
  source's indices comes through exactly.
- With none of them land (the coast, the Door Peninsula's tip, Washington Island, the Apostle Islands), the nearest
  land point within MAX_COAST_KM (`finish`).
- On water by our own 2.5 km mask (`water`: where URMA analyzes a wave height, the Great Lakes and the ocean;
  `scripts/make_water_mask.py`), nothing: soil and snow are missing there, whatever the source holds.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np

from agdata.grid import NDFD, Window

WATER = Path(__file__).parent / "data" / "water.npz"
KERNEL_OFFSETS = (-1, 0, 1, 2)  # `bspline`'s points, from the source point at or before a cell
PASS_BUDGET = 4_000_000  # cell-hours in a pass of `Weights.apply` (float64: ~32 MB an array)
MAX_COAST_KM = 40.0  # a land cell of ours reaches this far for the nearest land point (Washington Island: 32 km)
EARTH_KM = 6371.0


@cache
def _water_full() -> np.ndarray:
    with np.load(WATER) as f:
        shape = tuple(int(n) for n in f["shape"])
        return np.unpackbits(f["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)


def water(window: Window) -> np.ndarray:
    """Open water on the window (ny, nx): the Great Lakes and the ocean, from URMA's wave height."""
    return _water_full()[window.j0 : window.j1, window.i0 : window.i1]


def bspline(t: np.ndarray) -> np.ndarray:
    """The cubic B-spline's weights (4, …) for the points at KERNEL_OFFSETS from the one at or before a position,
    `t` (0–1) past it. Positive, summing to 1."""
    t = np.asarray(t, dtype=np.float64)
    s = 1 - t
    return np.stack([s**3 / 6, (3 * t**3 - 6 * t**2 + 4) / 6, (3 * s**3 - 6 * s**2 + 4) / 6, t**3 / 6])


@dataclass(frozen=True, kw_only=True)
class Weights:
    """Each 2.5 km cell's neighbours in a source (flat indices into its points) and their weights: (k, ny, nx). A
    cell whose weights are all zero is missing."""

    cells: np.ndarray
    weights: np.ndarray

    def apply(self, values: np.ndarray, needed: np.ndarray, hours_per_pass: int | None = None) -> np.ndarray:
        """Values at the `needed` flat points (sorted), (points, hours) → (hours, ny, nx); NaN where no neighbour
        with weight has one. Hours go `hours_per_pass` at a time, by default as many as PASS_BUDGET allows; within a
        pass the neighbours are summed one at a time, so a pass holds a few (cells, hours) arrays, whatever k is."""
        k, shape = self.cells.shape[0], self.cells.shape[1:]
        cells = self.cells.reshape(k, -1)
        weights = self.weights.reshape(k, -1)
        used = np.flatnonzero((weights > 0).any(axis=0))  # cells with no weight (our water) stay NaN unread
        # a neighbour with no weight anywhere may not be in `needed`: any row will do for it
        rows = np.minimum(np.searchsorted(needed, cells[:, used]), max(0, needed.size - 1))
        weights = weights[:, used]
        hours = values.shape[1]
        out = np.full((hours, int(np.prod(shape))), np.nan, dtype=np.float32)
        if hours_per_pass is None:
            hours_per_pass = max(1, PASS_BUDGET // max(1, used.size))
        weight_total = weights.sum(axis=0)[:, None]  # > 0 for every used cell
        for h in range(0, hours, hours_per_pass):
            block = values[:, h : h + hours_per_pass]
            weighted = np.zeros((used.size, block.shape[1]))
            if np.isfinite(block).all():  # the usual case: every neighbour counts, with its weight as built
                for n in range(k):
                    weighted += weights[n][:, None] * block[rows[n]]
                out[h : h + hours_per_pass, used] = (weighted / weight_total).T
                continue
            total = np.zeros_like(weighted)
            for n in range(k):
                v = block[rows[n]]  # (cells, hours)
                w = np.where(np.isfinite(v), weights[n][:, None], 0.0)
                total += w
                weighted += np.where(w > 0, v, 0.0) * w
            with np.errstate(invalid="ignore", divide="ignore"):
                out[h : h + hours_per_pass, used] = np.where(total > 0, weighted / total, np.nan).T
        return out.reshape(hours, *shape)

    @property
    def needed(self) -> np.ndarray:
        """The source points read, sorted: those with weight somewhere."""
        return np.unique(self.cells[self.weights > 0])


def land_only(weights: Weights, is_land: np.ndarray) -> Weights:
    """Zero weight for neighbours that aren't land (`is_land`: by flat point, as `weights.cells`)."""
    return Weights(cells=weights.cells, weights=np.where(is_land, weights.weights, 0.0))


def finish(
    weights: Weights, window: Window, land_points: np.ndarray, point_lat: np.ndarray, point_lon: np.ndarray
) -> tuple[Weights, np.ndarray]:
    """Land-only `weights` with the coast rule: a cell of ours on land with no land neighbour takes the nearest of
    `land_points` (flat indices, with their `point_lat`, `point_lon`) within MAX_COAST_KM; a cell on water takes
    nothing. Returns the weights and where the nearest point was used (ny, nx)."""
    on_water = water(window)
    total = weights.weights.sum(axis=0)
    lonely = (total <= 0) & ~on_water
    cells, w = weights.cells.copy(), weights.weights.copy()
    nearest = np.zeros(on_water.shape, dtype=bool)
    if lonely.any() and land_points.size:
        lat, lon = NDFD.window_latlon(window)
        jj, ii = np.nonzero(lonely)
        found, km = _nearest(np.asarray(lat)[jj, ii], np.asarray(lon)[jj, ii], point_lat, point_lon)
        near = km <= MAX_COAST_KM
        jj, ii = jj[near], ii[near]
        cells[:, jj, ii] = land_points[found[near]]
        w[:, jj, ii] = 0.0
        w[0, jj, ii] = 1.0
        nearest[jj, ii] = True
    w[:, on_water] = 0.0
    return Weights(cells=cells, weights=w), nearest


def _nearest(
    lat: np.ndarray, lon: np.ndarray, point_lat: np.ndarray, point_lon: np.ndarray, budget: int = 5_000_000
) -> tuple[np.ndarray, np.ndarray]:
    """For each (lat, lon), the index of the nearest point and its distance in km (equirectangular: exact enough
    over 40 km). Only points near the targets' box are searched, `budget` distances a block."""
    margin = 0.5  # degrees: well past MAX_COAST_KM
    near = np.flatnonzero(
        (point_lat >= lat.min() - margin)
        & (point_lat <= lat.max() + margin)
        & (point_lon >= lon.min() - margin)
        & (point_lon <= lon.max() + margin)
    )
    found = np.zeros(lat.size, dtype=np.int64)
    km = np.full(lat.size, np.inf)
    if not near.size:
        return found, km
    plat, plon = np.radians(point_lat[near]), np.radians(point_lon[near])
    block = max(1, budget // near.size)
    for k in range(0, lat.size, block):
        a, b = np.radians(lat[k : k + block])[:, None], np.radians(lon[k : k + block])[:, None]
        x = (plon[None] - b) * np.cos((plat[None] + a) / 2)
        y = plat[None] - a
        d = x * x + y * y
        best = np.argmin(d, axis=1)
        found[k : k + block] = near[best]
        km[k : k + block] = np.sqrt(d[np.arange(d.shape[0]), best]) * EARTH_KM
    return found, km
