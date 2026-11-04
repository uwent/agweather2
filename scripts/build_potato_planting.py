"""Build `agdata/data/potato_planting.csv`: early, mid and late potato planting dates at Veg Path's locations.

The source is UW Vegetable Pathology's Vegetable Crop Updates: each season's early and late blight table gives
early, mid and late planting dates (estimated from growers' reports) and 50% emergence at Wisconsin's potato areas.
Ben compiled 2020–2026 into `tmp/planting-dates/potato_dates.xlsx` (sheet Dates: year, location, planting, planting
and emergence dates; sheet Locations: a cultivated field near each place). A location's row is each tier's mean
date over its years, written as MM-DD in a non-leap year.

An interim table (D64): `agdata.planting` serves it only near these locations, until Phase 6's climatology gives a
planting estimate on the grid. Emergence isn't kept: `potato-stages` models it from the planting date.
Run: `uv run --with openpyxl python scripts/build_potato_planting.py [--quiet]`.
"""

import argparse
import csv
import datetime as dt
import statistics
import sys
from pathlib import Path

import openpyxl

from agdata.progress import Reporter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp" / "planting-dates" / "potato_dates.xlsx"
OUT = ROOT / "packages" / "agdata" / "src" / "agdata" / "data" / "potato_planting.csv"
YEAR = 2025  # a non-leap year for MM-DD
TIERS = ("early", "mid", "late")


def month_day(doy: float) -> str:
    return (dt.date(YEAR, 1, 1) + dt.timedelta(days=round(doy) - 1)).strftime("%m-%d")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)

    report.step(f"reading {SOURCE}")
    book = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    places = {
        r[0]: (float(r[1]), float(r[2])) for r in book["Locations"].iter_rows(min_row=2, values_only=True) if r[0]
    }
    days: dict[tuple[str, str], list[int]] = {}
    years: dict[str, set[int]] = {}
    for year, location, tier, planted, _ in book["Dates"].iter_rows(min_row=2, values_only=True):
        if not year:
            continue
        tier = str(tier).strip().lower()
        if location not in places or tier not in TIERS or not isinstance(planted, dt.datetime):
            report.warn(f"skipped a row: {year}, {location!r}, {tier!r}, {planted!r}")
            continue
        days.setdefault((location, tier), []).append(planted.timetuple().tm_yday)
        years.setdefault(location, set()).add(int(year))

    rows = []
    for location, (lat, lng) in places.items():
        if not all((location, t) in days for t in TIERS):
            report.warn(f"{location}: not every tier has dates, left out")
            continue
        means = [month_day(statistics.mean(days[(location, t)])) for t in TIERS]
        rows.append([location, f"{lat:.4f}", f"{lng:.4f}", *means, len(years[location])])
        report.step(f"{location}: early {means[0]}, mid {means[1]}, late {means[2]} ({len(years[location])} years)")

    report.step(f"writing {OUT} (overwriting)")
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["location", "latitude", "longitude", "early", "mid", "late", "years"])
        writer.writerows(rows)
    if not report.finish(f"{len(rows)} locations"):
        sys.exit(1)


if __name__ == "__main__":
    main()
