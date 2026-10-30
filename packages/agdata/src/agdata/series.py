"""One series from the archive and the forecast, for a point or a map day (PLAN.md Phase 4 C).

Each hour is observed (the archive, through its last observed hour) or forecast (the current run after it). Each
day is observed (every hour observed), partial (today: some of each) or forecast; a day with nothing is missing.
The days come from the stores rolled up the same way: observed days from the archive's daily store, today and
later from the run's (`agdata.forecast`), whose stitched hours make today's values. Running totals likewise: the
archive's through yesterday, the run's from today (they continue the archive's).

The forecast is used only while its run is fresh (`MAX_RUN_AGE`); otherwise the series ends with the archive and
says why. Kinds are per point, as each cell's day follows its own time zone.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata import forecast
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.daily import cell_timezones
from agdata.grid import Window
from agdata.point import daily_at_point
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore, StoreLayout
from agdata.timezones import day_bounds

HOUR = timedelta(hours=1)
MAX_RUN_AGE = timedelta(hours=12)  # past this a run's forecast isn't used (D43; the job runs every 6 hours)
OBSERVED, PARTIAL, FORECAST = "observed", "partial", "forecast"


@dataclass(kw_only=True)
class Forecast:
    """The run a series takes its forecast from, or why there's none."""

    path: Path | None
    cycle: datetime | None = None
    last_observed: datetime | None = None
    last_hour: datetime | None = None
    reason: str | None = None  # when path is None: "none", "stale"


def current_forecast(data_dir: Path, now: datetime | None = None) -> Forecast:
    """The published run if it's fresh (its cycle within MAX_RUN_AGE of `now`)."""
    path = forecast.current_run(data_dir)
    if path is None:
        return Forecast(path=None, reason="none")
    info = forecast.run_info(path)
    cycle = datetime.fromisoformat(info["cycle"])
    if (now or datetime.now(UTC)) - cycle > MAX_RUN_AGE:
        return Forecast(path=None, cycle=cycle, reason="stale")
    observed = info.get("last_observed")
    return Forecast(
        path=path,
        cycle=cycle,
        last_observed=datetime.fromisoformat(observed) if observed else None,
        last_hour=datetime.fromisoformat(info["last_hour"]),
    )


@dataclass(kw_only=True)
class HourlyFrame:
    times: list[datetime]  # hour ends, UTC
    values: dict[str, np.ndarray]
    sources: dict[str, list[str | None]]
    kinds: list[str | None]
    forecast: Forecast


@dataclass(kw_only=True)
class DailySeries:
    dates: list[date]  # the point's local days
    values: dict[str, np.ndarray]
    kinds: list[str | None]
    forecast: Forecast
    zone: str = ""
    totals: dict[str, np.ndarray] = field(default_factory=dict)  # running totals from January 1, if asked for


def point_hours(
    data_dir: Path,
    j: int,
    i: int,
    start: datetime,
    end: datetime,
    names,
    now: datetime | None = None,
    stores: "_Stores | None" = None,
) -> HourlyFrame:
    """Hours ending start..end (inclusive, UTC) at a cell: the archive's through its last observed hour, then the
    current run's."""
    run = current_forecast(data_dir, now)
    times = [start + k * HOUR for k in range((end - start) // HOUR + 1)]
    n = len(times)
    stores = stores or _Stores(names)
    observed_until = _last_observed(data_dir, run, end, now)
    cut = 0 if observed_until is None else max(0, min(n, (observed_until - start) // HOUR + 1))
    values: dict[str, np.ndarray] = {}
    sources: dict[str, list[str | None]] = {}
    for name in names:
        values[name] = np.full(n, np.nan)
        sources[name] = [None] * n
        if cut:
            values[name][:cut], sources[name][:cut] = _point_steps(stores, data_dir, HOURLY, name, j, i, start, cut)
        if run.path is not None and cut < n:
            fc_values, fc_sources = _point_steps(stores, run.path, HOURLY, name, j, i, times[cut], n - cut)
            values[name][cut:], sources[name][cut:] = fc_values, fc_sources
    beyond = run.last_hour if run.path is not None else observed_until
    kinds: list[str | None] = [
        OBSERVED if k < cut else (FORECAST if beyond is not None and times[k] <= beyond else None) for k in range(n)
    ]
    return HourlyFrame(times=times, values=values, sources=sources, kinds=kinds, forecast=run)


def point_days(
    data_dir: Path,
    j: int,
    i: int,
    first: date,
    last: date,
    names,
    totals=(),
    now: datetime | None = None,
) -> DailySeries:
    """Local days first..last at a cell, from its stitched hours by the rollup's definitions (`agdata.point`): a
    day is observed if every hour is, partial with some of each, forecast with only forecast hours.

    A point's days come from its hours rather than the daily store, whose chunks are a day of a map: a season of
    them is ~300 chunk reads per variable (2.4 s for five), its hours ~11 (0.5 s for every variable, days included).
    Running totals (`totals`) are read from the cumulative stores: the archive's before the first day that isn't
    observed, the run's from it."""
    run = current_forecast(data_dir, now)
    n = (last - first).days + 1
    dates = [first + timedelta(days=k) for k in range(n)]
    stores = _Stores([*VARIABLES, *totals])
    zone = cell_zone(data_dir, j, i, first.year, stores)
    start = _midnight(first - timedelta(days=1))  # before the first day's 8 pm-day in any zone
    end = _midnight(last + timedelta(days=1)) + timedelta(hours=8)  # past the last day's end in any zone
    frame = point_hours(data_dir, j, i, start, end, list(VARIABLES), now=now, stores=stores)
    days = daily_at_point(start, frame.values, zone, first, last)
    kinds: list[str | None] = []
    for day in dates:
        begin, close = day_bounds(day, zone)
        hour_kinds = set(frame.kinds[(begin - start) // HOUR : (close - start) // HOUR + 1])
        if hour_kinds == {OBSERVED}:
            kinds.append(OBSERVED)
        elif hour_kinds == {FORECAST}:
            kinds.append(FORECAST)
        elif OBSERVED in hour_kinds and FORECAST in hour_kinds:
            kinds.append(PARTIAL)
        else:
            kinds.append(None)  # some hours neither: the forecast stops partway, or nothing is there
    split = next((k for k, kind in enumerate(kinds) if kind != OBSERVED), n)
    out_totals: dict[str, np.ndarray] = {}
    for name in totals:
        series = _point_steps(stores, data_dir, CUMULATIVE, name, j, i, first, n)[0]
        if split < n:
            series[split:] = np.nan
            if run.path is not None:
                series[split:] = _point_steps(stores, run.path, CUMULATIVE, name, j, i, dates[split], n - split)[0]
        out_totals[name] = series
    values = {name: days[name] for name in names}
    return DailySeries(dates=dates, values=values, kinds=kinds, forecast=run, zone=zone, totals=out_totals)


def grid_day(
    data_dir: Path, name: str, day: date, window: Window | None = None, now: datetime | None = None
) -> tuple[np.ndarray, str | None]:
    """A daily variable over the window for one date, and its kind (by the box's latest time zone, so a day is
    forecast only once it's forecast everywhere it's shown): the archive's if observed, else the run's."""
    return _grid(data_dir, DAILY, name, day, window, now)


def grid_total(
    data_dir: Path, name: str, day: date, window: Window | None = None, now: datetime | None = None
) -> tuple[np.ndarray, str | None]:
    """A running total over the window on one date, and its kind, as `grid_day`."""
    return _grid(data_dir, CUMULATIVE, name, day, window, now)


def cell_zone(data_dir: Path, j: int, i: int, year: int, stores: "_Stores | None" = None) -> str:
    """The time zone a cell's days follow, from the archive's daily store."""
    store = (stores or _Stores([])).get(data_dir, DAILY, year)
    if store is None:
        raise FileNotFoundError(f"no daily store for {year} in {data_dir}")
    zones, index = cell_timezones(store)
    y, x = store.window.local(j, i)
    return zones[int(index[y, x])]


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _last_observed(data_dir: Path, run: Forecast, before: datetime, now: datetime | None) -> datetime | None:
    """The archive's last observed hour now (it may have moved past the run's stitch)."""
    found = forecast.last_observed_hour(data_dir, min(before, now or datetime.now(UTC)))
    if found is None and run.last_observed is not None:
        return run.last_observed
    return found


def _grid(data_dir, layout, name, day, window, now):
    run = current_forecast(data_dir, now)
    stores = _Stores([name])
    archive = _read_day(stores, data_dir, layout, name, day, window)
    observed_until = _last_observed(data_dir, run, _midnight(day + timedelta(days=2)), now)
    if observed_until is None:
        return archive, None
    # The day is observed everywhere once the westernmost zone has closed it (the lower 48 are UTC−4 to −8)
    if _midnight(day + timedelta(days=1)) + timedelta(hours=8) <= observed_until:
        return archive, OBSERVED
    if run.path is None:
        return archive, None
    values = _read_day(stores, run.path, layout, name, day, window)
    if run.last_hour is not None and day > run.last_hour.date():
        return values, None
    started = _midnight(day) + timedelta(hours=5) <= observed_until  # the easternmost zone's day has begun
    return values, PARTIAL if started else FORECAST


class _Stores:
    """Stores opened once per call, each for only the variables the call reads (an open checks every variable it's
    given: ~90 ms for a daily store's 45, ~40 ms for one)."""

    def __init__(self, names):
        self.names = set(names)
        self.opened: dict[tuple[str, str, int], GridStore | None] = {}

    def get(self, path: Path, layout: StoreLayout, year: int) -> GridStore | None:
        key = (str(path), layout.kind, year)
        if key not in self.opened:
            catalog = {"hourly": VARIABLES, "daily": DAILY_VARIABLES, "cumulative": CUMULATIVE_VARIABLES}[layout.kind]
            wanted = [catalog[n] for n in self.names if n in catalog] or [next(iter(catalog.values()))]
            try:
                self.opened[key] = GridStore.open(path, layout, year, wanted, add_missing=True)
            except FileNotFoundError:
                self.opened[key] = None
        return self.opened[key]


def _read_day(
    stores: _Stores, path: Path, layout: StoreLayout, name: str, day: date, window: Window | None
) -> np.ndarray:
    store = stores.get(path, layout, day.year)
    if store is None:
        shape = window.shape if window is not None else (0, 0)
        return np.full(shape, np.nan, dtype=np.float32)
    t = store.index_of(day)
    return store.read_steps(name, t, t + 1, window)[0]


def _point_steps(
    stores: _Stores, path: Path, layout: StoreLayout, name: str, j: int, i: int, first, n: int
) -> tuple[np.ndarray, list[str | None]]:
    """n steps from `first` (a UTC hour or a date) at a cell, across years; NaN and None where nothing's stored."""
    hourly = layout.step == "hour"
    step = HOUR if hourly else timedelta(days=1)
    values = np.full(n, np.nan)
    sources: list[str | None] = [None] * n
    k = 0
    while k < n:
        when = first + k * step
        year = when.year
        store = stores.get(path, layout, year)
        start_of_next = datetime(year + 1, 1, 1, tzinfo=UTC) if hourly else date(year + 1, 1, 1)
        count = min(n - k, int((start_of_next - when) / step))
        if store is not None:
            t = store.index_of(when)
            values[k : k + count] = store.read_point(name, j, i, t, t + count)
            if hourly:
                sources[k : k + count] = store.sources(name)[t : t + count]
        k += count
    return values, sources
