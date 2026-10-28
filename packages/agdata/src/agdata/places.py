"""Which county and state a point is in, from a 0.025° grid of county ids over the lower 48 (D34).

`data/counties.npz` and `data/counties.csv` are built by `scripts/build_counties.py` from the Census Bureau's 2024
cartographic boundaries (1:500,000). A point is looked up by index arithmetic; one in water or just over the border
(the grid misses within about 1.5 km of a line) takes the nearest county within `NEAREST_STEPS` grid steps, so a
coastal field still finds its county. Points outside the lower 48 have none.
"""

import csv
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"
NEAREST_STEPS = 4  # 0.1°, about 10 km


@dataclass(frozen=True)
class County:
    geoid: str  # five-digit FIPS code, state first
    name: str
    state: str  # postal abbreviation


@cache
def _grid() -> tuple[np.ndarray, float, float, float]:
    with np.load(DATA / "counties.npz") as z:
        return z["county"], float(z["south"]), float(z["west"]), float(z["step"])


@cache
def counties() -> tuple[County | None, ...]:
    """Counties by grid id (index 0 is no county)."""
    with (DATA / "counties.csv").open() as f:
        rows = list(csv.DictReader(f))
    return (None, *(County(r["geoid"], r["name"], r["state"]) for r in rows))


def county_ids(latitude, longitude) -> np.ndarray:
    """Grid ids of the counties at each point (0 for none), the nearest within NEAREST_STEPS where a point misses."""
    grid, south, west, step = _grid()
    lat, lon = np.broadcast_arrays(np.asarray(latitude, dtype=float), np.asarray(longitude, dtype=float))
    j = np.rint((lat - south) / step).astype(int)
    i = np.rint((lon - west) / step).astype(int)
    inside = (j >= 0) & (j < grid.shape[0]) & (i >= 0) & (i < grid.shape[1])
    ids = np.where(inside, grid[np.clip(j, 0, grid.shape[0] - 1), np.clip(i, 0, grid.shape[1] - 1)], 0)
    for k in np.flatnonzero((ids == 0) & inside):
        ids.flat[k] = _nearest(grid, j.flat[k], i.flat[k])
    return ids


def county_at(latitude: float, longitude: float) -> County | None:
    return counties()[int(county_ids(latitude, longitude))]


def _nearest(grid: np.ndarray, j: int, i: int) -> int:
    n = NEAREST_STEPS
    block = grid[max(j - n, 0) : j + n + 1, max(i - n, 0) : i + n + 1]
    found = np.argwhere(block > 0)
    if not found.size:
        return 0
    offset = np.array([max(j - n, 0), max(i - n, 0)])
    distance = np.sum((found + offset - [j, i]) ** 2, axis=1)
    jj, ii = found[np.argmin(distance)]
    return int(block[jj, ii])
