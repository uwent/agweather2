"""Build `agdata/data/planting_dates.csv`: typical planting dates by county where published, else by state (D34).

Two static sources, downloaded once into `tmp/planting-dates/` (no ongoing data sources):

- Deines, J. M. et al. (2023). Field-scale dynamics of planting dates in the US Corn Belt from 2000 to 2020. Remote
  Sensing of Environment 291, 113551 (doi:10.1016/j.rse.2023.113551); county tables on Zenodo
  (doi:10.5281/zenodo.7790257, CC-BY 4.0): the day of year by which 10, 25, 50, 75 and 90% of each county's maize
  and soybean area was planted, from Landsat, in 12 Corn Belt states. A county's row is the median over its years
  (at least `MIN_YEARS`): typical at 50%, early at 10%, late at 90%.
- USDA NASS (2010). Usual planting and harvesting dates for U.S. field crops. Agricultural Handbook 628, from 20
  years of crop progress (1990–2009): by state, begin (about 5% planted), most active (15–85%) and end (95%).
  Typical is the middle of the most active range, early and late its ends.

Dates are written as MM-DD in a non-leap year; a row's level (county or state) says which source it's from
(`agdata.planting.SOURCES`). Run: `uv run --with pyshp python scripts/build_planting_dates.py [--quiet]`
(`--quiet` prints only warnings, failures and the summary).
"""

import argparse
import csv
import datetime as dt
import io
import os
import re
import statistics
import sys
import zipfile
from pathlib import Path

import requests
import shapefile  # pyshp

from agdata.progress import Reporter

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tmp" / "planting-dates"
OUT = ROOT / "packages" / "agdata" / "src" / "agdata" / "data" / "planting_dates.csv"
MIN_YEARS = 10
ZENODO = "https://zenodo.org/records/7790257/files/{crop}_countyStats_doyPercentPlanted_2000-2020_DeinesEtAl_vRSE.csv"
DEINES = {"corn": "maize", "soybean": "soybeans"}
NASS_URL = (
    "https://usda.library.cornell.edu/sites/default/release-files/vm40xr56k/dv13zw65p/z603r1055/planting-10-29-2010.txt"
)
NASS = {  # our crop: the table's heading, and the month a season starts in (winter wheat crosses the new year)
    "corn": ("Corn for Grain", 1),
    "soybean": ("Soybean", 1),
    "spring-wheat": ("Spring Wheat", 1),
    "winter-wheat": ("Winter Wheat", 7),
}
COUNTIES = CACHE / "cb_county_500k.zip"  # from build_counties.py, for state names
YEAR = 2025  # a non-leap year to write dates in
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def cached(name: str, url: str, report: Reporter) -> Path:
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        report.step(f"downloading {url}")
        response = requests.get(url, timeout=300, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()  # never cache an error page as data
        part = path.with_name(path.name + ".part")
        part.write_bytes(response.content)
        os.replace(part, path)
    else:
        report.step(f"using the cached {path}")
    return path


def month_day(doy: float) -> str:
    return (dt.date(YEAR, 1, 1) + dt.timedelta(days=round(doy) - 1)).strftime("%m-%d")


def deines_rows(report: Reporter) -> list[list[str]]:
    rows = []
    for crop, name in DEINES.items():
        report.step(f"Deines et al. county table for {crop}")
        path = cached(f"{name}_county.csv", ZENODO.format(crop=name) + "?download=1", report)
        by_county: dict[tuple[str, str], list[dict]] = {}
        with path.open() as f:
            for r in csv.DictReader(f):
                if r["doy_50"] not in ("", "NA"):
                    by_county.setdefault((f"{int(r['GEOID']):05d}", r["state"]), []).append(r)
        short = 0
        for (geoid, _), years in sorted(by_county.items()):
            if len(years) < MIN_YEARS:
                short += 1
                continue
            early, typical, late = (
                statistics.median(float(y[k]) for y in years) for k in ("doy_10", "doy_50", "doy_90")
            )
            rows.append(
                [
                    crop,
                    "county",
                    geoid,
                    month_day(early),
                    month_day(typical),
                    month_day(late),
                    str(len(years)),
                ]
            )
        report.step(f"{crop}: {len(by_county) - short} counties kept, {short} with under {MIN_YEARS} years left out")
    return rows


def state_abbreviations() -> dict[str, str]:
    with zipfile.ZipFile(COUNTIES) as z:
        reader = shapefile.Reader(dbf=io.BytesIO(z.read("cb_2024_us_county_500k.dbf")))
        return {r["STATE_NAME"]: r["STUSPS"] for r in reader.iterRecords()}


def nass_rows(report: Reporter) -> list[list[str]]:
    report.step("NASS usual planting dates by state")
    text = cached("nass-usual-2010.txt", NASS_URL, report).read_text().replace("\r", "")
    abbreviations = state_abbreviations()
    date = r"([A-Z][a-z]{2,3})\s+(\d{1,2})"
    row = re.compile(rf"^([A-Z][A-Za-z .]+?)\s*\.*\s*:\s*\S+\s+{date}\s+{date}\s*-\s*{date}\s+{date}")
    rows = []
    for crop, (heading, season_start) in NASS.items():
        table = text.split(f"\n{heading} Usual Planting and Harvesting Dates - States\n", 1)[1]
        table = table.split("\n-----", 2)[1]  # the rows, between the header rule and the closing rule
        for line in table.splitlines():
            m = row.match(line)
            if not m:
                continue
            state = abbreviations.get(m[1].strip(" ."))
            if state is None:
                report.warn(f"{crop}: unknown state {m[1].strip(' .')!r} in the NASS table, row skipped")
                continue
            days = [_day(m[k], m[k + 1], season_start) for k in (2, 4, 6, 8)]  # begin, active from, to, end
            early, late = days[1], days[2]
            rows.append(
                [
                    crop,
                    "state",
                    state,
                    month_day(early),
                    month_day((early + late) / 2),
                    month_day(late),
                    "",
                ]
            )
    return rows


def _day(month: str, day: str, season_start: int) -> float:
    """Day of the season's first year, past 365 for dates in the next calendar year (winter wheat's January)."""
    m = MONTHS.index(month[:3]) + 1
    doy = dt.date(YEAR, m, int(day)).timetuple().tm_yday
    return doy + 365 if m < season_start else doy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)

    report.step(f"building planting dates for {', '.join(DEINES)} (counties) and {', '.join(NASS)} (states)")
    rows = deines_rows(report) + nass_rows(report)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report.step(f"writing {OUT} (overwriting)")
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["crop", "level", "area", "early", "typical", "late", "years"])  # level says the source
        writer.writerows(rows)
    counts = {}
    for r in rows:
        counts[(r[0], r[1])] = counts.get((r[0], r[1]), 0) + 1
    if not report.finish(
        f"{len(rows)} rows: " + ", ".join(f"{crop} {level} {n}" for (crop, level), n in counts.items())
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
