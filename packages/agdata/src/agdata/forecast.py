"""Forecast runs on the grid, stitched to the archive (PLAN.md Phase 4 B, C).

Each NBM run gets its own directory, laid out like the archive (`hourly/{year}.zarr`, `daily/…`, `cumulative/…`),
so the archive's rollup runs on it unchanged:

    {data_dir}/forecast/runs/{YYYYMMDDHH}/   one run: hourly, daily, cumulative stores and run.json
    {data_dir}/forecast/current              a symlink to the run readers use, swapped when a new one is complete

A run's hourly store is the stitched frame: the archive's hours up to its last observed hour (copied in with their
sources, so a run's days can be rolled up whole), then the run's forecast hours (`nbm`, soil `hrrr_forecast`, RH and
ET0 `derived`). Its daily store holds those days, so today mixes observed and forecast hours. Its running totals
continue the archive's: the archive's total on the day before the run's first day, plus the run's days. When the
archive gains hours, `stitch` copies them over the forecast's and rolls the affected days again. A reader opens one
run and keeps it, so it never mixes two.
"""

import json
import os
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import MAX_BRIDGE_DAYS, open_or_create_cumulative, running_totals
from agdata.daily import rollup_days
from agdata.grid import NDFD, Window
from agdata.ingest import open_or_create_hourly
from agdata.qc import check_range
from agdata.sources.nbm import HourlyRun
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore
from agmodels.weather import et0_hourly_series, relative_humidity_percent

HOUR = timedelta(hours=1)
PRESSURE_DAYS = 30  # the archive's days whose mean surface pressure stands in for the forecast's (NBM has none)
STITCH_HOURS_BEFORE = 48  # archive hours copied before the first forecast hour: the run's first day and its 8 pm


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


def last_observed_hour(data_dir: Path, before: datetime, lookback: timedelta = timedelta(days=14)) -> datetime | None:
    """The archive's last hour with temperature at or before `before`, looking back up to `lookback`."""
    t = before.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    stop = t - lookback
    while t > stop:
        try:
            store = GridStore.open(data_dir, HOURLY, t.year, VARIABLES.values(), add_missing=True)
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
    """Writes a run's forecast hours into its own directory (replacing any earlier attempt), then stitches it to
    the archive and rolls up its days. Not yet published: call `publish`."""
    path = run_path(data_dir, hourly.cycle)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    times = hourly.valid_times
    first = times[0]
    if pressure_kpa is None:
        pressure_kpa = archive_pressure_kpa(data_dir, window, first.date())
    pressure = np.broadcast_to(np.asarray(pressure_kpa, dtype=float), window.shape)

    values: dict[str, np.ndarray] = dict(hourly.values)
    sources: dict[str, str] = dict.fromkeys(values, "nbm")
    for name, series in (soil or {}).items():
        values[name] = series
        sources[name] = "hrrr_forecast"
    values["surface_pressure"] = np.broadcast_to(pressure, (len(times), *window.shape))
    sources["surface_pressure"] = "derived"
    values["relative_humidity"] = relative_humidity_percent(values["air_temperature"], values["dew_point"])
    lat, lon = NDFD.window_latlon(window)
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
    sources["relative_humidity"] = sources["et0"] = "derived"

    for year in range(first.year, times[-1].year + 1):
        store = open_or_create_hourly(path, year, window)
        begin = max(first, datetime(year, 1, 1, tzinfo=UTC))
        end = min(times[-1] + HOUR, datetime(year + 1, 1, 1, tzinfo=UTC))
        k0, k1 = (begin - first) // HOUR, (end - first) // HOUR
        for name, series in values.items():
            cleaned, _ = check_range(VARIABLES[name], series[k0:k1])
            store.write(begin, {name: cleaned}, source=None)
            store.set_sources(
                name, begin, [sources[name] if np.isfinite(cleaned[k]).any() else None for k in range(k1 - k0)]
            )
    info = {"cycle": hourly.cycle.isoformat(), "first_hour": first.isoformat(), "last_hour": times[-1].isoformat()}
    (path / "run.json").write_text(json.dumps(info, indent=2))
    stitch(data_dir, path, window)
    return path


def stitch(data_dir: Path, path: Path, window: Window) -> datetime | None:
    """Copies the archive's hours, up to its last observed one, over the run's; rolls up the run's days from the
    first one they touch and continues the archive's running totals through them. Returns the last observed hour
    (None: the archive has none in the two weeks before)."""
    info = run_info(path)
    first_forecast = datetime.fromisoformat(info["first_hour"])
    last_forecast = datetime.fromisoformat(info["last_hour"])
    observed = last_observed_hour(data_dir, min(last_forecast, datetime.now(UTC)))
    copy_from = first_forecast - STITCH_HOURS_BEFORE * HOUR
    if observed is not None and observed >= copy_from:
        _copy_archive_hours(data_dir, path, window, copy_from, observed)
    # The day after the first copied hour's: its hours, and its 8 pm-day from the evening before, are all copied in
    # every lower-48 zone. The last day may be partial (the rollup leaves its incomplete statistics missing).
    first_day = (copy_from + timedelta(hours=24)).date()
    last_day = last_forecast.date()
    rollup_days(path, window, first_day, last_day)
    _continue_totals(data_dir, path, window, first_day, last_day)
    info |= {"last_observed": observed.isoformat() if observed else None, "first_day": first_day.isoformat()}
    (path / "run.json").write_text(json.dumps(info, indent=2))
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
        for name in VARIABLES:
            values = archive.read_steps(name, t0, t1, window)
            store.write(begin, {name: values}, source=None)
            store.set_sources(name, begin, archive.sources(name)[t0:t1])


def _continue_totals(data_dir: Path, path: Path, window: Window, first_day: date, last_day: date) -> None:
    """The run's running totals for first_day..last_day: the archive's on the day before, plus the run's days
    (bridged across gaps with the archive's days before as neighbours, as the archive's own totals are)."""
    pad = MAX_BRIDGE_DAYS
    n = (last_day - first_day).days + 1
    names = ("air_temperature_min", "air_temperature_max", "et0_sum", "precipitation_sum", "et0_sum_estimate")
    series = {name: np.full((n + 2 * pad, *window.shape), np.nan, dtype=np.float32) for name in names}
    for name in names:
        series[name][:pad] = _read_days(data_dir, DAILY, name, first_day - timedelta(days=pad), pad, window)
        series[name][pad : pad + n] = _read_days(path, DAILY, name, first_day, n, window)
    totals = running_totals(*(series[name] for name in names))
    base_day = first_day - timedelta(days=1)
    for year in range(first_day.year, last_day.year + 1):
        store = open_or_create_cumulative(path, year, window)
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
        store.write(begin, out, source="derived")


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
