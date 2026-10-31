"""Backtest of the NBM forecast against the archive (PLAN.md Phase 4 G).

For the 13z long run on every 5th day of a period, fetches NBM at one cell per old-API 0.1° point in Central time
(`compare_legacy.central_points`), fills its hours as the forecast job does (`nbm.to_hourly`, then RH and ET0), and
rolls up lead days 1–10 (the complete local days after the cycle) with `daily_at_point`. Compares them with the
archive's daily store, and the first forecast hours with the archive's hours (the seam). NBM's own 12-hour TMAX
and TMIN are kept beside the hours' extremes, to settle D39.

Each run's values are cached in tmp/backtest/{cycle}.npz, and its filled hours in {cycle}_hours.npz, so a restart
resumes. `--report` writes the report from the cache without fetching; `--rescore` first replays the cached hours
through the current post-processing (`derive`), for a change to it that needs no new fetch.

    uv run python scripts/backtest_forecast.py --start 2025-01-01 --end 2025-12-31
    uv run python scripts/backtest_forecast.py --start 2025-01-01 --end 2025-12-31 --rescore
"""

import argparse
import itertools
import json
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_legacy import central_points

from agdata import calibration
from agdata.calibration import Adjustments
from agdata.catalog import DAILY_VARIABLES, VARIABLES, variable
from agdata.forecast import adjust_hours, archive_pressure_kpa
from agdata.gaps import FALLBACK_PRESSURE_KPA, clear_sky_shortwave_w_m2
from agdata.grid import NDFD, Window, service_window
from agdata.point import daily_at_point
from agdata.qc import check_range
from agdata.shortwave import NBM_TABLE_PATH
from agdata.sources import nbm
from agdata.sources.grib import MessageRef, RemoteGrib, place
from agdata.store import DAILY, HOURLY, GridStore
from agdata.units import convert
from agmodels.degree_days import degree_days_sine
from agmodels.weather import et0_hourly_series, relative_humidity_percent

HOUR = timedelta(hours=1)
ZONE = "America/Chicago"
CENTRAL = ZoneInfo(ZONE)
LEAD_DAYS = 10
SEAM_HOURS = 6
CACHE = Path("tmp/backtest")
COMPARED = (
    "air_temperature_min",
    "air_temperature_max",
    "dew_point_mean",
    "precipitation_sum",
    "relative_humidity_mean",
    "hours_rh_over_80",
    "hours_rh_over_90",
    "hours_rh_over_90_night",
    "wind_speed_mean",
    "shortwave_radiation_sum",
    "et0_sum",
)
EXTREMES = {("TMAX", "2 m above ground"): ("tmax_nbm", "max"), ("TMIN", "2 m above ground"): ("tmin_nbm", "min")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last cycle day, inclusive")
    parser.add_argument("--every", type=int, default=5, help="days between cycles")
    parser.add_argument("--hour", type=int, default=13, help="the cycle's UTC hour (a long run)")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--report", action="store_true", help="write the report from the cache, fetching nothing")
    parser.add_argument(
        "--fit-shortwave", action="store_true", help="fit NBM's shortwave correction from the cache (D48)"
    )
    parser.add_argument(
        "--fit-calibration", action="store_true", help="fit the forecast's calibration from the cached hours (D39, D49)"
    )
    parser.add_argument(
        "--rescore", action="store_true", help="replay the cached hours through `derive`, then write the report"
    )
    parser.add_argument(
        "--refresh-observed", action="store_true", help="reread the archive's side of cached runs (after a rebuild)"
    )
    parser.add_argument("--out", default="docs/validation-forecast.md")
    args = parser.parse_args()
    first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    cycles = [
        datetime(d.year, d.month, d.day, args.hour, tzinfo=UTC)
        for d in (first + timedelta(days=n) for n in range(0, (last - first).days + 1, args.every))
    ]
    data_dir = Path(args.data)
    window = service_window(args.box)
    CACHE.mkdir(parents=True, exist_ok=True)

    if args.fit_shortwave:
        Path("docs/validation-forecast-shortwave.md").write_text(fit_shortwave(cycles))
        print("wrote docs/validation-forecast-shortwave.md and the NBM table", flush=True)
        return
    if args.fit_calibration:
        Path("docs/validation-forecast-calibration.md").write_text(fit_calibration(Path(args.data), cycles, window))
        print("wrote docs/validation-forecast-calibration.md and the calibration tables", flush=True)
        return
    if args.rescore:
        lat, lon = cell_latlon(window)
        rescored = [c for c in cycles if cache_path(c).exists() and hours_path(c).exists()]
        for cycle in rescored:
            cached = dict(np.load(cache_path(cycle))) | replay(cycle, lat, lon)
            np.savez_compressed(cache_path(cycle), **cast(dict[str, Any], cached))
        print(f"replayed {len(rescored)} runs", flush=True)
    elif args.refresh_observed:
        _, js, is_ = point_cells(data_dir, window)
        for cycle in cycles:
            if cache_path(cycle).exists():
                refresh_observed(data_dir, window, cycle, js - window.j0, is_ - window.i0)
        print(f"refreshed the archive's side of {sum(cache_path(c).exists() for c in cycles)} runs", flush=True)
    elif not args.report:
        points, js, is_ = point_cells(data_dir, window)
        np.savez(CACHE / "cells.npz", j=js, i=is_)
        print(f"{len(points)} points, {len(cycles)} cycles", flush=True)
        for cycle in cycles:
            if cache_path(cycle).exists() and hours_path(cycle).exists():
                continue
            began = time.monotonic()
            result, hours = backtest_run(data_dir, window, cycle, js, is_, args.workers)
            np.savez_compressed(cache_path(cycle), **cast(dict[str, Any], result))  # pyright reads the names as flags
            np.savez_compressed(hours_path(cycle), **cast(dict[str, Any], hours))
            failed = len(result["failed_leads"])
            print(f"{cycle:%Y-%m-%d %HZ}: {time.monotonic() - began:.0f} s, {failed} failed leads", flush=True)

    Path(args.out).write_text(report(args, cycles))
    print(f"wrote {args.out}")


def cache_path(cycle: datetime) -> Path:
    return CACHE / f"{cycle:%Y%m%d%H}.npz"


def hours_path(cycle: datetime) -> Path:
    """The run's filled hours at the cells (264 × cells per variable, float32) and NBM's raw TMAX/TMIN by lead,
    for trying adjustments to the forecast without fetching it again."""
    return CACHE / f"{cycle:%Y%m%d%H}_hours.npz"


def cached_run(cycle: datetime) -> tuple[nbm.HourlyRun, np.ndarray]:
    """A run's filled hours from its cache (`hours_path`) as `nbm.to_hourly` returned them, with NBM's TMAX as the
    job fetches it, and the cells' pressure (1, cells). Older caches also hold RH and ET0, which are dropped."""
    h = np.load(hours_path(cycle))
    values = {name: h[name][:, None].astype(float) for name in nbm.NAMES}
    pressure = h["surface_pressure"]
    pressure = (pressure[0] if pressure.ndim == 2 else pressure)[None].astype(float)  # older caches: per hour
    pressure = np.where(np.isfinite(pressure), pressure, FALLBACK_PRESSURE_KPA)
    run = nbm.HourlyRun(
        cycle=cycle,
        values=values,
        filled={name: np.zeros(v.shape, dtype=bool) for name, v in values.items()},
        extras={"tmax_12h": h["raw_tmax_nbm"][:, None].astype(float)},
    )
    return run, pressure


def cell_latlon(window: Window) -> tuple[np.ndarray, np.ndarray]:
    """The cached cells' latitude and longitude, (1, cells)."""
    cells = np.load(CACHE / "cells.npz")
    lat, lon = NDFD.window_latlon(window)
    y, x = cells["j"] - window.j0, cells["i"] - window.i0
    return lat[y, x][None, :], lon[y, x][None, :]


def refresh_observed(data_dir: Path, window: Window, cycle: datetime, y, x) -> None:
    cached = dict(np.load(cache_path(cycle)))
    day1 = (cycle + timedelta(days=1)).date()
    observed = read_days(data_dir, window, [day1 + timedelta(days=k) for k in range(LEAD_DAYS)], y, x)
    for name in COMPARED:
        cached[f"obs_{name}"] = observed[name]
    archive_hours = read_hours(data_dir, window, cycle + HOUR, SEAM_HOURS, y, x)
    for name in ("air_temperature", "dew_point"):
        cached[f"seam_obs_{name}"] = archive_hours[name]
    np.savez_compressed(cache_path(cycle), **cast(dict[str, Any], cached))


def point_cells(data_dir: Path, window: Window) -> tuple[list[str], np.ndarray, np.ndarray]:
    """One cell per old-API point: its cell nearest the point (grid indices j, i)."""
    points, labels = central_points(data_dir, window)
    lat, lon = NDFD.window_latlon(window)
    js, is_ = np.zeros(len(points), dtype=int), np.zeros(len(points), dtype=int)
    for k, key in enumerate(points):
        plat, plon = (float(v) for v in key.strip("[]").split(","))
        y, x = np.nonzero(labels == k)
        nearest = np.argmin((lat[y, x] - plat) ** 2 + (lon[y, x] - plon) ** 2)
        js[k], is_[k] = y[nearest] + window.j0, x[nearest] + window.i0
    return points, js, is_


def backtest_run(
    data_dir: Path, window: Window, cycle: datetime, js, is_, workers: int
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """One run at the cells: its lead days and the archive's, NBM's TMAX/TMIN by day, and the seam hours; and its
    filled hours (`hours_path`)."""
    n = len(js)
    y, x = js - window.j0, is_ - window.i0
    cells = Window(j0=0, j1=1, i0=0, i1=n)  # the run's arrays hold the cells as one row

    def step(cycle: datetime, lead: int, _: Window, session) -> dict[str, np.ndarray]:
        grib = RemoteGrib(nbm.url(cycle, lead), session)
        values: dict[str, np.ndarray] = {}
        for ref, found in grib.iter_fields_where(lambda ref: wanted(ref, lead) is not None):
            name = wanted(ref, lead)
            if name is None or name in values:
                continue
            field = place(found, window)[y, x][None, :]
            if name == "precipitation":
                unit = "kg_m2"
            elif name in ("tmax_nbm", "tmin_nbm"):
                unit = "K"
            else:
                unit = nbm.FIELDS[ref.key][1]
            values[name] = convert(field, unit, "degC" if name.endswith("_nbm") else variable(name).unit)
        return values

    raw = {
        name: np.full((nbm.HORIZON_HOURS, 1, n), np.nan, dtype=np.float32)
        for name in (*nbm.NAMES, "tmax_nbm", "tmin_nbm")
    }
    run = nbm.fetch_run(cycle, cells, step=step, workers=workers, out=raw)
    lat, lon = NDFD.window_latlon(window)
    lat, lon = lat[y, x][None, :], lon[y, x][None, :]
    pressure = archive_pressure_kpa(data_dir, window, cycle.date())[y, x][None, :]
    pressure = np.where(np.isfinite(pressure), pressure, FALLBACK_PRESSURE_KPA)  # as the forecast job does
    run_values = {k: raw[k] for k in nbm.NAMES} | {"tmax_12h": raw["tmax_nbm"]}  # as the job fetches it (D39)
    filled = nbm.to_hourly(nbm.Run(cycle=cycle, values=run_values), lat, lon, pressure)
    times = filled.valid_times
    values = derive(filled, lat, lon, pressure)

    day1 = (cycle + timedelta(days=1)).date()  # the 13z cycle is morning in Central time: day 0 is partial
    days = [day1 + timedelta(days=k) for k in range(LEAD_DAYS)]
    out: dict[str, np.ndarray] = {}
    forecast = roll_up(times[0], values, days, COMPARED)
    out["fc_raw_shortwave_radiation_sum"] = roll_up(
        times[0], {"shortwave_radiation": filled.values["shortwave_radiation"]}, days, ("shortwave_radiation_sum",)
    )["shortwave_radiation_sum"]
    observed = read_days(data_dir, window, days, y, x)
    for name in COMPARED:
        out[f"fc_{name}"], out[f"obs_{name}"] = forecast[name], observed[name]

    # NBM's extremes by local day: TMAX over 12–00Z (the day's daytime), TMIN over 00–12Z (the night before it)
    for name, hour_end in (("tmax_nbm", 24), ("tmin_nbm", 12)):
        by_day = np.full((LEAD_DAYS, n), np.nan)
        for k, day in enumerate(days):
            lead = (datetime(day.year, day.month, day.day, tzinfo=UTC) + hour_end * HOUR - cycle) // HOUR
            if 1 <= lead <= nbm.HORIZON_HOURS:
                by_day[k] = raw[name][lead - 1, 0]
        out[name] = by_day

    # The seam: the first forecast hours against the archive's
    archive_hours = read_hours(data_dir, window, times[0], SEAM_HOURS, y, x)
    for name in ("air_temperature", "dew_point"):
        out[f"seam_fc_{name}"] = values[name][:SEAM_HOURS, 0]
        out[f"seam_obs_{name}"] = archive_hours[name]
    out["failed_leads"] = np.array(run.failed, dtype=int)
    hours = {name: np.asarray(series[:, 0], dtype=np.float32) for name, series in filled.values.items()}
    hours["surface_pressure"] = np.asarray(pressure[0], dtype=np.float32)
    hours |= {f"raw_{name}": np.asarray(raw[name][:, 0], dtype=np.float32) for name in ("tmax_nbm", "tmin_nbm")}
    out["month"] = np.array(cycle.month)
    return out, hours


SHORTWAVE_GROUPS = [[1], [2, 3], [4, 5, 6], [7, 8, 9, 10]]  # lead days sharing a table
SHORTWAVE_EDGES = np.linspace(0, 1.2, 13)  # the forecast day's clearness
SHORTWAVE_MIN_DAYS = 2000  # cell-days a bin needs; thinner bins take their neighbours' factor


def fit_shortwave(cycles: list[datetime]) -> str:
    """NBM's shortwave correction by lead group and the forecast day's clearness: the archive's total over the raw
    forecast's in each bin. Fitted on alternate runs and tested on the rest, then on every run for the table."""
    cells = np.load(CACHE / "cells.npz")
    window = service_window("wisconsin")
    lat, lon = NDFD.window_latlon(window)
    lat, lon = lat[cells["j"] - window.j0, cells["i"] - window.i0], lon[cells["j"] - window.j0, cells["i"] - window.i0]
    runs = [c for c in cycles if cache_path(c).exists()]
    raw, observed, clear = [], [], []
    for cycle in runs:
        cached = np.load(cache_path(cycle))
        key = (
            "fc_raw_shortwave_radiation_sum"
            if "fc_raw_shortwave_radiation_sum" in cached
            else "fc_shortwave_radiation_sum"
        )
        raw.append(cached[key])
        observed.append(cached["obs_shortwave_radiation_sum"])
        day1 = (cycle + timedelta(days=1)).date()
        clear.append([clear_sky_day(day1 + timedelta(days=k), lat, lon) for k in range(LEAD_DAYS)])
    fc, obs, rso = np.array(raw), np.array(observed), np.array(clear)
    clearness = fc / rso
    ok = np.isfinite(fc) & np.isfinite(obs)
    middles = (SHORTWAVE_EDGES[:-1] + SHORTWAVE_EDGES[1:]) / 2

    def tables(use: np.ndarray) -> list[np.ndarray]:
        out = []
        for group in SHORTWAVE_GROUPS:
            leads = np.isin(np.arange(1, LEAD_DAYS + 1), group)[None, :, None]
            factor = []
            for lo, hi in itertools.pairwise(SHORTWAVE_EDGES):
                m = use[:, None, None] & leads & ok & (clearness >= lo) & (clearness < hi)
                factor.append(obs[m].sum() / fc[m].sum() if m.sum() >= SHORTWAVE_MIN_DAYS else np.nan)
            factor = np.array(factor)
            good = np.isfinite(factor)
            out.append(np.interp(middles, middles[good], factor[good]))
        return out

    def apply(table: list[np.ndarray]) -> np.ndarray:
        corrected = np.empty_like(fc)
        for group, factor in zip(SHORTWAVE_GROUPS, table, strict=True):
            for lead in group:
                corrected[:, lead - 1] = fc[:, lead - 1] * np.interp(clearness[:, lead - 1], middles, factor)
        return corrected

    index = np.arange(len(runs))
    fit, test = index % 2 == 0, index % 2 == 1
    held_out = apply(tables(fit))
    final = tables(np.ones(len(runs), dtype=bool))
    NBM_TABLE_PATH.write_text(
        json.dumps(
            {
                "version": 1,
                "fitted": f"{datetime.now(UTC):%Y-%m-%d}",
                "source": f"backtest of {len(runs)} 13z runs, {runs[0]:%Y-%m-%d} to {runs[-1]:%Y-%m-%d}, against the "
                "corrected archive",
                "clearness": middles.round(3).tolist(),
                "lead_days": SHORTWAVE_GROUPS,
                "factor": [[round(float(f), 4) for f in t] for t in final],
            },
            indent=2,
        )
        + "\n"
    )
    lines = [
        "# NBM shortwave correction",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/backtest_forecast.py --fit-shortwave` (D48). The raw "
        f"forecast's daily shortwave (NBM's DSWRF by solar-day clearness) at {fc.shape[2]} cells in {len(runs)} runs, "
        "against the archive (HRRR corrected against Wisconet). Factors by lead group and the forecast day's clearness "
        "(its total over the FAO-56 clear-sky total); bins with fewer than "
        f"{SHORTWAVE_MIN_DAYS} cell-days take their neighbours'. Most of it is calibration: as skill falls with lead, "
        "a forecast very dark or very clear day turns out less so.",
        "",
        "| Lead days | " + " | ".join(f"{m:.2f}" for m in middles) + " |",
        "|---|" + "---|" * len(middles),
        *(
            f"| {g[0]}–{g[-1]} | " + " | ".join(f"{f:.2f}" for f in t) + " |"
            for g, t in zip(SHORTWAVE_GROUPS, final, strict=True)
        ),
        "",
        "Fitted on alternate runs, tested on the others (bias / MAE, MJ/m² a day, by lead day):",
        "",
        "| | " + " | ".join(f"day {k + 1}" for k in range(LEAD_DAYS)) + " | ratio |",
        "|---|" + "---|" * (LEAD_DAYS + 1),
    ]
    for label, values in (("raw", fc), ("corrected", held_out)):
        cells_ = [errors(values[test, k], obs[test, k]) for k in range(LEAD_DAYS)]
        m = ok[test]
        ratio = values[test][m].sum() / obs[test][m].sum()
        lines.append(f"| {label} | " + " | ".join(f"{b:+.2f} / {e:.2f}" for b, e in cells_) + f" | {ratio:.3f} |")
    lines.append("")
    return "\n".join(lines)


def clear_sky_day(day: date, lat, lon) -> np.ndarray:
    """Each cell's FAO-56 clear-sky total (MJ/m²) over the Central-time day's hours ending 01:00–24:00."""
    start = datetime(day.year, day.month, day.day, 1, tzinfo=CENTRAL).astimezone(UTC)
    times = np.array([(start + k * HOUR).replace(tzinfo=None) for k in range(24)], dtype="datetime64[s]")
    return (
        clear_sky_shortwave_w_m2(times, lat, lon, np.full((24, *np.shape(lat)), FALLBACK_PRESSURE_KPA)).sum(0) * 0.0036
    )


def derive(filled: nbm.HourlyRun, lat, lon, pressure, adjustments: Adjustments | None = None) -> dict[str, np.ndarray]:
    """A run's filled hours as the forecast job publishes them: post-processed (`forecast.adjust_hours`), then
    pressure, RH and ET0 derived and the range checks applied."""
    hourly = adjust_hours(filled, lat, lon, pressure, adjustments)
    values = dict(hourly.values)
    values["surface_pressure"] = np.broadcast_to(pressure, values["air_temperature"].shape)
    values["relative_humidity"] = relative_humidity_percent(values["air_temperature"], values["dew_point"])
    with np.errstate(invalid="ignore"):
        values["et0"] = et0_hourly_series(
            np.array([t.replace(tzinfo=None) for t in hourly.valid_times], dtype="datetime64[s]"),
            lat,
            lon,
            values["air_temperature"],
            values["dew_point"],
            values["wind_speed"],
            values["surface_pressure"],
            values["shortwave_radiation"],
        )
    return {name: check_range(VARIABLES[name], series)[0] for name, series in values.items()}


def replay(cycle: datetime, lat, lon, adjustments: Adjustments | None = None) -> dict[str, np.ndarray]:
    """A cached run's forecast days and seam hours (the `fc_` and `seam_fc_` values of its cache) from its cached
    hours through `derive`."""
    run, pressure = cached_run(cycle)
    values = derive(run, lat, lon, pressure, adjustments)
    day1 = (cycle + timedelta(days=1)).date()
    days = [day1 + timedelta(days=k) for k in range(LEAD_DAYS)]
    forecast = roll_up(run.valid_times[0], values, days, COMPARED)
    out = {f"fc_{name}": forecast[name] for name in COMPARED}
    for name in ("air_temperature", "dew_point"):
        out[f"seam_fc_{name}"] = values[name][:SEAM_HOURS, 0]
    return out


SCORED = (
    "air_temperature_max",
    "air_temperature_min",
    "hours_rh_over_80",
    "hours_rh_over_90",
    "hours_rh_over_90_night",
)
SEASON_DAYS = [15, 105, 196, 288]  # mid-January, April, July and October: the tables' seasons, DJF … SON
RH_LEAD_GROUP_ENDS = [72, 144]  # lead hours: 1–72, 73–144, 145 on
RH_LEAD_HOURS = [36, 108, 204]  # their middles, between which the maps are blended
RH_EVERY = 2  # every other cell for the RH fit (memory)
RH_QUANTILES = np.linspace(0, 1, 201)


def fit_calibration(data_dir: Path, cycles: list[datetime], window: Window) -> str:
    """The forecast's calibration (`agdata.calibration`), fitted in order, each step on the forecast with the steps
    before it applied: the max offset by season (lead days 1–3), the night min's warm bias by lead, then the RH
    maps by season, lead group and solar hour. Each is checked by 2-fold cross-validation (fitted on alternate
    runs, applied to the others) before it's fitted on every run for its table."""
    lat, lon = cell_latlon(window)
    runs = [c for c in cycles if cache_path(c).exists() and hours_path(c).exists()]
    if any(c.hour != runs[0].hour for c in runs):
        raise ValueError("fit runs of one cycle hour")
    observed = [np.load(cache_path(c)) for c in runs]
    obs = {name: np.array([o[f"obs_{name}"] for o in observed]) for name in SCORED}
    fold = np.arange(len(runs)) % 2
    day_season = np.array(  # each run's lead days' seasons
        [[calibration.season_index(c + timedelta(days=k + 1)) for k in range(LEAD_DAYS)] for c in runs]
    )

    def forecast(adjust: list[Adjustments]) -> dict[str, np.ndarray]:
        """Each run's forecast days through its own adjustments."""
        out = [replay(c, lat, lon, a) for c, a in zip(runs, adjust, strict=True)]
        return {name: np.array([o[f"fc_{name}"] for o in out]) for name in SCORED}

    def by_fold(make) -> list[Adjustments]:
        """Each run's adjustments from the tables fitted on the other fold."""
        tables = [make(fold != f) for f in (0, 1)]
        return [tables[f] for f in fold]

    # 1. The max offset
    base = forecast([Adjustments()] * len(runs))

    def max_table(use: np.ndarray) -> dict:
        error = (base["air_temperature_max"] - obs["air_temperature_max"])[use, :3]
        season = day_season[use, :3]
        offsets = [float(np.nanmean(error[season == s])) for s in range(4)]
        return {"day_of_year": SEASON_DAYS, "offset_c": [round(o, 2) for o in offsets]}

    steps = [("none", base)]
    max_held = forecast(by_fold(lambda use: Adjustments(max_offset=max_table(use))))
    steps.append(("+ max offset", max_held))
    max_offset = max_table(np.ones(len(runs), dtype=bool))

    # 2. The night min, with the max offset
    with_max = forecast([Adjustments(max_offset=max_offset)] * len(runs))
    first = runs[0]
    lead_hours = [
        (datetime(d.year, d.month, d.day, 12, tzinfo=UTC) - first) // HOUR
        for d in ((first + timedelta(days=k + 1)).date() for k in range(LEAD_DAYS))
    ]

    def night_table(use: np.ndarray) -> dict:
        error = (with_max["air_temperature_min"] - obs["air_temperature_min"])[use]
        return {"lead_hours": lead_hours, "warm_bias_c": [round(float(b), 2) for b in np.nanmean(error, axis=(0, 2))]}

    night_held = forecast(by_fold(lambda use: Adjustments(max_offset=max_offset, night_min=night_table(use))))
    steps.append(("+ night min", night_held))
    night_min = night_table(np.ones(len(runs), dtype=bool))

    # 3. The RH maps, with both
    cells = slice(None, None, RH_EVERY)
    j, i = np.load(CACHE / "cells.npz")["j"] - window.j0, np.load(CACHE / "cells.npz")["i"] - window.i0
    fc_rh, ob_rh = [], []
    for cycle in runs:
        run, pressure = cached_run(cycle)
        values = derive(run, lat, lon, pressure, Adjustments(max_offset=max_offset, night_min=night_min))
        fc_rh.append(values["relative_humidity"][:, 0, cells].astype(np.float32))
        ob_rh.append(
            read_hours(
                data_dir, window, run.valid_times[0], nbm.HORIZON_HOURS, j[cells], i[cells], ("relative_humidity",)
            )["relative_humidity"]
        )
    fc_rh, ob_rh = np.array(fc_rh), np.array(ob_rh)
    group_table = {"lead_group_ends": RH_LEAD_GROUP_ENDS}
    bins = np.empty(fc_rh.shape, dtype=np.int16)  # season × lead group × solar hour
    for r, cycle in enumerate(runs):
        for k in range(nbm.HORIZON_HOURS):
            valid = cycle + (k + 1) * HOUR
            s, g = calibration.season_index(valid), calibration.lead_index(cycle, valid, group_table)
            hour = np.floor(calibration.solar_hour(valid, lon[0, cells])).astype(int) % 24
            bins[r, k] = (s * len(RH_LEAD_HOURS) + g) * 24 + hour
    grid = np.arange(101, dtype=float)

    def rh_table(use: np.ndarray) -> dict:
        b, f, o = bins[use].ravel(), fc_rh[use].ravel(), ob_rh[use].ravel()
        ok = np.isfinite(f) & np.isfinite(o)
        b, f, o = b[ok], f[ok], o[ok]
        order = np.argsort(b, kind="stable")
        b, f, o = b[order], f[order], o[order]
        edges = np.searchsorted(b, np.arange(4 * len(RH_LEAD_HOURS) * 24 + 1))
        maps = np.empty((4, len(RH_LEAD_HOURS), 24, len(grid)))
        for n in range(4 * len(RH_LEAD_HOURS) * 24):
            lo, hi = edges[n], edges[n + 1]
            if hi - lo < 1000:
                raise ValueError(f"RH bin {n} has {hi - lo} pairs")
            qf, qo = np.quantile(f[lo:hi], RH_QUANTILES), np.quantile(o[lo:hi], RH_QUANTILES)
            maps.reshape(-1, len(grid))[n] = np.interp(grid, qf, qo)
        return {
            "season_day_of_year": SEASON_DAYS,
            "lead_group_ends": RH_LEAD_GROUP_ENDS,
            "lead_hours": RH_LEAD_HOURS,
            "rh_grid": grid.astype(int).tolist(),
            "map": np.round(maps, 1).tolist(),
        }

    rh_held = forecast(
        by_fold(lambda use: Adjustments(max_offset=max_offset, night_min=night_min, rh_map=rh_table(use)))
    )
    steps.append(("+ RH map", rh_held))
    rh_map = rh_table(np.ones(len(runs), dtype=bool))

    source = f"backtest of {len(runs)} {first:%H}z runs, {runs[0]:%Y-%m-%d} to {runs[-1]:%Y-%m-%d}, against the archive"
    for path, table in (
        (calibration.MAX_OFFSET_PATH, max_offset),
        (calibration.NIGHT_MIN_PATH, night_min),
        (calibration.RH_MAP_PATH, rh_map),
    ):
        head = {"version": 1, "fitted": f"{datetime.now(UTC):%Y-%m-%d}", "source": source}
        indent = None if table is rh_map else 2  # the maps are 29,000 numbers
        path.write_text(json.dumps(head | table, indent=indent) + "\n")

    lines = [
        "# NBM forecast calibration",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/backtest_forecast.py --fit-calibration` (D39, D49), "
        f"from the forecast's hours at {lat.shape[1]} cells in {len(runs)} runs against the archive, after the "
        "max is reshaped to NBM's TMAX. In order, each on the forecast with the ones before it applied:",
        "",
        "1. **Max offset** by season: NBM's TMAX less the archive's daily max (the warmest top-of-hour value) on "
        "lead days 1–3, applied at every lead (later leads' errors are mostly weather) and interpolated through "
        "the year between mid-season days.",
        "2. **Night min**: the hours' warm bias at each night's min by lead (interpolation between NBM's steps "
        "rounds off the coldest hours), each night's coldest hours (00–12Z) lowered by it.",
        "3. **RH maps**: quantile maps from the forecast's hourly RH to the archive's, by season, lead group "
        f"(hours {', '.join(str(e) for e in RH_LEAD_GROUP_ENDS)} and on) and solar hour, on every {RH_EVERY}nd "
        "cell; the dew point is recomputed with the temperature kept. NBM's blended humidity rarely saturates, so "
        "the forecast counts too few humid hours (most in daytime rain and overcast).",
        "",
        "| Season | DJF | MAM | JJA | SON |",
        "|---|---|---|---|---|",
        "| max offset (°C) | " + " | ".join(f"{o:+.2f}" for o in max_offset["offset_c"]) + " |",
        "",
        "| Lead day | " + " | ".join(str(k + 1) for k in range(LEAD_DAYS)) + " |",
        "|---|" + "---|" * LEAD_DAYS,
        "| night warm bias (°C) | " + " | ".join(f"{b:.2f}" for b in night_min["warm_bias_c"]) + " |",
        "",
        "Held out (2-fold: each run with its step's table fitted on the other half; the steps before it use the "
        "tables fitted on every run), bias / MAE by lead day (°C, hours a day):",
        "",
        "| | | " + " | ".join(f"day {k + 1}" for k in range(LEAD_DAYS)) + " |",
        "|---|---|" + "---|" * LEAD_DAYS,
    ]
    for name in SCORED:
        for label, values in steps:
            row = [errors(values[name][:, k], obs[name][:, k]) for k in range(LEAD_DAYS)]
            lines.append(f"| `{name}` | {label} | " + " | ".join(f"{b:+.2f} / {e:.2f}" for b, e in row) + " |")
    lines.append("")
    return "\n".join(lines)


def roll_up(first_hour: datetime, values: dict[str, np.ndarray], days: list[date], names) -> dict[str, np.ndarray]:
    """Each cell's local days (`daily_at_point`, all at once) from hours (time, 1, cells): name → (days, cells)."""
    rolled = daily_at_point(first_hour, {k: v[:, 0] for k, v in values.items()}, ZONE, days[0], days[-1])
    return {name: rolled[name] for name in names}


def wanted(ref: MessageRef, lead: int) -> str | None:
    """`nbm.wanted`, plus NBM's 12-hour TMAX and TMIN ending at this lead."""
    if ref.key in EXTREMES and not ref.extra:
        name, kind = EXTREMES[ref.key]
        return name if ref.detail == f"{lead - 12}-{lead} hour {kind} fcst" else None
    return nbm.wanted(ref, lead)


def read_days(data_dir: Path, window: Window, days: list[date], y, x) -> dict[str, np.ndarray]:
    out = {name: np.full((len(days), len(y)), np.nan) for name in COMPARED}
    for year in sorted({d.year for d in days}):
        store = GridStore.open(data_dir, DAILY, year, [DAILY_VARIABLES[n] for n in COMPARED])
        ks = [k for k, d in enumerate(days) if d.year == year]
        t0 = store.index_of(days[ks[0]])
        for name in COMPARED:
            out[name][ks[0] : ks[-1] + 1] = store.read_steps(name, t0, t0 + len(ks), window)[:, y, x]
    return out


def read_hours(
    data_dir: Path, window: Window, first: datetime, n: int, y, x, names=("air_temperature", "dew_point")
) -> dict[str, np.ndarray]:
    """The archive's hours ending first … first + (n − 1) h at the cells, across years (NaN past the archive)."""
    out = {name: np.full((n, len(y)), np.nan, dtype=np.float32) for name in names}
    k = 0
    while k < n:
        t = first + k * HOUR
        step = min(n - k, (datetime(t.year + 1, 1, 1, tzinfo=UTC) - t) // HOUR)
        try:
            store = GridStore.open(data_dir, HOURLY, t.year, [VARIABLES[name] for name in names])
        except FileNotFoundError:
            k += step
            continue
        t0 = store.index_of(t)
        for name in names:
            out[name][k : k + step] = store.read_steps(name, t0, t0 + step, window)[:, y, x]
        k += step
    return out


# The report


def report(args, cycles: list[datetime]) -> str:
    runs = [dict(np.load(cache_path(c))) for c in cycles if cache_path(c).exists()]
    if not runs:
        return "# Forecast backtest\n\nNo runs cached yet.\n"
    shared = set.intersection(*(set(r) for r in runs)) - {"failed_leads", "month"}  # older caches hold fewer keys
    stack = {key: np.stack([r[key] for r in runs]) for key in runs[0] if key in shared}
    months = np.array([int(r["month"]) for r in runs])
    n_points = stack["fc_air_temperature_min"].shape[2]
    failed = sum(len(r["failed_leads"]) for r in runs)
    fc_dd, obs_dd = (
        degree_days_sine(stack[f"{k}_air_temperature_min"], stack[f"{k}_air_temperature_max"], 10.0, 30.0) * 1.8
        for k in ("fc", "obs")
    )
    pairs = [(name, stack[f"fc_{name}"], stack[f"obs_{name}"], DAILY_VARIABLES[name].unit) for name in COMPARED]
    pairs.insert(2, ("dd_50_86 (°F·d)", fc_dd, obs_dd, "degF_day"))
    pairs.insert(2, ("NBM TMIN (12 h, 00–12Z)", stack["tmin_nbm"], stack["obs_air_temperature_min"], "degC"))
    pairs.insert(2, ("NBM TMAX (12 h, 12–00Z)", stack["tmax_nbm"], stack["obs_air_temperature_max"], "degC"))

    lines = [
        "# Forecast backtest: NBM against the archive",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/backtest_forecast.py` (PLAN.md Phase 4 G). "
        f"The {args.hour}z "
        f"long run on every {args.every}th day, {cycles[0]:%Y-%m-%d} to {cycles[-1]:%Y-%m-%d}: {len(runs)} runs at "
        f"{n_points} cells (one per old-API 0.1° point in Central time, box `{args.box}`), {failed} forecast files "
        "unreadable. The forecast's hours are filled as the forecast job fills them and rolled up by the archive's "
        "day definitions. Lead day 1 is the first complete local day after the cycle. Errors are forecast minus "
        "archive, in stored units.",
        "",
        "## Bias and MAE by lead day",
        "",
        "| Variable | unit | " + " | ".join(f"day {k + 1}" for k in range(LEAD_DAYS)) + " |",
        "|---|---|" + "---|" * LEAD_DAYS,
    ]
    for name, fc, obs, unit in pairs:
        cells = []
        for k in range(LEAD_DAYS):
            bias, mae = errors(fc[:, k], obs[:, k])
            cells.append(f"{bias:+.2f} / {mae:.2f}")
        lines.append(f"| {name} | {unit} | " + " | ".join(cells) + " |")
    lines += ["", "Each cell is bias / MAE.", ""]

    lines += ["## Daily extremes: the hours' against NBM's TMAX and TMIN (D39)", ""]
    lines += [
        "| Lead day | max from hours MAE | NBM TMAX MAE | min from hours MAE | NBM TMIN MAE |",
        "|---|---|---|---|---|",
    ]
    for k in range(LEAD_DAYS):
        row = [
            errors(stack["fc_air_temperature_max"][:, k], stack["obs_air_temperature_max"][:, k])[1],
            errors(stack["tmax_nbm"][:, k], stack["obs_air_temperature_max"][:, k])[1],
            errors(stack["fc_air_temperature_min"][:, k], stack["obs_air_temperature_min"][:, k])[1],
            errors(stack["tmin_nbm"][:, k], stack["obs_air_temperature_min"][:, k])[1],
        ]
        lines.append(f"| {k + 1} | " + " | ".join(f"{v:.2f}" for v in row) + " |")
    lines.append("")

    lines += [
        "## Precipitation: wet days (≥ 1 mm)",
        "",
        "| Lead day | hit rate | false alarm ratio | forecast/observed total |",
        "|---|---|---|---|",
    ]
    for k in range(LEAD_DAYS):
        fc, obs = stack["fc_precipitation_sum"][:, k], stack["obs_precipitation_sum"][:, k]
        ok = np.isfinite(fc) & np.isfinite(obs)
        fw, ow = fc[ok] >= 1, obs[ok] >= 1
        hit = (fw & ow).sum() / max(ow.sum(), 1)
        far = (fw & ~ow).sum() / max(fw.sum(), 1)
        lines.append(f"| {k + 1} | {hit:.2f} | {far:.2f} | {fc[ok].sum() / max(obs[ok].sum(), 1e-9):.2f} |")
    lines.append("")

    lines += ["## By month, lead days 1 and 5 (bias / MAE)", ""]
    monthly = [
        ("air_temperature_max", "°C"),
        ("air_temperature_min", "°C"),
        ("precipitation_sum", "mm"),
        ("et0_sum", "mm"),
    ]
    lines += [
        "| Month | " + " | ".join(f"{n} d1 | {n} d5" for n, _ in monthly) + " |",
        "|---|" + "---|---|" * len(monthly),
    ]
    for month in sorted(set(months)):
        sel = months == month
        cells = []
        for name, _ in monthly:
            for k in (0, 4):
                bias, mae = errors(stack[f"fc_{name}"][sel, k], stack[f"obs_{name}"][sel, k])
                cells.append(f"{bias:+.2f} / {mae:.2f}")
        lines.append(f"| {month} | " + " | ".join(cells) + " |")
    lines.append("")

    lines += [
        "## The seam: the first forecast hours against the archive's",
        "",
        "| Hour after cycle | temperature bias / MAE (°C) | dew point bias / MAE (°C) |",
        "|---|---|---|",
    ]
    for h in range(SEAM_HOURS):
        t = errors(stack["seam_fc_air_temperature"][:, h], stack["seam_obs_air_temperature"][:, h])
        d = errors(stack["seam_fc_dew_point"][:, h], stack["seam_obs_dew_point"][:, h])
        lines.append(f"| {h + 1} | {t[0]:+.2f} / {t[1]:.2f} | {d[0]:+.2f} / {d[1]:.2f} |")
    lines.append("")
    return "\n".join(lines)


def errors(fc: np.ndarray, obs: np.ndarray) -> tuple[float, float]:
    diff = (np.asarray(fc, dtype=float) - np.asarray(obs, dtype=float)).ravel()
    diff = diff[np.isfinite(diff)]
    if not diff.size:
        return float("nan"), float("nan")
    return float(diff.mean()), float(np.abs(diff).mean())


if __name__ == "__main__":
    main()
