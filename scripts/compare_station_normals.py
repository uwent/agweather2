"""Normal maps (`agdata.normals`, D85) against station normals: the Wisconsin State Climatology Office's 1991–2020
modified GDD 50/86 normals at DATCP's points (DATCP's spreadsheet), and each station's own daily record from ACIS.

Three comparisons, so a difference can be put down to the right cause:

1. the spreadsheet against the station's ACIS record over the same years (1991–2020): checks the spreadsheet;
2. the station's ACIS record over `last30`'s years (1996–2025) against `last30` at the station's cell: the grid
   against the station, with the years the same;
3. the station's 2016–2025 against `last10`: the archive alone, without gridMET.

A station's normal is the mean modified GDD of each calendar day over the years that reported it, accumulated from
January 1 (the State Climatology Office's method: its sheets give the count of years per day). Summer's mean maximum
and minimum (June–August) are compared beside it, to say which end of the day a GDD difference comes from.

    uv run python scripts/compare_station_normals.py "tmp/DATCP Climate Normals 1991-2020.xlsx"

Reads ACIS (cached in tmp/d5/acis); writes docs/validation-normals.md.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np

from agdata import climatology, normals
from agdata.clients.acis import Acis
from agdata.grid import NDFD, Window
from agdata.progress import Reporter
from agmodels.degree_days import degree_days_modified

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "validation-normals.md"
CACHE = ROOT / "tmp" / "d5" / "acis"

# The spreadsheet's "All" sheet column → COOP id (its "All site reports" sheet)
STATIONS = {
    "Dubuque": "132367",
    "Beloit": "470696",
    "Madison": "474961",
    "Milwaukee": "475479",
    "Hartford": "473453",
    "Appleton": "470265",
    "Green Bay": "473269",
    "Hancock": "473405",
    "La Crosse": "474370",
    "Eau Claire": "472428",
    "Cumberland": "471923",
    "Wausau": "478968",
    "Medford": "475255",
    "Racine": "476922",
    "Horicon": "473756",
    "Lancaster": "474546",
    "Oconomowoc": "476200",
    "Watertown": "478919",
}
CHECKPOINTS = [date(2025, m, d) for m, d in ((4, 30), (5, 31), (6, 30), (7, 31), (8, 31), (9, 30), (12, 31))]
SUMMER = (climatology.slot(date(2000, 6, 1)), climatology.slot(date(2000, 8, 31)) + 1)


def read_sheet(path: Path) -> dict[str, np.ndarray]:
    """Each station's accumulated normal by calendar slot (366), from the "All" sheet (hidden columns too)."""
    import openpyxl

    sheet = openpyxl.load_workbook(path, data_only=True)["All"]
    header = [c.value for c in sheet[3]]
    found: dict[str, np.ndarray] = {}
    for k, name in enumerate(header):
        if name not in STATIONS:
            continue
        values = np.full(climatology.SLOTS, np.nan)
        for row in sheet.iter_rows(min_row=4, values_only=True):
            month, day, value = row[0], row[1], row[k]
            if isinstance(month, int) and isinstance(day, int) and isinstance(value, (int, float)):
                values[climatology.slot(date(2000, month, day))] = value
        if np.isfinite(values).sum() > 300:
            found[name] = values  # the later of two same-named columns (Racine's hidden one has values)
    return found


def station_days(acis: Acis, sid: str) -> dict:
    query = {"sid": f"{sid} 2", "sdate": "1991-01-01", "edate": "2025-12-31", "elems": "maxt,mint", "meta": "name,ll"}
    return acis.post("StnData", query, cache_key=f"stn_{sid}.json")


def by_year(rows: list, years: range) -> tuple[np.ndarray, np.ndarray]:
    """(years, 366) daily max and min, °F, on the calendar slots."""
    days: dict[int, list[tuple[date, float, float]]] = {}
    for d, hi, lo in rows:
        day = date.fromisoformat(d)
        if day.year in years:
            days.setdefault(day.year, []).append((day, _f(hi), _f(lo)))
    tmax = np.full((len(years), climatology.SLOTS), np.nan)
    tmin = np.full_like(tmax, np.nan)
    for k, year in enumerate(years):
        for day, hi, lo in days.get(year, []):
            s = climatology.slot(day)
            tmax[k, s], tmin[k, s] = hi, lo
    return tmax, tmin


def _f(value: str) -> float:
    text = str(value).strip().rstrip("A")
    try:
        return float(text)
    except ValueError:
        return np.nan


def station_normal(
    tmax: np.ndarray, tmin: np.ndarray, office_rounding: bool = False
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Accumulated mean modified GDD by slot, the fewest years behind any day, and summer's mean max and min. With
    `office_rounding`, as the State Climatology Office's sheets appear to round: each day's GDD to a whole degree
    day, halves up, and each calendar day's mean the same way."""
    gdd = degree_days_modified(tmin, tmax, 50.0, 86.0)
    gdd = np.where(np.isfinite(tmax) & np.isfinite(tmin), gdd, np.nan)
    if office_rounding:
        gdd = np.floor(gdd + 0.5)
    with np.errstate(invalid="ignore"):
        daily = np.nanmean(gdd, axis=0)
    if office_rounding:
        daily = np.floor(daily + 0.5)
    counts = np.isfinite(gdd).sum(axis=0)
    counts[climatology.FEB29] = counts.max()  # February 29 reports in leap years only
    daily[climatology.FEB29] = np.nan_to_num(daily[climatology.FEB29])
    lo, hi = SUMMER
    return np.cumsum(daily), counts, float(np.nanmean(tmax[:, lo:hi])), float(np.nanmean(tmin[:, lo:hi]))


def grid_normal(period: str, j: int, i: int) -> tuple[np.ndarray, float, float]:
    w = Window(j0=j, j1=j + 1, i0=i, i1=i + 1)
    totals = np.array(
        [normals.read_map(DATA, period, "dd_modified_50_86/mean", d, window=w)[0, 0] for d in CHECKPOINTS]
    )
    lo, hi = SUMMER
    days = [date.fromordinal(date(2000, 1, 1).toordinal() + s) for s in range(lo, hi)]
    tmax = [normals.read_map(DATA, period, "air_temperature_max/mean", d, window=w)[0, 0] for d in days]
    tmin = [normals.read_map(DATA, period, "air_temperature_min/mean", d, window=w)[0, 0] for d in days]
    return totals, float(np.mean(tmax)) * 1.8 + 32, float(np.mean(tmin)) * 1.8 + 32


YEARS = range(1996, 2026)


def summer_max_by_year(rows: list, j: int, i: int) -> list[float]:
    """Each year's June–August mean maximum, the grid's cell (gridMET's derived years, then the archive's) less the
    station's, °F; NaN where the station missed more than ten days."""
    cell = climatology.read_point(DATA, j, i, list(YEARS), ["air_temperature_max"])["air_temperature_max"]
    station, _ = by_year(rows, YEARS)
    lo, hi = SUMMER
    found = []
    for k in range(len(YEARS)):
        s = station[k, lo:hi]
        if np.isfinite(s).sum() < (hi - lo) - 10:
            found.append(np.nan)
            continue
        found.append(float(np.nanmean(cell[k, lo:hi]) * 1.8 + 32 - np.nanmean(s)))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet", type=Path)
    args = parser.parse_args()
    report = Reporter()
    report.step("normal maps against station normals at DATCP's points")
    sheet = read_sheet(args.sheet)
    acis = Acis(cache_dir=CACHE)
    slots = [climatology.slot(d) for d in CHECKPOINTS]
    rows = []
    for k, (name, sid) in enumerate(STATIONS.items()):
        report.progress("stations", k, len(STATIONS))
        got = station_days(acis, sid)
        lat, lon = got["meta"]["ll"][1], got["meta"]["ll"][0]
        cell = NDFD.cell_of(lat, lon)
        if cell is None:
            report.warn(f"{name}: outside the grid")
            continue
        j, i = cell
        found = {}
        for label, years in (("9120", range(1991, 2021)), ("last30", range(1996, 2026)), ("last10", range(2016, 2026))):
            tmax, tmin = by_year(got["data"], years)
            acc, counts, smax, smin = station_normal(tmax, tmin)
            found[label] = (acc[slots], int(counts.min()), smax, smin)
        tmax, tmin = by_year(got["data"], range(1991, 2021))
        found["9120_office"] = (station_normal(tmax, tmin, office_rounding=True)[0][slots],)
        grid = {p: grid_normal(p, j, i) for p in ("last30", "last10")}
        rows.append(
            {
                "name": name,
                "station": got["meta"]["name"],
                "sid": sid,
                "ll": (lat, lon),
                "sheet": sheet[name][slots] if name in sheet else None,
                "acis": found,
                "grid": grid,
                "years": summer_max_by_year(got["data"], j, i),
            }
        )
        report.detail(f"{name}: {got['meta']['name']} ({lat:.3f}, {lon:.3f}) → cell ({j}, {i})")
    report.progress("stations", len(STATIONS), len(STATIONS))
    OUT.write_text(render(rows))
    report.step(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if report.finish(f"{len(rows)} stations") else 1


def render(rows: list[dict]) -> str:
    out = [
        "# Normals against station normals",
        "",
        "Generated by `scripts/compare_station_normals.py` (PLAN.md Phase 6 D5). Modified growing degree days",
        "50/86 °F from January 1, mean over the years. Stations: the 18 behind DATCP's normals spreadsheet",
        "(the Wisconsin State Climatology Office's 1991–2020 normals, April 2021), with their daily maximum and",
        "minimum from ACIS. A station's normal is each calendar day's mean over the years that reported it,",
        "accumulated (the Climatology Office's method). The grid's are `agdata.normals`' maps at the station's",
        "cell: `last30` (1996–2025: adjusted gridMET to 2015, the archive after) and `last10` (2016–2025).",
        "",
        "Cooperative observers (the WWTPs, Hancock, Lancaster, Medford, Watertown, Cumberland) read their",
        "thermometers once a day, often in the morning, so a station day isn't midnight to midnight; totals over a",
        "season barely move, but single days do.",
        "",
        "## 1. The spreadsheet against ACIS, 1991–2020",
        "",
        "The spreadsheet's total by each date, and ACIS's over the same years less it.",
        "",
        "| Station | "
        + " | ".join(d.strftime("%b %-d") for d in CHECKPOINTS)
        + " | ACIS − sheet, Dec 31 | the same, rounded as the Office rounds | fewest years |",
        "| --- | " + " | ".join("---:" for _ in CHECKPOINTS) + " | ---: | ---: | ---: |",
    ]
    for r in rows:
        acc, count, *_ = r["acis"]["9120"]
        (office,) = r["acis"]["9120_office"]
        if r["sheet"] is None:
            continue
        cells = " | ".join(f"{v:.0f}" for v in r["sheet"])
        plain, rounded = acc[-1] - r["sheet"][-1], office[-1] - r["sheet"][-1]
        out.append(f"| {r['name']} | {cells} | {plain:+.0f} | {rounded:+.0f} | {count} |")
    out += [
        "",
        "The sheet runs about 50 GDD a year above the same stations' unrounded normals. Its daily values are whole",
        "numbers: rounding each day's GDD to a whole degree day with halves up (a day's mean of whole-degree",
        "readings often ends in .5), then each calendar day's mean the same way, reproduces it (the last column but",
        "one). So the sheet and ACIS agree; the sheet's convention adds ~50 GDD a year. The normal maps don't round.",
    ]
    out += [
        "",
        "## 2. The grid against the station, the same years",
        "",
        "`last30` at the station's cell less the station's own 1996–2025, by date, and summer's (June–August) mean",
        "maximum and minimum, grid less station, °F.",
        "",
        "| Station (cell's lat, lon) | "
        + " | ".join(d.strftime("%b %-d") for d in CHECKPOINTS)
        + " | station Dec 31 | summer max | summer min | fewest years |",
        "| --- | " + " | ".join("---:" for _ in CHECKPOINTS) + " | ---: | ---: | ---: | ---: |",
    ]
    diffs30, diffs10 = [], []
    for r in rows:
        acc, count, smax, smin = r["acis"]["last30"]
        totals, gmax, gmin = r["grid"]["last30"]
        d = totals - acc
        diffs30.append(d[-1] / acc[-1])
        cells = " | ".join(f"{v:+.0f}" for v in d)
        out.append(
            f"| {r['name']} ({r['ll'][0]:.2f}, {r['ll'][1]:.2f}) | {cells} | {acc[-1]:.0f} | {gmax - smax:+.1f} | "
            f"{gmin - smin:+.1f} | {count} |"
        )
    out += [
        "",
        "## 3. The archive alone: `last10` against the station's 2016–2025",
        "",
        "| Station | "
        + " | ".join(d.strftime("%b %-d") for d in CHECKPOINTS)
        + " | station Dec 31 | summer max | summer min | fewest years |",
        "| --- | " + " | ".join("---:" for _ in CHECKPOINTS) + " | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        acc, count, smax, smin = r["acis"]["last10"]
        totals, gmax, gmin = r["grid"]["last10"]
        d = totals - acc
        diffs10.append(d[-1] / acc[-1])
        cells = " | ".join(f"{v:+.0f}" for v in d)
        out.append(f"| {r['name']} | {cells} | {acc[-1]:.0f} | {gmax - smax:+.1f} | {gmin - smin:+.1f} | {count} |")
    out += [
        "",
        "## 4. Summer's maximum, year by year",
        "",
        "Each year's June–August mean maximum at the station's cell less the station's, °F: adjusted gridMET for",
        "1996–2015, the archive from 2016.",
        "",
        "| Station | " + " | ".join(f"{y % 100:02d}" for y in YEARS) + " |",
        "| --- | " + " | ".join("---:" for _ in YEARS) + " |",
    ]
    for r in rows:
        out.append(f"| {r['name']} | " + " | ".join(f"{v:+.0f}" if np.isfinite(v) else "." for v in r["years"]) + " |")
    median = np.nanmedian(np.array([r["years"] for r in rows]), axis=0)
    out.append("| **median** | " + " | ".join(f"**{v:+.1f}**" for v in median) + " |")
    out += [
        "",
        "## Summary",
        "",
        f"The year's total, grid less station: `last30` median {np.median(diffs30) * 100:+.1f}% "
        f"(range {min(diffs30) * 100:+.1f}% to {max(diffs30) * 100:+.1f}%); `last10` median "
        f"{np.median(diffs10) * 100:+.1f}% ({min(diffs10) * 100:+.1f}% to {max(diffs10) * 100:+.1f}%).",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
