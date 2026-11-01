"""Soil temperature against Wisconet's stations (PLAN.md Phase 4 handoff): the archive's soil (ERA5-Land since
D52; HRRR's before), Open-Meteo's IFS (what fills the archive's last days and the forecast) and ERA5-Land (Open-Meteo's
archive endpoint, ~5 days behind) at each station, by depth, season and snow cover. A comparison, not a
basis for correction factors (Ben): a station's soil under snow is insulated, which is real but doesn't stand for
fields the wind has scoured.

Wisconet's CS655 thermistors sit at 5, 10, 20, 50 and 100 cm (named 2, 4, 8, 20 and 40 in), hourly averages
stamped at the hour's end. The potato model's depths are 2, 4 and 8 in, taken from the archive's 4 and 10 cm and
20.3 cm interpolated between 10 and 30 (`agmodels.features`); IFS's 0–7, 7–28 and 28–100 cm layers go to those
depths by `agdata.sources.openmeteo.soil_at_depths`. Each depth is compared with the station's nearest sensor
(5, 10 and 20 cm). A second table sets IFS's raw layers against the stations at the layers' middles, to tell a
layer's error from the interpolation's. Snow cover is IFS's snow depth (Wisconet doesn't measure it).

IFS comes from Open-Meteo's historical-forecast API, which stitches each run's first hours: it's IFS's short-lead
soil, not the 2–11-day leads a forecast hands over to, so it measures the two land-surface models' climates
rather than IFS's forecast skill.

    uv run python tmp/wisconet/fetch_soil.py   # the stations' hours, cached in tmp/wisconet
    uv run python scripts/compare_soil_wisconet.py --start 2025-01-01 --end 2026-10-29
"""

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_openmeteo_wisconet import CACHE, WISCONET, cell, daily, dotenv

from agdata import soil_seam
from agdata.catalog import VARIABLES
from agdata.clients.openmeteo_points import OpenMeteoPoints
from agdata.clients.wisconet import CENTRAL, Wisconet
from agdata.grid import service_window
from agdata.sources.openmeteo import SOIL_LAYERS, soil_at_depths
from agdata.store import HOURLY, GridStore
from agmodels.features import EIGHT_INCHES_CM, KILLING_SOIL_C, soil_between

HOUR = timedelta(hours=1)
STATION_DEPTHS = {2: 5.0, 4: 10.0, 8: 20.0, 20: 50.0, 40: 100.0}  # Wisconet's name (in) → sensor depth (cm)
ARCHIVE = ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm")
POTATO = {"2 in": 5.0, "4 in": 10.0, "8 in": 20.0}  # the potato model's depth → the station sensor compared
SNOW_M = 0.02  # IFS snow depth at or over which an hour counts as snow-covered
SEASONS = {"Dec–Feb": (12, 1, 2), "Mar–May": (3, 4, 5), "Jun–Aug": (6, 7, 8), "Sep–Nov": (9, 10, 11)}
LAGS_DAYS = (1, 2, 3, 5, 7, 9)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-soil.md")
    parser.add_argument(
        "--fit-seam",
        action="store_true",
        help=f"fit IFS's seam weights (Q23) on the first year, test on the rest, write {soil_seam.TABLE_PATH.name} "
        "fitted on every year, and add the test to the report",
    )
    args = parser.parse_args()
    first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    window = service_window(args.box)
    wisconet = Wisconet(cache_dir=WISCONET)
    stations = [s for s in wisconet.stations() if (c := cell(s)) is not None and window.contains(*c)]
    start = datetime(first.year, first.month, first.day, tzinfo=UTC)
    n = ((last - first).days + 1) * 24
    times = [start + (k + 1) * HOUR for k in range(n)]

    station = station_soil(wisconet, stations, start, n)
    ifs_layers, snow = openmeteo_soil(stations, first, last, start, n, "historical", "ecmwf_ifs")
    ifs = {name: value for name, (value, _) in soil_at_depths(ifs_layers).items()}
    era5_layers, _ = openmeteo_soil(stations, first, last, start, n, "archive", "era5_land")
    era5 = {name: value for name, (value, _) in soil_at_depths(era5_layers).items()}
    archive = archive_soil(Path(args.data), stations, start, n)

    # Each source at the potato model's depths, as the model reads it
    at_potato = {
        "archive": potato_depths(archive),
        "IFS": potato_depths(ifs),
        "ERA5-Land": potato_depths(era5),
    }
    local = [(t - HOUR).astimezone(CENTRAL) for t in times]
    local_day = np.array([t.date().toordinal() for t in local])
    month = np.array([t.month for t in local])
    text = report(args, stations, station, at_potato, ifs_layers, snow, archive, local_day, month)
    if args.fit_seam:
        text += fit_seam(archive, ifs, times)
    Path(args.out).write_text(text)
    print(f"wrote {args.out}")


def station_soil(wisconet: Wisconet, stations, start: datetime, n: int) -> dict[float, np.ndarray]:
    """Each station's hourly soil temperature (°C) by sensor depth (cm), on the hours ending start + 1 h, …"""
    ids = {wisconet.field_id(f"60min_soil_temp_f_avg@{name}in"): depth for name, depth in STATION_DEPTHS.items()}
    out = {depth: np.full((len(stations), n), np.nan) for depth in STATION_DEPTHS.values()}
    for k, s in enumerate(stations):
        for year in (start.year, start.year + 1):
            path = WISCONET / f"{s['station_id']}_{year}_60min_soil.json"
            if not path.exists():
                continue
            for row in json.loads(path.read_text()).get("data", []):
                t = int((row["collection_time"] - start.timestamp()) // 3600) - 1
                if not 0 <= t < n:
                    continue
                for fid, value in row["measures"]:
                    if value is not None and fid in ids:
                        out[ids[fid]][k, t] = (value - 32) / 1.8
    for depth, values in out.items():
        out[depth] = qc(values)
    return out


def qc(values: np.ndarray) -> np.ndarray:
    """Wisconet doesn't QC its soil: drop values out of range, and hours that jump from both neighbours (a
    sensor's spike), by more than soil at 5 cm moves in an hour."""
    v = np.where((values > -30) & (values < 50), values, np.nan)
    before = np.abs(v - np.roll(v, 1, axis=1))
    after = np.abs(v - np.roll(v, -1, axis=1))
    return np.where((before > 6) & (after > 6), np.nan, v)


def openmeteo_soil(stations, first: date, last: date, start: datetime, n: int, endpoint: str, model: str):
    """A model's soil layers (°C) and snow depth (m) at the stations from an Open-Meteo endpoint, a year per
    request."""
    key = os.environ.get("OPEN_METEO_API_KEY") or dotenv("OPEN_METEO_API_KEY")
    client = OpenMeteoPoints(endpoint=endpoint, cache_dir=CACHE, api_key=key)
    variables = [*SOIL_LAYERS, "snow_depth"]
    out = {v: np.full((len(stations), n), np.nan) for v in variables}
    locations = [(s["latitude"], s["longitude"]) for s in stations]
    for year in range(first.year, last.year + 1):
        lo, hi = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        for k, block in enumerate(client.hourly(locations, lo, hi, variables, model=model)):
            index = (np.asarray(block["time"], dtype=np.int64) - int(start.timestamp())) // 3600 - 1
            ok = (index >= 0) & (index < n)
            for v in variables:
                series = np.array([np.nan if x is None else x for x in block.get(v, [])], dtype=float)
                if series.size:
                    out[v][k, index[ok]] = series[ok]
    snow = out.pop("snow_depth")
    return out, snow


def archive_soil(data_dir: Path, stations, start: datetime, n: int) -> dict[str, np.ndarray]:
    out = {name: np.full((len(stations), n), np.nan) for name in ARCHIVE}
    k = 0
    while k < n:
        t = start + (k + 1) * HOUR
        step = min(n - k, (datetime(t.year + 1, 1, 1, tzinfo=UTC) - t) // HOUR)
        store = GridStore.open(data_dir, HOURLY, t.year, [VARIABLES[name] for name in ARCHIVE])
        t0 = store.index_of(t)
        for s_index, s in enumerate(stations):
            j, i = cell(s) or (0, 0)
            for name in ARCHIVE:
                out[name][s_index, k : k + step] = store.read_point(name, j, i, t0, t0 + step)
        k += step
    return out


def potato_depths(soil: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """The soil the potato model reads at 2, 4 and 8 in, from the catalog's 4, 10 and 30 cm."""
    return {
        "2 in": soil["soil_temperature_4cm"],
        "4 in": soil["soil_temperature_10cm"],
        "8 in": soil_between(EIGHT_INCHES_CM, 10, soil["soil_temperature_10cm"], 30, soil["soil_temperature_30cm"]),
    }


def at_depth(station: dict[float, np.ndarray], depth: float) -> np.ndarray:
    """The stations' soil at a depth, linear between the sensors around it."""
    depths = sorted(station)
    if depth in station:
        return station[depth]
    k = int(np.clip(np.searchsorted(depths, depth) - 1, 0, len(depths) - 2))
    lo, hi = depths[k], depths[k + 1]
    w = (depth - lo) / (hi - lo)
    return station[lo] * (1 - w) + station[hi] * w


def stats(model: np.ndarray, observed: np.ndarray, sel: np.ndarray) -> str:
    ok = sel & np.isfinite(model) & np.isfinite(observed)
    if ok.sum() < 100:
        return "—"
    d = model[ok] - observed[ok]
    return f"{d.mean():+.2f} / {np.abs(d).mean():.2f}"


def report(args, stations, station, at_potato, ifs_layers, snow, archive, local_day, month) -> str:
    days = sorted(set(local_day.tolist()))
    winter = np.isin(month, (11, 12, 1, 2, 3))[None, :]
    snowy = snow >= SNOW_M
    have = {d: np.isfinite(v).any(axis=1).sum() for d, v in station.items()}
    lines = [
        "# Soil temperature against Wisconet",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_soil_wisconet.py`, {args.start} to {args.end}, "
        f"at {len(stations)} Wisconet stations (with a sensor at 5 cm: {have[5.0]}, 10: {have[10.0]}, 20: "
        f"{have[20.0]}, 50: {have[50.0]}, 100: {have[100.0]}). The archive is v2's grid at the "
        "station's cell (ERA5-Land's soil, D52, where the archive has it); IFS is Open-Meteo's `ecmwf_ifs` from its "
        "historical-forecast API (short leads) and ERA5-Land "
        "from its archive API (`era5_land`), both at the station's location and taken to the depths the same way. "
        "Each depth the potato model reads (2, 4 and 8 in) is set against the station's "
        f"sensor at 5, 10 and 20 cm. Bias is the source minus the station, in °C; snow-covered hours are those "
        f"with IFS's snow depth ≥ {SNOW_M * 100:.0f} cm.",
        "",
        "## By depth and season (bias / MAE, °C)",
        "",
        "| Depth | Source | all | " + " | ".join(SEASONS) + " | Nov–Mar, snow | Nov–Mar, bare |",
        "|---|---|---|" + "---|" * len(SEASONS) + "---|---|",
    ]
    for depth, sensor in POTATO.items():
        observed = station[sensor]
        for name, source in at_potato.items():
            cells = [stats(source[depth], observed, np.ones_like(observed, dtype=bool))]
            cells += [stats(source[depth], observed, np.isin(month, m)[None, :]) for m in SEASONS.values()]
            cells += [stats(source[depth], observed, winter & snowy), stats(source[depth], observed, winter & ~snowy)]
            lines.append(f"| {depth} ({sensor:.0f} cm) | {name} | " + " | ".join(cells) + " |")

    # The handover's step: the archive minus IFS where both have the hour, by month
    lines += [
        "",
        "## Archive minus IFS, by month (°C, mean over the hours both have)",
        "",
        "What a forecast steps by at the handover, on average, if neither drifts with lead. Beside it, each "
        "source's bias against the stations at 4 in.",
        "",
        "| Month | 2 in | 4 in | 8 in | archive − station, 4 in | IFS − station, 4 in |",
        "|---|---|---|---|---|---|",
    ]
    hrrr, ifs = at_potato["archive"], at_potato["IFS"]
    for m in range(1, 13):
        sel = (month == m)[None, :]
        if not sel.any():
            continue
        cells = []
        for depth in POTATO:
            ok = sel & np.isfinite(hrrr[depth]) & np.isfinite(ifs[depth])
            cells.append(f"{(hrrr[depth] - ifs[depth])[ok].mean():+.2f}" if ok.any() else "—")
        cells += [
            stats(hrrr["4 in"], station[10.0], sel).split(" / ")[0],
            stats(ifs["4 in"], station[10.0], sel).split(" / ")[0],
        ]
        lines.append(f"| {MONTHS[m - 1]} | " + " | ".join(cells) + " |")
    diffs = []
    for depth in POTATO:
        ok = np.isfinite(hrrr[depth]) & np.isfinite(ifs[depth])
        d = (hrrr[depth] - ifs[depth])[ok]
        diffs.append(f"{depth} {np.quantile(d, 0.05):+.1f} to {np.quantile(d, 0.95):+.1f}")
    lines += ["", f"5th to 95th percentile of the hourly difference: {'; '.join(diffs)} °C."]

    # Would shifting IFS by the difference at the seam help, and for how long?
    lines += [
        "",
        "## Shifting IFS by the difference at the seam",
        "",
        "If the archive hands over to IFS at hour t (ERA5-Land's last hour), how far is IFS from the archive d days "
        "later: unshifted, shifted by the difference in hour t, or by the mean difference over the 24 hours to t? "
        "RMSE (°C) of archive − IFS d days on, over every station-hour of the period (IFS's short leads stand in for "
        "its longer ones). r is the correlation of the difference with itself d days later (each station's mean "
        "removed).",
        "",
        "| Depth | shift | " + " | ".join(f"{d} d" for d in LAGS_DAYS) + " |",
        "|---|---|" + "---|" * len(LAGS_DAYS),
    ]
    for depth in POTATO:
        d = hrrr[depth] - ifs[depth]
        day_mean = trailing_mean(d, 24)
        rows = {"none": [], "hour t": [], "24 h to t": [], "r": []}
        for lag in LAGS_DAYS:
            h = lag * 24
            then, now, mean = d[:, h:], d[:, :-h], day_mean[:, :-h]
            ok = np.isfinite(then) & np.isfinite(now) & np.isfinite(mean)
            rows["none"].append(rmse(then[ok]))
            rows["hour t"].append(rmse(then[ok] - now[ok]))
            rows["24 h to t"].append(rmse(then[ok] - mean[ok]))
            a = np.where(ok, now - np.nanmean(np.where(ok, now, np.nan), axis=1, keepdims=True), np.nan)
            b = np.where(ok, then - np.nanmean(np.where(ok, then, np.nan), axis=1, keepdims=True), np.nan)
            rows["r"].append(np.corrcoef(a[ok], b[ok])[0, 1])
        for label, values in rows.items():
            lines.append(f"| {depth} | {label} | " + " | ".join(f"{v:.2f}" for v in values) + " |")

    # IFS's layers, against the stations at the layers' middles
    lines += [
        "",
        "## IFS's layers against the stations at their middles (bias / MAE, °C)",
        "",
        "The stations' value at a layer's middle is linear between their sensors around it (64 cm between 50 and "
        "100). If a layer agrees here but its interpolated depths don't, the interpolation is at fault.",
        "",
        "| Layer | middle (cm) | all | " + " | ".join(SEASONS) + " |",
        "|---|---|---|" + "---|" * len(SEASONS),
    ]
    for layer, middle in SOIL_LAYERS.items():
        observed = at_depth(station, middle)
        cells = [stats(ifs_layers[layer], observed, np.ones_like(observed, dtype=bool))]
        cells += [stats(ifs_layers[layer], observed, np.isin(month, m)[None, :]) for m in SEASONS.values()]
        lines.append(f"| {layer.removeprefix('soil_temperature_')} | {middle:g} | " + " | ".join(cells) + " |")
    observed = at_depth(station, 30.0)
    cells = [stats(archive["soil_temperature_30cm"], observed, np.ones_like(observed, dtype=bool))]
    cells += [stats(archive["soil_temperature_30cm"], observed, np.isin(month, m)[None, :]) for m in SEASONS.values()]
    lines.append("| The archive's 30 cm, for comparison | 30 | " + " | ".join(cells) + " |")

    # What the potato model counts: hours below 27 °F, and the daily range at 2 in
    lines += [
        "",
        "## Hours below 27 °F, November–March",
        "",
        "Hours per station-winter-day, over the station-days on which the station and every source have every hour, "
        "and in brackets the share of those days with any. "
        "Station soil under snow is insulated; a field the wind has scoured is colder, so a source below the "
        "stations isn't necessarily wrong here.",
        "",
        "| Depth | station | " + " | ".join(at_potato) + " | station-days |",
        "|---|---|" + "---|" * len(at_potato) + "---|",
    ]
    winter_days = np.array([date.fromordinal(d).month in (11, 12, 1, 2, 3) for d in days])
    for depth, sensor in POTATO.items():
        counts = {}
        for name, values in (("station", station[sensor]), *((n, v[depth]) for n, v in at_potato.items())):
            below = np.where(np.isfinite(values), (values < KILLING_SOIL_C).astype(float), np.nan)
            counts[name] = daily(below, local_day, days)[:, winter_days]
        ok = np.all([np.isfinite(v) for v in counts.values()], axis=0)
        cells = [f"{v[ok].mean():.2f} ({(v[ok] > 0).mean():.0%})" for v in counts.values()]
        lines.append(f"| {depth} | " + " | ".join(cells) + f" | {ok.sum():,} |")
    lines += [
        "",
        "## Daily range at 2 in (°C, max − min of the local day)",
        "",
        "| Source | " + " | ".join(SEASONS) + " |",
        "|---|" + "---|" * len(SEASONS),
    ]
    day_month = np.array([date.fromordinal(d).month for d in days])
    ranges = {"station (5 cm)": daily_range(station[5.0], local_day, days)}
    ranges |= {name: daily_range(source["2 in"], local_day, days) for name, source in at_potato.items()}
    ok = np.all([np.isfinite(r) for r in ranges.values()], axis=0)
    for name, r in ranges.items():
        cells = [f"{r[ok & np.isin(day_month, m)[None, :]].mean():.2f}" for m in SEASONS.values()]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


SEAM_LEADS = np.arange(0, 25 * 24 + 1, 6)  # the provisional hours (up to 14 days) and the forecast (10), 6-hourly


def fit_seam(archive: dict[str, np.ndarray], ifs: dict[str, np.ndarray], times: list[datetime]) -> str:
    """Fits the seam weights on the first year's start hours and tests them on the later years', writes the table
    fitted on every year, and returns the report's section."""
    first_year = np.array([t.year == times[0].year for t in times])
    lines = [
        "",
        "## IFS shifted at the seam (Q23)",
        "",
        f"The weight on the difference in ERA5-Land's last hour, fitted on {times[0].year}'s hours and tested on the "
        "later ones: RMSE (°C) of the archive − IFS at each lead, unshifted, shifted by the whole difference, and by "
        f"the fitted weight. The table written (`{soil_seam.TABLE_PATH.name}`) is fitted on every year.",
        "",
        "| Depth | lead (d) | weight | none | whole | weighted |",
        "|---|---|---|---|---|---|",
    ]
    fitted = {}
    for name in soil_seam.VARIABLES:
        print(f"fitting the seam weights for {name}", flush=True)
        d = archive[name] - ifs[name]
        w = soil_seam.fit(d, SEAM_LEADS, starts=first_year)
        fitted[name] = soil_seam.fit(d, SEAM_LEADS)
        n = d.shape[1]
        for k, h in enumerate(SEAM_LEADS):
            if h % 72 or h == 0:
                continue
            now, then = d[:, : n - h], d[:, h:]
            ok = np.isfinite(now) & np.isfinite(then) & ~first_year[None, : n - h]
            lines.append(
                f"| {name.removeprefix('soil_temperature_')} | {h // 24} | {w[k]:.2f} | {rmse(then[ok]):.2f} "
                f"| {rmse(then[ok] - now[ok]):.2f} | {rmse(then[ok] - w[k] * now[ok]):.2f} |"
            )
    table = {
        "version": 1,
        "fitted": f"{datetime.now(UTC):%Y-%m-%d}",
        "source": f"The archive (ERA5-Land) minus Open-Meteo's ecmwf_ifs at 80 Wisconet stations' cells, "
        f"{times[0]:%Y-%m-%d} to {times[-1]:%Y-%m-%d}",
        "lead_hours": [int(h) for h in SEAM_LEADS],
        "weight": {name: [round(float(x), 4) for x in w] for name, w in fitted.items()},
    }
    soil_seam.TABLE_PATH.write_text(json.dumps(table, indent=1) + "\n")
    print(f"wrote {soil_seam.TABLE_PATH}")
    return "\n".join(lines) + "\n"


def trailing_mean(values: np.ndarray, hours: int) -> np.ndarray:
    """The mean over each hour and the `hours` - 1 before it, along axis 1; NaN unless every hour is there."""
    out = np.full_like(values, np.nan)
    sums = np.cumsum(np.nan_to_num(values), axis=1)
    counts = np.cumsum(np.isfinite(values), axis=1)
    total = sums[:, hours - 1 :] - np.pad(sums, ((0, 0), (1, 0)))[:, :-hours]
    full = counts[:, hours - 1 :] - np.pad(counts, ((0, 0), (1, 0)))[:, :-hours] == hours
    out[:, hours - 1 :] = np.where(full, total / hours, np.nan)
    return out


def rmse(d: np.ndarray) -> float:
    return float(np.sqrt(np.mean(d**2)))


def daily_range(hourly: np.ndarray, local_day: np.ndarray, days: list[int]) -> np.ndarray:
    out = np.full((hourly.shape[0], len(days)), np.nan)
    for k, d in enumerate(days):
        block = hourly[:, local_day == d]
        if block.shape[1] < 23:
            continue
        full = np.isfinite(block).all(axis=1)
        with np.errstate(invalid="ignore"):
            out[:, k] = np.where(full, block.max(axis=1, initial=-np.inf) - block.min(axis=1, initial=np.inf), np.nan)
    return out


if __name__ == "__main__":
    main()
