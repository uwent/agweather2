"""Daily rollups: the catalog's daily statistics over each cell's local calendar day (PLAN.md §5.4, D25).

A local day is the hours ending after local midnight up to the next local midnight (23, 24 or 25 of them).
Days stay raw: min, max and mean need `DAILY_MIN_HOURS` of the day's hours and sums need every hour, or the day
is NaN; estimates across gaps belong to the running totals (`agdata.cumulative`). The daily store for a year
holds that year's local days, so local Dec 31 reads the next year's first UTC hours. The window is rolled up
in bands of rows so a large box fits in memory.
"""

import warnings
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from agdata.catalog import DAILY_MIN_HOURS, DAILY_STATISTICS, DAILY_VARIABLES, VARIABLES, DailyStatistic
from agdata.grid import Window
from agdata.store import DAILY, HOURLY, GridStore
from agdata.timezones import day_bounds, window_timezones

BAND_ROWS = 128
MAX_DAYS_PER_PASS = 31
HOUR = timedelta(hours=1)


def open_or_create_daily(data_dir: Path, year: int, window: Window) -> GridStore:
    """The year's daily store, created with each cell's time zone on first use."""
    try:
        store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values())
    except FileNotFoundError:
        store = GridStore.create(data_dir, DAILY, year, window, DAILY_VARIABLES.values())
        zones, index = window_timezones(window)
        store.group.attrs["timezones"] = zones
        array = store.group.create_array("_meta/timezone", shape=index.shape, dtype="uint8", fill_value=0)
        array[:] = index
    if store.window != window:
        raise ValueError(f"{store.path} covers {store.window}, not {window}; widening the box needs a rebuild")
    return store


def cell_timezones(store: GridStore) -> tuple[list[str], np.ndarray]:
    """A daily store's zone names and each cell's index into them, (y, x)."""
    zones: Any = store.group.attrs["timezones"]
    return [str(z) for z in zones], store.read_meta("timezone")


def rollup_days(data_dir: Path, window: Window, first: date, last: date) -> int:
    """Rolls up local days first..last (inclusive) from the hourly store into the daily store; returns the
    number of days written. Hours not in the hourly store count as missing."""
    hourly = _HourlyReader(data_dir)
    written = 0
    for days in _passes(first, last):
        store = open_or_create_daily(data_dir, days[0].year, window)
        zones, zone_index = cell_timezones(store)
        # Per day, the zones grouped by their (first, last) hour ends
        groups: list[dict[tuple[datetime, datetime], list[int]]] = []
        for day in days:
            by_bounds: dict[tuple[datetime, datetime], list[int]] = {}
            for k, zone in enumerate(zones):
                by_bounds.setdefault(day_bounds(day, zone), []).append(k)
            groups.append(by_bounds)
        span_start = min(b[0] for g in groups for b in g)
        span_stop = max(b[1] for g in groups for b in g) + HOUR

        for band in _bands(window):
            y0, _ = window.local(band.j0, band.i0)
            band_zones = zone_index[y0 : y0 + band.shape[0]]
            out: dict[str, np.ndarray] = {}
            for name in VARIABLES:
                stats = [s for s in DAILY_STATISTICS.values() if s.hourly == name]
                if not stats:
                    continue
                hours = hourly.read(name, span_start, span_stop, band)
                for s in stats:
                    out[s.variable.name] = np.full((len(days), *band.shape), np.nan, dtype=np.float32)
                for d, by_bounds in enumerate(groups):
                    for (begin, end), ids in by_bounds.items():
                        mask = np.isin(band_zones, ids)
                        if not mask.any():
                            continue
                        segment = hours[(begin - span_start) // HOUR : (end - span_start) // HOUR + 1]
                        for s in stats:
                            target = out[s.variable.name][d]
                            target[mask] = daily_statistic(segment, s)[mask]
            store.write(days[0], out, source="derived", window=band)
        written += len(days)
    return written


def daily_statistic(hours: np.ndarray, s: DailyStatistic) -> np.ndarray:
    """One day's statistic from its hours (time on axis 0), NaN where the day is too incomplete (D25)."""
    present = np.isfinite(hours).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells
        if s.stat == "sum":
            return np.where(present == hours.shape[0], np.nansum(hours, axis=0) * s.factor, np.nan)
        value = {"min": np.nanmin, "max": np.nanmax, "mean": np.nanmean}[s.stat](hours, axis=0)
    return np.where(present >= DAILY_MIN_HOURS, value, np.nan)


class _HourlyReader:
    """Reads hours across the yearly hourly stores; hours in a missing store are NaN."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.stores: dict[int, GridStore | None] = {}

    def read(self, name: str, start: datetime, stop: datetime, window: Window) -> np.ndarray:
        """Hours ending at start, start + 1 h, … before stop, (hours, y, x) as float32."""
        out = np.full(((stop - start) // HOUR, *window.shape), np.nan, dtype=np.float32)
        for year in range(start.year, (stop - HOUR).year + 1):
            store = self._store(year)
            if store is None:
                continue
            begin = max(start, datetime(year, 1, 1, tzinfo=UTC))
            end = min(stop, datetime(year + 1, 1, 1, tzinfo=UTC))
            t0 = store.index_of(begin)
            out[(begin - start) // HOUR : (end - start) // HOUR] = store.read_steps(
                name, t0, t0 + (end - begin) // HOUR, window
            )
        return out

    def _store(self, year: int) -> GridStore | None:
        if year not in self.stores:
            try:
                self.stores[year] = GridStore.open(self.data_dir, HOURLY, year, VARIABLES.values())
            except FileNotFoundError:
                self.stores[year] = None
        return self.stores[year]


def _passes(first: date, last: date) -> Iterator[list[date]]:
    """Days first..last in runs within one year and at most MAX_DAYS_PER_PASS long."""
    day = first
    while day <= last:
        run = []
        while day <= last and len(run) < MAX_DAYS_PER_PASS and (not run or day.year == run[0].year):
            run.append(day)
            day += timedelta(days=1)
        yield run


def _bands(window: Window) -> Iterator[Window]:
    for j in range(window.j0, window.j1, BAND_ROWS):
        yield Window(j, min(j + BAND_ROWS, window.j1), window.i0, window.i1)
