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

from agdata import climatestore, climatology, normals
from agdata.clients.acis import Acis
from agdata.grid import NDFD, Window
from agdata.progress import Reporter
from agdata.sources import gridmet
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


def by_year(rows: list, years: range | list[int]) -> tuple[np.ndarray, np.ndarray]:
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
LEFT_OUT = climatestore.LEFT_OUT["air_temperature_max"]  # gridMET's maximum, left out of the normal (Q38)
_RAW: dict[int, gridmet.Year] = {}


def _raw_summer_max(year: int, lat: float, lon: float) -> float:
    """gridMET's own June–August mean maximum at its pixel nearest a point, °F, unadjusted: for the years the normal
    leaves out, so the table still shows why."""
    if year not in _RAW:
        _RAW[year] = gridmet.read(gridmet.path(DATA, "tmmx", year), "tmmx")
    found = _RAW[year]
    fj, fi = found.grid.fractional_index(lat, lon)
    summer = np.array([d.month in (6, 7, 8) for d in found.days])
    return float(np.nanmean(found.values[summer, round(float(fj)), round(float(fi))])) * 1.8 + 32


def summer_max_by_year(rows: list, j: int, i: int, lat: float, lon: float) -> list[float]:
    """Each year's June–August mean maximum, the grid's cell (gridMET's derived years, then the archive's; for the
    years left out, gridMET's raw pixel) less the station's, °F; NaN where the station missed more than ten days."""
    cell = climatology.read_point(DATA, j, i, list(YEARS), ["air_temperature_max"])["air_temperature_max"]
    station, _ = by_year(rows, YEARS)
    lo, hi = SUMMER
    found = []
    for k, year in enumerate(YEARS):
        s = station[k, lo:hi]
        if np.isfinite(s).sum() < (hi - lo) - 10:
            found.append(np.nan)
            continue
        grid = _raw_summer_max(year, lat, lon) if year in LEFT_OUT else float(np.nanmean(cell[k, lo:hi])) * 1.8 + 32
        found.append(grid - float(np.nanmean(s)))
    return found


FREEZE_F = (32, 28)


def station_freezes(tmin: np.ndarray) -> dict[str, float]:
    """The median last spring and first fall freeze (calendar slots) at each of `FREEZE_F` from a station's daily
    minimums (°F), as the normal maps find them (`climatology.freezes`)."""
    found = {}
    for f in FREEZE_F:
        spring, fall = climatology.freezes(tmin, float(f)).dates(0.5)
        found[f"spring_{f}"], found[f"fall_{f}"] = float(spring), float(fall)
    return found


def grid_freezes(period: str, j: int, i: int) -> dict[str, float]:
    w = Window(j0=j, j1=j + 1, i0=i, i1=i + 1)
    found = {}
    for f in FREEZE_F:
        for season in ("spring", "fall"):
            found[f"{season}_{f}"] = float(normals.read_map(DATA, period, f"freeze_{f}/{season}_p50", window=w)[0, 0])
    return found


BOX_STATS = (
    ("modified GDD 50/86 by December 31", "dd_modified_50_86/mean", date(2025, 12, 31), 1.0, "GDD"),
    ("precipitation by December 31", "precipitation/mean", date(2025, 12, 31), 1 / 25.4, "in"),
    ("mean maximum, July 15", "air_temperature_max/mean", date(2025, 7, 15), 1.8, "°F"),
    ("mean minimum, January 15", "air_temperature_min/mean", date(2025, 1, 15), 1.8, "°F"),
    ("median last spring freeze (32 °F)", "freeze_32/spring_p50", None, 1.0, "days"),
    ("median first fall freeze (32 °F)", "freeze_32/fall_p50", None, 1.0, "days"),
)


def box_differences() -> list[tuple[str, np.ndarray, str]]:
    """`last10` less `last30` over the whole map (cells both have), P10/P50/P90, per statistic."""
    found = []
    for label, name, day, factor, unit in BOX_STATS:
        d = (normals.read_map(DATA, "last10", name, day) - normals.read_map(DATA, "last30", name, day)) * factor
        found.append((label, np.nanpercentile(d, [10, 50, 90]), unit))
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
        periods = {
            "9120": range(1991, 2021),
            "last30": [y for y in YEARS if y not in LEFT_OUT],
            "last30_all": YEARS,
            "last10": range(2016, 2026),
        }
        for label, years in periods.items():
            tmax, tmin = by_year(got["data"], years)
            acc, counts, smax, smin = station_normal(tmax, tmin)
            found[label] = (acc[slots], int(counts.min()), smax, smin)
            if label in ("last30_all", "last10"):
                found[f"{label}_freezes"] = station_freezes(tmin)
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
                "years": summer_max_by_year(got["data"], j, i, lat, lon),
                "freezes": {p: grid_freezes(p, j, i) for p in ("last30", "last10")},
            }
        )
        report.detail(f"{name}: {got['meta']['name']} ({lat:.3f}, {lon:.3f}) → cell ({j}, {i})")
    report.progress("stations", len(STATIONS), len(STATIONS))
    report.step("last10 against last30 over the map")
    OUT.write_text(render(rows, box_differences()))
    report.step(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if report.finish(f"{len(rows)} stations") else 1


def render(rows: list[dict], box: list[tuple[str, np.ndarray, str]]) -> str:
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
        f"maximum and minimum, grid less station, °F. The station's years leave out {LEFT_OUT[0]}–{LEFT_OUT[-1]},",
        "as the grid's maximum (and so its degree days) does (gridMET's maximum is wrong in them: section 4). The",
        "last column but one is what leaving them out costs the station's own total: 27 years' normal less 30's.",
        "",
        "| Station (cell's lat, lon) | "
        + " | ".join(d.strftime("%b %-d") for d in CHECKPOINTS)
        + " | station Dec 31 | summer max | summer min | 27 years less 30, station | fewest years |",
        "| --- | " + " | ".join("---:" for _ in CHECKPOINTS) + " | ---: | ---: | ---: | ---: | ---: |",
    ]
    diffs30, diffs10, costs = [], [], []
    for r in rows:
        acc, count, smax, smin = r["acis"]["last30"]
        every = r["acis"]["last30_all"][0]
        totals, gmax, gmin = r["grid"]["last30"]
        d = totals - acc
        diffs30.append(d[-1] / acc[-1])
        costs.append(acc[-1] - every[-1])
        cells = " | ".join(f"{v:+.0f}" for v in d)
        out.append(
            f"| {r['name']} ({r['ll'][0]:.2f}, {r['ll'][1]:.2f}) | {cells} | {acc[-1]:.0f} | {gmax - smax:+.1f} | "
            f"{gmin - smin:+.1f} | {acc[-1] - every[-1]:+.0f} | {count} |"
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
        f"1996–2015, the archive from 2016. In italics, {LEFT_OUT[0]}–{LEFT_OUT[-1]}: gridMET's own maximum at its",
        "pixel nearest the station, unadjusted, which the normal leaves out (Q38).",
        "",
        "| Station | " + " | ".join(f"{y % 100:02d}" for y in YEARS) + " |",
        "| --- | " + " | ".join("---:" for _ in YEARS) + " |",
    ]
    for r in rows:
        out.append(
            f"| {r['name']} | " + " | ".join(_year_cell(v, y) for v, y in zip(r["years"], YEARS, strict=True)) + " |"
        )
    median = np.nanmedian(np.array([r["years"] for r in rows]), axis=0)
    out.append("| **median** | " + " | ".join(f"**{v:+.1f}**" for v in median) + " |")
    out += [
        "",
        "## 5. `last10` against `last30`",
        "",
        "Over the map (every cell both periods have), `last10` less `last30`: the change from 1996–2025 to",
        "2016–2025, with the sources' difference after the adjustment (D84) in it too.",
        "",
        "| Statistic | P10 | median | P90 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, (p10, p50, p90), unit in box:
        out.append(f"| {label} ({unit}) | {p10:+.1f} | {p50:+.1f} | {p90:+.1f} |")
    out += [
        "",
        "At the stations, the same change on the grid and in the station's own record (the station's 30 years",
        f"without {LEFT_OUT[0]}–{LEFT_OUT[-1]}, as the grid's). Where the two agree, the grid's 30 years carry the",
        "stations' change between the periods; where they don't, the difference is the sources'.",
        "",
        "| Station | GDD by Dec 31, grid | station | summer max, grid (°F) | station | summer min, grid (°F) "
        "| station |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    gaps = []
    for r in rows:
        g30, gmax30, gmin30 = r["grid"]["last30"]
        g10, gmax10, gmin10 = r["grid"]["last10"]
        s30, _, smax30, smin30 = r["acis"]["last30"]
        s10, _, smax10, smin10 = r["acis"]["last10"]
        gaps.append((g10[-1] - g30[-1]) - (s10[-1] - s30[-1]))
        out.append(
            f"| {r['name']} | {g10[-1] - g30[-1]:+.0f} | {s10[-1] - s30[-1]:+.0f} | {gmax10 - gmax30:+.1f} | "
            f"{smax10 - smax30:+.1f} | {gmin10 - gmin30:+.1f} | {smin10 - smin30:+.1f} |"
        )
    out += [
        "",
        f"The grid's change less the station's, GDD by December 31: median {np.median(gaps):+.0f} "
        f"({min(gaps):+.0f} to {max(gaps):+.0f}).",
        "",
        "## 6. Frost dates",
        "",
        "The median last spring and first fall freeze, the grid's cell less the station's own over the same years,",
        "in days (later is positive). The station's dates are from its daily minimums by the method the maps use",
        "(`climatology.freezes`); its dates are given beside. A cooperative station read in the morning puts a",
        "night's minimum on the day it was read, so its dates may run a day late.",
        "",
        "| Station | period | 32 °F spring: station | grid − station | 32 °F fall: station | grid − station | "
        "28 °F spring: station | grid − station | 28 °F fall: station | grid − station |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    shifts: dict[str, list[float]] = {}
    for r in rows:
        for period, key in (("last30", "last30_all_freezes"), ("last10", "last10_freezes")):
            station, grid = r["acis"][key], r["freezes"][period]
            cells = []
            for f in FREEZE_F:
                for season in ("spring", "fall"):
                    k = f"{season}_{f}"
                    d = grid[k] - station[k]
                    if np.isfinite(d):
                        shifts.setdefault(f"{period} {k}", []).append(d)
                    cells.append(
                        f"{_slot_text(station[k])} | {d:+.0f}" if np.isfinite(d) else f"{_slot_text(station[k])} | ."
                    )
            out.append(f"| {r['name']} | {period} | " + " | ".join(cells) + " |")
    out += ["", "Medians, grid less station, days:", ""]
    for k, v in shifts.items():
        out.append(
            f"- {k.replace('_', ' at ')} °F: {np.median(v):+.1f} "
            f"(P10 {np.percentile(v, 10):+.0f}, P90 {np.percentile(v, 90):+.0f})"
        )
    out += [
        "",
        "## Summary",
        "",
        f"The year's total, grid less station: `last30` median {np.median(diffs30) * 100:+.1f}% "
        f"(range {min(diffs30) * 100:+.1f}% to {max(diffs30) * 100:+.1f}%); `last10` median "
        f"{np.median(diffs10) * 100:+.1f}% ({min(diffs10) * 100:+.1f}% to {max(diffs10) * 100:+.1f}%). Leaving "
        f"{LEFT_OUT[0]}–{LEFT_OUT[-1]} out of the 30 years changes the stations' own totals by a median of "
        f"{np.median(costs):+.0f} GDD a year ({min(costs):+.0f} to {max(costs):+.0f}), "
        "so the shorter period costs the normal little.",
        "",
    ]
    return "\n".join(out)


def _slot_text(value: float) -> str:
    if not np.isfinite(value):
        return "."
    day = climatology.slot_date(round(value), 2000)
    return day.strftime("%b %-d") if day is not None else "."


def _year_cell(value: float, year: int) -> str:
    if not np.isfinite(value):
        return "."
    return f"*{value:+.0f}*" if year in LEFT_OUT else f"{value:+.0f}"


if __name__ == "__main__":
    sys.exit(main())
