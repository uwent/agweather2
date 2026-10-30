"""Backtest of the NBM forecast against the archive (PLAN.md Phase 4 G).

For the 13z long run on every 5th day of a period, fetches NBM at one cell per old-API 0.1° point in Central time
(`compare_legacy.central_points`), fills its hours as the forecast job does (`nbm.to_hourly`, then RH and ET0), and
rolls up lead days 1–10 (the complete local days after the cycle) with `daily_at_point`. Compares them with the
archive's daily store, and the first forecast hours with the archive's hours (the seam). NBM's own 12-hour TMAX
and TMIN are kept beside the hours' extremes, to settle D39.

Each run's values are cached in tmp/backtest/{cycle}.npz, so a restart resumes. `--report` writes the report from
the cache without fetching.

    uv run python scripts/backtest_forecast.py --start 2025-01-01 --end 2025-12-31
    uv run python scripts/backtest_forecast.py --start 2025-01-01 --end 2025-12-31 --report
"""

import argparse
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_legacy import central_points

from agdata.catalog import DAILY_VARIABLES, VARIABLES, variable
from agdata.forecast import archive_pressure_kpa
from agdata.grid import NDFD, Window, service_window
from agdata.point import daily_at_point
from agdata.qc import check_range
from agdata.sources import nbm
from agdata.sources.grib import MessageRef, RemoteGrib, place
from agdata.store import DAILY, HOURLY, GridStore
from agdata.units import convert
from agmodels.degree_days import degree_days_sine
from agmodels.weather import et0_hourly_series, relative_humidity_percent

HOUR = timedelta(hours=1)
ZONE = "America/Chicago"
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

    if not args.report:
        points, js, is_ = point_cells(data_dir, window)
        print(f"{len(points)} points, {len(cycles)} cycles", flush=True)
        for cycle in cycles:
            path = cache_path(cycle)
            if path.exists():
                continue
            began = time.monotonic()
            result = backtest_run(data_dir, window, cycle, js, is_, args.workers)
            np.savez_compressed(path, **cast(dict[str, Any], result))  # pyright reads the names as savez's flags
            failed = len(result["failed_leads"])
            print(f"{cycle:%Y-%m-%d %HZ}: {time.monotonic() - began:.0f} s, {failed} failed leads", flush=True)

    Path(args.out).write_text(report(args, cycles))
    print(f"wrote {args.out}")


def cache_path(cycle: datetime) -> Path:
    return CACHE / f"{cycle:%Y%m%d%H}.npz"


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


def backtest_run(data_dir: Path, window: Window, cycle: datetime, js, is_, workers: int) -> dict[str, np.ndarray]:
    """One run at the cells: its lead days and the archive's, NBM's TMAX/TMIN by day, and the seam hours."""
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
    hourly = nbm.to_hourly(nbm.Run(cycle=cycle, values={k: raw[k] for k in nbm.NAMES}), lat, lon, pressure)
    times = hourly.valid_times
    values = dict(hourly.values)
    values["surface_pressure"] = np.broadcast_to(pressure, values["air_temperature"].shape)
    values["relative_humidity"] = relative_humidity_percent(values["air_temperature"], values["dew_point"])
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
    values = {name: check_range(VARIABLES[name], series)[0] for name, series in values.items()}

    day1 = (cycle + timedelta(days=1)).date()  # the 13z cycle is morning in Central time: day 0 is partial
    days = [day1 + timedelta(days=k) for k in range(LEAD_DAYS)]
    out: dict[str, np.ndarray] = {}
    forecast = {name: np.full((LEAD_DAYS, n), np.nan) for name in COMPARED}
    for p in range(n):
        rolled = daily_at_point(
            times[0], {name: series[:, 0, p] for name, series in values.items()}, ZONE, days[0], days[-1]
        )
        for name in COMPARED:
            forecast[name][:, p] = rolled[name]
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
    out["month"] = np.array(cycle.month)
    return out


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


def read_hours(data_dir: Path, window: Window, first: datetime, n: int, y, x) -> dict[str, np.ndarray]:
    store = GridStore.open(data_dir, HOURLY, first.year, [VARIABLES["air_temperature"], VARIABLES["dew_point"]])
    t0 = store.index_of(first)
    return {name: store.read_steps(name, t0, t0 + n, window)[:, y, x] for name in ("air_temperature", "dew_point")}


# The report


def report(args, cycles: list[datetime]) -> str:
    runs = [dict(np.load(cache_path(c))) for c in cycles if cache_path(c).exists()]
    if not runs:
        return "# Forecast backtest\n\nNo runs cached yet.\n"
    stack = {key: np.stack([r[key] for r in runs]) for key in runs[0] if key not in ("failed_leads", "month")}
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
