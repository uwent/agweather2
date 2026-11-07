"""Each year's daily minimum and maximum temperature laid out for reading a season over the map (Phase 6 B; §3's
custom degree-day map, < 2 s).

The daily store is chunked a day at a time (one map per chunk), right for one day's map: a season of one variable is a
chunk read per day, ~250 of ~1 ms each over Wisconsin and ~12 times as many over the launch box. This copy holds the
same packed values in chunks of 32 days × 256 × 256 cells, so a season is ~8 chunk reads per variable and 256-cell
block (0.33 → 0.05 s over Wisconsin, measured 2026-11-06). One day reads slower from it (7.8 ms against 1.2), so day
maps and short ranges keep reading the daily store (`MIN_DAYS`).

It's a cache, never the only copy. `cumulative.update_days`, which every archive rollup goes through, copies the
days it rolls up (its callers hold the write lock, as for every archive write), and `manage.py timecopy` fills the
years rolled up before the copy existed. A reader takes a day from the copy only if the copy wrote it after the daily
store last did (each store stamps every day it writes); any other day comes from the daily store, and so does a
variable the daily store holds as stale (D29), so a copy behind the daily store is slower, never wrong. The copy's
arrays keep the version they were made with: a rebuild rewrites the daily days, which stamps them newer than the
copy's and so recopies them, so the stamps, not the version, say what's current."""

from collections.abc import Iterable
from datetime import date
from pathlib import Path

import numpy as np

from agdata.catalog import DAILY_VARIABLES, Variable
from agdata.grid import Window
from agdata.store import DAILY, GridStore, StoreLayout, steps_in_year

COPY = StoreLayout(kind="daily-by-time", step="day")
NAMES = ("air_temperature_min", "air_temperature_max")
CHUNKS = (32, 256, 256)
MIN_DAYS = 8  # fewer days read faster from the daily store (a chunk a day, against 32 days decoded per chunk)


def variables() -> list[Variable]:
    return [DAILY_VARIABLES[name] for name in NAMES]


def update(data_dir: Path, first: date, last: date) -> None:
    """Copies days first..last of the daily store into each year's copy (made if missing), over the daily store's
    whole window, so a day stamped in the copy is current everywhere. The caller holds the write lock."""
    for year in range(first.year, last.year + 1):
        daily = _open(data_dir, DAILY, year)
        if daily is None:
            continue
        a, b = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        if a > b:
            continue
        copy = _open(data_dir, COPY, year) or GridStore.create(
            data_dir, COPY, year, daily.window, variables(), chunks=CHUNKS
        )
        t0, t1 = daily.index_of(a), daily.index_of(b) + 1
        step = CHUNKS[0]
        for c0 in range(t0, t1, step):  # a chunk's days at a time, aligned to the copy's chunks
            c1 = min(t1, (c0 // step + 1) * step)
            values = {name: daily.read_steps(name, c0, c1) for name in NAMES}
            copy.write(daily.time_of(c0).date(), values, source="derived")


def behind(data_dir: Path, year: int) -> int:
    """How many of a year's days the daily store has written since the copy last copied them (all of them written
    so far, without a copy); 0 if the year has no daily store."""
    daily = _open(data_dir, DAILY, year)
    if daily is None:
        return 0
    copy = _open(data_dir, COPY, year)
    out = 0
    for name in NAMES:
        theirs = daily.read_meta(f"{name}.written")
        ours = copy.read_meta(f"{name}.written") if copy is not None else np.full(theirs.shape, np.nan)
        out = max(out, int(np.sum(np.isfinite(theirs) & ~(ours >= theirs))))
    return out


def fill(data_dir: Path, year: int) -> int:
    """Copies the year's days the copy is behind on, in runs of consecutive days; returns how many. The caller
    holds the write lock."""
    daily = _open(data_dir, DAILY, year)
    if daily is None:
        return 0
    copy = _open(data_dir, COPY, year)
    stale = np.zeros(steps_in_year(year, "day"), dtype=bool)
    for name in NAMES:
        theirs = daily.read_meta(f"{name}.written")
        ours = copy.read_meta(f"{name}.written") if copy is not None else np.full(theirs.shape, np.nan)
        stale |= np.isfinite(theirs) & ~(ours >= theirs)
    for k0, k1 in runs_of(stale):
        update(data_dir, daily.time_of(k0).date(), daily.time_of(k1 - 1).date())
    return int(stale.sum())


def read(
    copy: GridStore, daily: GridStore, name: str, t0: int, t1: int, window: Window
) -> tuple[np.ndarray, np.ndarray]:
    """Days t0..t1-1 of `name` over the window from the copy, and which of them are current there (False: the
    daily store wrote them after the copy did, or the copy never had them; read those from the daily store)."""
    ours = copy.read_meta(f"{name}.written")[t0:t1]
    theirs = daily.read_meta(f"{name}.written")[t0:t1]
    current = np.isnan(theirs) | (ours >= theirs)  # a day the daily store never wrote is missing in both
    return copy.read_steps(name, t0, t1, window, dtype=np.float32), current


def runs_of(mask: np.ndarray) -> Iterable[tuple[int, int]]:
    """(start, stop) of each run of True."""
    k, n = 0, len(mask)
    while k < n:
        if not mask[k]:
            k += 1
            continue
        start = k
        while k < n and mask[k]:
            k += 1
        yield start, k


def _open(data_dir: Path, layout: StoreLayout, year: int) -> GridStore | None:
    wanted = variables() if layout is COPY else [DAILY_VARIABLES[name] for name in NAMES]
    try:
        return GridStore.open(data_dir, layout, year, wanted, add_missing=layout is DAILY)
    except FileNotFoundError:
        return None
