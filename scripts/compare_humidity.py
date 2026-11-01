"""Hourly humidity in the archive against Wisconet's stations (PLAN.md Phase 4 G, D49).

At each station's cell, the archive's hourly RH and temperature against the station's hourly means
(`60min_relative_humidity_pct_avg`, `60min_air_temp_f_avg`, stamped at the hour's end as ours), and its
flat-plate leaf wetness (`60min_leaf_wetness_hst_avg`, the share of the hour the sensor read wet). Reports bias
by month, humid-hour counts per day, by hour of day and by station, and the archive RH thresholds that count as
many hours as the stations' RH ≥ 90% and as their wet-leaf hours: the gridded threshold a disease model needs to
see what an in-field station saw.

Wisconet is throttled: each station-year is one request, cached in tmp/wisconet/ (fetched with
tmp/wisconet/fetch_humidity.py's fields and cache names).

    uv run python scripts/compare_humidity.py --start 2025-01-01 --end 2026-10-27

`--quiet` prints only warnings, failures and the summary.
"""

import argparse
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import VARIABLES
from agdata.clients.wisconet import CENTRAL, Wisconet
from agdata.grid import NDFD, service_window
from agdata.progress import Reporter
from agdata.store import HOURLY, GridStore

CACHE = Path("tmp/wisconet")
FIELDS = [
    "60min_relative_humidity_pct_avg",
    "60min_air_temp_f_avg",
    "60min_dew_point_f_avg",
    "60min_leaf_wetness_hst_avg",
    "60min_canopy_wetness_pct",
    "60min_leaf_wetness_hrs_hours@wet",
]
HOUR = timedelta(hours=1)
WET_SHARE = 0.5  # an hour counts as wet when the leaf sensor read wet for at least half of it
FULL_DAY_HOURS = 22  # station-days with fewer paired hours are left out of the daily counts
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-humidity.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last:
        parser.error("--start must not be after --end")
    window = service_window(args.box)
    wisconet = Wisconet(cache_dir=CACHE)
    stations = [s for s in wisconet.stations() if (c := cell(s)) is not None and window.contains(*c)]
    ids = {name: wisconet.field_id(name) for name in FIELDS[:4]}
    if not stations:
        report.fail("stations", f"no Wisconet stations inside the {args.box} box")
        sys.exit(1)
    report.step(
        f"humidity {first} to {last}: {len(stations)} Wisconet stations in the {args.box} box, "
        f"{last.year - first.year + 1} year(s); writing {args.out}"
    )

    start = datetime(first.year, first.month, first.day, tzinfo=UTC)
    n = int((datetime(last.year, last.month, last.day, tzinfo=UTC) + timedelta(days=1) - start) / HOUR)
    times = [start + k * HOUR for k in range(n)]
    archive_rh, archive_t = np.full((len(stations), n), np.nan), np.full((len(stations), n), np.nan)
    station = {name: np.full((len(stations), n), np.nan) for name in ("rh", "t", "wet")}
    requests_done, requests_total = 0, len(stations) * (last.year - first.year + 1)
    for year in range(first.year, last.year + 1):
        report.step(f"{year}: reading the archive's hours at {len(stations)} cells")
        store = GridStore.open(
            Path(args.data), HOURLY, year, [VARIABLES["relative_humidity"], VARIABLES["air_temperature"]]
        )
        lo = max(start, datetime(year, 1, 1, tzinfo=UTC))
        hi = min(start + n * HOUR, datetime(year + 1, 1, 1, tzinfo=UTC))
        k0, count = int((lo - start) / HOUR), int((hi - lo) / HOUR)
        t0 = store.index_of(lo)
        for k, s in enumerate(stations):
            j, i = cell(s) or (0, 0)
            archive_rh[k, k0 : k0 + count] = store.read_point("relative_humidity", j, i, t0, t0 + count)
            archive_t[k, k0 : k0 + count] = store.read_point("air_temperature", j, i, t0, t0 + count)
        for k, s in enumerate(stations):
            begin = datetime(year, 1, 1, tzinfo=CENTRAL)
            end = min(datetime(year + 1, 1, 1, tzinfo=CENTRAL), start + n * HOUR) + HOUR  # to the range's end
            key = f"{s['station_id']}_{year}_60min_humidity.json"
            try:
                rows = list(wisconet.measures(s["station_id"], begin, end, FIELDS, cache_key=key))
            except Exception as error:  # the station stays missing for the year; a rerun retries it
                report.fail(f"station {s['station_id']} {year}", error)
                rows = []
            requests_done += 1
            report.progress("station-years", requests_done, requests_total)
            for row in rows:
                t = int((row["collection_time"] - start.timestamp()) // 3600)
                if not 0 <= t < n:
                    continue
                for fid, value in row["measures"]:
                    if value is None:
                        continue
                    if fid == ids["60min_relative_humidity_pct_avg"]:
                        station["rh"][k, t] = value
                    elif fid == ids["60min_air_temp_f_avg"]:
                        station["t"][k, t] = (value - 32) / 1.8
                    elif fid == ids["60min_leaf_wetness_hst_avg"]:
                        station["wet"][k, t] = value
    rh = station["rh"]
    rh[(rh < 1) | (rh > 103)] = np.nan  # sensor faults; RH sensors read a little over 100 when saturated
    rh[:] = np.minimum(rh, 100)
    station["wet"][(station["wet"] < 0) | (station["wet"] > 1)] = np.nan
    report.step(f"writing {args.out} (overwriting)")
    Path(args.out).write_text(build_report(args, stations, times, archive_rh, archive_t, station))
    report.step(f"wrote {args.out}")
    if not report.finish(f"{len(stations)} stations, {n} hours, {requests_total} station-years"):
        sys.exit(1)


def cell(s: dict) -> tuple[int, int] | None:
    return NDFD.cell_of(s["latitude"], s["longitude"])


def build_report(args, stations, times, archive_rh, archive_t, station) -> str:
    rh, t, wet = station["rh"], station["t"], station["wet"]
    paired = np.isfinite(rh) & np.isfinite(archive_rh)
    local = [x.astimezone(CENTRAL) for x in times]
    month = np.array([x.month for x in local])
    hour = np.array([x.hour for x in local])
    day = np.array([(x - HOUR).date().toordinal() for x in local])  # the local day an hour ending closes
    lines = [
        "# Humidity: the archive against Wisconet",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_humidity.py`, {args.start} to {args.end}: "
        f"{len(stations)} Wisconet stations, each against its archive cell (URMA/RTMA RH from temperature and dew "
        f"point at the top of the hour; the station's are hourly means). {paired.sum():,} paired hours.",
        "",
        "## By month",
        "",
        "| Month | RH bias (archive − station) | RH MAE | temperature bias (°C) "
        "| RH ≥ 90: station / archive (share of hours) | RH ≥ 80: station / archive | leaf wet (station) |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in range(1, 13):
        sel = paired & (month == m)[None]
        if not sel.any():
            continue
        tsel = sel & np.isfinite(t) & np.isfinite(archive_t)
        wsel = np.isfinite(wet) & (month == m)[None]
        lines.append(
            f"| {MONTHS[m - 1]} | {np.mean(archive_rh[sel] - rh[sel]):+.1f} "
            f"| {np.mean(np.abs(archive_rh[sel] - rh[sel])):.1f} "
            f"| {np.mean(archive_t[tsel] - t[tsel]):+.2f} "
            f"| {np.mean(rh[sel] >= 90):.3f} / {np.mean(archive_rh[sel] >= 90):.3f} "
            f"| {np.mean(rh[sel] >= 80):.3f} / {np.mean(archive_rh[sel] >= 80):.3f} "
            f"| {np.mean(wet[wsel] >= WET_SHARE):.3f} |"
        )

    # Daily counts at full station-days
    lines += ["", "## Hours a day", ""]
    days = np.unique(day)
    counts = {key: [] for key in ("st90", "ar90", "st80", "ar80", "wet", "warm")}
    for k in range(len(stations)):
        for d in days:
            hours = (day == d) & paired[k]
            if hours.sum() < FULL_DAY_HOURS:
                continue
            counts["st90"].append((rh[k, hours] >= 90).sum())
            counts["ar90"].append((archive_rh[k, hours] >= 90).sum())
            counts["st80"].append((rh[k, hours] >= 80).sum())
            counts["ar80"].append((archive_rh[k, hours] >= 80).sum())
            w = wet[k, hours]
            counts["wet"].append((w >= WET_SHARE).sum() if np.isfinite(w).all() else np.nan)
            counts["warm"].append(datetime.fromordinal(int(d)).month in (5, 6, 7, 8, 9))
    c = {key: np.array(v, dtype=float) for key, v in counts.items()}
    warm = c["warm"] == 1
    lines += [
        "| Station-days | RH ≥ 90 station | RH ≥ 90 archive | RH ≥ 80 station | RH ≥ 80 archive | leaf wet (station) |",
        "|---|---|---|---|---|---|",
    ]
    for label, sel in (("all", np.ones(len(warm), dtype=bool)), ("May–September", warm)):
        lines.append(
            f"| {label} ({sel.sum():,}) | {c['st90'][sel].mean():.2f} | {c['ar90'][sel].mean():.2f} "
            f"| {c['st80'][sel].mean():.2f} | {c['ar80'][sel].mean():.2f} | {np.nanmean(c['wet'][sel]):.2f} |"
        )
    both = np.isfinite(c["wet"]) & warm
    lines += [
        "",
        f"May–September daily counts, correlation with the station's leaf-wet hours: station RH ≥ 90 "
        f"{np.corrcoef(c['st90'][both], c['wet'][both])[0, 1]:.2f}, archive RH ≥ 90 "
        f"{np.corrcoef(c['ar90'][both], c['wet'][both])[0, 1]:.2f}; archive against station RH ≥ 90 "
        f"{np.corrcoef(c['ar90'][warm], c['st90'][warm])[0, 1]:.2f}.",
    ]

    # Equivalent thresholds: the archive RH whose hours count as many as the station's
    lines += [
        "",
        "## Equivalent archive thresholds",
        "",
        "The archive RH at or above which there are as many hours as the stations' RH ≥ 90% and as their leaf-wet "
        "hours (a share of the hour wet ≥ 0.5), over the paired hours:",
        "",
        "| Hours | station RH ≥ 90 | leaf wet |",
        "|---|---|---|",
    ]
    for label, months in (("all", range(1, 13)), ("May–September", (5, 6, 7, 8, 9))):
        sel = paired & np.isin(month, months)[None]
        wsel = sel & np.isfinite(wet)
        lines.append(
            f"| {label} | {threshold(archive_rh[sel], np.mean(rh[sel] >= 90)):.1f} "
            f"| {threshold(archive_rh[wsel], np.mean(wet[wsel] >= WET_SHARE)):.1f} |"
        )

    # By hour of day
    lines += [
        "",
        "## By local hour (May–September), share of hours",
        "",
        "| Hour ending | RH ≥ 90 station | RH ≥ 90 archive | leaf wet | RH bias |",
        "|---|---|---|---|---|",
    ]
    for h in range(24):
        sel = paired & ((hour == h) & np.isin(month, (5, 6, 7, 8, 9)))[None]
        wsel = sel & np.isfinite(wet)
        lines.append(
            f"| {h:02d} | {np.mean(rh[sel] >= 90):.3f} | {np.mean(archive_rh[sel] >= 90):.3f} "
            f"| {np.mean(wet[wsel] >= WET_SHARE):.3f} | {np.mean(archive_rh[sel] - rh[sel]):+.1f} |"
        )

    # By station
    ratio = []
    for k in range(len(stations)):
        sel = paired[k]
        if sel.sum() > 24 * 90 and (rh[k, sel] >= 90).sum() > 0:
            ratio.append((archive_rh[k, sel] >= 90).sum() / (rh[k, sel] >= 90).sum())
    r = np.array(ratio)
    lines += [
        "",
        f"By station ({len(r)} with 90 days or more): archive RH ≥ 90 hours over the station's, median "
        f"{np.median(r):.2f}, 10–90% {np.percentile(r, 10):.2f}–{np.percentile(r, 90):.2f}.",
        "",
    ]
    return "\n".join(lines)


def threshold(values: np.ndarray, share: float) -> float:
    """The value at or above which `share` of `values` lie."""
    return float(np.quantile(values, 1 - share))


if __name__ == "__main__":
    main()
