"""One series from the archive and the forecast, for a point or a map day (PLAN.md Phase 4 C).

Each hour is observed (the archive, through its last observed hour) or forecast (the current run after it). Each
day is observed (every hour observed), partial (today: some of each) or forecast; a day with nothing is missing.
The days come from the stores rolled up the same way: observed days from the archive's daily store, today and
later from the run's (`agdata.forecast`), whose stitched hours make today's values. Running totals likewise: the
archive's through yesterday, the run's from today (they continue the archive's).

The forecast is used only while its run is fresh (`MAX_RUN_AGE`); otherwise the series ends with the archive and
says why. Map days are grid days (CST, D74); a point's days follow the zone it's given (the grid's by default, or
its own with `day_basis=local`), and so do their kinds.

A point's forecast soil hours the run lacks (its IFS soil ends some 30 hours before NBM's last hour) can be filled from
another source (`fill_soil`: the app passes Open-Meteo's ECMWF IFS through its cell cache, D44). Maps keep the gap
rather than mixing sources.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata import computed, corrections, forecast, pastyears, projection, timecopy
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, GAP_FILL, VARIABLES, Variable
from agdata.grid import NDFD, Window
from agdata.places import county_at
from agdata.planting import typical_planting
from agdata.point import daily_at_point, hourly_sources
from agdata.store import CUMULATIVE, DAILY, HOURLY, INGREDIENTS, SOURCES, GridStore, StoreLayout
from agdata.timezones import GRID_ZONE, day_bounds
from agmodels import runner
from agmodels.registry import model as find_model
from agmodels.runner import ModelRun
from agmodels.scenarios import run_scenarios

HOUR = timedelta(hours=1)
MAX_RUN_AGE = timedelta(hours=12)  # past this a run's forecast isn't used (D43; the job runs every 6 hours)
OBSERVED, PARTIAL, FORECAST = "observed", "partial", "forecast"
SOIL = ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm")

# Hours ending start..end (UTC, inclusive) of the given variables from another source, for a point's forecast soil
FillSoil = Callable[[datetime, datetime, list[str]], dict[str, np.ndarray]]


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
    corrections: tuple[str, ...] = ()  # the source corrections its days went through (`agdata.corrections` labels)
    sources: tuple[str, ...] = ()  # the sources of the hours its days were rolled up from, in catalog order


def point_hours(
    data_dir: Path,
    j: int,
    i: int,
    start: datetime,
    end: datetime,
    names,
    now: datetime | None = None,
    stores: "Stores | None" = None,
    fill_soil: FillSoil | None = None,
) -> HourlyFrame:
    """Hours ending start..end (inclusive, UTC) at a cell: the archive's through its last observed hour, then the
    current run's, with forecast soil hours the run lacks from `fill_soil` (sourced `openmeteo`)."""
    return cells_hours(data_dir, [(j, i)], start, end, names, now=now, stores=stores, fill_soil=[fill_soil])[0]


def cells_hours(
    data_dir: Path,
    cells: Sequence[tuple[int, int]],
    start: datetime,
    end: datetime,
    names,
    now: datetime | None = None,
    stores: "Stores | None" = None,
    fill_soil: Sequence[FillSoil | None] | None = None,
) -> list[HourlyFrame]:
    """`point_hours` at each of several cells, on one read per variable and store (`GridStore.read_cells`: a chunk
    holding several of the cells is read once). `fill_soil`, if given, has one entry per cell. A computed variable
    (`agdata.computed`) is made from its inputs' hours, with its first input's sources."""
    asked = list(names)
    names = computed.expand(asked, computed.HOURLY_COMPUTED)
    run = current_forecast(data_dir, now)
    times = [start + k * HOUR for k in range((end - start) // HOUR + 1)]
    n = len(times)
    stores = stores or Stores(names)
    observed_until = _last_observed(data_dir, run, end, now, stores)
    cut = 0 if observed_until is None else max(0, min(n, (observed_until - start) // HOUR + 1))
    values: dict[str, np.ndarray] = {}
    sources: dict[str, list[str | None]] = {}
    for name in names:
        values[name] = np.full((n, len(cells)), np.nan)
        sources[name] = [None] * n
        if cut:
            values[name][:cut], sources[name][:cut] = _cells_steps(stores, data_dir, HOURLY, name, cells, start, cut)
        if run.path is not None and cut < n:
            fc_values, fc_sources = _cells_steps(stores, run.path, HOURLY, name, cells, times[cut], n - cut)
            values[name][cut:], sources[name][cut:] = fc_values, fc_sources
    beyond = run.last_hour if run.path is not None else observed_until
    archived = {year: stores.get(data_dir, HOURLY, year) is not None for year in {t.year for t in times[:cut]}}
    kinds: list[str | None] = [
        (OBSERVED if archived[times[k].year] else None)  # an hour before the archive began is missing
        if k < cut
        else (FORECAST if beyond is not None and times[k] <= beyond else None)
        for k in range(n)
    ]
    frames = []
    for c in range(len(cells)):
        own = {name: np.ascontiguousarray(values[name][:, c]) for name in names}
        own_sources = sources
        fill = fill_soil[c] if fill_soil is not None else None
        if fill is not None and run.path is not None:
            own_sources = {name: list(s) for name, s in sources.items()}  # this cell's fills are its own
            _fill_soil(fill, times, own, own_sources, [n for n in names if n in SOIL], cut, run.last_hour)
        if asked != names:
            own = computed.complete(own, asked, computed.HOURLY_COMPUTED)
            own_sources = {
                name: own_sources[c.inputs[0] if (c := computed.computed(name)) is not None else name] for name in asked
            }
        frames.append(HourlyFrame(times=times, values=own, sources=own_sources, kinds=kinds, forecast=run))
    return frames


def point_days(
    data_dir: Path,
    j: int,
    i: int,
    first: date,
    last: date,
    names,
    totals=(),
    now: datetime | None = None,
    fill_soil: FillSoil | None = None,
    stores: "Stores | None" = None,
    zone: str = GRID_ZONE,
) -> DailySeries:
    """Days first..last at a cell by `zone`'s clock, from its stitched hours by the rollup's definitions
    (`agdata.point`): a day is observed if every hour is, partial with some of each, forecast with only forecast
    hours.

    A point's days come from its hours rather than the daily store, whose chunks are a day of a map: a season of
    them is ~300 chunk reads per variable (2.4 s for five), its hours ~11 per variable. Only the hourly variables
    `names` are made from are read (`hourly_needed`), and only `names` are rolled up.
    Running totals (`totals`) are read from the cumulative stores: the archive's before the first day that isn't
    observed, the run's from it. `fill_soil` is used only when one of `names` is a soil variable. Days in a year
    the archive doesn't have are missing. `stores`, shared by a caller reading many points, must open at least
    `hourly_needed(names)` and `totals`."""
    found = cells_days(
        data_dir, [(j, i)], first, last, names, totals, now=now, fill_soil=[fill_soil], stores=stores, zones=[zone]
    )
    return found[0]


def cells_days(
    data_dir: Path,
    cells: Sequence[tuple[int, int]],
    first: date,
    last: date,
    names,
    totals=(),
    now: datetime | None = None,
    fill_soil: Sequence[FillSoil | None] | None = None,
    stores: "Stores | None" = None,
    zones: Sequence[str] | None = None,
) -> list[DailySeries]:
    """`point_days` at each of several cells (each by its own zone in `zones`, default the grid's), on one read of
    each variable's hours (`cells_hours`) and one rollup per zone, the cells as a trailing axis: a request for 50
    points costs a few times one, not 50 (the rollup's per-day work is the same for one cell or many)."""
    run = current_forecast(data_dir, now)
    n = (last - first).days + 1
    dates = [first + timedelta(days=k) for k in range(n)]
    hourly = hourly_needed(names)
    if stores is not None and not {*hourly, *totals} <= stores.names:
        raise ValueError(f"the shared stores don't open {sorted({*hourly, *totals} - stores.names)}")
    stores = stores or Stores([*hourly, *totals])
    zones = list(zones) if zones is not None else [GRID_ZONE] * len(cells)
    start = _midnight(first - timedelta(days=1))  # before the first day's earliest window (from noon) in any zone
    end = _midnight(last + timedelta(days=1)) + timedelta(hours=8)  # past the last day's end in any zone
    wants_soil = any(name in SOIL for name in hourly)
    frames = cells_hours(
        data_dir, cells, start, end, hourly, now=now, stores=stores, fill_soil=fill_soil if wants_soil else None
    )
    rolled: list[dict[str, np.ndarray]] = [{} for _ in cells]
    kinds_in: dict[str, list[str | None]] = {}
    for zone in dict.fromkeys(zones):
        group = [c for c, z in enumerate(zones) if z == zone]
        if len(group) == 1:  # one cell's hours as they are
            hours = frames[group[0]].values
        else:
            hours = {name: np.stack([frames[c].values[name] for c in group], axis=1) for name in hourly}
        days = daily_at_point(start, hours, zone, first, last, names=names)
        for k, c in enumerate(group):
            rolled[c] = {name: days[name] if len(group) == 1 else days[name][:, k] for name in names}
        kinds_in[zone] = day_kinds(frames[group[0]].times, frames[group[0]].kinds, zone, dates)
    out_totals: list[dict[str, np.ndarray]] = [{} for _ in cells]
    for name in totals:
        archive = _cells_steps(stores, data_dir, CUMULATIVE, name, cells, first, n)[0]
        for zone, kinds in kinds_in.items():
            split = next((k for k, kind in enumerate(kinds) if kind != OBSERVED), n)
            group = [c for c, z in enumerate(zones) if z == zone]
            ahead = None
            if split < n and run.path is not None:
                ahead = _cells_steps(
                    stores, run.path, CUMULATIVE, name, [cells[c] for c in group], dates[split], n - split
                )[0]
            for k, c in enumerate(group):
                series = archive[:, c].copy()
                if split < n:
                    series[split:] = np.nan if ahead is None else ahead[:, k]
                out_totals[c][name] = series
    return [
        DailySeries(
            dates=dates,
            values=rolled[c],
            kinds=kinds_in[zones[c]],
            forecast=run,
            zone=zones[c],
            totals=out_totals[c],
            corrections=in_box_corrections(kinds_in[zones[c]], run, hourly),
            sources=_sources_seen(frames[c]),
        )
        for c in range(len(cells))
    ]


def hourly_needed(names) -> list[str]:
    """The hourly variables the daily `names` are rolled up from (`agdata.point.hourly_sources`), in catalog order:
    a read of the min and max temperature reads one variable's hours, not all of them. A name the table doesn't
    know (`et0_sum_estimate`) reads them all."""
    table = hourly_sources()
    if any(name not in table for name in names):
        return list(VARIABLES)
    wanted = {hourly for name in names for hourly in table[name]}
    return [name for name in VARIABLES if name in wanted]


def _sources_seen(frame: HourlyFrame) -> tuple[str, ...]:
    seen = {source for sources in frame.sources.values() for source in sources if source is not None}
    return source_order(seen)


def source_order(sources) -> tuple[str, ...]:
    """Sources in the store's code order: the archive's (URMA, RTMA, HRRR) before the forecast's."""
    return tuple(sorted(sources, key=lambda name: SOURCES.get(name, 99)))


def last_written(
    data_dir: Path,
    first: date,
    last: date,
    totals=(),
    now: datetime | None = None,
    daily=(),
    hourly: Sequence[str] | None = None,
    ingredients=(),
) -> str:
    """A stamp that changes whenever `point_days(first..last, totals=…)` at a cell can answer differently for the same
    `now`, at any cell: the latest write time of the hours it reads (archive and forecast run) and of its running
    totals, and which run it takes the forecast from (a run going stale ends the series without any write). Write
    times are kept per step, not per cell, so a write anywhere in the window counts. Cheap next to the read itself:
    one small array per variable and year. `daily` adds daily-store variables (a map reads them, and a rebuild of
    a stale variable writes them without writing any hour). `hourly` limits the hours stamped to those variables
    (default every one): a map of a daily variable needs none, since its daily store is written after its hours,
    and opening a store for all 16 hourly variables is most of a small map's time. `ingredients` adds a model map's
    variables in `agdata.modelmaps`' store (a running total rewritten at its biofix is rewritten after it too)."""
    run = current_forecast(data_dir, now)
    stamps: list[float] = []
    start = _midnight(first - timedelta(days=1))
    end = _midnight(last + timedelta(days=1)) + timedelta(hours=8)
    hourly_names = list(VARIABLES) if hourly is None else list(hourly)
    stores = Stores([*hourly_names, *totals, *daily, *ingredients])
    for path in (data_dir, run.path):
        if path is None:
            continue
        for year in range(start.year, end.year + 1):
            hours = stores.get(path, HOURLY, year) if hourly_names else None
            if hours is not None:
                lo = max(start, datetime(year, 1, 1, tzinfo=UTC))
                hi = min(end, datetime(year, 12, 31, 23, tzinfo=UTC))
                t0, t1 = hours.index_of(lo), hours.index_of(hi) + 1
                stamps += [s for name in hourly_names if (s := hours.written(name, t0, t1)) is not None]
            # Days are stamped only in the years first..last reach (the hours above start the evening before)
            lo, hi = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
            if lo > hi:
                continue
            for layout, names in ((CUMULATIVE, totals), (DAILY, daily), (INGREDIENTS, ingredients)):
                if names and (days := stores.get(path, layout, year)) is not None:
                    d0, d1 = days.index_of(lo), days.index_of(hi) + 1
                    stamps += [s for name in names if (s := days.written(name, d0, d1)) is not None]
    latest = max(stamps) if stamps else None
    cycle = run.cycle.isoformat() if run.cycle is not None and run.path is not None else run.reason
    return f"{latest}:{cycle}"


# Hourly variables computed from others at ingest, so a correction to those is in them too
_DERIVED_FROM = {
    "et0": ("air_temperature", "dew_point", "wind_speed", "shortwave_radiation", "surface_pressure"),
    "relative_humidity": ("air_temperature", "dew_point"),
}


def in_box_corrections(kinds: list[str | None], run: Forecast, variables=None) -> tuple[str, ...]:
    """The corrections behind a series in the box: HRRR's shortwave on observed days, the forecast's calibration
    on forecast days (D48, D49), and IFS's soil shifted at the ERA5-Land seam (D55) whenever the series reaches the
    forecast. (The last few observed days' soil went through it too until ERA5-Land replaces them, ~5 days; a series
    ending before the forecast doesn't list it.) With `variables` (the hourly ones read), only the corrections to
    them or to what they're computed from."""
    applied = [corrections.HRRR_SHORTWAVE] if any(k in (OBSERVED, PARTIAL) for k in kinds) else []
    if run.path is not None and any(k in (PARTIAL, FORECAST) for k in kinds):
        applied += [corrections.NBM_SHORTWAVE, corrections.NBM_MAX, corrections.NBM_NIGHT_MIN, corrections.NBM_RH]
        applied += [corrections.IFS_SOIL_SEAM]
    if variables is not None:
        read = set(variables) | {source for name in variables for source in _DERIVED_FROM.get(name, ())}
        applied = [c for c in applied if any(name in c.variable.replace(",", " ").split() for name in read)]
    return tuple(c.label for c in applied)


def grid_day(
    data_dir: Path, name: str, day: date, window: Window | None = None, now: datetime | None = None
) -> tuple[np.ndarray, str | None]:
    """A daily variable over the window for one grid day (CST), and its kind: the archive's if observed, else the
    run's."""
    return _grid(data_dir, DAILY, name, day, window, now)


def grid_total(
    data_dir: Path, name: str, day: date, window: Window | None = None, now: datetime | None = None
) -> tuple[np.ndarray, str | None]:
    """A running total over the window on one date, and its kind, as `grid_day`."""
    return _grid(data_dir, CUMULATIVE, name, day, window, now)


@dataclass(kw_only=True)
class GridSteps:
    """A run of steps (days or hours) of one variable over a window: values (steps, y, x), each step's kind (as
    `grid_day`'s), the steps read from a store whose variable is stale (D29: another version of its code wrote
    them), and the hourly sources behind them (store order)."""

    steps: list
    values: np.ndarray
    kinds: list[str | None]
    stale: np.ndarray
    sources: tuple[str, ...]
    forecast: Forecast
    run_from: int  # the first step read from the forecast run (len(steps) if none)


def grid_days(
    data_dir: Path,
    layout: StoreLayout,
    name: str,
    first: date,
    last: date,
    window: Window,
    now: datetime | None = None,
    stores: "Stores | None" = None,
    read: bool = True,
) -> GridSteps:
    """Days first..last of a daily variable or running total over the window, as `grid_day` reads one day: the
    archive's while the day is observed everywhere in the box, the run's after. One read per year and store;
    `read=False` gives the kinds alone (values all missing)."""
    run = current_forecast(data_dir, now)
    stores = stores or Stores([name, *hourly_needed([name])])
    n = (last - first).days + 1
    dates = [first + timedelta(days=k) for k in range(n)]
    observed_until = _last_observed(data_dir, run, _midnight(last + timedelta(days=2)), now, stores)
    closed = 0  # observed once its last hour is (grid days, CST)
    if observed_until is not None:
        closed = sum(day_bounds(d, GRID_ZONE)[1] <= observed_until for d in dates)
    cut = closed if run.path is not None else n  # without a run, the archive's values with no kind
    values, stale, archived = read_split(stores, data_dir, run.path, layout, name, dates, cut, window, read=read)
    kinds: list[str | None] = [OBSERVED if archived[k] and k < closed else None for k in range(n)]
    if run.path is not None and observed_until is not None:
        for k in range(cut, n):
            if run.last_hour is not None and dates[k] > run.last_hour.date():
                continue
            started = day_bounds(dates[k], GRID_ZONE)[0] <= observed_until  # its first hour is observed
            kinds[k] = PARTIAL if started else FORECAST
    if read:  # a day with no value anywhere has nothing to show (the run's last, incomplete day)
        kinds = [None if np.isnan(values[k]).all() else kind for k, kind in enumerate(kinds)]
    start, end = _midnight(first - timedelta(days=1)), _midnight(last + timedelta(days=1)) + timedelta(hours=8)
    sources = _grid_sources(stores, data_dir, run, hourly_needed([name]), start, end, observed_until)
    return GridSteps(steps=dates, values=values, kinds=kinds, stale=stale, sources=sources, forecast=run, run_from=cut)


def grid_hours(
    data_dir: Path,
    name: str,
    start: datetime,
    end: datetime,
    window: Window,
    now: datetime | None = None,
    stores: "Stores | None" = None,
) -> GridSteps:
    """Hours ending start..end (UTC, inclusive) of an hourly variable over the window: the archive's through its last
    observed hour, then the run's, as `point_hours`."""
    run = current_forecast(data_dir, now)
    stores = stores or Stores([name])
    times = [start + k * HOUR for k in range((end - start) // HOUR + 1)]
    n = len(times)
    observed_until = _last_observed(data_dir, run, end, now, stores)
    cut = 0 if observed_until is None else max(0, min(n, (observed_until - start) // HOUR + 1))
    values = np.full((n, *window.shape), np.nan, dtype=np.float32)
    kinds: list[str | None] = [None] * n
    for path, k0, k1 in ((data_dir, 0, cut), (run.path, cut, n)):
        if path is None or k0 >= k1:
            continue
        for year, a, b in _year_runs(times, k0, k1):
            store = stores.get(path, HOURLY, year)
            if store is None:
                continue
            t0 = store.index_of(times[a])
            values[a:b] = store.read_steps(name, t0, t0 + b - a, window)
            if path == data_dir:
                kinds[a:b] = [OBSERVED] * (b - a)
            else:
                kinds[a:b] = [
                    FORECAST if run.last_hour is not None and t <= run.last_hour else None for t in times[a:b]
                ]
    sources = _grid_sources(stores, data_dir, run, [name], start, end, observed_until)
    return GridSteps(
        steps=times,
        values=values,
        kinds=kinds,
        stale=np.zeros(n, dtype=bool),
        sources=sources,
        forecast=run,
        run_from=cut,
    )


def combine(c: "computed.Computed", reads: Mapping[str, GridSteps]) -> GridSteps:
    """A computed variable's steps over a window from its inputs' reads (`grid_days` or `grid_hours` of each, over
    the same steps): missing wherever an input is, a step's kind its first input's unless no value is left anywhere,
    stale where any input's was read stale, and the inputs' sources together."""
    first = reads[c.inputs[0]]
    values = c.compute({name: reads[name].values for name in c.inputs}).astype(np.float32)
    kinds = [None if np.isnan(values[k]).all() else kind for k, kind in enumerate(first.kinds)]
    stale = np.zeros(len(first.steps), dtype=bool)
    for name in c.inputs:
        stale |= reads[name].stale
    sources = source_order({s for name in c.inputs for s in reads[name].sources})
    return replace(first, values=values, kinds=kinds, stale=stale, sources=sources)


def last_observed(data_dir: Path, now: datetime | None = None) -> datetime | None:
    """The archive's last observed hour (its end, UTC), or the current run's stitch if the archive has none."""
    return _last_observed(data_dir, current_forecast(data_dir, now), now or datetime.now(UTC), now)


def last_closed_day(observed_until: datetime) -> date:
    """The last grid day observed through its last hour (CST, `grid_days`' rule)."""
    return (observed_until - timedelta(hours=6)).date() - timedelta(days=1)


def read_split(
    stores: "Stores",
    data_dir: Path,
    run_path: Path | None,
    layout: StoreLayout,
    name: str,
    dates: list[date],
    cut: int,
    window: Window,
    read: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A variable on `dates` over the window, the archive's before index `cut` and the run's from it: (values, stale,
    whether the archive held the day), as `grid_days` reads them. One read per year and store; `read=False` leaves the
    values missing."""
    n = len(dates)
    stale = np.zeros(n, dtype=bool)
    archived = np.zeros(n, dtype=bool)
    pieces: list[tuple[int, int, np.ndarray]] = []
    for path, k0, k1 in ((data_dir, 0, cut), (run_path, cut, n)):
        if path is None or k0 >= k1:
            continue
        for year, a, b in _year_runs(dates, k0, k1):
            store = stores.get(path, layout, year)
            if store is None:
                continue
            if read:
                t0 = store.index_of(dates[a])
                pieces.append((a, b, _read_days(stores, data_dir, path, layout, store, name, t0, t0 + b - a, window)))
            stale[a:b] = name in store.stale
            archived[a:b] = path == data_dir
    if len(pieces) == 1 and pieces[0][:2] == (0, n):  # one store's read is the whole range: no copy (a season is
        return pieces[0][2], stale, archived  # ~60 MB over Wisconsin, and filling a NaN array first cost 70 ms)
    values = np.full((n, *window.shape), np.nan, dtype=np.float32)
    for a, b, piece in pieces:
        values[a:b] = piece
    return values, stale, archived


def _read_days(
    stores: "Stores",
    data_dir: Path,
    path: Path,
    layout: StoreLayout,
    store: GridStore,
    name: str,
    t0: int,
    t1: int,
    window: Window,
) -> np.ndarray:
    """Steps t0..t1-1 of a store: a season of the archive's daily min or max from its copy laid out by time
    (`agdata.timecopy`), with any day the copy is behind on, or all of them if the daily store holds the variable
    as stale, from the daily store."""
    if not (path == data_dir and layout is DAILY and name in timecopy.NAMES and t1 - t0 >= timecopy.MIN_DAYS):
        return store.read_steps(name, t0, t1, window, dtype=np.float32)
    copy = stores.get(data_dir, timecopy.COPY, store.year)
    if copy is None or name in store.stale:  # the copy's days are as current as the stamps say (D29: the daily's)
        return store.read_steps(name, t0, t1, window, dtype=np.float32)
    values, current = timecopy.read(copy, store, name, t0, t1, window)
    for k0, k1 in timecopy.runs_of(~current):
        values[k0:k1] = store.read_steps(name, t0 + k0, t0 + k1, window, dtype=np.float32)
    return values


def _year_runs(steps: list, k0: int, k1: int):
    """(year, a, b): steps[a:b] within k0..k1 that fall in one year."""
    a = k0
    while a < k1:
        year = steps[a].year
        b = a
        while b < k1 and steps[b].year == year:
            b += 1
        yield year, a, b
        a = b


def _grid_sources(
    stores: "Stores",
    data_dir: Path,
    run: Forecast,
    hourly: list[str],
    start: datetime,
    end: datetime,
    observed_until: datetime | None,
) -> tuple[str, ...]:
    """The sources of the hours behind a grid read: the archive's through its last observed hour, the run's after."""
    seen: set[str] = set()
    cut = observed_until if observed_until is not None else start - HOUR
    for path, lo, hi in ((data_dir, start, min(end, cut)), (run.path, max(start, cut + HOUR), end)):
        if path is None or lo > hi:
            continue
        for year in range(lo.year, hi.year + 1):
            store = stores.get(path, HOURLY, year)
            if store is None:
                continue
            a = max(lo, datetime(year, 1, 1, tzinfo=UTC))
            b = min(hi, datetime(year, 12, 31, 23, tzinfo=UTC))
            if a > b:
                continue
            t0, t1 = store.index_of(a), store.index_of(b) + 1
            seen |= {s for name in hourly for s in store.sources(name, t0, t1) if s is not None}
    return source_order(seen)


def _fill_soil(fill_soil: FillSoil, times, values, sources, names: list[str], cut: int, last_hour) -> None:
    """Fills the forecast's missing soil hours (after the observed `cut`, through the run's last hour) in place."""
    n = len(times)
    end = n if last_hour is None else next((k for k in range(n) if times[k] > last_hour), n)
    gaps = {name: np.flatnonzero(np.isnan(values[name][cut:end])) + cut for name in names}
    wanted = [name for name, k in gaps.items() if k.size]
    if not wanted:
        return
    lo = min(int(gaps[name][0]) for name in wanted)
    hi = max(int(gaps[name][-1]) for name in wanted)
    filled = fill_soil(times[lo], times[hi], wanted)
    for name in wanted:
        other = filled.get(name)
        if other is None:
            continue
        for k in gaps[name]:
            value = other[k - lo]
            if np.isfinite(value):
                values[name][k] = value
                sources[name][k] = "openmeteo"


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _last_observed(
    data_dir: Path, run: Forecast, before: datetime, now: datetime | None, stores: "Stores | None" = None
) -> datetime | None:
    """The archive's last observed hour now (it may have moved past the run's stitch)."""
    key = (str(data_dir), before, now)
    if stores is not None and key in stores.observed:
        found = stores.observed[key]
    else:
        found = forecast.last_observed_hour(data_dir, min(before, now or datetime.now(UTC)))
        if stores is not None:
            stores.observed[key] = found
    if found is None and run.last_observed is not None:
        return run.last_observed
    return found


def _grid(data_dir, layout, name, day, window, now):
    run = current_forecast(data_dir, now)
    stores = Stores([name])
    archive = _read_day(stores, data_dir, layout, name, day, window)
    observed_until = _last_observed(data_dir, run, _midnight(day + timedelta(days=2)), now)
    if observed_until is None:
        return archive, None
    # The day is observed once its last hour is (grid days, CST)
    if day_bounds(day, GRID_ZONE)[1] <= observed_until:
        # ...and only if the archive has its year (a day before the archive began is missing, not observed)
        return archive, OBSERVED if stores.get(data_dir, layout, day.year) is not None else None
    if run.path is None:
        return archive, None
    values = _read_day(stores, run.path, layout, name, day, window)
    if run.last_hour is not None and day > run.last_hour.date():
        return values, None
    started = day_bounds(day, GRID_ZONE)[0] <= observed_until  # its first hour is observed
    return values, PARTIAL if started else FORECAST


class Stores:
    """Stores opened once per call, each for only the variables the call reads (an open checks every variable it's
    given: ~90 ms for a daily store's 45, ~40 ms for one). A caller reading many points (an API request) passes one
    to each `point_days` so they share the opens, and the archive's last observed hour, read once."""

    def __init__(self, names):
        self.names = set(names)
        self.opened: dict[tuple[str, str, int], GridStore | None] = {}
        self.observed: dict[tuple[str, datetime, datetime | None], datetime | None] = {}

    def get(self, path: Path, layout: StoreLayout, year: int) -> GridStore | None:
        key = (str(path), layout.kind, year)
        if key not in self.opened:
            catalog = _catalog(layout.kind)
            wanted = [catalog[n] for n in self.names if n in catalog] or [next(iter(catalog.values()))]
            try:
                self.opened[key] = GridStore.open(path, layout, year, wanted, add_missing=True)
            except FileNotFoundError:
                self.opened[key] = None
        return self.opened[key]


def _catalog(kind: str) -> Mapping[str, Variable]:
    if kind == "ingredients":
        from agdata import modelmaps  # imports every model: only when a model map is read

        return {v.name: v for v in modelmaps.variables()}
    return {
        "hourly": VARIABLES,
        "daily": DAILY_VARIABLES,
        "cumulative": CUMULATIVE_VARIABLES,
        timecopy.COPY.kind: {v.name: v for v in timecopy.variables()},
    }[kind]


def _read_day(
    stores: Stores, path: Path, layout: StoreLayout, name: str, day: date, window: Window | None
) -> np.ndarray:
    store = stores.get(path, layout, day.year)
    if store is None:
        shape = window.shape if window is not None else (0, 0)
        return np.full(shape, np.nan, dtype=np.float32)
    t = store.index_of(day)
    return store.read_steps(name, t, t + 1, window)[0]


def _cells_steps(
    stores: Stores, path: Path, layout: StoreLayout, name: str, cells: Sequence[tuple[int, int]], first, n: int
) -> tuple[np.ndarray, list[str | None]]:
    """n steps from `first` (a UTC hour or a date) at each cell, (steps, cells), across years; NaN and None where
    nothing's stored. The sources are per step (a write covers the whole window)."""
    hourly = layout.step == "hour"
    step = HOUR if hourly else timedelta(days=1)
    values = np.full((n, len(cells)), np.nan)
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
            values[k : k + count] = store.read_cells(name, cells, t, t + count)
            if hourly:
                sources[k : k + count] = store.sources(name, t, t + count)
        k += count
    return values, sources


ReadDays = Callable[[date, date, list[str]], DailySeries]  # local days first..last of the named variables


@dataclass(frozen=True, kw_only=True)
class RunSpec:
    """One model run at a point: the model and the choices that change it (`runner.run`'s)."""

    model_id: str
    biofix: date | None = None
    planting: date | None = None
    options: Mapping[str, str] = field(default_factory=dict)
    crop_options: Mapping[str, str] = field(default_factory=dict)


def with_planting(run: RunSpec, latitude: float, longitude: float, start: date) -> RunSpec:
    """The run with the typical planting date (D34) for a stage-gated model given none, where one is published."""
    crops = runner.crop_models(find_model(run.model_id).SPEC)
    if run.planting is not None or not crops:
        return run
    typical = typical_planting(crops[0].removesuffix("-stages"), latitude, longitude)
    if typical is None:
        return run
    month, day = (int(p) for p in typical.typical.split("-"))
    return replace(run, planting=date(start.year, month, day))


def days_needed(runs: Sequence[RunSpec], start: date) -> tuple[date, list[str]]:
    """The first day and the daily variables that every run from `start` needs, so they're read once."""
    first, names = start, []
    for run in runs:
        m = find_model(run.model_id)
        first = min(first, runner.first_day_needed(m, start, biofix=run.biofix, planting=run.planting))
        names += [name for name in runner.required_inputs(m) if name not in names]
    return first, names


def sliced(days: DailySeries, first: date, names: list[str]) -> DailySeries:
    """The days from `first` of the named variables (running totals and sources as they are)."""
    k = (first - days.dates[0]).days
    if k < 0:
        raise ValueError(f"{first} is before the series' first day, {days.dates[0]}")
    return replace(days, dates=days.dates[k:], kinds=days.kinds[k:], values={n: days.values[n][k:] for n in names})


def runs_at_point(
    read_days: ReadDays,
    latitude: float,
    longitude: float,
    runs: Sequence[RunSpec],
    start: date,
    end: date,
    planting_default: bool = True,
) -> list[ModelRun]:
    """Models at a point from any source of days (the archive and forecast, or Open-Meteo), read once for them all
    (`days_needed`): each run gets its own days from its `runner.first_day_needed`, so the result is the same as
    running it alone. The region is checked against the county grid; `planting_default` gives a stage-gated model
    without a planting date the typical one (D34)."""
    if planting_default:
        runs = [with_planting(run, latitude, longitude, start) for run in runs]
    first, names = days_needed(runs, start)
    days = read_days(first, end, names)
    county = county_at(latitude, longitude)
    results = []
    for run in runs:
        m = find_model(run.model_id)
        own = sliced(
            days,
            first=runner.first_day_needed(m, start, biofix=run.biofix, planting=run.planting),
            names=runner.required_inputs(m),
        )
        in_region = not m.SPEC.region or (county is not None and county.state in m.SPEC.region)
        results.append(
            runner.run(
                m,
                dates=own.dates,
                daily=own.values,
                latitude=latitude,
                start=start,
                kinds=own.kinds,
                biofix=run.biofix,
                planting=run.planting,
                options=run.options,
                crop_options=run.crop_options,
                in_region=in_region,
                gap_fill=GAP_FILL,
            )
        )
        results[-1].sources, results[-1].corrections = days.sources, days.corrections
    return results


@dataclass(kw_only=True)
class Projected:
    """Runs carried past the series' last day with data on each earlier year's days (D63): per `RunSpec`, one
    `ModelRun` per scenario (in `years` order), or the one plain run when there's nothing to project."""

    runs: list[list[ModelRun]]
    years: list[int]  # each scenario's source year; empty: no projection
    start: date | None = None  # the first projected day
    coverage: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))  # years with every input, per day


def archive_years(data_dir: Path) -> list[int]:
    """The years the archive has a daily store for."""
    return pastyears.years_on_disk(data_dir, DAILY)


def projected_runs(
    read_days: ReadDays,
    read_past: Callable[[date, date, list[str]], dict[str, np.ndarray]],
    latitude: float,
    longitude: float,
    runs: Sequence[RunSpec],
    start: date,
    end: date,
    years: Sequence[int],
) -> Projected:
    """`runs_at_point` carried on past the series' last day with data to `end`, once per earlier year in `years`
    (`agdata.projection`; `read_past` reads a past year's days). Each run's scenarios come from
    `agmodels.scenarios.run_scenarios`, the same as running each year alone."""
    first, names = days_needed(runs, start)
    days = read_days(first, end, names)
    begins = projection.projection_start(days.dates, days.kinds)
    county = county_at(latitude, longitude)
    if begins is None or begins > end:
        plain = runs_at_point(lambda *_: days, latitude, longitude, runs, start, end, planting_default=False)
        return Projected(runs=[[r] for r in plain], years=[])
    kept = (begins - first).days
    scenarios_found = projection.build(begins, end, [y for y in years if y < end.year], names, read_past)
    if not scenarios_found.years:
        plain = runs_at_point(lambda *_: days, latitude, longitude, runs, start, end, planting_default=False)
        return Projected(runs=[[r] for r in plain], years=[], start=begins, coverage=scenarios_found.coverage)
    values, kinds = projection.stacked(
        {name: days.values[name][:kept] for name in names}, days.kinds[:kept], scenarios_found
    )
    dates = days.dates[:kept] + scenarios_found.dates
    out = []
    for run in runs:
        m = find_model(run.model_id)
        k = (runner.first_day_needed(m, start, biofix=run.biofix, planting=run.planting) - first).days
        in_region = not m.SPEC.region or (county is not None and county.state in m.SPEC.region)
        found = run_scenarios(
            m,
            dates=dates[k:],
            daily={name: values[name][k:] for name in runner.required_inputs(m)},
            latitude=latitude,
            start=start,
            kinds=kinds[k:],
            biofix=run.biofix,
            planting=run.planting,
            options=run.options,
            crop_options=run.crop_options,
            in_region=in_region,
            gap_fill=GAP_FILL,
        )
        for r in found:
            r.sources, r.corrections = days.sources, days.corrections
        out.append(found)
    return Projected(runs=out, years=scenarios_found.years, start=begins, coverage=scenarios_found.coverage)


def past_reader(data_dir: Path, j: int, i: int, stores: "Stores | None" = None):
    """`projected_runs`' `read_past` at a cell: a past year's days from the copies laid out for points
    (`agdata.pastyears`), or rolled up from the archive's hours where a year has none yet."""
    copies = pastyears.Reader(data_dir)

    def read(first: date, last: date, names: list[str]) -> dict[str, np.ndarray]:
        found = copies.read(j, i, first, last, names)
        if found is not None:
            return found
        return point_days(data_dir, j, i, first, last, names, stores=stores).values

    return read


def models_at_point(
    data_dir: Path,
    latitude: float,
    longitude: float,
    runs: Sequence[RunSpec],
    start: date,
    end: date,
    now: datetime | None = None,
    fill_soil: FillSoil | None = None,
    planting_default: bool = True,
    zone: str = GRID_ZONE,
) -> list[ModelRun]:
    """Models at a point in the box from `start` to `end`, through the forecast (D30), from the archive and the
    current run (`runs_at_point` with one `point_days` by `zone`'s days; soil past the run's from `fill_soil`, D44)."""
    cell = NDFD.cell_of(latitude, longitude)
    if cell is None:
        raise ValueError(f"({latitude}, {longitude}) is off the grid")

    def read_days(first: date, last: date, names: list[str]) -> DailySeries:
        return point_days(data_dir, *cell, first, last, names, now=now, fill_soil=fill_soil, zone=zone)

    return runs_at_point(read_days, latitude, longitude, runs, start, end, planting_default=planting_default)


def model_at_point(
    data_dir: Path,
    latitude: float,
    longitude: float,
    model_id: str,
    start: date,
    end: date,
    biofix: date | None = None,
    planting: date | None = None,
    options: dict[str, str] | None = None,
    crop_options: dict[str, str] | None = None,
    now: datetime | None = None,
    fill_soil: FillSoil | None = None,
) -> ModelRun:
    """One model's three layers at a point in the box (`models_at_point`)."""
    run = RunSpec(
        model_id=model_id, biofix=biofix, planting=planting, options=options or {}, crop_options=crop_options or {}
    )
    return models_at_point(data_dir, latitude, longitude, [run], start, end, now=now, fill_soil=fill_soil)[0]


def day_kinds(times: list[datetime], hour_kinds: list[str | None], zone: str, dates: list[date]) -> list[str | None]:
    """Each local day's kind from its hours' (observed, partial, forecast; None when some hour has neither)."""
    start = times[0]
    kinds: list[str | None] = []
    for day in dates:
        begin, close = day_bounds(day, zone)
        found = set(hour_kinds[max(0, (begin - start) // HOUR) : max(0, (close - start) // HOUR + 1)])
        if found == {OBSERVED}:
            kinds.append(OBSERVED)
        elif found == {FORECAST}:
            kinds.append(FORECAST)
        elif found == {OBSERVED, FORECAST}:
            kinds.append(PARTIAL)
        else:
            kinds.append(None)
    return kinds
