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
can't serve, and the caller falls back to reading the hours (`agdata.series.point_days`). Builds take turns (an
flock on the copies' folder): they write a shared `.part` beside the copy, and two at once (the weekly job beside
`archive fill` or `manage.py pastyears`) once left 2017's marked complete without its array (2026-11-09)."""

import fcntl
import os
import shutil
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from zarr.codecs.numcodecs import PCodec
from zarr.errors import GroupNotFoundError

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


OUT_OF_DATE_DATA = "out of date: the daily data changed"
OUT_OF_DATE_CODE = "out of date: the daily variables' code changed"


def status(data_dir: Path, year: int) -> str | None:
    """Why a year's copy needs building, in words for the archive table and the dashboard, or None if it's current:
    "missing", "incomplete" (a build stopped partway), "out of date: the daily data changed" (the daily store was
    written since the copy was built, by an ingest, a rebuild or `archive fill`'s December 31), or "out of date: the
    daily variables' code changed"."""
    group = _open_copy(PAST.path(data_dir, year))
    if group is None:
        return "missing"
    attrs: dict[str, Any] = dict(group.attrs)
    if not _complete(PAST.path(data_dir, year), attrs):
        return "incomplete"  # a build stopped partway
    daily = GridStore.open(data_dir, DAILY, year, _present(data_dir, year))
    written = _daily_written(daily)
    if written is not None and written > float(attrs.get("daily_written") or 0):
        return OUT_OF_DATE_DATA
    if attrs.get("versions") != {v.name: int(v.version) for v in daily.variables.values()}:
        return OUT_OF_DATE_CODE
    return None


def stale_years(data_dir: Path, before: int) -> dict[int, str]:
    """Each year before `before` with a daily store whose copy needs building, and why."""
    found = {}
    for year in years_on_disk(data_dir, DAILY):
        if year < before and (reason := status(data_dir, year)) is not None:
            found[year] = reason
    return found


def _open_copy(path: Path) -> zarr.Group | None:
    """A year's copy, or None if there's none. `build` swaps a new copy in by two renames, and a reader that looks
    between them finds no copy rather than an error (the dashboard's year table did)."""
    try:
        return zarr.open_group(path, mode="r")
    except (FileNotFoundError, GroupNotFoundError):
        return None


def _complete(path: Path, attrs: dict[str, Any]) -> bool:
    """Marked complete, with its array there: two builds at once once left a copy marked complete without it."""
    return bool(attrs.get("complete")) and (path / "values" / "zarr.json").exists()


@contextmanager
def _one_build_at_a_time(folder: Path) -> Iterator[None]:
    """Waits for any other build of a copy (in any process) to finish, and holds them off until this one has."""
    folder.mkdir(parents=True, exist_ok=True)
    handle = os.open(folder, os.O_RDONLY)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        os.close(handle)  # releases the flock


def _present(data_dir: Path, year: int) -> list[Variable]:
    group = zarr.open_group(DAILY.path(data_dir, year), mode="r")
    keys = set(group.array_keys())
    return [v for name, v in DAILY_VARIABLES.items() if name in keys]


def build(data_dir: Path, year: int, progress: Callable[[int, int], None] | None = None) -> None:
    """(Re)builds a year's copy from its daily store, which must have no stale variables (`rebuild --stale` first).
    Built beside its path and renamed into place once whole, one build at a time."""
    with _one_build_at_a_time(PAST.path(data_dir, year).parent):
        _build(data_dir, year, progress)


def _build(data_dir: Path, year: int, progress: Callable[[int, int], None] | None) -> None:
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
    # Swapped in by renames, the old copy deleted after, so the path is empty only between two renames
    old = path.with_name(path.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if path.exists():
        path.rename(old)
    building.rename(path)
    if old.exists():
        shutil.rmtree(old)


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
            group = _open_copy(PAST.path(self.data_dir, year))
            found = None
            if group is not None:
                attrs: dict[str, Any] = dict(group.attrs)
                if _complete(PAST.path(self.data_dir, year), attrs):
                    w = attrs["window"]
                    window = Window(j0=w["j0"], j1=w["j1"], i0=w["i0"], i1=w["i1"])
                    try:
                        found = _Year(values=group["values"], names=list(attrs["names"]), window=window)
                    except KeyError:  # swapped out since the check: read as missing, like the group
                        found = None
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
