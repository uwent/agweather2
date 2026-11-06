"""Daily rollups: the catalog's daily statistics over each grid day (PLAN.md §5.4, D25, D74).

A grid day is midnight to midnight CST (`timezones.GRID_ZONE`, all year): the hours ending 01:00 through 24:00 CST,
06:00–06:00 UTC, the same for every cell. A store records its zones (`timezones` and `_meta/timezone`); one written
before D74 holds each cell's local zone, and `rebuild --stale` moves it to the grid's (`on_grid_days`).
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
import zarr

from agdata.catalog import DAILY_MIN_HOURS, DAILY_STATISTICS, DAILY_VARIABLES, VARIABLES, DailyStatistic
from agdata.gaps import estimate_et0_hourly_mm
from agdata.grid import NDFD, Window
from agdata.store import DAILY, HOURLY, GridStore
from agdata.timezones import GRID_ZONE, day_bounds, evening_bounds, overnight_bounds
from agmodels import features
from agmodels.weather import relative_humidity_percent

BAND_ROWS = 128
MAX_DAYS_PER_PASS = 31
HOUR = timedelta(hours=1)
ESTIMATE_CONTEXT = timedelta(hours=30)  # hours read around a pass for the ET0 estimate's cloudiness


def open_or_create_daily(data_dir: Path, year: int, window: Window) -> GridStore:
    """The year's daily store, created on grid days (CST) on first use."""
    try:
        store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
    except FileNotFoundError:

        def with_zones(group) -> None:
            group.attrs["timezones"] = [GRID_ZONE]
            group.create_array("_meta/timezone", shape=window.shape, dtype="uint8", fill_value=0)

        store = GridStore.create(data_dir, DAILY, year, window, DAILY_VARIABLES.values(), finish=with_zones)
    if store.window != window:
        raise ValueError(f"{store.path} covers {store.window}, not {window}; widening the box needs a rebuild")
    return store


def cell_timezones(store: GridStore) -> tuple[list[str], np.ndarray]:
    """A daily store's zone names and each cell's index into them, (y, x)."""
    zones: Any = store.group.attrs["timezones"]
    return [str(z) for z in zones], store.read_meta("timezone")


def on_grid_days(store: GridStore) -> bool:
    """Whether a daily store's days are grid days (D74), not each cell's local ones."""
    return cell_timezones(store)[0] == [GRID_ZONE]


def year_on_grid_days(data_dir: Path, year: int) -> bool:
    """`on_grid_days` for a year's store, read-only (for the health check)."""
    zones: Any = zarr.open_group(DAILY.path(data_dir, year), mode="r").attrs.get("timezones", [])
    return [str(z) for z in zones] == [GRID_ZONE]


def move_to_grid_days(store: GridStore) -> None:
    """Records a store written on local days as on grid days, every variable stale until its days are rolled up
    again (`rebuild`): its values are still the local days'."""
    store.group.attrs["timezones"] = [GRID_ZONE]
    store._array("_meta/timezone")[:] = 0
    store.stale |= set(store.variables)


def rollup_days(data_dir: Path, window: Window, first: date, last: date) -> int:
    """Rolls up grid days first..last (inclusive) from the hourly store into the daily store; returns the
    number of days written. Hours not in the hourly store count as missing. A day's variable is marked `derived`
    only if some cell has a value (so a day not yet observed, such as today with too few hours, reads as not
    rolled up, and the running totals stop before it)."""
    hourly = _HourlyReader(data_dir)
    written = 0
    for days in _passes(first, last):
        store = open_or_create_daily(data_dir, days[0].year, window)
        has_value: dict[str, np.ndarray] = {}
        for band, out in _rolled(hourly, window, days):
            store.write(days[0], out, source=None, window=band)
            for name, values in out.items():
                some = np.isfinite(values).any(axis=(1, 2))
                has_value[name] = some | has_value.get(name, np.zeros(len(days), dtype=bool))
        for name, some in has_value.items():
            store.set_sources(name, days[0], ["derived" if x else None for x in some])
        written += len(days)
    return written


def days_from_hours(data_dir: Path, window: Window, first: date, last: date) -> dict[str, np.ndarray]:
    """Every daily variable for grid days first..last over `window`, rolled up from `data_dir`'s hourly stores as
    `rollup_days` does, without writing anything: a read of a stale variable (D29) computes it this way."""
    hourly = _HourlyReader(data_dir)
    out: dict[str, np.ndarray] = {}
    offset = 0
    for days in _passes(first, last):
        for band, values in _rolled(hourly, window, days):
            y0 = band.j0 - window.j0
            for name, v in values.items():
                target = out.setdefault(name, np.full(((last - first).days + 1, *window.shape), np.nan, np.float32))
                target[offset : offset + len(days), y0 : y0 + band.shape[0]] = v
        offset += len(days)
    return out


Span = tuple[datetime, datetime]  # a window's first and last readings (hour ends, UTC)


def _rolled(
    hourly: "_HourlyReader", window: Window, days: list[date]
) -> Iterator[tuple[Window, dict[str, np.ndarray]]]:
    """Each band of the window and its days' daily variables, (days, rows, columns). Every cell shares a day's
    windows (grid days, CST): the calendar day, the day from 6 pm and noon to noon (`agdata.timezones`)."""
    calendar = [day_bounds(day, GRID_ZONE) for day in days]
    evenings = [evening_bounds(day, GRID_ZONE) for day in days]
    overnights = [overnight_bounds(day, GRID_ZONE) for day in days]
    span_start, span_stop = calendar[0][0], calendar[-1][1] + HOUR
    feature_start = min(span_start, evenings[0][0], overnights[0][0])
    for band in _bands(window):
        out: dict[str, np.ndarray] = {}
        for name in VARIABLES:
            stats = [s for s in DAILY_STATISTICS.values() if s.hourly == name]
            if stats:
                hours = hourly.read(name, span_start, span_stop, band)
                for s in stats:
                    out[s.variable.name] = _each_day(hours, span_start, calendar, s)
        out["et0_sum_estimate"] = np.full_like(out["et0_sum"], np.nan)
        short = np.flatnonzero(np.isnan(out["et0_sum"]).any(axis=(1, 2)))
        if short.size:
            # Only over the days missing some ET0, with context: the estimate's arrays are many times the hours'
            d0, d1 = int(short[0]), int(short[-1]) + 1
            start = calendar[d0][0] - ESTIMATE_CONTEXT
            stop = calendar[d1 - 1][1] + HOUR + ESTIMATE_CONTEXT
            et0 = _estimated_et0_hours(hourly, start, stop, band)
            estimate = _each_day(et0, start, calendar[d0:d1], DAILY_STATISTICS["et0_sum"])
            out["et0_sum_estimate"][d0:d1] = np.where(np.isnan(out["et0_sum"][d0:d1]), estimate, np.nan)
        temperature = hourly.read("air_temperature", feature_start, span_stop, band)
        dew_point = hourly.read("dew_point", feature_start, span_stop, band)
        hours = {
            "temperature": temperature,
            "dew_point": dew_point,
            "rh": relative_humidity_percent(temperature, dew_point),
            "soil_4cm": hourly.read("soil_temperature_4cm", feature_start, span_stop, band),
            "soil_10cm": hourly.read("soil_temperature_10cm", feature_start, span_stop, band),
            "soil_30cm": hourly.read("soil_temperature_30cm", feature_start, span_stop, band),
        }
        out |= _each_window(
            hours,
            feature_start,
            calendar,
            lambda h, _: (
                features.calendar_features(h["temperature"], h["rh"], h["dew_point"])
                | features.soil_features(h["soil_4cm"], h["soil_10cm"], h["soil_30cm"])
            ),
        )
        out |= _each_window(
            hours,
            feature_start,
            evenings,
            lambda h, local_hour: features.evening_features(h["temperature"], h["rh"], local_hour),
        )
        out |= _each_window(
            hours, feature_start, overnights, lambda h, _: features.overnight_features(h["temperature"])
        )
        yield band, out


def _each_window(
    hours: dict[str, np.ndarray],
    first_hour: datetime,
    spans: list[Span],
    reduce: Callable[[dict[str, np.ndarray], np.ndarray], dict[str, np.ndarray]],
) -> dict[str, np.ndarray]:
    """`reduce(a window's hours, their clock hours on the grid's days)` for each day's window, stacked by day; hours
    from first_hour on."""
    found: dict[str, list[np.ndarray]] = {}
    clock = ZoneInfo(GRID_ZONE)
    for begin, end in spans:
        i0, i1 = (begin - first_hour) // HOUR, (end - first_hour) // HOUR + 1
        local_hour = np.array([(begin + n * HOUR).astimezone(clock).hour for n in range(i1 - i0)])
        for name, value in reduce({k: v[i0:i1] for k, v in hours.items()}, local_hour).items():
            found.setdefault(name, []).append(np.asarray(value, dtype=np.float32))
    return {name: np.stack(values) for name, values in found.items()}


def _each_day(hours: np.ndarray, first_hour: datetime, spans: list[Span], s: DailyStatistic) -> np.ndarray:
    """The statistic for each day's span, from hours ending at first_hour, first_hour + 1 h, …"""
    return np.stack(
        [
            daily_statistic(hours[(begin - first_hour) // HOUR : (end - first_hour) // HOUR + 1], s).astype(np.float32)
            for begin, end in spans
        ]
    )


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
                self.stores[year] = GridStore.open(self.data_dir, HOURLY, year, VARIABLES.values(), add_missing=True)
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
        yield Window(j0=j, j1=min(j + BAND_ROWS, window.j1), i0=window.i0, i1=window.i1)
