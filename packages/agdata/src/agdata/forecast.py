"""Forecast runs on the grid, stitched to the archive (Phase 4 B, C).

Each NBM run gets its own directory, laid out like the archive (`hourly/{year}.zarr`, `daily/…`, `cumulative/…`),
so the archive's rollup runs on it unchanged:

    {data_dir}/forecast/runs/{YYYYMMDDHH}/   one run: hourly, daily, cumulative stores and run.json
    {data_dir}/forecast/current              a symlink to the run readers use, swapped when a new one is complete

A run's hourly store is the stitched frame: the archive's hours up to its last observed hour (copied in with their
sources, so a run's days can be rolled up whole), then the run's forecast hours (`nbm`, soil and snow `ifs`, RH and
ET0 `derived`). Soil and snow reach the archive only when IFS or ERA5-Land is read, so they're copied only through the
archive's last hour of them, and the run's own IFS hours carry on from there (a gap otherwise, until the next read). Its daily store holds those days, so today mixes observed and forecast hours. Its running totals
continue the archive's: the archive's total on the day before the run's first day, plus the run's days. When the
archive gains hours, `stitch` copies them over the forecast's and rolls the affected days again. A reader opens one
run and keeps it, so it never mixes two.
"""

import json
import os
import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from functools import partial
from pathlib import Path

import numpy as np
import requests
import zarr

from agdata import blocks, calibration, chillseason, coverage, interpolate, modelmaps, shortwave
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import INPUTS, MAX_BRIDGE_DAYS, open_or_create_cumulative, running_totals
from agdata.daily import rollup_days
from agdata.gaps import FALLBACK_PRESSURE_KPA
from agdata.grid import NDFD, Window
from agdata.ingest import SOIL, open_or_create_hourly
from agdata.qc import check_range
from agdata.sources import nbm
from agdata.sources.nbm import HourlyRun
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore
from agdata.timezones import GRID_ZONE, first_reading
from agmodels.weather import et0_hourly_series, relative_humidity_percent

HOUR = timedelta(hours=1)
PRESSURE_DAYS = 30  # the archive's days whose mean surface pressure stands in for the forecast's (NBM has none)
PART_SIZE = 128  # cells a side of the parts a run is derived in: 16,384 cells, ~1.1 GB at peak over 264 hours
# Sources of a run's forecast hours, by variable; the rest are NBM's
SOURCE_OF = {
    **dict.fromkeys(SOIL, "ifs"),  # soil temperature, snow depth and soil moisture
    "surface_pressure": "derived",
    "relative_humidity": "derived",
    "et0": "derived",
}
STITCH_HOURS_BEFORE = 144  # archive hours copied before the first forecast hour: the run's first day and its windows (apple scab's reach 120 hours back, D96)
CALIBRATION = calibration.fitted()  # read when adjust_hours runs, so tests can swap it


def forecast_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "forecast"


def run_path(data_dir: Path, cycle: datetime) -> Path:
    return forecast_dir(data_dir) / "runs" / f"{cycle.astimezone(UTC):%Y%m%d%H}"


def current_run(data_dir: Path) -> Path | None:
    """The published run's directory, or None."""
    link = forecast_dir(data_dir) / "current"
    return link.resolve() if link.exists() else None


def run_info(path: Path) -> dict:
    """A run's run.json: cycle, first and last forecast hours, last observed hour, first rolled-up day."""
    return json.loads((path / "run.json").read_text())


def _write_info(path: Path, info: dict) -> None:
    """Writes run.json atomically: a request reading the published run while it's restitched sees the old file
    or the new one, never half of one."""
    partial = path / "run.json.part"
    partial.write_text(json.dumps(info, indent=2))
    partial.replace(path / "run.json")


def last_observed_hour(data_dir: Path, before: datetime, lookback: timedelta = timedelta(days=14)) -> datetime | None:
    """The archive's last hour with temperature at or before `before`, looking back up to `lookback`."""
    t = before.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    stop = t - lookback
    while t > stop:
        try:
            # only temperature's sources are read: opening for every variable checks each (~90 ms)
            store = GridStore.open(data_dir, HOURLY, t.year, [VARIABLES["air_temperature"]])
        except FileNotFoundError:
            t = datetime(t.year, 1, 1, tzinfo=UTC) - HOUR
            continue
        start = datetime(t.year, 1, 1, tzinfo=UTC)
        codes = store.read_meta("air_temperature.source")[: store.index_of(t) + 1]
        lo = max(0, int((stop - start) / HOUR))
        written = np.flatnonzero(codes[lo:] > 0)
        if written.size:
            return start + (lo + int(written[-1])) * HOUR
        t = start - HOUR
    return None


def archive_pressure_kpa(data_dir: Path, window: Window, before: date) -> np.ndarray:
    """Each cell's mean surface pressure over the archive's last PRESSURE_DAYS days before `before` (NaN: none)."""
    days = [before - timedelta(days=n) for n in range(1, PRESSURE_DAYS + 1)]
    total = np.zeros(window.shape)
    count = np.zeros(window.shape)
    for year in sorted({d.year for d in days}):
        try:
            store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
        except FileNotFoundError:
            continue
        in_year = sorted(d for d in days if d.year == year)
        t0 = store.index_of(in_year[0])
        values = store.read_steps("surface_pressure_mean", t0, t0 + len(in_year), window)
        total += np.nansum(values, axis=0)
        count += np.isfinite(values).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, total / count, np.nan)


def write_run(
    data_dir: Path,
    window: Window,
    hourly: HourlyRun,
    soil: dict[str, np.ndarray] | None = None,
    pressure_kpa: np.ndarray | float | None = None,
) -> Path:
    """Writes a run already filled to every hour (the whole window in memory) into its own directory, replacing
    any earlier attempt, then stitches it to the archive and rolls up its days. Not yet published: call `publish`.
    `build_run` does the same from NBM in parts, for windows too large to hold."""
    path = _fresh_run_dir(data_dir, hourly.cycle)
    times = hourly.valid_times
    pressure = _pressure(data_dir, window, times[0], pressure_kpa)
    lat, lon = NDFD.window_latlon(window)
    hourly = adjust_hours(hourly, lat, lon, pressure)
    present = _write_hours(path, window, window, times, dict(hourly.values), soil or {}, pressure)
    _finish(data_dir, path, window, hourly.cycle, times, present)
    return path


def adjust_hours(
    hourly: HourlyRun,
    latitude_deg,
    longitude_deg,
    pressure_kpa,
    adjustments: calibration.Adjustments | None = None,
) -> HourlyRun:
    """Post-processing of a run's filled hours, before RH and ET0 are derived from them (D39): each daytime
    window's hours reshaped to reach NBM's 12-hour max less the season's offset, each night's coldest hours
    lowered by the hours' warm bias at the min (the interpolated max runs cool and min warm), dew point kept at or
    below temperature, RH mapped onto the archive's (D49), and NBM's shortwave corrected by lead and clearness
    (D48, `agdata.shortwave`). The forecast job and the backtest both call it, so the backtest measures what's
    published. `adjustments` are the fitted tables (`CALIBRATION`, `agdata.calibration`) unless given; the
    backtest's fits leave steps out."""
    adjust = CALIBRATION if adjustments is None else adjustments
    times = np.array([t.replace(tzinfo=None) for t in hourly.valid_times], dtype="datetime64[s]")
    values = dict(hourly.values)
    if "tmax_12h" in hourly.extras:
        targets = calibration.max_targets(hourly.valid_times, hourly.extras["tmax_12h"], adjust.max_offset)
        values["air_temperature"] = interpolate.reach_window_max(values["air_temperature"], targets)
    if adjust.night_min is not None:
        targets = calibration.night_min_targets(
            hourly.cycle, hourly.valid_times, values["air_temperature"], adjust.night_min
        )
        values["air_temperature"] = interpolate.reach_window_min(values["air_temperature"], targets)
    with np.errstate(invalid="ignore"):
        values["dew_point"] = np.fmin(values["dew_point"], values["air_temperature"])
    if adjust.rh_map is not None:
        values["dew_point"] = calibration.map_humidity(
            hourly.cycle,
            hourly.valid_times,
            longitude_deg,
            values["air_temperature"],
            values["dew_point"],
            adjust.rh_map,
        )
    values["shortwave_radiation"] = shortwave.correct_nbm_w_m2(
        times, latitude_deg, longitude_deg, values["shortwave_radiation"], pressure_kpa, hourly.cycle
    )
    return HourlyRun(cycle=hourly.cycle, values=values, filled=hourly.filled, extras=hourly.extras)


def build_run(
    data_dir: Path,
    window: Window,
    cycle: datetime,
    step: nbm.Step = nbm.fetch_step,
    soil: Callable[[list[datetime], Window], dict[str, np.ndarray]] | None = None,
    workers: int = 8,
    pressure_kpa: np.ndarray | float | None = None,
    session_factory=requests.Session,
) -> Path:
    """Fetches a long NBM run into the run's directory (with `soil`'s soil and snow at its valid times: IFS's,
    D52), fills its hours and derives the rest in parts over the coverage (`parts`, in `agdata.blocks`' pool), then
    stitches it to the archive and rolls up its days.

    The fetch writes each step straight to a scratch array chunked by step and block, so threads never share a
    chunk and no step is held whole, and a part reads whole chunks; the scratch is deleted once the parts are
    written."""
    path = _fresh_run_dir(data_dir, cycle)
    scratch = zarr.open_group(path / "scratch.zarr", mode="w")
    names = [*nbm.FETCHED, *(SOIL if soil else ())]
    side = (min(blocks.SIZE, window.shape[0]), min(blocks.SIZE, window.shape[1]))
    raw = {
        name: scratch.create_array(
            name, shape=(nbm.HORIZON_HOURS, *window.shape), chunks=(1, *side), dtype="float32", fill_value=np.nan
        )
        for name in names
    }
    run = nbm.fetch_run(
        cycle, window, step=step, workers=workers, session_factory=session_factory, out={n: raw[n] for n in nbm.FETCHED}
    )
    times = run.valid_times
    if soil is not None:  # a day at a time: a run's every hour over the window is ~1 GB a variable
        for k in range(0, len(times), 24):
            for name, values in soil(times[k : k + 24], window).items():
                raw[name][k : k + len(values)] = values
    pressure = _pressure(data_dir, window, times[0], pressure_kpa)
    for year in range(times[0].year, times[-1].year + 1):
        open_or_create_hourly(path, year, window)  # made here, before a worker writes to one
    chains = [
        [(None, partial(_derive_part, path, window, cycle, times, names, pressure[_local(window, part)], part))]
        for part in parts(window)
    ]
    present: dict[str, np.ndarray] = {}

    def handle(_, found: dict[str, np.ndarray]) -> None:
        for name, steps in found.items():
            present[name] = present[name] | steps if name in present else steps

    blocks.run(chains, handle)
    for year in range(times[0].year, times[-1].year + 1):  # the workers wrote the values only
        store = open_or_create_hourly(path, year, window)
        begin, k0, k1 = _year_steps(times, year)
        store.record(present, begin, k1 - k0, source=None)
    shutil.rmtree(path / "scratch.zarr")
    _finish(data_dir, path, window, cycle, times, present, failed=run.failed)
    return path


def parts(window: Window) -> list[Window]:
    """The parts a run's hours are derived in: `agdata.blocks`' blocks (over the coverage only, largest first) in
    squares of PART_SIZE, those with a covered cell."""
    return [
        square
        for block in blocks.blocks(window)
        for square in coverage.parts(block, PART_SIZE)
        if coverage.covered(window, square).any()
    ]


def _local(window: Window, part: Window) -> tuple[slice, slice]:
    return slice(part.j0 - window.j0, part.j1 - window.j0), slice(part.i0 - window.i0, part.i1 - window.i0)


def _year_steps(times: list[datetime], year: int) -> tuple[datetime, int, int]:
    """The run's first hour in `year` and its steps k0..k1 there."""
    first = times[0]
    begin = max(first, datetime(year, 1, 1, tzinfo=UTC))
    end = min(times[-1] + HOUR, datetime(year + 1, 1, 1, tzinfo=UTC))
    return begin, (begin - first) // HOUR, (end - first) // HOUR


def _derive_part(
    path: Path,
    window: Window,
    cycle: datetime,
    times: list[datetime],
    names: list[str],
    pressure: np.ndarray,
    part: Window,
) -> dict[str, np.ndarray]:
    """One part of a run (a task for `blocks.run`): its fetched hours from the scratch, filled, adjusted and
    derived, its values written (not recorded); returns which steps of each variable have a value."""
    scratch = zarr.open_group(path / "scratch.zarr", mode="r")
    y, x = _local(window, part)
    raw = {name: np.asarray(scratch[name][:, y, x]) for name in names}  # type: ignore[index]
    lat, lon = NDFD.window_latlon(part)
    run = nbm.Run(cycle=cycle, values={n: raw[n] for n in nbm.FETCHED})
    filled = adjust_hours(nbm.to_hourly(run, lat, lon, pressure), lat, lon, pressure)
    soil = {n: raw[n] for n in names if n not in nbm.FETCHED}
    return _write_hours(path, window, part, times, filled.values, soil, pressure, record=False)


def _fresh_run_dir(data_dir: Path, cycle: datetime) -> Path:
    path = run_path(data_dir, cycle)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _pressure(data_dir: Path, window: Window, first: datetime, pressure_kpa) -> np.ndarray:
    """The run's surface pressure: given, or the archive's recent mean; where neither has one (a cell or a window
    the archive doesn't reach back to), a typical value, so shortwave and ET0 aren't lost for want of it."""
    if pressure_kpa is None:
        pressure_kpa = archive_pressure_kpa(data_dir, window, first.date())
    pressure = np.broadcast_to(np.asarray(pressure_kpa, dtype=float), window.shape)
    return np.where(np.isfinite(pressure), pressure, FALLBACK_PRESSURE_KPA)


def _write_hours(
    path: Path,
    window: Window,
    band: Window,
    times: list[datetime],
    values: dict[str, np.ndarray],
    soil: dict[str, np.ndarray],
    pressure: np.ndarray,
    record: bool = True,
) -> dict[str, np.ndarray]:
    """Derives pressure, RH and ET0 over a part of the window and writes every variable's hours (`record`: their
    write times too); returns, per variable, which steps have any value (for the sources, set once every part is
    written)."""
    values = dict(values) | dict(soil)
    values["surface_pressure"] = np.broadcast_to(pressure, (len(times), *band.shape))
    values["relative_humidity"] = relative_humidity_percent(values["air_temperature"], values["dew_point"])
    lat, lon = NDFD.window_latlon(band)
    with np.errstate(invalid="ignore"):
        values["et0"] = et0_hourly_series(
            np.array([t.replace(tzinfo=None) for t in times], dtype="datetime64[s]"),
            lat,
            lon,
            values["air_temperature"],
            values["dew_point"],
            values["wind_speed"],
            values["surface_pressure"],
            values["shortwave_radiation"],
        )
    present: dict[str, np.ndarray] = {}
    for year in range(times[0].year, times[-1].year + 1):
        store = open_or_create_hourly(path, year, window)
        begin, k0, k1 = _year_steps(times, year)
        for name, series in values.items():
            cleaned, _ = check_range(VARIABLES[name], series[k0:k1])
            store.write(begin, {name: cleaned}, source=None, window=band, record=record)
            steps = np.isfinite(cleaned).reshape(k1 - k0, -1).any(axis=1)
            present.setdefault(name, np.zeros(len(times), dtype=bool))[k0:k1] |= steps
    return present


def _finish(
    data_dir: Path,
    path: Path,
    window: Window,
    cycle: datetime,
    times: list[datetime],
    present: dict[str, np.ndarray],
    failed: list[int] | None = None,
) -> None:
    """Records each variable's source per step and the run's times, then stitches it to the archive."""
    first = times[0]
    for year in range(first.year, times[-1].year + 1):
        store = open_or_create_hourly(path, year, window)
        begin = max(first, datetime(year, 1, 1, tzinfo=UTC))
        end = min(times[-1] + HOUR, datetime(year + 1, 1, 1, tzinfo=UTC))
        k0, k1 = (begin - first) // HOUR, (end - first) // HOUR
        for name, steps in present.items():
            source = SOURCE_OF.get(name, "nbm")
            store.set_sources(name, begin, [source if steps[k] else None for k in range(k0, k1)])
    info = {
        "cycle": cycle.isoformat(),
        "first_hour": first.isoformat(),
        "last_hour": times[-1].isoformat(),
        "failed_leads": failed or [],
    }
    _write_info(path, info)
    stitch(data_dir, path, window)


def stitch(data_dir: Path, path: Path, window: Window) -> datetime | None:
    """Copies the archive's hours, up to its last observed one, over the run's; rolls up the run's days from the first
    one they touch and continues the archive's running totals and the models' ingredients through them. Returns the last
    observed hour (None: the archive has none in the two weeks before)."""
    info = run_info(path)
    first_forecast = datetime.fromisoformat(info["first_hour"])
    last_forecast = datetime.fromisoformat(info["last_hour"])
    observed = last_observed_hour(data_dir, min(last_forecast, datetime.now(UTC)))
    copy_from = first_forecast - STITCH_HOURS_BEFORE * HOUR
    if observed is not None and observed >= copy_from:
        _copy_archive_hours(data_dir, path, window, copy_from, observed)
    # The first grid day whose every window (back to apple scab's 120 hours) is copied in. The last day may be partial
    # (the rollup leaves its incomplete statistics missing).
    first_day = copy_from.date()
    while first_reading(first_day, GRID_ZONE) < copy_from:
        first_day += timedelta(days=1)
    last_day = last_forecast.date()
    rollup_days(path, window, first_day, last_day)
    _continue_totals(data_dir, path, window, first_day, last_day)
    chillseason.update(path, window, first_day, last_day, base_dir=data_dir)  # the archive's chill, carried on
    modelmaps.update(data_dir, window, first_day, last_day, run=path, run_first=first_day)
    info |= {"last_observed": observed.isoformat() if observed else None, "first_day": first_day.isoformat()}
    _write_info(path, info)
    return observed


def publish(data_dir: Path, path: Path, keep: int = 2) -> None:
    """Points `current` at the run (an atomic rename of a new symlink) and deletes all but the newest `keep` runs."""
    root = forecast_dir(data_dir)
    tmp = root / "current.tmp"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(path.relative_to(root))
    os.replace(tmp, root / "current")
    runs = sorted((root / "runs").iterdir())
    for old in runs[:-keep]:
        if old.resolve() != path.resolve():
            shutil.rmtree(old)


def _copy_archive_hours(data_dir: Path, path: Path, window: Window, start: datetime, last: datetime) -> None:
    for year in range(start.year, last.year + 1):
        try:
            archive = GridStore.open(data_dir, HOURLY, year, VARIABLES.values(), add_missing=True)
        except FileNotFoundError:
            continue
        store = open_or_create_hourly(path, year, window)
        begin = max(start, datetime(year, 1, 1, tzinfo=UTC))
        end = min(last + HOUR, datetime(year + 1, 1, 1, tzinfo=UTC))
        t0, t1 = archive.index_of(begin), archive.index_of(end - HOUR) + 1
        part = coverage.extent(window)  # outside it the hours are missing in both
        for name in VARIABLES:  # as stored: the same variables, packed the same way
            stop = t1
            if name in SOIL:  # through the archive's last hour of them: the run's own IFS hours carry on from there
                held = np.flatnonzero(archive.has_data(name, t0, t1))
                stop = t0 + (int(held[-1]) + 1 if held.size else 0)
            if stop > t0:
                store.write_packed(begin, name, archive.read_packed(name, t0, stop, window=part), window=part)
                store.set_sources(name, begin, archive.sources(name, t0, stop))


def _continue_totals(data_dir: Path, path: Path, window: Window, first_day: date, last_day: date) -> None:
    """The run's running totals for first_day..last_day: the archive's on the day before, plus the run's days
    (bridged across gaps with the archive's days before as neighbours, as the archive's own totals are)."""
    pad = MAX_BRIDGE_DAYS
    n = (last_day - first_day).days + 1
    names = INPUTS
    store_window, window = window, coverage.extent(window)  # outside it every day is missing
    series = {name: np.full((n + 2 * pad, *window.shape), np.nan, dtype=np.float32) for name in names}
    for name in names:
        series[name][:pad] = _read_days(data_dir, DAILY, name, first_day - timedelta(days=pad), pad, window)
        series[name][pad : pad + n] = _read_days(path, DAILY, name, first_day, n, window)
    totals = running_totals(*(series[name] for name in names))
    base_day = first_day - timedelta(days=1)
    for year in range(first_day.year, last_day.year + 1):
        store = open_or_create_cumulative(path, year, store_window)
        begin = max(first_day, date(year, 1, 1))
        end = min(last_day, date(year, 12, 31))
        k0, k1 = (begin - first_day).days, (end - first_day).days + 1
        out = {}
        for name, values in totals.items():
            if year == first_day.year:
                # The archive's total on the day before (none when the run starts on January 1)
                base = _read_days(data_dir, CUMULATIVE, name, base_day, 1, window)[0] if base_day.year == year else 0.0
                out[name] = values[k0:k1] + base
            else:  # totals restart on January 1
                out[name] = values[k0:k1] - values[(date(year, 1, 1) - first_day).days - 1]
        store.write(begin, out, source="derived", window=window)


def _read_days(data_dir: Path, layout, name: str, first: date, n: int, window: Window) -> np.ndarray:
    """Days first..first + n − 1 of a daily-step store across years, NaN where none is stored."""
    variables = DAILY_VARIABLES if layout is DAILY else CUMULATIVE_VARIABLES
    out = np.full((n, *window.shape), np.nan, dtype=np.float32)
    days = [first + timedelta(days=k) for k in range(n)]
    for year in sorted({d.year for d in days}):
        try:
            store = GridStore.open(data_dir, layout, year, variables.values(), add_missing=True)
        except FileNotFoundError:
            continue
        in_year = [k for k, d in enumerate(days) if d.year == year]
        t0 = store.index_of(days[in_year[0]])
        out[in_year[0] : in_year[-1] + 1] = store.read_steps(name, t0, t0 + len(in_year), window)
    return out
