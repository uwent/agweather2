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


@dataclass(frozen=True, kw_only=True)
class County:
    geoid: str  # five-digit FIPS code, state first
    name: str
    state: str  # postal abbreviation
    land_m2: int = 0  # the Census Bureau's land area
    cells: int = 0  # 2.5 km grid cells that summaries count as the county (`agdata.regions.summary_counties`)


@cache
def _grid() -> tuple[np.ndarray, float, float, float]:
    with np.load(DATA / "counties.npz") as z:
        return z["county"], float(z["south"]), float(z["west"]), float(z["step"])


@cache
def counties() -> tuple[County | None, ...]:
    """Counties by grid id (index 0 is no county)."""
    with (DATA / "counties.csv").open() as f:
        rows = list(csv.DictReader(f))
    return (
        None,
        *(
            County(
                geoid=r["geoid"],
                name=r["name"],
                state=r["state"],
                land_m2=int(r.get("land_m2") or 0),
                cells=int(r.get("cells") or 0),
            )
            for r in rows
        ),
    )


def county_ids(latitude, longitude) -> np.ndarray:
    """Grid ids of the counties at each point (0 for none), the nearest within NEAREST_STEPS where a point misses."""
    grid, south, west, step = _grid()
    lat, lon = np.broadcast_arrays(np.asarray(latitude, dtype=float), np.asarray(longitude, dtype=float))
    j = np.rint((lat - south) / step).astype(int)
    i = np.rint((lon - west) / step).astype(int)
    inside = (j >= 0) & (j < grid.shape[0]) & (i >= 0) & (i < grid.shape[1])
    ids = np.where(inside, grid[np.clip(j, 0, grid.shape[0] - 1), np.clip(i, 0, grid.shape[1] - 1)], 0)
    misses = np.flatnonzero((ids == 0) & inside)
    if misses.size:
        ids.flat[misses] = _nearest(grid, j.flat[misses], i.flat[misses])
    return ids


def county_at(latitude: float, longitude: float) -> County | None:
    return counties()[int(county_ids(latitude, longitude))]


def _nearest(grid: np.ndarray, j: np.ndarray, i: np.ndarray) -> np.ndarray:
    """The nearest county id within NEAREST_STEPS of each grid index (0 for none): offsets tried nearest first, ties
    to the lower row then column, all misses at once (a state's shore had thousands, ~0.3 s one by one)."""
    n = NEAREST_STEPS
    offsets = sorted(
        ((dj, di) for dj in range(-n, n + 1) for di in range(-n, n + 1) if (dj, di) != (0, 0)),
        key=lambda o: (o[0] ** 2 + o[1] ** 2, o[0], o[1]),
    )
    found = np.zeros(j.shape, dtype=grid.dtype)
    for dj, di in offsets:
        open_ = found == 0
        if not open_.any():
            break
        jj, ii = j[open_] + dj, i[open_] + di
        ok = (jj >= 0) & (jj < grid.shape[0]) & (ii >= 0) & (ii < grid.shape[1])
        value = np.zeros(jj.shape, dtype=grid.dtype)
        value[ok] = grid[jj[ok], ii[ok]]
        found[open_] = value
    return found
