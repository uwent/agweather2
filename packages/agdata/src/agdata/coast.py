"""Coarse land-only fields on the 2.5 km grid at the coast: soil temperature and snow depth (D79).

ERA5-Land (0.1°) and IFS (~9 km) give soil over water too, but there it's the lake's temperature, and a cell that's
partly water is a blend of soil and lake by its land fraction (checked over Door County, July and January 2025:
open water +2.5 °C in mid-January, land −5.6 °C, mixed cells between). So a 2.5 km cell takes its value from the
source's land points only (fraction ≥ 0.5), wherever its own center is:

- Its interpolation neighbours that are land, their weights renormalized (`Weights`, `land_only`).
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


@dataclass(frozen=True, kw_only=True)
class Weights:
    """Each 2.5 km cell's neighbours in a source (flat indices into its points) and their weights: (k, ny, nx). A
    cell whose weights are all zero is missing."""

    cells: np.ndarray
    weights: np.ndarray

    def apply(self, values: np.ndarray, needed: np.ndarray, hours_per_pass: int = 24) -> np.ndarray:
        """Values at the `needed` flat points (sorted), (points, hours) → (hours, ny, nx); NaN where no neighbour
        with weight has one."""
        # (k, ny, nx); a neighbour with no weight anywhere may not be in `needed`: any row will do for it
        rows = np.minimum(np.searchsorted(needed, self.cells), max(0, needed.size - 1))
        out = np.full((values.shape[1], *self.cells.shape[1:]), np.nan, dtype=np.float32)
        for h in range(0, values.shape[1], hours_per_pass):
            v = np.moveaxis(values[rows, h : h + hours_per_pass], -1, 1)  # (k, hours, ny, nx)
            w = np.where(np.isfinite(v), self.weights[:, None], 0.0)
            total = w.sum(axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = (np.where(w > 0, v, 0.0) * w).sum(axis=0) / total
            out[h : h + hours_per_pass] = np.where(total > 0, mean, np.nan)
        return out

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
