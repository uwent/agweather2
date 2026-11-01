"""Fits the HRRR shortwave correction against Wisconet's pyranometers (D48, PLAN.md Phase 2 H).

HRRR's hourly mean shortwave reads ~18% high against 80 Wisconet stations, more under cloud. The correction is a
factor by the hour's clearness (HRRR's value over the FAO-56 clear-sky Rso, `agdata.gaps`), fitted as the ratio of
the station totals to HRRR's in each clearness bin over one year and tested on the next. Solar elevation as a
second dimension gained nothing (2026 daily MAE 1.64 vs 1.65 MJ/m²), so the table is one-dimensional.

Reads raw HRRR (`shortwave_radiation_hrrr`, or `shortwave_radiation` in stores not yet migrated) from the hourly
store at each station's cell and Wisconet's `60min_solar_radiation_w_avg` (stamped at the hour's end, as ours:
r 0.96 at lag 0, 0.90–0.92 an hour either way), cached in tmp/wisconet/.

    uv run python scripts/fit_shortwave_correction.py --fit 2025 --test 2026 --test-end 2026-10-27

Always overwrites the committed table (`agdata.shortwave.TABLE_PATH`), and says so before it does; it won't if a
station failed or a clearness bin is empty. `--quiet` prints only warnings, failures and the summary.
"""

import argparse
import itertools
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import VARIABLES
from agdata.clients.wisconet import CENTRAL, Wisconet
from agdata.gaps import clear_sky_shortwave_w_m2
from agdata.grid import NDFD, service_window
from agdata.progress import Reporter
from agdata.shortwave import RAW, TABLE_PATH
from agdata.store import HOURLY, GridStore

CACHE = Path("tmp/wisconet")
FIELD = "60min_solar_radiation_w_avg"
EDGES = np.linspace(0, 1.2, 13)  # clearness bins
MIN_HOURS_PER_DAY = 20  # station days with fewer paired hours are left out of the daily check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit", type=int, required=True, help="year to fit on")
    parser.add_argument("--test", type=int, required=True, help="year to test on")
    parser.add_argument("--test-end", required=True, help="last day of the test year with data")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--out", default="docs/validation-shortwave-correction.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        test_end = date.fromisoformat(args.test_end)
    except ValueError as error:
        parser.error(f"--test-end must be a YYYY-MM-DD date: {error}")
    if test_end.year != args.test:
        parser.error(f"--test-end {args.test_end} is not in the test year {args.test}")
    if args.fit == args.test:
        parser.error("--fit and --test must be different years")
    window = service_window(args.box)
    wisconet = Wisconet(cache_dir=CACHE)
    stations = [s for s in wisconet.stations() if (c := cell(s)) is not None and window.contains(*c)]
    field_id = wisconet.field_id(FIELD)
    if not stations:
        report.fail("stations", f"no Wisconet stations inside the {args.box} box")
        sys.exit(1)
    report.step(
        f"fitting the HRRR shortwave correction on {args.fit}, testing on {args.test} (to {args.test_end}), "
        f"{len(stations)} stations; writing {TABLE_PATH} and {args.out}"
    )

    fit = pairs(Path(args.data), wisconet, stations, field_id, args.fit, date(args.fit, 12, 31), report)
    test = pairs(Path(args.data), wisconet, stations, field_id, args.test, test_end, report)
    clearness_fit = clearness(fit)
    sun = fit[:, 2] > 1
    factor = []
    for lo, hi in itertools.pairwise(EDGES):
        inside = sun & (clearness_fit >= lo) & (clearness_fit < hi)
        factor.append(float(fit[inside, 1].sum() / fit[inside, 0].sum()))
    if not np.isfinite(factor).all():
        bins = [
            f"{lo:.2f}-{hi:.2f}"
            for (lo, hi), f in zip(itertools.pairwise(EDGES), factor, strict=True)
            if not np.isfinite(f)
        ]
        report.fail("fit", f"no paired sunlit hours in clearness bins {', '.join(bins)}; {TABLE_PATH} left as it was")
    if report.failures:
        report.finish()
        sys.exit(1)
    middles = ((EDGES[:-1] + EDGES[1:]) / 2).round(3).tolist()
    table = {
        "version": args.version,
        "fitted": f"{datetime.now(UTC):%Y-%m-%d}",
        "source": f"Wisconet {FIELD} at {len(stations)} stations, {args.fit}; tested on {args.test}",
        "clearness": middles,
        "factor": [round(f, 4) for f in factor],
    }
    report.step(f"overwriting the committed table {TABLE_PATH}")
    TABLE_PATH.write_text(json.dumps(table, indent=2) + "\n")
    report.step(f"wrote {TABLE_PATH}")

    lines = [
        "# HRRR shortwave correction",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/fit_shortwave_correction.py` (D48). Fitted on {args.fit}, "
        f"tested on {args.test} (to {args.test_end}), at {len(stations)} Wisconet stations: hourly HRRR at each "
        f"station's cell against the station's `{FIELD}`. The factor is by the hour's clearness (HRRR over FAO-56 "
        "clear-sky Rso), applied as a linear interpolation between bin middles.",
        "",
        "| Clearness | " + " | ".join(f"{m:.2f}" for m in middles) + " |",
        "|---|" + "---|" * len(middles),
        "| Factor | " + " | ".join(f"{f:.2f}" for f in factor) + " |",
        "",
        "| Year | correction | hourly bias (W/m²) | hourly MAE | daily MAE (MJ/m²) | ratio | daily r |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, data in ((f"{args.fit} (fit)", fit), (f"{args.test} (held out)", test)):
        corrected = data[:, 0] * np.interp(clearness(data), middles, factor)
        for name, values in (("none", data[:, 0]), ("applied", corrected)):
            lines.append(f"| {label} | {name} | " + " | ".join(scores(data, values)) + " |")
    corrected = test[:, 0] * np.interp(clearness(test), middles, factor)
    months = test[:, 4].astype("datetime64[D]").astype("datetime64[M]").astype(int) % 12 + 1
    lines += [
        "",
        f"{args.test} corrected over observed, by month: "
        + ", ".join(f"{m}: {corrected[months == m].sum() / test[months == m, 1].sum():.2f}" for m in np.unique(months)),
    ]
    ratios = np.array(
        [corrected[test[:, 5] == k].sum() / test[test[:, 5] == k, 1].sum() for k in np.unique(test[:, 5])]
    )
    lines += [
        "",
        f"By station: median {np.median(ratios):.2f}, 10–90% {np.percentile(ratios, 10):.2f}–"
        f"{np.percentile(ratios, 90):.2f} (raw HRRR differs by station too: 1.15 at Arlington, 1.26 at Hancock "
        "in 2025).",
        "",
    ]
    report.step(f"writing {args.out} (overwriting)")
    Path(args.out).write_text("\n".join(lines))
    report.step(f"wrote {args.out}")
    if not report.finish(f"{len(stations)} stations, {len(fit)} fit hours, {len(test)} test hours"):
        sys.exit(1)


def cell(station: dict) -> tuple[int, int] | None:
    return NDFD.cell_of(station["latitude"], station["longitude"])


def pairs(
    data_dir: Path, wisconet: Wisconet, stations: list[dict], field_id: int, year: int, last: date, report: Reporter
) -> np.ndarray:
    """Rows of (HRRR W/m², station W/m², Rso W/m², UTC hour index, local day, station index) where both have a value
    and the station's is plausible (at most 1.3 × Rso + 30)."""
    first_hour = datetime(year, 1, 1, tzinfo=UTC)
    n = int(
        (datetime(last.year, last.month, last.day, tzinfo=UTC) + timedelta(days=1) - first_hour) / timedelta(hours=1)
    )
    store = GridStore.open(data_dir, HOURLY, year, VARIABLES.values(), add_missing=True)
    raw = RAW if any(store.sources(RAW)) else "shortwave_radiation"  # stores not yet migrated hold raw HRRR
    times = np.array([np.datetime64((first_hour + timedelta(hours=k)).replace(tzinfo=None)) for k in range(n)])
    rows = []
    for k, station in enumerate(stations):
        report.progress(f"stations {year}", k + 1, len(stations))
        j, i = cell(station) or (0, 0)
        hrrr = store.read_point(raw, j, i, 0, n)
        pressure = store.read_point("surface_pressure", j, i, 0, n)
        rso = clear_sky_shortwave_w_m2(times, np.array(station["latitude"]), np.array(station["longitude"]), pressure)
        observed = np.full(n, np.nan)
        start = datetime(year, 1, 1, tzinfo=CENTRAL)
        end = datetime(year + 1, 1, 1, tzinfo=CENTRAL) + timedelta(hours=1)
        key = f"{station['station_id']}_{year}_{FIELD}.json"
        try:
            station_rows = list(wisconet.measures(station["station_id"], start, end, [FIELD], cache_key=key))
        except Exception as error:  # the station's hours stay missing, and the table isn't written
            report.fail(f"station {station['station_id']} {year}", error)
            station_rows = []
        for row in station_rows:
            t = int((row["collection_time"] - first_hour.timestamp()) // 3600)
            for fid, value in row["measures"]:
                if fid == field_id and value is not None and 0 <= t < n:
                    observed[t] = value
        local_day = (times - np.timedelta64(6, "h")).astype("datetime64[D]").astype(int)
        rows.append(np.column_stack([hrrr, observed, rso.ravel(), np.arange(n), local_day, np.full(n, k)]))
    a = np.concatenate(rows)
    ok = np.isfinite(a[:, :3]).all(axis=1) & (a[:, 1] >= 0) & (a[:, 1] <= 1.3 * a[:, 2] + 30)
    return a[ok]


def clearness(a: np.ndarray) -> np.ndarray:
    return np.where(a[:, 2] > 1, a[:, 0] / np.maximum(a[:, 2], 1), 0.0)


def scores(a: np.ndarray, values: np.ndarray) -> list[str]:
    diff = values - a[:, 1]
    key = a[:, 4] * 1000 + a[:, 5]
    _, inverse = np.unique(key, return_inverse=True)
    model_day = np.bincount(inverse, values) * 0.0036
    observed_day = np.bincount(inverse, a[:, 1]) * 0.0036
    full = np.bincount(inverse) >= MIN_HOURS_PER_DAY
    m, o = model_day[full], observed_day[full]
    return [
        f"{diff.mean():+.1f}",
        f"{np.abs(diff).mean():.1f}",
        f"{np.abs(m - o).mean():.2f}",
        f"{values.sum() / a[:, 1].sum():.3f}",
        f"{np.corrcoef(m, o)[0, 1]:.3f}",
    ]


if __name__ == "__main__":
    main()
