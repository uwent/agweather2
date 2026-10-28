"""Daily rollups: the catalog's daily statistics over each cell's local calendar day (PLAN.md §5.4, D25).

A local day is the hours ending after local midnight up to the next local midnight (23, 24 or 25 of them).
Days stay raw: min, max and mean need `DAILY_MIN_HOURS` of the day's hours and sums need every hour, or the day
is NaN; estimates across gaps belong to the running totals (`agdata.cumulative`). The daily store for a year
holds that year's local days, so local Dec 31 reads the next year's first UTC hours. The window is rolled up
in bands of rows so a large box fits in memory.
"""

import warnings
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from agdata.catalog import DAILY_MIN_HOURS, DAILY_STATISTICS, DAILY_VARIABLES, VARIABLES, DailyStatistic
from agdata.gaps import estimate_et0_hourly_mm
from agdata.grid import NDFD, Window
from agdata.store import DAILY, HOURLY, GridStore
from agdata.timezones import day_bounds, from_8pm_bounds, window_timezones
from agmodels import features
from agmodels.weather import relative_humidity_percent

BAND_ROWS = 128
MAX_DAYS_PER_PASS = 31
HOUR = timedelta(hours=1)
ESTIMATE_CONTEXT = timedelta(hours=30)  # hours read around a pass for the ET0 estimate's cloudiness


def open_or_create_daily(data_dir: Path, year: int, window: Window) -> GridStore:
    """The year's daily store, created with each cell's time zone on first use."""
    try:
        store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
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
        # Per day, the zones grouped by their (first, last) hour ends, for calendar days and days from 8 pm
        groups = _group_zones(days, zones, day_bounds)
        evenings = _group_zones(days, zones, from_8pm_bounds)
        span_start = min(b[0] for g in groups for b in g)
        span_stop = max(b[1] for g in groups for b in g) + HOUR
        feature_start = min(span_start, *(b[0] for g in evenings for b in g))

        for band in _bands(window):
            y0, _ = window.local(band.j0, band.i0)
            band_zones = zone_index[y0 : y0 + band.shape[0]]
            day_zones = _DayZones(groups, band_zones, zones)
            out: dict[str, np.ndarray] = {}
            for name in VARIABLES:
                stats = [s for s in DAILY_STATISTICS.values() if s.hourly == name]
                if stats:
                    hours = hourly.read(name, span_start, span_stop, band)
                    for s in stats:
                        out[s.variable.name] = day_zones.each_day(hours, span_start, s)
            out["et0_sum_estimate"] = np.full_like(out["et0_sum"], np.nan)
            short = np.flatnonzero(np.isnan(out["et0_sum"]).any(axis=(1, 2)))
            if short.size:
                # Only over the days missing some ET0, with context: the estimate's arrays are many times the hours'
                d0, d1 = int(short[0]), int(short[-1]) + 1
                some = _DayZones(groups[d0:d1], day_zones.zone_index, zones)
                start = min(b[0] for g in some.groups for b in g) - ESTIMATE_CONTEXT
                stop = max(b[1] for g in some.groups for b in g) + HOUR + ESTIMATE_CONTEXT
                et0 = _estimated_et0_hours(hourly, start, stop, band)
                estimate = some.each_day(et0, start, DAILY_STATISTICS["et0_sum"])
                out["et0_sum_estimate"][d0:d1] = np.where(np.isnan(out["et0_sum"][d0:d1]), estimate, np.nan)
            temperature = hourly.read("air_temperature", feature_start, span_stop, band)
            rh = relative_humidity_percent(temperature, hourly.read("dew_point", feature_start, span_stop, band))
            hours = {"temperature": temperature, "rh": rh}
            out |= day_zones.each_window(
                hours, feature_start, lambda h, _: features.calendar_features(h["temperature"], h["rh"])
            )
            out |= _DayZones(evenings, band_zones, zones).each_window(
                hours,
                feature_start,
                lambda h, local_hour: features.from_8pm_features(
                    h["temperature"], h["rh"], features.is_night(local_hour)
                ),
            )
            store.write(days[0], out, source="derived", window=band)
        written += len(days)
    return written


Bounds = Callable[[date, str], tuple[datetime, datetime]]


def _group_zones(
    days: list[date], zones: list[str], bounds: Bounds
) -> list[dict[tuple[datetime, datetime], list[int]]]:
    groups = []
    for day in days:
        by_bounds: dict[tuple[datetime, datetime], list[int]] = {}
        for k, zone in enumerate(zones):
            by_bounds.setdefault(bounds(day, zone), []).append(k)
        groups.append(by_bounds)
    return groups


class _DayZones:
    """A pass's days over a band: each cell's day follows its zone, and zones sharing bounds go together."""

    def __init__(
        self, groups: list[dict[tuple[datetime, datetime], list[int]]], zone_index: np.ndarray, zones: list[str]
    ):
        self.groups = groups
        self.zone_index = zone_index
        self.zones = zones

    def each_window(
        self,
        hours: dict[str, np.ndarray],
        first_hour: datetime,
        reduce: Callable[[dict[str, np.ndarray], np.ndarray], dict[str, np.ndarray]],
    ) -> dict[str, np.ndarray]:
        """`reduce(window's hours, their local clock hours)` for each day's window; hours from first_hour on."""
        result: dict[str, np.ndarray] = {}
        for d, by_bounds in enumerate(self.groups):
            for (begin, end), ids in by_bounds.items():
                mask = np.isin(self.zone_index, ids)
                if not mask.any():
                    continue
                i0, i1 = (begin - first_hour) // HOUR, (end - first_hour) // HOUR + 1
                tz = ZoneInfo(self.zones[ids[0]])  # zones with the same bounds share the day's offsets
                local_hour = np.array([(begin + n * HOUR).astimezone(tz).hour for n in range(i1 - i0)])
                for name, value in reduce({k: v[i0:i1] for k, v in hours.items()}, local_hour).items():
                    target = result.setdefault(
                        name, np.full((len(self.groups), *self.zone_index.shape), np.nan, dtype=np.float32)
                    )
                    target[d][mask] = value[mask]
        return result

    def each_day(self, hours: np.ndarray, first_hour: datetime, s: DailyStatistic) -> np.ndarray:
        """The statistic for each day, from hours ending at first_hour, first_hour + 1 h, …"""
        result = np.full((len(self.groups), *self.zone_index.shape), np.nan, dtype=np.float32)
        for d, by_bounds in enumerate(self.groups):
            for (begin, end), ids in by_bounds.items():
                mask = np.isin(self.zone_index, ids)
                if mask.any():
                    segment = hours[(begin - first_hour) // HOUR : (end - first_hour) // HOUR + 1]
                    result[d][mask] = daily_statistic(segment, s)[mask]
        return result


def _estimated_et0_hours(hourly: "_HourlyReader", start: datetime, stop: datetime, band: Window) -> np.ndarray:
    names = ("et0", "air_temperature", "dew_point", "wind_speed", "surface_pressure", "shortwave_radiation")
    inputs = [hourly.read(name, start, stop, band) for name in names]
    first = np.datetime64(start.replace(tzinfo=None), "s")
    hour_end = first + np.arange((stop - start) // HOUR) * np.timedelta64(3600, "s")
    lat, lon = NDFD.window_latlon(band)
    return estimate_et0_hourly_mm(hour_end, lat, lon, *inputs)


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
