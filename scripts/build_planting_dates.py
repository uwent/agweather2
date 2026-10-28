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
(`agdata.planting.SOURCES`). Run: `uv run --with pyshp python scripts/build_planting_dates.py`.
"""

import csv
import datetime as dt
import io
import re
import statistics
import zipfile
from pathlib import Path

import requests
import shapefile  # pyshp

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


def cached(name: str, url: str) -> Path:
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, timeout=300, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def month_day(doy: float) -> str:
    return (dt.date(YEAR, 1, 1) + dt.timedelta(days=round(doy) - 1)).strftime("%m-%d")


def deines_rows() -> list[list[str]]:
    rows = []
    for crop, name in DEINES.items():
        path = cached(f"{name}_county.csv", ZENODO.format(crop=name) + "?download=1")
        by_county: dict[tuple[str, str], list[dict]] = {}
        with path.open() as f:
            for r in csv.DictReader(f):
                if r["doy_50"] not in ("", "NA"):
                    by_county.setdefault((f"{int(r['GEOID']):05d}", r["state"]), []).append(r)
        for (geoid, _), years in sorted(by_county.items()):
            if len(years) < MIN_YEARS:
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
    return rows


def state_abbreviations() -> dict[str, str]:
    with zipfile.ZipFile(COUNTIES) as z:
        reader = shapefile.Reader(dbf=io.BytesIO(z.read("cb_2024_us_county_500k.dbf")))
        return {r["STATE_NAME"]: r["STUSPS"] for r in reader.iterRecords()}


def nass_rows() -> list[list[str]]:
    text = cached("nass-usual-2010.txt", NASS_URL).read_text().replace("\r", "")
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
            state = abbreviations[m[1].strip(" .")]
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
    rows = deines_rows() + nass_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["crop", "level", "area", "early", "typical", "late", "years"])  # level says the source
        writer.writerows(rows)
    counts = {}
    for r in rows:
        counts[(r[0], r[1])] = counts.get((r[0], r[1]), 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
