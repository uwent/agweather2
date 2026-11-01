"""Open-Meteo against Wisconet's stations (PLAN.md Phase 4 handoff): shortwave, temperature, humidity and ET0 at
each station, from the models points outside the box and WISP use (`ncep_nbm_conus`, `best_match`, and the two
merged hour by hour, NBM first, as `agdata.sources.openmeteo` and WISP do), beside the archive (v2's grid) and,
for ET, the old API.

The reference ET0 is FAO-56's hourly form (`agmodels.weather.et0_hourly_series`, the archive's) from each
station's own measurements: its pyranometer's shortwave, temperature, dew point, 3 m wind (taken to 10 m by
FAO-56's eq. 47 before the series takes it to 2 m) and pressure. Wisconet's own ET isn't a reference (Ben).

Then fits Open-Meteo's corrections for points (D51) on one year and tests them on the other: shortwave by the hour's
clearness against the stations, as D48 did for HRRR, and RH quantile-mapped onto the archive's by season and solar
hour, as D49 does for NBM's forecast (so the 88% of D50 holds for Open-Meteo too). Both are applied through the
production code (`agdata.shortwave`, `agdata.calibration`). `--fit` writes them to `agdata/data`, fitted on every
year (Open-Meteo's humidity differs from year to year: tested on the other year, a one-year map lands ±1 h a day off).

Station data come from tmp/wisconet/ (fetched by tmp/wisconet/fetch_humidity.py, fetch_wind.py and
`scripts/fit_shortwave_correction.py`); Open-Meteo's from the historical-forecast API, cached in tmp/openmeteo/.

    uv run python scripts/compare_openmeteo_wisconet.py --start 2025-01-01 --end 2026-10-27 --fit

`--quiet` prints only warnings, failures and the summary. `--fit` names the two files it overwrites before it writes
them, and doesn't write them if a failure was reported.
"""

import argparse
import itertools
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_legacy import OLD_API

from agdata import calibration, shortwave
from agdata.catalog import VARIABLES
from agdata.clients.agweather_v1 import point_key
from agdata.clients.openmeteo_points import OpenMeteoPoints
from agdata.clients.wisconet import CENTRAL, Wisconet
from agdata.gaps import clear_sky_shortwave_w_m2
from agdata.grid import NDFD, service_window
from agdata.progress import Reporter
from agdata.store import HOURLY, GridStore
from agmodels.weather import et0_hourly_series, relative_humidity_percent

WISCONET = Path("tmp/wisconet")
CACHE = Path("tmp/openmeteo")
HOUR = timedelta(hours=1)
MODELS = ("ncep_nbm_conus", "best_match")
OM_VARIABLES = [
    "temperature_2m",
    "dew_point_2m",
    "relative_humidity_2m",
    "shortwave_radiation",
    "wind_speed_10m",
    "surface_pressure",
    "et0_fao_evapotranspiration",
]
STATION_FILES = {  # cache name suffix → {field standard name: our name}
    "60min_humidity": {
        "60min_relative_humidity_pct_avg": "rh",
        "60min_air_temp_f_avg": "t",
        "60min_dew_point_f_avg": "td",
    },
    "60min_solar_radiation_w_avg": {"60min_solar_radiation_w_avg": "sw"},
    "60min_wind": {"60min_wind_speed_mph_avg": "wind", "60min_pressure_in_avg": "p"},
}
WIND_3M_TO_10M = np.log(67.8 * 10 - 5.42) / np.log(67.8 * 3 - 5.42)  # FAO-56 eq. 47's profile, 3 m → 10 m
CLEARNESS_EDGES = np.linspace(0, 1.2, 13)
GROWING = (4, 5, 6, 7, 8, 9, 10)  # WISP's season
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--fit-year", type=int, default=2025)
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-openmeteo.md")
    parser.add_argument("--fit", action="store_true", help="write the corrections' tables to agdata/data")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last:
        parser.error("--start must not be after --end")
    if not first.year <= args.fit_year <= last.year:
        parser.error(f"--fit-year {args.fit_year} is outside --start to --end")
    window = service_window(args.box)
    wisconet = Wisconet(cache_dir=WISCONET)
    stations = [s for s in wisconet.stations() if (c := cell(s)) is not None and window.contains(*c)]
    if not stations:
        report.fail("stations", f"no Wisconet stations inside the {args.box} box")
        sys.exit(1)
    start = datetime(first.year, first.month, first.day, tzinfo=UTC)
    n = ((last - first).days + 1) * 24
    report.step(
        f"Open-Meteo against Wisconet, {first} to {last}: {len(stations)} stations, {n} hours, models "
        f"{', '.join(MODELS)}; writing {args.out}" + (" and the fitted correction tables" if args.fit else "")
    )
    times = [start + (k + 1) * HOUR for k in range(n)]  # hours ending 01Z on the first day …

    report.step("reading the stations' cached measurements")
    station = station_hours(wisconet, stations, start, n, report)
    om = {model: openmeteo_hours(stations, first, last, model, start, n, report) for model in MODELS}
    om["merged"] = {
        name: np.where(np.isfinite(om[MODELS[0]][name]), om[MODELS[0]][name], om[MODELS[1]][name])
        for name in om[MODELS[0]]
    }
    report.step("reading the archive at the stations' cells")
    archive = archive_hours(Path(args.data), stations, start, n, report)
    report.step("fitting and checking the corrections")

    lat = np.array([s["latitude"] for s in stations])[:, None]
    lon = np.array([s["longitude"] for s in stations])[:, None]
    stamps = np.array([t.replace(tzinfo=None) for t in times], dtype="datetime64[s]")
    rso = clear_sky_shortwave_w_m2(stamps, lat[:, 0], lon[:, 0], np.full((n, len(stations)), 97.0)).T
    station["sw"] = np.where((station["sw"] >= 0) & (station["sw"] <= 1.3 * rso + 30), station["sw"], np.nan)
    station["et0"] = et0(
        stamps, lat, lon, station["t"], station["td"], station["wind"] * WIND_3M_TO_10M, station["p"], station["sw"]
    )
    for source in om.values():
        source["rh_derived"] = relative_humidity_percent(source["t"], source["td"])
        source["et0_ours"] = et0(stamps, lat, lon, source["t"], source["td"], source["wind"], source["p"], source["sw"])

    # Open-Meteo's corrections (D51), fitted on one year, applied as points apply them
    years = np.array([t.year for t in times])
    fit = years == args.fit_year
    m = om["merged"]
    rso_om = clear_sky_shortwave_w_m2(stamps, lat[:, 0], lon[:, 0], m["p"].T).T
    clear = np.where(rso_om > 1, m["sw"] / np.maximum(rso_om, 1), 0.0)
    middles, factor = fit_clearness(m["sw"], station["sw"], clear, fit)
    source = f"{MODELS[0]} then {MODELS[1]} (historical-forecast) at {len(stations)} Wisconet stations, {args.fit_year}"
    sw_table = {
        "version": 1,
        "fitted": f"{datetime.now(UTC):%Y-%m-%d}",
        "source": f"{source}, against the stations' 60min_solar_radiation_w_avg",
        "clearness": middles.round(3).tolist(),
        "factor": [round(float(f), 4) for f in factor],
    }
    m["sw_corrected"] = shortwave.correct_w_m2(stamps, lat[:, 0], lon[:, 0], m["sw"].T, m["p"].T, sw_table).T
    m["et0_corrected"] = et0(stamps, lat, lon, m["t"], m["td"], m["wind"], m["p"], m["sw_corrected"])
    rh_table = {
        "version": 1,
        "fitted": f"{datetime.now(UTC):%Y-%m-%d}",
        "source": f"{source}, against the archive's RH at their cells",
        **fit_rh_map(m["rh_derived"], archive["rh"], times, lon[:, 0], fit),
    }
    m["td_mapped"] = calibration.map_humidity(times[0] - HOUR, times, lon[:, 0], m["t"].T, m["td"].T, rh_table).T
    m["rh_mapped"] = relative_humidity_percent(m["t"], m["td_mapped"])

    local_day = np.array([(t - HOUR).astimezone(CENTRAL).date().toordinal() for t in times])
    month = np.array([(t - HOUR).astimezone(CENTRAL).month for t in times])
    days = sorted(set(local_day))
    report.step(f"the old API's ET for {len(days)} days")
    old_et = old_api_et(stations, [date.fromordinal(d) for d in days], report)
    report.step(f"writing {args.out} (overwriting)")
    Path(args.out).write_text(
        build_report(args, stations, station, om, archive, old_et, local_day, month, days, years, (middles, factor))
    )
    report.step(f"wrote {args.out}")
    if args.fit and report.failures:
        report.warn("not overwriting the correction tables because of the failures above")
    elif args.fit:  # every year's hours, now the held-out check is written
        every = np.ones(len(times), dtype=bool)
        middles, factor = fit_clearness(m["sw"], station["sw"], clear, every)
        years_fitted = "–".join(str(y) for y in sorted(set(years.tolist())))
        source = (
            f"{MODELS[0]} then {MODELS[1]} (historical-forecast) at {len(stations)} Wisconet stations, {years_fitted}"
        )
        sw_table |= {
            "source": f"{source}, against the stations' 60min_solar_radiation_w_avg",
            "factor": [round(float(f), 4) for f in factor],
        }
        rh_table |= {
            "source": f"{source}, against the archive's RH at their cells",
            **fit_rh_map(m["rh_derived"], archive["rh"], times, lon[:, 0], every),
        }
        report.step(
            f"overwriting {shortwave.OPENMETEO_TABLE_PATH} and {calibration.OPENMETEO_RH_MAP_PATH} "
            f"(fitted on {years_fitted})"
        )
        shortwave.OPENMETEO_TABLE_PATH.write_text(json.dumps(sw_table, indent=2) + "\n")
        calibration.OPENMETEO_RH_MAP_PATH.write_text(json.dumps(rh_table) + "\n")
        report.step(f"wrote {shortwave.OPENMETEO_TABLE_PATH} and {calibration.OPENMETEO_RH_MAP_PATH}")
    if not report.finish(f"{len(stations)} stations, {n} hours, {len(days)} days"):
        sys.exit(1)


def cell(s: dict) -> tuple[int, int] | None:
    return NDFD.cell_of(s["latitude"], s["longitude"])


def station_hours(wisconet: Wisconet, stations, start: datetime, n: int, report: Reporter) -> dict[str, np.ndarray]:
    """Each station's hourly measurements on the hours ending start + 1 h …, in °C, %, W/m², m/s and kPa."""
    names = {v for fields in STATION_FILES.values() for v in fields.values()}
    out = {name: np.full((len(stations), n), np.nan) for name in names}
    ids = {name: wisconet.field_id(name) for fields in STATION_FILES.values() for name in fields}
    missing = 0
    for k, s in enumerate(stations):
        report.progress("stations", k + 1, len(stations))
        for year, (suffix, fields) in itertools.product(
            range(start.year, (start + (n - 1) * HOUR).year + 1), STATION_FILES.items()
        ):
            path = WISCONET / f"{s['station_id']}_{year}_{suffix}.json"
            if not path.exists():
                missing += 1
                continue
            by_id = {ids[name]: ours for name, ours in fields.items()}
            try:
                rows = json.loads(path.read_text()).get("data", [])
            except (OSError, ValueError) as error:
                report.fail(str(path), error)
                continue
            for row in rows:
                t = int((row["collection_time"] - start.timestamp()) // 3600) - 1
                if not 0 <= t < n:
                    continue
                for fid, value in row["measures"]:
                    if value is not None and fid in by_id:
                        out[by_id[fid]][k, t] = value
    if missing:
        report.warn(f"{missing} station-year cache files not found in {WISCONET} (those hours stay missing)")
    out["t"] = (out["t"] - 32) / 1.8
    out["td"] = (out["td"] - 32) / 1.8
    out["wind"] = out["wind"] * 0.44704
    out["p"] = out["p"] * 3.386389
    out["rh"] = np.where((out["rh"] >= 1) & (out["rh"] <= 103), np.minimum(out["rh"], 100), np.nan)
    out["t"] = np.where((out["t"] > -45) & (out["t"] < 45), out["t"], np.nan)
    out["td"] = np.where((out["td"] > -50) & (out["td"] <= out["t"] + 0.5), np.fmin(out["td"], out["t"]), np.nan)
    out["wind"] = np.where((out["wind"] >= 0) & (out["wind"] < 40), out["wind"], np.nan)
    out["p"] = np.where((out["p"] > 85) & (out["p"] < 105), out["p"], np.nan)
    return out


def openmeteo_hours(
    stations, first: date, last: date, model: str, start: datetime, n: int, report: Reporter
) -> dict[str, np.ndarray]:
    """Open-Meteo's hours at the stations, a year per request, in °C, %, W/m², m/s, kPa and mm."""
    key = os.environ.get("OPEN_METEO_API_KEY") or dotenv("OPEN_METEO_API_KEY")
    client = OpenMeteoPoints(cache_dir=CACHE, api_key=key)
    locations = [(s["latitude"], s["longitude"]) for s in stations]
    ours = {"temperature_2m": "t", "dew_point_2m": "td", "relative_humidity_2m": "rh", "shortwave_radiation": "sw"}
    ours |= {"wind_speed_10m": "wind", "surface_pressure": "p", "et0_fao_evapotranspiration": "et0_om"}
    out = {name: np.full((len(stations), n), np.nan) for name in ours.values()}
    for year in range(first.year, last.year + 1):
        lo, hi = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        report.step(f"Open-Meteo {model} {year}: {len(locations)} locations, {lo} to {hi}")
        for k, block in enumerate(client.hourly(locations, lo, hi, OM_VARIABLES, model=model)):
            index = (np.asarray(block["time"], dtype=np.int64) - int(start.timestamp())) // 3600 - 1
            ok = (index >= 0) & (index < n)
            for variable, name in ours.items():
                series = np.array([np.nan if v is None else v for v in block.get(variable, [])], dtype=float)
                if series.size:
                    out[name][k, index[ok]] = series[ok]
    out["p"] = out["p"] / 10  # hPa → kPa
    return out


def dotenv(name: str) -> str | None:
    path = Path(".env")
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"') or None
    return None


def archive_hours(data_dir: Path, stations, start: datetime, n: int, report: Reporter) -> dict[str, np.ndarray]:
    names = {"relative_humidity": "rh", "air_temperature": "t", "shortwave_radiation": "sw", "et0": "et0"}
    out = {ours: np.full((len(stations), n), np.nan) for ours in names.values()}
    k = 0
    while k < n:
        t = start + (k + 1) * HOUR
        step = min(n - k, (datetime(t.year + 1, 1, 1, tzinfo=UTC) - t) // HOUR)
        report.step(f"archive {t.year}: {step} hours at {len(stations)} cells")
        store = GridStore.open(data_dir, HOURLY, t.year, [VARIABLES[name] for name in names])
        t0 = store.index_of(t)
        for s_index, s in enumerate(stations):
            j, i = cell(s) or (0, 0)
            for name, ours in names.items():
                out[ours][s_index, k : k + step] = store.read_point(name, j, i, t0, t0 + step)
        k += step
    return out


def et0(stamps, lat, lon, t, td, wind_10m, pressure, shortwave) -> np.ndarray:
    """Hourly FAO-56 ET0 (mm) on (stations, hours) arrays, NaN where an input is."""
    with np.errstate(invalid="ignore"):
        out = et0_hourly_series(stamps, lat[:, 0], lon[:, 0], t.T, td.T, wind_10m.T, pressure.T, shortwave.T).T
    return np.where(np.isfinite(t + td + wind_10m + pressure + shortwave), out, np.nan)


def fit_clearness(model, observed, clear, use) -> tuple[np.ndarray, np.ndarray]:
    """The station total over the model's in each clearness bin (daylight hours both have)."""
    ok = use[None, :] & np.isfinite(model) & np.isfinite(observed) & (model > 0)
    factor = []
    for lo, hi in itertools.pairwise(CLEARNESS_EDGES):
        m = ok & (clear >= lo) & (clear < hi)
        factor.append(observed[m].sum() / model[m].sum() if m.sum() > 500 else np.nan)
    middles = (CLEARNESS_EDGES[:-1] + CLEARNESS_EDGES[1:]) / 2
    factor = np.array(factor)
    good = np.isfinite(factor)
    return middles, np.interp(middles, middles[good], factor[good])


def fit_rh_map(model_rh, target_rh, times, longitude, use) -> dict:
    """Quantile maps from the model's hourly RH to the target's, by season and solar hour (`calibration.map_rh`'s
    table, with one lead group): (stations, hours) arrays, fitted on the hours `use` marks."""
    season = np.array([calibration.season_index(t) for t in times])
    hour = np.floor(np.stack([calibration.solar_hour(t, longitude) for t in times], axis=1)).astype(int) % 24
    grid = np.arange(101, dtype=float)
    quantiles = np.linspace(0, 1, 201)
    maps = np.empty((4, 1, 24, len(grid)))
    ok = np.isfinite(model_rh) & np.isfinite(target_rh) & use[None, :]
    for s, h in itertools.product(range(4), range(24)):
        sel = ok & (season == s)[None, :] & (hour == h)
        if sel.sum() < 1000:
            raise ValueError(f"RH bin season {s}, hour {h} has {sel.sum()} pairs")
        maps[s, 0, h] = np.interp(grid, np.quantile(model_rh[sel], quantiles), np.quantile(target_rh[sel], quantiles))
    return {
        "season_day_of_year": [15, 105, 196, 288],
        "lead_group_ends": [],
        "lead_hours": [0],
        "rh_grid": grid.astype(int).tolist(),
        "map": np.round(maps, 1).tolist(),
    }


def old_api_et(stations, days: list[date], report: Reporter) -> np.ndarray:
    """The old API's daily ET (mm) at each station's 0.1° point, from compare_legacy's cache."""
    out = np.full((len(stations), len(days)), np.nan)
    keys = [point_key(s["latitude"], s["longitude"]) for s in stations]
    unavailable = 0
    for k, day in enumerate(days):
        report.progress("old API ET", k + 1, len(days))
        try:
            grid = OLD_API.evapotranspiration_mm(day)
        except Exception as error:  # not cached and not reachable: leave the day out
            unavailable += 1
            if unavailable == 1:
                report.warn(f"old API ET unavailable for {day}: {error!r} (further days counted below)")
            continue
        for s, key in enumerate(keys):
            value = grid.get(key)
            out[s, k] = np.nan if value is None else value
    if unavailable:
        report.warn(f"old API ET unavailable for {unavailable} of {len(days)} days (left out of the old-API row)")
    return out


def daily(hourly: np.ndarray, local_day: np.ndarray, days: list[int]) -> np.ndarray:
    """Daily sums, (stations, days) from (stations, hours): complete local days only."""
    out = np.full((hourly.shape[0], len(days)), np.nan)
    for k, d in enumerate(days):
        sel = local_day == d
        if sel.sum() < 23:  # a DST day has 23 hours
            continue
        block = hourly[:, sel]
        full = np.isfinite(block).all(axis=1)
        out[:, k] = np.where(full, np.nansum(block, axis=1), np.nan)
    return out


def build_report(args, stations, station, om, archive, old_et, local_day, month, days, years, table) -> str:
    sources = {"NBM": om[MODELS[0]], "best_match": om[MODELS[1]], "merged": om["merged"], "archive (v2)": archive}
    day_month = np.array([date.fromordinal(d).month for d in days])
    day_year = np.array([date.fromordinal(d).year for d in days])
    growing = np.isin(day_month, GROWING)
    lines = [
        "# Open-Meteo against Wisconet",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_openmeteo_wisconet.py`, {args.start} to "
        f"{args.end}, at {len(stations)} Wisconet stations. Open-Meteo from its historical-forecast API at each "
        f"station's location: `{MODELS[0]}`, `{MODELS[1]}`, and the two merged hour by hour ({MODELS[0]} first, as "
        "v2's points and WISP use them). The archive is v2's grid at the station's cell. Ratios are totals over the "
        "days both have.",
        "",
        "## Coverage",
        "",
        "| Source | hours with temperature | with shortwave | with RH |",
        "|---|---|---|---|",
    ]
    for name, s in sources.items():
        lines.append(
            f"| {name} | {np.isfinite(s['t']).mean():.3f} | {np.isfinite(s['sw']).mean():.3f} "
            f"| {np.isfinite(s['rh']).mean():.3f} |"
        )

    # Shortwave, daily totals
    obs_sw = daily(station["sw"], local_day, days) * 0.0036
    lines += [
        "",
        "## Daily shortwave (MJ/m²)",
        "",
        "| Source | ratio, all | ratio, Apr–Oct | MAE | by month (ratio) |",
        "|---|---|---|---|---|",
    ]
    sw_sources = dict(sources) | {"merged, corrected": {"sw": om["merged"]["sw_corrected"]}}
    for name, s in sw_sources.items():
        model = daily(s["sw"], local_day, days) * 0.0036
        ok = np.isfinite(model) & np.isfinite(obs_sw)
        g = ok & growing[None]
        in_month = [ok & (day_month == m)[None] for m in range(1, 13)]
        by_month = " ".join(
            f"{MONTHS[m]} {model[sel].sum() / obs_sw[sel].sum():.2f}" for m, sel in enumerate(in_month) if sel.any()
        )
        lines.append(
            f"| {name} | {model[ok].sum() / obs_sw[ok].sum():.3f} | {model[g].sum() / obs_sw[g].sum():.3f} "
            f"| {np.mean(np.abs(model[ok] - obs_sw[ok])):.2f} | {by_month} |"
        )
    middles, factor = table
    held = (day_year != args.fit_year) & (day_year >= date.fromisoformat(args.start).year)
    model = daily(om["merged"]["sw_corrected"], local_day, days) * 0.0036
    ok = np.isfinite(model) & np.isfinite(obs_sw) & held[None]
    raw = daily(om["merged"]["sw"], local_day, days) * 0.0036
    lines += [
        "",
        f"The merged series' correction fitted on {args.fit_year}, for the held-out check (`--fit` writes "
        "`agdata/data/openmeteo_shortwave_correction.json` refitted on every year):",
        "",
        "| Clearness | " + " | ".join(f"{m:.2f}" for m in middles) + " |",
        "|---|" + "---|" * len(middles),
        "| Factor | " + " | ".join(f"{f:.2f}" for f in factor) + " |",
        "",
        f"Held out ({', '.join(str(y) for y in sorted(set(day_year[held])))}): "
        f"ratio {raw[ok].sum() / obs_sw[ok].sum():.3f} "
        f"→ {model[ok].sum() / obs_sw[ok].sum():.3f}, daily MAE {np.mean(np.abs(raw[ok] - obs_sw[ok])):.2f} → "
        f"{np.mean(np.abs(model[ok] - obs_sw[ok])):.2f} MJ/m².",
    ]

    # Temperature and humidity, hourly
    lines += [
        "",
        "## Hourly temperature and humidity",
        "",
        "RH is Open-Meteo's `relative_humidity_2m`, and RH from its temperature and dew point as v2 derives it. "
        "Humid hours per day are over complete local days, May–September; the threshold is the RH at or above which "
        "the source counts as many hours as the stations' RH ≥ 90% (the archive's: 88%, D50).",
        "",
        "| Source | temperature bias (°C) | RH bias | RH MAE | RH ≥ 90 h/day (station) | threshold |",
        "|---|---|---|---|---|---|",
    ]
    summer = np.isin(month, (5, 6, 7, 8, 9))
    st90 = daily(np.where(np.isfinite(station["rh"]), (station["rh"] >= 90).astype(float), np.nan), local_day, days)
    for name, s in sources.items():
        for label, rh in (("", s["rh"]), (", derived", s.get("rh_derived"))):
            if rh is None:
                continue
            ok = np.isfinite(rh) & np.isfinite(station["rh"])
            tok = np.isfinite(s["t"]) & np.isfinite(station["t"])
            hours90 = daily(np.where(np.isfinite(rh), (rh >= 90).astype(float), np.nan), local_day, days)
            both = np.isfinite(hours90) & np.isfinite(st90) & np.isin(day_month, (5, 6, 7, 8, 9))[None]
            sel = ok & summer[None]
            share = np.mean(station["rh"][sel] >= 90)
            lines.append(
                f"| {name}{label} | {np.mean(s['t'][tok] - station['t'][tok]):+.2f} "
                f"| {np.mean(rh[ok] - station['rh'][ok]):+.1f} | {np.mean(np.abs(rh[ok] - station['rh'][ok])):.1f} "
                f"| {hours90[both].mean():.2f} ({st90[both].mean():.2f}) | {np.quantile(rh[sel], 1 - share):.1f} |"
            )

    # The RH map, held out
    held_hours = (years != args.fit_year)[None, :] & summer[None, :]
    held_days = (day_year != args.fit_year)[None, :] & np.isin(day_month, (5, 6, 7, 8, 9))[None, :]
    lines += [
        "",
        f"The merged series' RH mapped onto the archive's, fitted on {args.fit_year} and held out, May–September "
        "(`--fit` writes `agdata/data/openmeteo_rh_map.json` refitted on every year; fitted on 2026 and tested on "
        "2025 instead, the map lands 0.2 h a day over the archive at RH ≥ 88%, where this way it's 1.2 under: "
        "Open-Meteo's humidity changes from year to year):",
        "",
        "| RH | RH ≥ 90 h/day | RH ≥ 88 h/day | bias against the archive | MAE against the stations |",
        "|---|---|---|---|---|",
    ]
    for label, rh in (
        ("stations", station["rh"]),
        ("archive", archive["rh"]),
        ("Open-Meteo, derived", om["merged"]["rh_derived"]),
        ("Open-Meteo, mapped", om["merged"]["rh_mapped"]),
    ):
        counts = []
        for threshold in (90, 88):
            hours = daily(np.where(np.isfinite(rh), (rh >= threshold).astype(float), np.nan), local_day, days)
            counts.append(np.nanmean(np.where(held_days, hours, np.nan)))
        ok = held_hours & np.isfinite(rh) & np.isfinite(archive["rh"])
        ok_st = held_hours & np.isfinite(rh) & np.isfinite(station["rh"])
        lines.append(
            f"| {label} | {counts[0]:.2f} | {counts[1]:.2f} | {np.mean(rh[ok] - archive['rh'][ok]):+.1f} "
            f"| {np.mean(np.abs(rh[ok_st] - station['rh'][ok_st])):.1f} |"
        )

    # ET0, daily
    obs_et = daily(station["et0"], local_day, days)
    lines += [
        "",
        "## Daily ET0 (mm), against FAO-56 from the stations' measurements",
        "",
        "| Source | ratio, Apr–Oct | MAE, Apr–Oct | ratio, all | by month, Apr–Oct (ratio) |",
        "|---|---|---|---|---|",
    ]
    et_sources = {
        "Open-Meteo's own (merged; WISP's)": daily(om["merged"]["et0_om"], local_day, days),
        "Open-Meteo's own, NBM": daily(om[MODELS[0]]["et0_om"], local_day, days),
        "Open-Meteo's own, best_match": daily(om[MODELS[1]]["et0_om"], local_day, days),
        "ours from Open-Meteo (merged; v2's points)": daily(om["merged"]["et0_ours"], local_day, days),
        "ours from Open-Meteo, shortwave corrected": daily(om["merged"]["et0_corrected"], local_day, days),
        "archive (v2, corrected shortwave)": daily(archive["et0"], local_day, days),
        "old API": old_et,
    }
    for name, model in et_sources.items():
        ok = np.isfinite(model) & np.isfinite(obs_et)
        g = ok & growing[None]
        by_month = " ".join(
            f"{MONTHS[m - 1]} {model[g & (day_month == m)[None]].sum() / obs_et[g & (day_month == m)[None]].sum():.2f}"
            for m in GROWING
            if (g & (day_month == m)[None]).any()
        )
        lines.append(
            f"| {name} | {model[g].sum() / obs_et[g].sum():.3f} | {np.mean(np.abs(model[g] - obs_et[g])):.2f} "
            f"| {model[ok].sum() / obs_et[ok].sum():.3f} | {by_month} |"
        )
    g = np.isfinite(obs_et) & growing[None]
    lines += [
        "",
        f"The stations' FAO-56 ET0 averages {obs_et[g].mean():.2f} mm a day over Apr–Oct ({g.sum():,} station-days).",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
