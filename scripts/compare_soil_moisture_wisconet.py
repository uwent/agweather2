"""Soil moisture against Wisconet's stations (Phase 6 step 6, F9): ERA5-Land (Open-Meteo's archive endpoint, the
archive's source, D52) and IFS (Open-Meteo's historical-forecast endpoint: what fills the archive's last days and the
forecast) at each station, by depth and season, with frozen hours apart; HRRR's analysis on a sample of days if
`--hrrr` names its file (`scripts/fetch_hrrr_soil_moisture.py`; HRRR isn't part of the archive).

Wisconet's CS655 sensors sit at 5, 10, 20, 50 and 100 cm (named 2, 4, 8, 20 and 40 in), hourly averages stamped at
the hour's end. The hourly fields are named `pct` but hold volumetric water content as a fraction (m³/m³), as the
daily `m3m-3` fields do. A CS655 measures the soil's permittivity, which sees liquid water only: in frozen soil it
reads the unfrozen water, a fraction of the total, while ERA5-Land and IFS carry soil water whether frozen or not. So
hours with the station's soil at or below FROZEN_C at the sensor (or, without a station reading, ERA5-Land's layer)
count as frozen and are left out of every table but the frozen column.

Modeled soil water is the model's soil over a ~9 km cell (its texture from a global map), not the station's, so a
station's level can differ from the model's for the whole record. Besides bias and MAE, the tables give the MAE with
each station's own mean difference taken out, and the median over stations of the correlation (Pearson and rank) of
daily means: what a percentile against the archive's own years depends on.

    uv run python scripts/compare_soil_moisture_wisconet.py --start 2025-01-01 --end 2026-11-17 \
        --cache tmp/soil-moisture --hrrr tmp/soil-moisture/hrrr_soilw.npz

`--fit-seam` writes the moisture layers' seam weights (D55's method) into `agdata/data/ifs_soil_seam.json`. `--quiet`
prints only warnings, failures and the summary.
"""

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_openmeteo_wisconet import cell, dotenv

from agdata import soil_seam
from agdata.clients.openmeteo_points import OpenMeteoPoints
from agdata.clients.wisconet import CENTRAL, Wisconet
from agdata.grid import service_window
from agdata.progress import Reporter

HOUR = timedelta(hours=1)
STATION_DEPTHS = {2: 5.0, 4: 10.0, 8: 20.0, 20: 50.0, 40: 100.0}  # Wisconet's name (in) → sensor depth (cm)
LAYERS = {  # Open-Meteo's layer → (top, bottom) in cm; ERA5-Land's 4th layer runs to 289 cm, Open-Meteo names it 255
    "0_to_7cm": (0, 7),
    "7_to_28cm": (7, 28),
    "28_to_100cm": (28, 100),
    "100_to_255cm": (100, 255),
}
MIDDLES = {name: (top + bottom) / 2 for name, (top, bottom) in LAYERS.items()}
COMPARED = (5.0, 10.0, 20.0, 50.0)  # the sensors set against the top three layers
FROZEN_C = 0.5  # soil at or below this at the sensor counts as frozen
VALID = (0.02, 0.65)  # m³/m³: a CS655's readings outside this are faults
SPIKE = 0.08  # m³/m³: an hour this far from both neighbours, in opposite directions, is a spike
SEASONS = {"Mar–May": (3, 4, 5), "Jun–Aug": (6, 7, 8), "Sep–Nov": (9, 10, 11), "Dec–Feb": (12, 1, 2)}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SEAM_LEADS = np.arange(0, 25 * 24 + 1, 6)  # the provisional hours (up to 14 days) and the forecast (10), 6-hourly
HRRR_DEPTHS = {5.0: (4, 4), 10.0: (10, 10), 20.0: (10, 30), 50.0: (30, 60)}  # sensor → HRRR levels between (cm)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive (ERA5-Land's last whole day)")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument(
        "--cache", default="tmp/soil-moisture", help="where the stations' and Open-Meteo's responses are cached"
    )
    parser.add_argument("--hrrr", help="HRRR's SOILW at the stations (npz: times, stations, levels, values)")
    parser.add_argument("--out", default="docs/validation/weather/soil-moisture.md")
    parser.add_argument(
        "--fit-seam",
        action="store_true",
        help=f"fit the moisture layers' seam weights on every year and write them into {soil_seam.TABLE_PATH.name} (temperature's kept)",
    )
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last:
        parser.error("--start must not be after --end")
    cache = Path(args.cache)
    window = service_window(args.box)
    wisconet = Wisconet(cache_dir=cache / "wisconet")
    stations = [s for s in wisconet.stations() if (c := cell(s)) is not None and window.contains(*c)]
    if not stations:
        report.fail("stations", f"no Wisconet stations inside the {args.box} box")
        sys.exit(1)
    start = datetime(first.year, first.month, first.day, tzinfo=UTC)
    n = ((last - first).days + 1) * 24
    report.step(
        f"soil moisture against Wisconet, {first} to {last}: {len(stations)} stations, {n} hours; writing {args.out}"
    )
    times = [start + (k + 1) * HOUR for k in range(n)]

    moisture, temperature = station_soil(wisconet, stations, start, n, report)
    era5 = openmeteo(stations, first, last, start, n, "archive", "era5_land", cache, report, with_temperature=True)
    ifs = openmeteo(stations, first, last, start, n, "historical", "ecmwf_ifs", cache, report)
    frozen = {
        depth: np.where(
            np.isfinite(temperature[depth]),
            temperature[depth] <= FROZEN_C,
            era5[f"soil_temperature_{layer_of(depth)}"] <= FROZEN_C,
        )
        for depth in STATION_DEPTHS.values()
    }
    local = [(t - HOUR).astimezone(CENTRAL) for t in times]
    local_day = np.array([t.date().toordinal() for t in local])
    month = np.array([t.month for t in local])
    hrrr = load_hrrr(Path(args.hrrr), stations, start, n, report) if args.hrrr else None
    report.step("building the report")
    text = build_report(args, stations, moisture, frozen, era5, ifs, hrrr, times, local_day, month, report)
    report.step(f"writing {args.out} (overwriting)")
    Path(args.out).write_text(text)
    report.step(f"wrote {args.out}")
    if not report.finish(f"{len(stations)} stations, {n} hours"):
        sys.exit(1)


def layer_of(depth: float) -> str:
    """The layer holding a depth (a sensor on a boundary, 100 cm, goes to the layer above)."""
    for name, (top, bottom) in LAYERS.items():
        if top < depth <= bottom:
            return name
    raise ValueError(f"no layer holds {depth} cm")


def station_soil(
    wisconet: Wisconet, stations, start: datetime, n: int, report: Reporter
) -> tuple[dict[float, np.ndarray], dict[float, np.ndarray]]:
    """Each station's hourly soil moisture (m³/m³, QC'd) and temperature (°C) by sensor depth (cm), on the hours
    ending start + 1 h, …"""
    moisture_ids = {wisconet.field_id(f"60min_soil_moisture_pct_avg@{name}in"): d for name, d in STATION_DEPTHS.items()}
    temperature_ids = {wisconet.field_id(f"60min_soil_temp_f_avg@{name}in"): d for name, d in STATION_DEPTHS.items()}
    fields = [f"60min_soil_moisture_pct_avg@{name}in" for name in STATION_DEPTHS]
    fields += [f"60min_soil_temp_f_avg@{name}in" for name in STATION_DEPTHS]
    moisture = {d: np.full((len(stations), n), np.nan) for d in STATION_DEPTHS.values()}
    temperature = {d: np.full((len(stations), n), np.nan) for d in STATION_DEPTHS.values()}
    end = start + n * HOUR
    for k, s in enumerate(stations):
        report.progress("stations", k + 1, len(stations))
        for year in range(start.year, (end - HOUR).year + 1):
            lo = max(start, datetime(year, 1, 1, tzinfo=UTC))
            hi = min(end, datetime(year + 1, 1, 1, tzinfo=UTC)) + HOUR
            key = f"{s['station_id']}_{year}_{lo:%m%d}-{hi:%m%d}_60min_soil_moisture.json"
            try:
                rows = wisconet.measures(s["station_id"], lo, hi, fields, cache_key=key)
            except Exception as error:
                report.fail(f"{s['station_id']} {year}", error)
                continue
            for row in rows:
                t = int((row["collection_time"] - start.timestamp()) // 3600) - 1
                if not 0 <= t < n:
                    continue
                for fid, value in row["measures"]:
                    if value is None:
                        continue
                    if fid in moisture_ids:
                        moisture[moisture_ids[fid]][k, t] = value
                    elif fid in temperature_ids:
                        temperature[temperature_ids[fid]][k, t] = (value - 32) / 1.8
    for depth, values in moisture.items():
        moisture[depth] = qc(values)
    return moisture, temperature


def qc(values: np.ndarray) -> np.ndarray:
    """Wisconet doesn't QC its soil: drop readings out of range, and hours that jump from both neighbours in opposite
    directions (a sensor's spike; rain raises the water and it drains over days, not the next hour)."""
    v = np.where((values >= VALID[0]) & (values <= VALID[1]), values, np.nan)
    before = v - np.roll(v, 1, axis=1)
    after = v - np.roll(v, -1, axis=1)
    spike = (np.abs(before) > SPIKE) & (np.abs(after) > SPIKE) & (np.sign(before) == np.sign(after))
    return np.where(spike, np.nan, v)


def openmeteo(
    stations,
    first: date,
    last: date,
    start: datetime,
    n: int,
    endpoint: str,
    model: str,
    cache: Path,
    report: Reporter,
    with_temperature: bool = False,
) -> dict[str, np.ndarray]:
    """A model's soil moisture layers (m³/m³), and temperature (°C) if asked, at the stations, a year per request."""
    key = os.environ.get("OPEN_METEO_API_KEY") or dotenv("OPEN_METEO_API_KEY")
    client = OpenMeteoPoints(endpoint=endpoint, cache_dir=cache / "openmeteo", api_key=key)
    groups = [[f"soil_moisture_{layer}" for layer in LAYERS]]  # a request each (the cache's file names)
    if with_temperature:
        groups.append([f"soil_temperature_{layer}" for layer in list(LAYERS)[:3]])
    out = {v: np.full((len(stations), n), np.nan) for group in groups for v in group}
    locations = [(s["latitude"], s["longitude"]) for s in stations]
    for year, variables in ((y, g) for y in range(first.year, last.year + 1) for g in groups):
        lo, hi = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        report.step(f"Open-Meteo {model} ({endpoint}) {year}: {len(locations)} locations, {lo} to {hi}")
        for k, block in enumerate(client.hourly(locations, lo, hi, variables, model=model)):
            index = (np.asarray(block["time"], dtype=np.int64) - int(start.timestamp())) // 3600 - 1
            ok = (index >= 0) & (index < n)
            for v in variables:
                series = np.array([np.nan if x is None else x for x in block.get(v, [])], dtype=float)
                if series.size:
                    out[v][k, index[ok]] = series[ok]
    return {name.replace("soil_moisture_", ""): v for name, v in out.items()}


def load_hrrr(path: Path, stations, start: datetime, n: int, report: Reporter) -> dict[float, np.ndarray]:
    """HRRR's SOILW at the stations, on the archive's hours (NaN but on the sampled ones), at the sensors' depths
    (linear between HRRR's levels)."""
    with np.load(path) as f:
        ids, levels, values, stamps = list(f["stations"]), list(f["levels"]), f["values"], f["times"]
    report.step(f"HRRR: {len(stamps)} sampled hours from {path}")
    out = {depth: np.full((len(stations), n), np.nan) for depth in HRRR_DEPTHS}
    rows = [ids.index(s["station_id"]) if s["station_id"] in ids else -1 for s in stations]
    for k_time, stamp in enumerate(stamps):
        t = int((int(stamp) - start.timestamp()) // 3600) - 1
        if not 0 <= t < n:
            continue
        for depth, (a, b) in HRRR_DEPTHS.items():
            w = 0.0 if a == b else (depth - a) / (b - a)
            value = values[k_time, :, levels.index(a)] * (1 - w) + values[k_time, :, levels.index(b)] * w
            for k, row in enumerate(rows):
                if row >= 0:
                    out[depth][k, t] = value[row]
    return out


def interpolated(source: dict[str, np.ndarray], depth: float) -> np.ndarray:
    """A source at a depth, linear between its top three layers' middles (3.5, 17.5, 64 cm), as soil temperature
    is taken to its depths; held at the top layer's above 3.5 cm."""
    names = list(LAYERS)[:3]
    middles = np.array([MIDDLES[name] for name in names])
    if depth <= middles[0]:
        return source[names[0]]
    k = int(np.clip(np.searchsorted(middles, depth) - 1, 0, len(middles) - 2))
    w = (depth - middles[k]) / (middles[k + 1] - middles[k])
    return source[names[k]] * (1 - w) + source[names[k + 1]] * w


def daily_mean(hourly: np.ndarray, local_day: np.ndarray, days: list[int]) -> np.ndarray:
    """Daily means (stations, days) of local days with at least 20 hours."""
    out = np.full((hourly.shape[0], len(days)), np.nan)
    order = np.argsort(local_day, kind="stable")
    bounds = np.searchsorted(local_day[order], [*days, days[-1] + 1])
    for k in range(len(days)):
        block = hourly[:, order[bounds[k] : bounds[k + 1]]]
        count = np.isfinite(block).sum(axis=1)
        with np.errstate(invalid="ignore"):
            out[:, k] = np.where(count >= 20, np.nansum(block, axis=1) / np.maximum(count, 1), np.nan)
    return out


def rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    out = np.empty(len(values))
    out[order] = np.arange(len(values))
    return out


def per_station_r(
    model: np.ndarray, observed: np.ndarray, sel: np.ndarray, minimum: int = 60
) -> tuple[float, float, int]:
    """The median over stations of Pearson's and Spearman's r between model and station (rows), over the columns
    `sel` allows where both are finite; with the number of stations that had `minimum` values."""
    pearson, spearman = [], []
    for k in range(model.shape[0]):
        ok = sel[k] & np.isfinite(model[k]) & np.isfinite(observed[k])
        if ok.sum() < minimum or np.std(model[k][ok]) == 0 or np.std(observed[k][ok]) == 0:
            continue
        pearson.append(np.corrcoef(model[k][ok], observed[k][ok])[0, 1])
        spearman.append(np.corrcoef(rank(model[k][ok]), rank(observed[k][ok]))[0, 1])
    if not pearson:
        return np.nan, np.nan, 0
    return float(np.median(pearson)), float(np.median(spearman)), len(pearson)


def errors(model: np.ndarray, observed: np.ndarray, sel: np.ndarray, minimum: int = 100) -> tuple[float, float, float]:
    """Bias, MAE and the MAE with each station's own mean difference taken out (m³/m³)."""
    ok = sel & np.isfinite(model) & np.isfinite(observed)
    if ok.sum() < minimum:
        return np.nan, np.nan, np.nan
    d = np.where(ok, model - observed, np.nan)
    counts = np.isfinite(d).sum(axis=1, keepdims=True)  # a station with none has no bias of its own (NaN)
    station_bias = np.nansum(d, axis=1, keepdims=True) / np.where(counts > 0, counts, np.nan)
    return float(np.nanmean(d)), float(np.nanmean(np.abs(d))), float(np.nanmean(np.abs(d - station_bias)))


def fmt(x: float, places: int = 3, sign: bool = False) -> str:
    if not np.isfinite(x):
        return "—"
    return f"{x:+.{places}f}" if sign else f"{x:.{places}f}"


def build_report(args, stations, moisture, frozen, era5, ifs, hrrr, times, local_day, month, report: Reporter) -> str:
    days = sorted(set(local_day.tolist()))
    day_month = np.array([date.fromordinal(d).month for d in days])
    have = {d: int(np.isfinite(v).any(axis=1).sum()) for d, v in moisture.items()}
    sources = {"ERA5-Land": era5, "IFS": ifs}
    lines = [
        "# Soil moisture against Wisconet",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_soil_moisture_wisconet.py`, {args.start} to {args.end}, at {len(stations)} Wisconet stations (with a moisture sensor at 5 cm: {have[5.0]}, 10: {have[10.0]}, 20: {have[20.0]}, 50: {have[50.0]}, 100: {have[100.0]}). ERA5-Land is Open-Meteo's `era5_land` (archive API), the archive's source; IFS is Open-Meteo's `ecmwf_ifs` from its historical-forecast API (each run's first hours: the model's own soil climate, not its forecast skill at long leads), both at the station's location. Water content is volumetric, m³/m³ (0.30 is 30% of the soil's volume). Bias is the source minus the station.",
        "",
        f"The stations' CS655 sensors see only liquid water, so in frozen soil they read low while the models carry the frozen water too. Hours with the station's soil at the sensor at or below {FROZEN_C} °C (ERA5-Land's layer where the station has no temperature) are counted as frozen and left out of every table but the frozen column. Readings outside {VALID[0]}–{VALID[1]} m³/m³ and one-hour spikes of more than {SPIKE} are dropped; Wisconet doesn't QC its soil data.",
        "",
        "Modeled soil water is for the model's soil over a ~9 km cell, with its texture from a global map, not the station's soil. Two columns judge the sources apart from that: the MAE with each station's own mean difference taken out (\"MAE, own bias out\"), and the median over stations of the correlation of daily means with the station's (Pearson r, and rank r: what a percentile against other years depends on).",
        "",
    ]

    lines += conclusions(moisture, frozen, era5, ifs, hrrr, local_day, days)

    # Depth mapping: the layer holding the sensor, or linear between the layers' middles
    lines += [
        "## By depth: layer or interpolated (unfrozen hours)",
        "",
        "Each sensor against the layer that holds it (5 cm in 0–7, 10 and 20 cm in 7–28, 50 cm in 28–100), and against the layers taken to the sensor's depth linearly between their middles (3.5, 17.5 and 64 cm), as soil temperature is.",
        "",
        "| Sensor | Source | taken as | bias | MAE | MAE, own bias out | Pearson r (daily) | rank r (daily) | stations |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    daily_obs = {d: daily_mean(np.where(frozen[d], np.nan, moisture[d]), local_day, days) for d in COMPARED}
    for depth in COMPARED:
        thawed = ~frozen[depth]
        for name, source in sources.items():
            for how, values in (("layer", source[layer_of(depth)]), ("interpolated", interpolated(source, depth))):
                bias, mae, own = errors(values, moisture[depth], thawed)
                pr, sr, count = per_station_r(
                    daily_mean(values, local_day, days), daily_obs[depth], np.ones_like(daily_obs[depth], dtype=bool)
                )
                lines.append(
                    f"| {depth:g} cm | {name} | {how} | {fmt(bias, sign=True)} | {fmt(mae)} | {fmt(own)} | {fmt(pr, 2)} | {fmt(sr, 2)} | {count} |"
                )
    lines += [
        "",
        "The 100 cm sensor sits on the boundary between the third and fourth layers:",
        "",
        "| Sensor | Source | layer | bias | MAE | MAE, own bias out | Pearson r (daily) | rank r (daily) | stations |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    obs100 = daily_mean(np.where(frozen[100.0], np.nan, moisture[100.0]), local_day, days)
    for name, source in sources.items():
        for layer in ("28_to_100cm", "100_to_255cm"):
            bias, mae, own = errors(source[layer], moisture[100.0], ~frozen[100.0])
            pr, sr, count = per_station_r(
                daily_mean(source[layer], local_day, days), obs100, np.ones_like(obs100, dtype=bool)
            )
            lines.append(
                f"| 100 cm | {name} | {layer.replace('_to_', '–')} | {fmt(bias, sign=True)} | {fmt(mae)} | {fmt(own)} | {fmt(pr, 2)} | {fmt(sr, 2)} | {count} |"
            )

    # Seasons, frozen apart
    lines += [
        "",
        "## By season (bias / MAE, m³/m³; each sensor against the layer that holds it)",
        "",
        "Seasons count unfrozen hours only; the frozen column is every frozen hour, to show what the sensors do then.",
        "",
        "| Sensor | Source | " + " | ".join(SEASONS) + " | frozen | station mean, unfrozen |",
        "|---|---|" + "---|" * len(SEASONS) + "---|---|",
    ]
    for depth in COMPARED:
        thawed = ~frozen[depth]
        observed = moisture[depth]
        for name, source in sources.items():
            values = source[layer_of(depth)]
            cells = []
            for m in SEASONS.values():
                bias, mae, _ = errors(values, observed, thawed & np.isin(month, m)[None, :])
                cells.append(f"{fmt(bias, sign=True)} / {fmt(mae)}")
            bias, mae, _ = errors(values, observed, frozen[depth])
            cells.append(f"{fmt(bias, sign=True)} / {fmt(mae)}")
            mean = np.nanmean(np.where(thawed, observed, np.nan))
            lines.append(f"| {depth:g} cm | {name} | " + " | ".join(cells) + f" | {mean:.3f} |")
    share = {d: np.nanmean(np.where(np.isfinite(moisture[d]), frozen[d], np.nan)) for d in COMPARED}
    lines += [
        "",
        "Share of the stations' hours counted as frozen: "
        + ", ".join(f"{d:g} cm {share[d]:.0%}" for d in COMPARED)
        + ".",
    ]

    # Correlation by season of daily means
    lines += [
        "",
        "## Correlation by season (median over stations of Pearson r of daily means, unfrozen days)",
        "",
        "| Sensor | Source | all | " + " | ".join(SEASONS) + " |",
        "|---|---|---|" + "---|" * len(SEASONS),
    ]
    for depth in COMPARED:
        for name, source in sources.items():
            model_daily = daily_mean(source[layer_of(depth)], local_day, days)
            cells = [fmt(per_station_r(model_daily, daily_obs[depth], np.ones_like(model_daily, dtype=bool))[0], 2)]
            for m in SEASONS.values():
                sel = np.broadcast_to(np.isin(day_month, m)[None, :], model_daily.shape)
                cells.append(fmt(per_station_r(model_daily, daily_obs[depth], sel, minimum=30)[0], 2))
            lines.append(f"| {depth:g} cm | {name} | " + " | ".join(cells) + " |")

    # Each station's mean difference: is it the cell's soil?
    lines += [
        "",
        "## Each station's mean difference (unfrozen hours, m³/m³)",
        "",
        "The spread of the stations' own mean differences: how much of the MAE is a lasting difference of level between the model's cell and the station's soil.",
        "",
        "| Sensor | Source | lowest | 10th pct | median | 90th pct | highest |",
        "|---|---|---|---|---|---|---|",
    ]
    for depth in COMPARED:
        for name, source in sources.items():
            d = np.where(~frozen[depth], source[layer_of(depth)] - moisture[depth], np.nan)
            counts = np.isfinite(d).sum(axis=1)
            means = np.array([np.nanmean(row) for row in d[counts >= 500]])
            if means.size:
                q = np.quantile(means, (0, 0.1, 0.5, 0.9, 1))
                lines.append(f"| {depth:g} cm | {name} | " + " | ".join(fmt(x, sign=True) for x in q) + " |")

    # The seam
    lines += seam_section(era5, ifs, times, month, report, fit_seam=args.fit_seam)

    if hrrr is not None:
        lines += hrrr_section(hrrr, moisture, frozen, era5, ifs)
    lines.append("")
    return "\n".join(lines)


def conclusions(moisture, frozen, era5, ifs, hrrr, local_day, days) -> list[str]:
    """The report's findings, with their numbers from the tables below."""
    found = {}
    for depth in COMPARED:
        observed = daily_mean(np.where(frozen[depth], np.nan, moisture[depth]), local_day, days)
        everywhere = np.ones_like(observed, dtype=bool)
        for name, source in (("ERA5-Land", era5), ("IFS", ifs)):
            values = source[layer_of(depth)]
            bias, mae, own = errors(values, moisture[depth], ~frozen[depth])
            r = per_station_r(daily_mean(values, local_day, days), observed, everywhere)[0]
            layered = per_station_r(daily_mean(interpolated(source, depth), local_day, days), observed, everywhere)[0]
            found[name, depth] = (bias, mae, own, r, layered)
    frozen_bias = errors(era5["0_to_7cm"], moisture[5.0], frozen[5.0])[0]
    thawed_bias = found["ERA5-Land", 5.0][0]
    step = {layer: float(np.nanmean(era5[layer] - ifs[layer])) for layer in list(LAYERS)[:3]}
    e, i = (lambda k: found["ERA5-Land", k]), (lambda k: found["IFS", k])
    span = lambda values, places=3: f"{min(values):.{places}f}–{max(values):.{places}f}"  # noqa: E731
    lines = [
        "## Conclusions",
        "",
        f"- **ERA5-Land is the better source of the two, by timing.** Its daily soil water follows the stations' better at every depth (median r {span([e(d)[3] for d in COMPARED], 2)} against IFS's {span([i(d)[3] for d in COMPARED], 2)}); IFS is weakest in summer and at 50 cm. ERA5-Land reads wetter than the stations ({span([e(d)[0] for d in COMPARED])} m³/m³ on average, MAE {span([e(d)[1] for d in COMPARED])}), but most of that is a lasting difference of level at each station: with each station's own mean difference taken out, its MAE is {span([e(d)[2] for d in COMPARED])} m³/m³.",
        "- **The level at a place is not a field's.** The stations' own mean differences run from about −0.2 to +0.3 m³/m³ in either model (the model's soil for its ~9 km cell against the station's): a map of water content shows where soils are wetter or drier than usual only roughly, and a value at a site can be off by a soil's whole range. A percentile against the archive's own years (the next step) depends only on timing, where ERA5-Land does well.",
        f"- **Layers, not depths.** Interpolating between the layers' middles, as soil temperature is, changes ERA5-Land's r by no more than {max(abs(v[4] - v[3]) for (name, _), v in found.items() if name == 'ERA5-Land'):.2f} at any depth (IFS's by up to {max(abs(v[4] - v[3]) for (name, _), v in found.items() if name == 'IFS'):.2f}, at 50 cm), so the archive keeps each layer's water as the model computes it (0–7, 7–28 and 28–100 cm), which is also what plant-available water needs.",
        f"- **Frozen soil.** About a fifth of the shallow sensors' hours are frozen, when the sensors see only the unfrozen water: ERA5-Land reads {frozen_bias:+.2f} m³/m³ above them then, against {thawed_bias:+.2f} in thawed hours. Winter values compare with nothing on the ground; the archive carries the models' total water.",
        f"- **IFS needs the seam shift.** IFS is drier than ERA5-Land by {span(list(step.values()), 2)} m³/m³ on average (from May to December most), and the difference lasts for weeks. Shifting IFS by the difference in ERA5-Land's last hour, faded by D55's fitted weights, cuts the difference 3 days on by about half in the top layer and by about 70% and 90% in the two below it (the seam table below).",
    ]
    if hrrr is not None:
        lines.append(
            "- **HRRR isn't better.** On a sample of days its analysed soil water is drier than the stations and correlates with them no better than ERA5-Land at any depth (its own table, at the end), so it isn't added as a source."
        )
    return [*lines, ""]


def seam_section(era5, ifs, times, month, report: Reporter, fit_seam: bool = False) -> list[str]:
    lines = [
        "",
        "## ERA5-Land minus IFS: the step at the seam",
        "",
        "Where the archive hands over from ERA5-Land to IFS (its last hour, ~5 days behind), the soil water steps by ERA5-Land − IFS. By month, the mean over the stations' cells, and the spread of the stations' own means over the whole period:",
        "",
        "| Layer | " + " | ".join(MONTHS) + " | stations' means: 10th / median / 90th pct |",
        "|---|" + "---|" * 12 + "---|",
    ]
    for layer in list(LAYERS)[:3]:
        d = era5[layer] - ifs[layer]
        cells = []
        for m in range(1, 13):
            sel = (month == m)[None, :] & np.isfinite(d)
            cells.append(fmt(float(d[sel].mean()), 2, sign=True) if sel.any() else "—")
        with np.errstate(invalid="ignore"):
            means = np.nanmean(d, axis=1)
        q = np.nanquantile(means, (0.1, 0.5, 0.9))
        lines.append(
            f"| {layer.replace('_to_', '–')} | "
            + " | ".join(cells)
            + f" | {' / '.join(fmt(x, 2, sign=True) for x in q)} |"
        )
    first_year = np.array([t.year == times[0].year for t in times])
    lines += [
        "",
        f"How much of the step is still there later: the weight on the difference in ERA5-Land's last hour that best predicts the difference at each lead (`agdata.soil_seam.fit`, as D55 fitted it for temperature), fitted on {times[0].year}'s hours and tested on the later ones, with the RMSE (m³/m³) of ERA5-Land − IFS at that lead: unshifted, shifted by the whole difference, and by the fitted weight.",
        "",
        "| Layer | lead (d) | weight | none | whole | weighted |",
        "|---|---|---|---|---|---|",
    ]
    for layer in list(LAYERS)[:3]:
        report.step(f"fitting the seam weights for {layer}")
        d = era5[layer] - ifs[layer]
        w = soil_seam.fit(d, SEAM_LEADS, starts=first_year)
        n = d.shape[1]
        for k, h in enumerate(SEAM_LEADS):
            if h % 72 or h == 0:
                continue
            now, then = d[:, : n - h], d[:, h:]
            ok = np.isfinite(now) & np.isfinite(then) & ~first_year[None, : n - h]
            if not ok.any():
                continue
            lines.append(
                f"| {layer.replace('_to_', '–')} | {h // 24} | {w[k]:.2f} | {rmse(then[ok]):.3f} | {rmse(then[ok] - now[ok]):.3f} | {rmse(then[ok] - w[k] * now[ok]):.3f} |"
            )
    if fit_seam:
        lines += write_seam_table(era5, ifs, times, report)
    return lines


def write_seam_table(era5, ifs, times, report: Reporter) -> list[str]:
    """Fits the moisture layers' seam weights on every year and writes them into the seam table beside soil
    temperature's (kept as they are), as its next version; returns the report's note."""
    table = json.loads(soil_seam.TABLE_PATH.read_text())
    if [int(h) for h in table["lead_hours"]] != [int(h) for h in SEAM_LEADS]:
        report.fail(
            "seam table", f"{soil_seam.TABLE_PATH.name}'s leads aren't this script's; fit temperature again first"
        )
        return []
    stations = int(np.isfinite(era5["0_to_7cm"] - ifs["0_to_7cm"]).any(axis=1).sum())
    for layer in list(LAYERS)[:3]:
        w = soil_seam.fit(era5[layer] - ifs[layer], SEAM_LEADS)
        table["weight"][f"soil_moisture_{layer}"] = [round(float(x), 4) for x in w]
    if not table.get("moisture_fitted"):
        table["version"] = int(table["version"]) + 1
    table["moisture_fitted"] = f"{datetime.now(UTC):%Y-%m-%d}"
    table["moisture_source"] = (
        f"Open-Meteo's era5_land minus its ecmwf_ifs (soil moisture) at {stations} Wisconet stations, {times[0]:%Y-%m-%d} to {times[-1]:%Y-%m-%d}"
    )
    if report.failures:
        report.warn(f"not overwriting {soil_seam.TABLE_PATH} because of the failures above")
        return []
    report.step(f"overwriting the seam table {soil_seam.TABLE_PATH}")
    soil_seam.TABLE_PATH.write_text(json.dumps(table, indent=1) + "\n")
    return [
        "",
        f"The table written (`{soil_seam.TABLE_PATH.name}`, version {table['version']}) holds the moisture layers' weights fitted on every year; soil temperature's are unchanged.",
    ]


def hrrr_section(hrrr, moisture, frozen, era5, ifs) -> list[str]:
    lines = [
        "",
        "## HRRR on a sample of days",
        "",
        "HRRR's analysed soil moisture (`SOILW`, `wrfprs` f00 at 12Z, every third day) at the HRRR point nearest each station, at its levels of 4, 10, 30 and 60 cm (20 cm linear between 10 and 30, 50 cm between 30 and 60), against the station's hour ending 12Z; ERA5-Land and IFS (the layer holding the sensor) on the same hours, for a like comparison. Unfrozen hours. Correlations are the median over stations of r over the sampled hours.",
        "",
        "| Sensor | Source | bias | MAE | MAE, own bias out | Pearson r | rank r | stations |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for depth in COMPARED:
        sampled = np.isfinite(hrrr[depth])
        thawed = ~frozen[depth] & sampled
        observed = moisture[depth]
        for name, values in (
            ("HRRR", hrrr[depth]),
            ("ERA5-Land", era5[layer_of(depth)]),
            ("IFS", ifs[layer_of(depth)]),
        ):
            both = thawed & np.isfinite(era5[layer_of(depth)]) & np.isfinite(ifs[layer_of(depth)])
            bias, mae, own = errors(values, observed, both)
            pr, sr, count = per_station_r(values, observed, both, minimum=40)
            lines.append(
                f"| {depth:g} cm | {name} | {fmt(bias, sign=True)} | {fmt(mae)} | {fmt(own)} | {fmt(pr, 2)} | {fmt(sr, 2)} | {count} |"
            )
    return lines


def rmse(d: np.ndarray) -> float:
    return float(np.sqrt(np.mean(d**2)))


if __name__ == "__main__":
    main()
