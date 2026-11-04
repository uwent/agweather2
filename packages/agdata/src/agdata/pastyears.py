"""Past years' daily values laid out for reading a point over time (D63's projection; Phase 6's climatology, D61).

The daily store is chunked a day at a time (one map tile per chunk), right for maps but slow at a point: a year of
one variable is 365 chunk reads (0.38 s). This keeps a copy of each settled year's daily store as one array of
every variable (variables × days × y × x), chunked as all of them over the whole year × 16 × 16 cells, so a cell's
year of everything is one chunk read: 17 ms for 24 variables, against 0.3–0.5 s rolling up the hours (opening a
store of 24 arrays alone took 75 ms). Same values, same
packing; built from the daily store by `build`, after the year is over and its days are final (the daily store
written no later than the copy, no stale variables). `stale_years` says which years need building or rebuilding
(a later write to the daily store, a variable's version, D29); `manage.py pastyears` and a weekly job keep them.

A copy marks itself complete last, so a reader never takes a half-built one; `read` returns None for a year it
can't serve, and the caller falls back to reading the hours (`agdata.series.point_days`)."""

import shutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from zarr.codecs.numcodecs import PCodec

from agdata.catalog import DAILY_VARIABLES, FILL, Variable
from agdata.grid import Window
from agdata.store import DAILY, GridStore, StoreLayout

PAST = StoreLayout(kind="daily-by-point", step="day")
CELLS = 16  # chunk side, in cells
TILE = 128  # cells per side of each block copied (a multiple of CELLS)


def years_on_disk(data_dir: Path, layout: StoreLayout) -> list[int]:
    folder = layout.path(data_dir, 2000).parent
    found = []
    for path in folder.glob("*.zarr") if folder.exists() else ():
        try:
            found.append(int(path.stem))
        except ValueError:
            continue
    return sorted(found)


def _daily_written(store: GridStore) -> float | None:
    stamps = [s for name in store.variables if (s := store.written(name)) is not None]
    return max(stamps) if stamps else None


def status(data_dir: Path, year: int) -> str | None:
    """Why a year's copy needs building ("missing", "incomplete", "older than the daily store", "versions"), or None
    if it's current."""
    path = PAST.path(data_dir, year)
    if not path.exists():
        return "missing"
    attrs: dict[str, Any] = dict(zarr.open_group(path, mode="r").attrs)
    if not attrs.get("complete"):
        return "incomplete"
    daily = GridStore.open(data_dir, DAILY, year, _present(data_dir, year))
    written = _daily_written(daily)
    if written is not None and written > float(attrs.get("daily_written") or 0):
        return "older than the daily store"
    if attrs.get("versions") != {v.name: int(v.version) for v in daily.variables.values()}:
        return "versions"
    return None


def stale_years(data_dir: Path, before: int) -> dict[int, str]:
    """Each year before `before` with a daily store whose copy needs building, and why."""
    found = {}
    for year in years_on_disk(data_dir, DAILY):
        if year < before and (reason := status(data_dir, year)) is not None:
            found[year] = reason
    return found


def _present(data_dir: Path, year: int) -> list[Variable]:
    group = zarr.open_group(DAILY.path(data_dir, year), mode="r")
    keys = set(group.array_keys())
    return [v for name, v in DAILY_VARIABLES.items() if name in keys]


def build(data_dir: Path, year: int, progress: Callable[[int, int], None] | None = None) -> None:
    """(Re)builds a year's copy from its daily store, which must have no stale variables (`rebuild --stale` first).
    Built beside its path and renamed into place once whole."""
    variables = _present(data_dir, year)
    daily = GridStore.open(data_dir, DAILY, year, variables)
    if daily.stale:
        raise ValueError(f"daily/{year} has stale variables ({', '.join(sorted(daily.stale))}): rebuild them first")
    written = _daily_written(daily)
    path = PAST.path(data_dir, year)
    building = path.with_name(path.name + ".part")
    if building.exists():
        shutil.rmtree(building)
    n, w = daily.length, daily.window
    group = zarr.open_group(building, mode="w")
    values = group.create_array(
        "values",
        shape=(len(variables), n, *w.shape),
        chunks=(len(variables), n, min(CELLS, w.shape[0]), min(CELLS, w.shape[1])),
        dtype="int16",
        fill_value=int(FILL),
        serializer=PCodec(level=8),
    )
    tiles = list(_tiles(w))
    for k, tile in enumerate(tiles):
        block = np.stack([v.encode(daily.read_steps(v.name, 0, n, tile)) for v in variables])
        values[:, :, tile.j0 - w.j0 : tile.j1 - w.j0, tile.i0 - w.i0 : tile.i1 - w.i0] = block
        if progress is not None:
            progress(k + 1, len(tiles))
    group.attrs.update(
        {
            "year": year,
            "window": {"j0": w.j0, "j1": w.j1, "i0": w.i0, "i1": w.i1},
            "names": [v.name for v in variables],
            "daily_written": written,
            "versions": {v.name: int(v.version) for v in variables},
            "complete": True,
        }
    )
    if path.exists():
        shutil.rmtree(path)
    building.rename(path)


def _tiles(window: Window) -> Iterable[Window]:
    for j in range(window.j0, window.j1, TILE):
        for i in range(window.i0, window.i1, TILE):
            yield Window(j0=j, j1=min(j + TILE, window.j1), i0=i, i1=min(i + TILE, window.i1))


@dataclass
class _Year:
    values: Any  # the zarr array
    names: list[str]
    window: Window


@dataclass
class Reader:
    """Reads a cell's days from the copies, opening each year's once (a request reads several years)."""

    data_dir: Path
    opened: dict[int, _Year | None] = field(default_factory=dict)

    def _year(self, year: int) -> _Year | None:
        if year not in self.opened:
            path = PAST.path(self.data_dir, year)
            found = None
            if path.exists():
                group = zarr.open_group(path, mode="r")
                attrs: dict[str, Any] = dict(group.attrs)
                if attrs.get("complete"):
                    w = attrs["window"]
                    window = Window(j0=w["j0"], j1=w["j1"], i0=w["i0"], i1=w["i1"])
                    found = _Year(values=group["values"], names=list(attrs["names"]), window=window)
            self.opened[year] = found
        return self.opened[year]

    def read(self, j: int, i: int, first: date, last: date, names: list[str]) -> dict[str, np.ndarray] | None:
        """Days first..last of `names` at a cell, or None if any year in the span has no complete copy with them
        (or the cell is outside it)."""
        n = (last - first).days + 1
        out = {name: np.full(n, np.nan) for name in names}
        day = first
        while day <= last:
            found = self._year(day.year)
            if found is None or not set(names) <= set(found.names) or not found.window.contains(j, i):
                return None
            end = min(last, date(day.year, 12, 31))
            t0, t1 = (day - date(day.year, 1, 1)).days, (end - date(day.year, 1, 1)).days + 1
            packed = np.asarray(found.values[:, t0:t1, j - found.window.j0, i - found.window.i0])
            k = (day - first).days
            for name in names:
                out[name][k : k + (t1 - t0)] = DAILY_VARIABLES[name].decode(packed[found.names.index(name)])
            day = end + timedelta(days=1)
        return out
