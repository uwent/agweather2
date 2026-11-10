"""The Dynamic model's chill portions on the grid, a running total from October 1 (D76; `agmodels.chill`).

Chill portions can't be a daily feature: the model's intermediate carries from hour to hour across days, so a day's
portions depend on the season before it. They're kept beside the other running totals (`agdata.cumulative`'s
store, by calendar year), as three variables a day: `chill_portions` (since the season's October 1), `chill_state`
(the intermediate at the day's end, which the next day starts from) and `chill_missing_hours` (hours without a
temperature since October 1, during which the intermediate was held and nothing accrued). A season runs October 1
to September 30; January 1 carries on from December 31, from the year before's store.

`update` recomputes from a changed day forward, as far as later days have been written (each depends on the one
before) but not past the season's end, and only through the last day the daily store has rolled up (a day still
coming in is written when it's complete). `agdata.cumulative.update_days` calls it after each rollup, and the forecast
run continues the archive's (`agdata.forecast`). A season reaching back before the archive starts from nothing on
October 1, so its missing hours say how much of the season it lacks.
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import CUMULATIVE_VARIABLES
from agdata.daily import _bands, _HourlyReader
from agdata.grid import Window
from agdata.store import CUMULATIVE, DAILY, GridStore
from agdata.timezones import GRID_ZONE, day_bounds
from agmodels import chill

NAMES = ("chill_portions", "chill_state", "chill_missing_hours")
SEASON_MONTH = 10  # October 1
DAYS_PER_READ = 31  # hours read a month at a time per band


def season_start(day: date) -> date:
    """The October 1 that `day`'s chill season began on."""
    year = day.year if day.month >= SEASON_MONTH else day.year - 1
    return date(year, SEASON_MONTH, 1)


def season_end(day: date) -> date:
    return date(season_start(day).year + 1, SEASON_MONTH, 1) - timedelta(days=1)


def update(
    data_dir: Path, window: Window, first: date, last: date, base_dir: Path | None = None
) -> tuple[date, date] | None:
    """Recomputes chill portions from `first` through `last` (or the last day `data_dir`'s daily store has rolled
    up, if that's earlier), and on through the days already written after them to their season's end; returns the
    days written (None: none). The day before `first` is read from `base_dir` (default `data_dir`); where it isn't
    there, the season is recomputed from October 1 (with `base_dir` given, a forecast run continuing the archive,
    nothing is written). A range crossing October 1 starts the new season afresh."""
    rolled = _last_rolled_up(data_dir, season_end(last))
    if rolled is None or rolled < first:
        return None
    written: tuple[date, date] | None = None
    day = first
    while day <= min(last, rolled):
        found = _update_season(data_dir, window, day, min(last, season_end(day)), rolled, base_dir)
        if found is not None:
            written = (found[0] if written is None else written[0], found[1])
        elif base_dir is not None:
            return written  # a forecast run whose archive has no chill to carry on
        day = season_end(day) + timedelta(days=1)
    return written


def _update_season(
    data_dir: Path, window: Window, first: date, last: date, rolled: date, base_dir: Path | None
) -> tuple[date, date] | None:
    """`update` within one season (first..last in it)."""
    end = min(max(last, _last_written(data_dir, first)), rolled)
    start = first
    base = None if first == season_start(first) else _read_day(base_dir or data_dir, first - timedelta(days=1), window)
    if first != season_start(first) and base is None:
        if base_dir is not None:
            return None
        start = season_start(first)  # recomputed from October 1
    data_from = _first_rolled_up(data_dir, start, end)
    if data_from is None:
        return None
    # Days before the season's first rolled-up day have no hours: nothing accrues, every hour is missing, and
    # nothing is written for them (a reader finds no data there, which is what there is)
    skipped_hours = 24.0 * (data_from - start).days if base is None else 0.0
    start = max(start, data_from) if base is None else start
    hourly = _HourlyReader(data_dir)
    for band in _bands(window):
        state, total, missing = _start_values(base, band, window)
        missing = missing + skipped_hours
        days: list[np.ndarray] = []
        day = start
        while day <= end:
            n = min(DAYS_PER_READ, (end - day).days + 1)
            begin = day_bounds(day, GRID_ZONE)[0]
            hours = hourly.read("air_temperature", begin, begin + timedelta(hours=24 * n), band)
            for k in range(n):
                portions, state, gaps = chill.dynamic(hours[24 * k : 24 * (k + 1)], state)
                total = total + portions.sum(axis=0)
                missing = missing + gaps
                days.append(np.stack([total, state, missing]))
            day += timedelta(days=n)
        _write(data_dir, window, band, start, np.stack(days))  # (days, 3, y, x)
    return start, end


def rebuild(data_dir: Path, window: Window, years: list[int]) -> None:
    """Recomputes every season that reaches into `years`, each from its October 1."""
    starts = sorted({date(y + k, SEASON_MONTH, 1) for y in years for k in (-1, 0)})
    for start in starts:
        update(data_dir, window, start, season_end(start))


def _start_values(base: dict[str, np.ndarray] | None, band: Window, window: Window):
    if base is None:
        zeros = np.zeros(band.shape)
        return zeros, zeros.copy(), zeros.copy()
    rows = slice(band.j0 - window.j0, band.j1 - window.j0)
    total, state, missing = (np.nan_to_num(base[name][rows]) for name in NAMES)
    return state, total, missing


def _write(data_dir: Path, window: Window, band: Window, start: date, stacked: np.ndarray) -> None:
    from agdata.cumulative import open_or_create_cumulative

    day = start
    k = 0
    while k < stacked.shape[0]:
        year_end = date(day.year, 12, 31)
        n = min(stacked.shape[0] - k, (year_end - day).days + 1)
        store = open_or_create_cumulative(data_dir, day.year, window)
        block = stacked[k : k + n]
        store.write(day, {name: block[:, m] for m, name in enumerate(NAMES)}, source="derived", window=band)
        k += n
        day += timedelta(days=n)


def _read_day(data_dir: Path, day: date, window: Window) -> dict[str, np.ndarray] | None:
    """The chill variables on `day` over the window, or None if that day isn't written."""
    try:
        store = GridStore.open(data_dir, CUMULATIVE, day.year, CUMULATIVE_VARIABLES.values(), add_missing=True)
    except FileNotFoundError:
        return None
    k = store.index_of(day)
    if not store.has_data("chill_state", k, k + 1).all():
        return None
    return {name: store.read_steps(name, k, k + 1, window)[0] for name in NAMES}


def _last_written(data_dir: Path, first: date) -> date:
    """The last day of `first`'s season with chill written (`first` if none is after it)."""
    found = first
    for year in range(first.year, season_end(first).year + 1):
        try:
            store = GridStore.open(data_dir, CUMULATIVE, year, CUMULATIVE_VARIABLES.values(), add_missing=True)
        except FileNotFoundError:
            continue
        days = np.flatnonzero(store.has_data("chill_portions"))
        if days.size:
            found = max(found, date(year, 1, 1) + timedelta(days=int(days[-1])))
    return min(found, season_end(first))


def _first_rolled_up(data_dir: Path, first: date, last: date) -> date | None:
    """The first day in first..last that the daily store has rolled up."""
    for year in range(first.year, last.year + 1):
        if not _has_daily(data_dir, year):
            continue
        store = GridStore.open(data_dir, DAILY, year, [], add_missing=False)
        days = np.flatnonzero(store.read_meta("air_temperature_min.source") > 0)
        lo = (first - date(year, 1, 1)).days if year == first.year else 0
        hi = (last - date(year, 1, 1)).days if year == last.year else 366
        days = days[(days >= lo) & (days <= hi)]
        if days.size:
            return date(year, 1, 1) + timedelta(days=int(days[0]))
    return None


def _has_daily(data_dir: Path, year: int) -> bool:
    return DAILY.path(data_dir, year).exists()


def _last_rolled_up(data_dir: Path, last: date) -> date | None:
    """The last day on or before `last` that the daily store has rolled up (its minimum temperature written)."""
    for year in range(last.year, last.year - 2, -1):
        if not _has_daily(data_dir, year):
            continue
        store = GridStore.open(data_dir, DAILY, year, [], add_missing=False)
        days = np.flatnonzero(store.read_meta("air_temperature_min.source") > 0)
        cap = (last - date(year, 1, 1)).days if year == last.year else 366
        days = days[days <= cap]
        if days.size:
            return date(year, 1, 1) + timedelta(days=int(days[-1]))
    return None
