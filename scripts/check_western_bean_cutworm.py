"""Western bean cutworm (agmodels `western-bean-cutworm`) on real weather (`docs/plans/models.md` part H2).

1. NEWA on the same weather: on the hours of the Wisconsin NEWA stations (tmp/newa/hours/, scripts/fetch_newa.py),
   the days the moth flight reaches 5, 10, 25, 50, 75, 90 and 95 % by NEWA's model and by ours. NEWA's model is its
   table on Hanson et al. 2015's log-logistic (°C·d above 3.3 °C, days of year 60–305), with its degree days as
   deployed: each day's max and min converted to °C and rounded to a whole degree, then passed to its formula in the
   wrong order (max as the minimum), so a day whose minimum rounds below 3.3 °C counts nothing and the cap applies
   only when the minimum is above 23.9 °C. Also as NEWA intended (the maximum capped at 23.9 °C, then averaged), to
   split the difference into the code's slip and the formula. Ours: Hanson's simple method (the daily mean capped at
   75 °F, base 38 °F, from March 1) and our curve, on the same station days and on the archive at the station's cell.
2. Typical dates at Arlington, Hancock and Rhinelander on the 1996–2025 normals (each year's own running total from
   March 1, averaged, as /api/v2/climate/normals computes it; the capped mean isn't one of its methods), and the old
   model's (VDIFN's: single sine above 50 °F from May 1, 25, 50 and 75 % at 1,320, 1,420 and 1,535).
3. DATCP's black light traps (docs/validation/data/datcp-blacklight-traps/), when that table holds western bean
   cutworm: each site-year's 25, 50 and 75 % of the season's catch against our dates on the archive.

    uv run python scripts/check_western_bean_cutworm.py [--out docs/validation/models/western-bean-cutworm/weather.md]
"""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from newa_reference import CACHE, js_round, load_hours, make_days

from agdata import climatology
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.progress import Reporter
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_average_capped_mean, degree_days_sine
from agmodels.insects.western_bean_cutworm import INSECT
from agmodels.phenology import curves, dd_grid

LEVELS = (5, 10, 25, 50, 75, 90, 95)
NEWA_C = {5: 1321, 10: 1364, 25: 1432, 50: 1502, 75: 1577, 90: 1654, 95: 1709}  # NEWA's table, °C·d (Hanson's Table 4)
SITES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
NORMAL_YEARS = range(1996, 2026)
OLD = {25: 1320, 50: 1420, 75: 1535}  # VDIFN's (Ahmad 1979's), single sine 50 °F from May 1
TRAPS = Path("docs/validation/data/datcp-blacklight-traps")


def our_dd_at(level: int) -> float:
    """Our curve's degree days (°F) at a level of the flight (%)."""
    return float(np.interp(level / 100, curves(INSECT)["generations_adult_flight"], dd_grid()))


def newa_deployed_c(lo_f: float, hi_f: float) -> float:
    """NEWA's daily degree days (°C) as deployed: rounded °C, the formula's (min, max) given (max, min)."""
    lo, hi = js_round((lo_f - 32) * 5 / 9), js_round((hi_f - 32) * 5 / 9)
    return _newa_formula(tmin=hi, tmax=lo)  # the slip: its arguments swapped


def newa_intended_c(lo_f: float, hi_f: float) -> float:
    lo, hi = js_round((lo_f - 32) * 5 / 9), js_round((hi_f - 32) * 5 / 9)
    return _newa_formula(tmin=lo, tmax=hi)


def _newa_formula(*, tmin: float, tmax: float) -> float:
    """NEWA's daily formula as written: the maximum capped at 23.9 °C before averaging, base 3.3 °C."""
    if tmax > 23.9:
        return max((23.9 + tmin) / 2 - 3.3, 0.0)
    if tmax < 3.3 or (tmax + tmin) / 2 < 3.3:
        return 0.0
    return (tmax + tmin) / 2 - 3.3


def first(total: np.ndarray, threshold: float) -> int | None:
    k = int(np.argmax(total >= threshold))
    return k if total[k] >= threshold else None


def ours_total(lo_f: np.ndarray, hi_f: np.ndarray, year: int) -> np.ndarray:
    """Hanson's simple degree days (°F) from March 1; a missing day adds nothing."""
    dd = np.nan_to_num(degree_days_average_capped_mean(lo_f, hi_f, base=38.0, upper=75.0))
    dd[: (date(year, 3, 1) - date(year, 1, 1)).days] = 0.0
    return np.cumsum(dd)


def _day(year: int, k: int | None) -> str:
    return "–" if k is None else f"{date(year, 1, 1) + timedelta(days=k):%b %-d}"


def newa_part(data: Path, lines: list[str], report: Reporter) -> None:
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    paths = [p for p in sorted((CACHE / "hours").glob("*.json")) if int(p.stem.rsplit("_", 1)[1]) < 2026]
    report.step(f"NEWA's western bean cutworm against ours on {len(paths)} station-seasons' hours and the archive")
    ours_at = {level: our_dd_at(level) for level in LEVELS}
    lines += [
        "## 1. NEWA's model against ours, on the station's hours and the archive's",
        "",
        f"Our curve passes 5, 10, 25, 50, 75, 90 and 95 % of the flight at {', '.join(f'{ours_at[v]:,.0f}' for v in LEVELS)} °F·d (Hanson's Table 4 and NEWA: {', '.join(f'{NEWA_C[v] * 1.8:,.0f}' for v in LEVELS)}). Dates of 25, 50 and 75 % of the flight: NEWA as deployed / NEWA as intended / ours on the station's days / ours on the archive.",
        "",
        "| Station | Year | 25 % | 50 % | 75 % |",
        "| --- | --- | --- | --- | --- |",
    ]
    keys = ("intended", "method", "station", "grid")
    diffs: dict[str, dict[int, list[int]]] = {k: {v: [] for v in LEVELS} for k in keys}
    totals_by_august: list[tuple[float, float, float]] = []
    for path in paths:
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        days = make_days(load_hours(path))
        if len(days) < 290:
            continue
        station = stations[sid]
        lo = np.array([d.mint for d in days])
        hi = np.array([d.maxt for d in days])
        ok = np.isfinite(lo) & np.isfinite(hi)
        counted = np.array([60 <= d.doy <= 305 for d in days])
        deployed = np.cumsum(
            [newa_deployed_c(a, b) if k and c else 0.0 for a, b, k, c in zip(lo, hi, ok, counted, strict=True)]
        )
        intended = np.cumsum(
            [newa_intended_c(a, b) if k and c else 0.0 for a, b, k, c in zip(lo, hi, ok, counted, strict=True)]
        )
        ours = ours_total(np.where(ok, lo, np.nan), np.where(ok, hi, np.nan), year)
        cell = NDFD.cell_of(station["lat"], station["lon"])
        grid = None
        if cell is not None:
            if year not in stores:
                stores[year] = GridStore.open(data, DAILY, year, temps)
            g_lo, g_hi = (
                np.asarray(stores[year].read_point(n, *cell)) * 1.8 + 32
                for n in ("air_temperature_min", "air_temperature_max")
            )
            grid = ours_total(g_lo, g_hi, year)
        august = (date(year, 8, 1) - date(year, 1, 1)).days
        totals_by_august.append((deployed[august] * 1.8, intended[august] * 1.8, ours[august]))
        found = {}
        for v in LEVELS:
            n = first(deployed, NEWA_C[v])
            found[v] = (
                n,
                first(intended, NEWA_C[v]),
                first(ours, ours_at[v]),
                first(grid, ours_at[v]) if grid is not None else None,
            )
            for key, value in zip(
                keys, (found[v][1], first(ours, NEWA_C[v] * 1.8), found[v][2], found[v][3]), strict=True
            ):
                if n is not None and value is not None:
                    diffs[key][v].append(value - n)
        lines.append(
            f"| {station['name']} | {year} | "
            + " | ".join(" / ".join(_day(year, k) for k in found[v]) for v in (25, 50, 75))
            + " |"
        )
        report.detail(lines[-1])
    labels = {
        "intended": "NEWA as intended (the code's slip alone)",
        "method": "Hanson's simple method at NEWA's totals (the method alone)",
        "station": "ours on the station's days (method and curve)",
        "grid": "ours on the archive",
    }
    lines += ["", "Days later (+) or earlier (−) than NEWA as deployed (median, 10th–90th percentile, range, n):", ""]
    for key in keys:
        for v in (5, 25, 50, 75, 95):
            values = np.array(diffs[key][v])
            if len(values):
                lines.append(
                    f"- {labels[key]}, {v} %: {np.median(values):+.0f} ({np.percentile(values, 10):+.0f} to {np.percentile(values, 90):+.0f}; {values.min():+d} to {values.max():+d}), n = {len(values)}"
                )
    t = np.array(totals_by_august)
    lines += [
        "",
        f"Degree days (°F) from March 1 to August 1, mean over the station-years: NEWA as deployed {t[:, 0].mean():,.0f}, as intended {t[:, 1].mean():,.0f}, Hanson's method {t[:, 2].mean():,.0f}.",
    ]


def normal_totals(lat: float, lon: float, data: Path, method, start: date) -> np.ndarray:
    """The normal running total from `start` (MM-DD of any year) on the 366 slots: each year's own, averaged."""
    cell = NDFD.cell_of(lat, lon)
    assert cell is not None
    years = list(NORMAL_YEARS)
    found = climatology.read_point(data, *cell, years, ["air_temperature_min", "air_temperature_max"])
    daily = []
    for k, year in enumerate(years):
        lo, hi = climatology.degree_day_temperatures(
            found["air_temperature_min"][k], found["air_temperature_max"][k], year
        )
        usable = np.isfinite(lo) & np.isfinite(hi)
        daily.append(np.where(usable, method(np.where(usable, lo, 0.0), np.where(usable, hi, 0.0)), np.nan))
    # As the API: a year missing too many days (gridMET's maximum for 2011–2013 is left out) doesn't count
    return climatology.running(np.stack(daily), years, start=climatology.slot(start)).mean


def when(total: np.ndarray, threshold: float) -> str:
    k = int(np.argmax(total >= threshold))
    found = climatology.slot_date(k, 2001 if k != 59 else 2000)
    return "–" if not total[k] >= threshold or found is None else f"{found:%b %-d}"


def normals_part(data: Path, lines: list[str], report: Reporter) -> None:
    report.step(f"typical dates on the {NORMAL_YEARS[0]}–{NORMAL_YEARS[-1]} normals at {', '.join(SITES)}")
    tables, x = curves(INSECT), dd_grid()
    window = x[tables["window_scout_corn_for_egg_masses"] > 0]
    events = {f"{v} % of the moths have flown": our_dd_at(v) for v in (5, 25, 50, 75, 90)}
    events["Scouting window opens"] = float(window[0])
    events["Most egg masses in fields"] = float(x[np.argmax(tables["activity_egg_masses"])])
    events["Scouting window closes"] = float(window[-1])
    ours = {
        s: normal_totals(
            *SITES[s], data, lambda lo, hi: degree_days_average_capped_mean(lo, hi, 38.0, 75.0), date(2001, 3, 1)
        )
        for s in SITES
    }
    old = {
        s: normal_totals(*SITES[s], data, lambda lo, hi: degree_days_sine(lo, hi, 50.0), date(2001, 5, 1))
        for s in SITES
    }
    lines += [
        "",
        f"## 2. Typical dates on the {NORMAL_YEARS[0]}–{NORMAL_YEARS[-1]} normals",
        "",
        "The day the normal running total (each year's own, averaged over the 30 years, at the archive's cell) reaches each event. Ours: Hanson's simple method, 38/75 °F from March 1. Old: VDIFN's model, single sine above 50 °F from May 1.",
        "",
        "| Event | Degree days | " + " | ".join(SITES) + " |",
        "| --- | --- | " + " | ".join("---" for _ in SITES) + " |",
    ]
    for label, threshold in events.items():
        lines.append(f"| {label} | {threshold:,.0f} | " + " | ".join(when(ours[s], threshold) for s in SITES) + " |")
    for v, threshold in OLD.items():
        lines.append(
            f"| Old: {v} % flown | {threshold:,} (sine 50) | "
            + " | ".join(when(old[s], threshold) for s in SITES)
            + " |"
        )
    for line in lines[-11:]:
        report.detail(line)


def _count(text: str) -> float:
    """A published weekly count; anything but a number (blank, '-', 'NA') read as none caught, as
    `scripts/check_insect_traps.py` reads it; 2024's '*' marks (counts over two or three weeks) dropped."""
    try:
        return float(text.rstrip("*"))
    except ValueError:
        return 0.0


def trap_seasons(network: str) -> dict[tuple[str, int], list[tuple[date, float]]]:
    """Each site-year's weekly western bean cutworm counts in one of DATCP's networks."""
    if network == "black light":
        rows = [r for r in csv.DictReader((TRAPS / "weekly.csv").open()) if r["species"] == "western bean cutworm"]
    else:
        rows = list(csv.DictReader((TRAPS / "wbc-pheromone-weekly.csv").open()))
    by: dict[tuple[str, int], list[tuple[date, float]]] = {}
    for r in rows:
        by.setdefault((r["site"], int(r["year"])), []).append((date.fromisoformat(r["week_end"]), _count(r["count"])))
    return by


def traps_part(data: Path, lines: list[str], report: Reporter) -> None:
    """Each site-year's 25, 50 and 75 % of the season's catch against our dates on the archive at the trap's cell."""
    lines += ["", "## 3. DATCP's traps", ""]
    if not (TRAPS / "weekly.csv").exists() or not (TRAPS / "sites.csv").exists():
        lines.append("Pending: the trap tables aren't there yet.")
        report.warn("DATCP's trap tables aren't there yet")
        return
    located = {
        (r["network"], r["site"]): (float(r["lat"]), float(r["lon"]))
        for r in csv.DictReader((TRAPS / "sites.csv").open())
    }
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    lines += [
        f"From `{TRAPS}/` (DATCP's weekly counts; see its README). Each site-year with at least 25 moths (Hanson et al.'s rule): the week (its last day) in which the season's catch passed 25, 50 and 75 %, against the day our curve passes the same level on the archive at the trap's approximate location. A week's catch is dated by its last day, so a difference from −6 to 0 days falls inside the week. Hanson's model was fitted to black light traps, which catch both sexes; pheromone traps catch males, whose flight can peak later (Hanson et al. 2015, citing Mahrt et al. 1987).",
        "",
    ]
    for network, label in (("black light", "Black light traps"), ("WBC pheromone", "Pheromone traps")):
        seasons = trap_seasons("black light" if network == "black light" else "pheromone")
        report.step(f"DATCP's {network} traps: {len(seasons)} site-years")
        diffs: dict[int, list[int]] = {25: [], 50: [], 75: []}
        table: list[str] = []
        for (site, year), weeks in sorted(seasons.items(), key=lambda item: (item[0][1], item[0][0])):
            weeks.sort()
            total = sum(c for _, c in weeks)
            where = located.get((network, site))
            if total < 25 or where is None:
                continue
            cell = NDFD.cell_of(*where)
            if cell is None:
                continue
            if year not in stores:
                stores[year] = GridStore.open(data, DAILY, year, temps)
            g_lo, g_hi = (
                np.asarray(stores[year].read_point(n, *cell)) * 1.8 + 32
                for n in ("air_temperature_min", "air_temperature_max")
            )
            ours = ours_total(g_lo, g_hi, year)
            cum = np.cumsum([c for _, c in weeks]) / total
            cells = []
            for v in (25, 50, 75):
                trap_day = weeks[int(np.argmax(cum >= v / 100))][0]
                k = first(ours, our_dd_at(v))
                ours_day = None if k is None else date(year, 1, 1) + timedelta(days=k)
                if ours_day is None:
                    cells.append(f"{trap_day:%b %-d} / –")
                    continue
                cells.append(f"{trap_day:%b %-d} / {(ours_day - trap_day).days:+d}")
                diffs[v].append((ours_day - trap_day).days)
            table.append(f"| {site} | {year} | {total:,.0f} | " + " | ".join(cells) + " |")
        lines += [
            f"### {label}",
            "",
            "Ours − the trap's week end, days (median, 10th–90th percentile; inside the week, −6 to 0; within a week either side, −13 to +7; n):",
            "",
        ]
        for v, values in diffs.items():
            if values:
                a = np.array(values)
                inside = int(((a >= -6) & (a <= 0)).sum())
                near = int(((a >= -13) & (a <= 7)).sum())
                lines.append(
                    f"- {v} %: {np.median(a):+.0f} ({np.percentile(a, 10):+.0f} to {np.percentile(a, 90):+.0f}; inside {inside}, within a week {near}), n = {len(a)}"
                )
        report.detail(f"{label}: " + "; ".join(lines[-3:]))
        lines += [
            "",
            "| Site | Year | Moths | 25 % week / ours − it | 50 % | 75 % |",
            "| --- | --- | --- | --- | --- | --- |",
            *table,
            "",
        ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/western-bean-cutworm/weather.md")
    parser.add_argument("--data", default="data")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    lines = [
        "# Western bean cutworm: NEWA on the same weather, typical dates in Wisconsin, and DATCP's traps",
        "",
        "Written by `scripts/check_western_bean_cutworm.py`. Ours: Hanson et al. 2015's simple degree days (the daily mean capped at 75 °F, base 38 °F) from March 1, and a curve following their log-logistic flight. Station days are NEWA's on the local clock; the archive's are CST.",
        "",
    ]
    newa_part(Path(args.data), lines, report)
    normals_part(Path(args.data), lines, report)
    traps_part(Path(args.data), lines, report)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    report.step(f"wrote {args.out}")
    if not report.finish("NEWA's stations, the normals and DATCP's traps"):
        sys.exit(1)


if __name__ == "__main__":
    main()
