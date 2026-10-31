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
import requests
import zarr

from agdata import calibration, interpolate, shortwave
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import MAX_BRIDGE_DAYS, open_or_create_cumulative, running_totals
from agdata.daily import rollup_days
from agdata.gaps import FALLBACK_PRESSURE_KPA
from agdata.grid import NDFD, Window
from agdata.ingest import open_or_create_hourly
from agdata.qc import check_range
from agdata.sources import hrrr, nbm
from agdata.sources.nbm import HourlyRun
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore
from agmodels.weather import et0_hourly_series, relative_humidity_percent

HOUR = timedelta(hours=1)
PRESSURE_DAYS = 30  # the archive's days whose mean surface pressure stands in for the forecast's (NBM has none)
BAND_CELLS = 15_000  # cells per strip when building a run: ~1 GB at peak over 264 hours
# Sources of a run's forecast hours, by variable; the rest are NBM's
SOURCE_OF = {
    "soil_temperature_4cm": "hrrr_forecast",
    "soil_temperature_10cm": "hrrr_forecast",
    "soil_temperature_30cm": "hrrr_forecast",
    "surface_pressure": "derived",
    "relative_humidity": "derived",
    "et0": "derived",
}
STITCH_HOURS_BEFORE = 48  # archive hours copied before the first forecast hour: the run's first day and its 8 pm
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
    """Writes a run already filled to every hour (the whole window in memory) into its own directory, replacing
    any earlier attempt, then stitches it to the archive and rolls up its days. Not yet published: call `publish`.
    `build_run` does the same from NBM in strips of rows, for windows too large to hold."""
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


def band_rows(window: Window) -> int:
    """Rows per strip: about BAND_CELLS cells, so a strip's 264 hours of every variable fit in about a GB."""
    return max(1, min(window.shape[0], BAND_CELLS // window.shape[1]))


def build_run(
    data_dir: Path,
    window: Window,
    cycle: datetime,
    step: nbm.Step = nbm.fetch_step,
    soil_run: datetime | None = None,
    workers: int = 8,
    pressure_kpa: np.ndarray | float | None = None,
    session_factory=requests.Session,
) -> Path:
    """Fetches a long NBM run (and, from `soil_run`, HRRR's soil forecast) into the run's directory, fills its
    hours and derives the rest a strip of rows at a time, then stitches it to the archive and rolls up its days.

    The fetch writes each step straight to a scratch array chunked by step and strip, so threads never share a
    chunk and no step is held whole; the scratch is deleted once the strips are written."""
    path = _fresh_run_dir(data_dir, cycle)
    rows = band_rows(window)
    scratch = zarr.open_group(path / "scratch.zarr", mode="w")
    names = [*nbm.FETCHED, *(hrrr.SOIL_LEVELS if soil_run else ())]
    raw = {
        name: scratch.create_array(
            name,
            shape=(nbm.HORIZON_HOURS, *window.shape),
            chunks=(1, rows, window.shape[1]),
            dtype="float32",
            fill_value=np.nan,
        )
        for name in names
    }
    run = nbm.fetch_run(
        cycle, window, step=step, workers=workers, session_factory=session_factory, out={n: raw[n] for n in nbm.FETCHED}
    )
    times = run.valid_times
    if soil_run is not None:
        hrrr.fetch_soil_forecast(soil_run, times, window, session_factory=session_factory, workers=workers, out=raw)
    pressure = _pressure(data_dir, window, times[0], pressure_kpa)
    lat, lon = NDFD.window_latlon(window)
    present: dict[str, np.ndarray] = {}
    for j in range(window.j0, window.j1, rows):
        band = Window(j0=j, j1=min(j + rows, window.j1), i0=window.i0, i1=window.i1)
        y = slice(j - window.j0, band.j1 - window.j0)
        part = nbm.Run(cycle=cycle, values={n: np.asarray(raw[n][:, y]) for n in nbm.FETCHED})
        filled = adjust_hours(nbm.to_hourly(part, lat[y], lon[y], pressure[y]), lat[y], lon[y], pressure[y])
        soil = {n: np.asarray(raw[n][:, y]) for n in names if n not in nbm.FETCHED}
        for name, steps in _write_hours(path, window, band, times, filled.values, soil, pressure[y]).items():
            present[name] = present[name] | steps if name in present else steps
    shutil.rmtree(path / "scratch.zarr")
    _finish(data_dir, path, window, cycle, times, present, failed=run.failed)
    return path


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
) -> dict[str, np.ndarray]:
    """Derives pressure, RH and ET0 for a strip of the window's rows and writes every variable's hours; returns,
    per variable, which steps have any value (for the sources, set once every strip is written)."""
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
    first = times[0]
    for year in range(first.year, times[-1].year + 1):
        store = open_or_create_hourly(path, year, window)
        begin = max(first, datetime(year, 1, 1, tzinfo=UTC))
        end = min(times[-1] + HOUR, datetime(year + 1, 1, 1, tzinfo=UTC))
        k0, k1 = (begin - first) // HOUR, (end - first) // HOUR
        for name, series in values.items():
            cleaned, _ = check_range(VARIABLES[name], series[k0:k1])
            store.write(begin, {name: cleaned}, source=None, window=band)
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
    (path / "run.json").write_text(json.dumps(info, indent=2))
    stitch(data_dir, path, window)


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
