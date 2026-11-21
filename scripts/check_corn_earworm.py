"""Corn earworm's default biofix and egg-laying spread against DATCP's corn earworm pheromone traps, 2021–2026 (models-plan part H, batch H2).

DATCP's pheromone network (docs/validation/data/datcp-blacklight-traps/cew-pheromone-weekly.csv, 12–16 sites a year,
Hartstack traps set about July 1 and read weekly to mid or late September) catches the migrant flights. For each
site-year with 50 or more moths:

1. The "significant flight": the first week with 35 or more moths (5 a night, the low end of UW–Madison's pheromone
   threshold of 5 to 10 a night), and the first such week from July 25 (the main flight, past the June–July
   migrants). Fixed default dates are compared with it: 0 inside the week (the 7 days ending on its date), else days
   before (−) or after (+). Also the degree days (single sine 55/92 °F) from January 1 at the week's middle, to see
   whether degree days would place it better than a date (they wouldn't for a migrant: compare the spreads).
2. The flight after the significant week (from July 25), as degree days (55/92 °F) from that week's first day to each
   later week's middle, each week weighted by its share of the site-year's catch from then on, every site-year
   counting alike: the percentiles that set the model's egg-laying curve. Catches stop when traps come down (mid to
   late September), so the tail is cut short.
3. Degree days from the default biofix to October 15 at the site, against the model's larval period (73–437) and a
   generation (873).

    uv run python scripts/check_corn_earworm.py [--out docs/validation/models/corn-earworm/traps.md]

Its summary is the "Against Wisconsin's pheromone traps" section of docs/validation/models/corn-earworm.md.
"""

import argparse
import csv
import statistics
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_sine
from agmodels.insects.corn_earworm import INSECT

DATA = Path(__file__).resolve().parent.parent / "docs/validation/data/datcp-blacklight-traps"
SIGNIFICANT = 35
MIN_MOTHS = 50
MAIN_FROM = (7, 25)
CANDIDATES = ((8, 1), (8, 8), (8, 15), (8, 20))


def offset(day: date, week_end: date) -> int:
    if week_end - timedelta(days=6) <= day <= week_end:
        return 0
    return (day - week_end).days if day > week_end else (day - (week_end - timedelta(days=6))).days


def read() -> dict[tuple[int, str, str], list[tuple[date, int]]]:
    weeks: dict[tuple[int, str, str], list[tuple[date, int]]] = defaultdict(list)
    with (DATA / "cew-pheromone-weekly.csv").open() as f:
        for r in csv.DictReader(f):
            if r["count"].isdigit():
                weeks[(int(r["year"]), r["site"], r["county"])].append(
                    (date.fromisoformat(r["week_end"]), int(r["count"]))
                )
    return {k: sorted(v) for k, v in weeks.items()}


def locations() -> dict[tuple[str, str], tuple[float, float]]:
    with (DATA / "sites.csv").open() as f:
        return {
            (r["site"], r["county"]): (float(r["lat"]), float(r["lon"]))
            for r in csv.DictReader(f)
            if r["network"] == "CEW pheromone"
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/corn-earworm/traps.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    default = tuple(int(p) for p in INSECT.biofix.split("-"))
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    where = locations()
    lines = [
        "# Corn earworm: the default biofix against DATCP's pheromone traps, 2021–2026",
        "",
        f"Written by `scripts/check_corn_earworm.py` from DATCP's corn earworm pheromone tables (`docs/validation/data/datcp-blacklight-traps/cew-pheromone-weekly.csv`) and the archive at each site's cell. Site-years with {MIN_MOTHS} or more moths. Significant flight: the first week with {SIGNIFICANT} or more moths (5 a night); main flight: the first such week from July 25. Days off: 0 inside the week (the 7 days ending on its date), else days before (−) or after (+) it. DD: single sine 55/92 °F.",
        "",
        "| Year | Site | Moths | Significant week | Main flight's week | DD from Jan 1 (main) | "
        + " | ".join(f"{date(2001, *c):%b %-d} off" for c in CANDIDATES)
        + f" | DD {date(2001, *default):%b %-d} to Oct 15 |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in CANDIDATES) + " | --- |",
    ]
    offs: dict[tuple[str, tuple[int, int]], list[int]] = defaultdict(list)
    main_doy: list[int] = []
    main_dd: list[float] = []
    to_oct15: list[float] = []
    after: list[tuple[np.ndarray, np.ndarray]] = []  # per site-year: DD from the main week's start, and weights
    for (year, site, county), weeks in sorted(read().items()):
        total = sum(c for _, c in weeks)
        if total < MIN_MOTHS:
            continue
        sig = next((d for d, c in weeks if c >= SIGNIFICANT), None)
        main = next((d for d, c in weeks if c >= SIGNIFICANT and d >= date(year, *MAIN_FROM)), None)
        loc = where[(site, county)]
        cell = NDFD.cell_of(*loc)
        assert cell is not None
        if year not in stores:
            stores[year] = GridStore.open(Path(args.data), DAILY, year, temps)
        lo, hi = (stores[year].read_point(n, *cell) for n in ("air_temperature_min", "air_temperature_max"))
        good = np.isfinite(lo) & np.isfinite(hi)
        f_lo, f_hi = (np.where(good, v * 1.8 + 32, 0.0) for v in (lo, hi))
        jan1 = np.cumsum(degree_days_sine(f_lo, f_hi, 55) - degree_days_sine(f_lo, f_hi, 92))

        def k(d: date, year: int = year) -> int:
            return (d - date(year, 1, 1)).days

        oct15 = float(jan1[k(date(year, 10, 15))] - jan1[k(date(year, *default)) - 1])
        to_oct15.append(oct15)
        cells = []
        for c in CANDIDATES:
            if sig is not None:
                offs[("significant", c)].append(offset(date(year, *c), sig))
            if main is not None:
                o = offset(date(year, *c), main)
                offs[("main", c)].append(o)
                cells.append(f"{o:+d}" if o else "0")
            else:
                cells.append("–")
        main_text = "–"
        if main is not None:
            mid = main - timedelta(days=3)
            main_doy.append(mid.timetuple().tm_yday)
            main_dd.append(float(jan1[k(mid)]))
            main_text = f"{jan1[k(mid)]:.0f}"
            start = k(main - timedelta(days=6)) - 1
            later = [(d, c) for d, c in weeks if d >= main]
            dd = np.array([jan1[k(d - timedelta(days=3))] - jan1[start] for d, _ in later])
            w = np.array([c for _, c in later], dtype=float)
            after.append((dd, w / w.sum()))
        lines.append(
            f"| {year} | {site} | {total} | {sig:%b %-d} | {main:%b %-d} | {main_text} | {' | '.join(cells)} | {oct15:.0f} |"
            if sig and main
            else f"| {year} | {site} | {total} | {sig:%b %-d} | – | – | {' | '.join(cells)} | {oct15:.0f} |"
            if sig
            else f"| {year} | {site} | {total} | – | – | – | {' | '.join(cells)} | {oct15:.0f} |"
        )
    lines += [
        "",
        "## Summary: fixed dates against the observed weeks",
        "",
        "| Against | Date | n | Inside the week | Within a week | Median, days | Mean absolute, days |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for (what, c), v in sorted(offs.items()):
        a = np.array(v)
        lines.append(
            f"| {what} | {date(2001, *c):%B %-d} | {len(a)} | {np.sum(a == 0)} | {np.sum(np.abs(a) <= 7)} | {np.median(a):+.0f} | {np.mean(np.abs(a)):.1f} |"
        )
    doy, dd = np.array(main_doy), np.array(main_dd)
    lines += [
        "",
        "## Date or degree days",
        "",
        f"The main flight's week (its middle), {len(doy)} site-years: day of year median {np.median(doy):.0f} ({date(2001, 1, 1) + timedelta(days=int(np.median(doy)) - 1):%B %-d}), SD {doy.std(ddof=1):.1f} days; degree days from January 1 median {np.median(dd):.0f}, SD {dd.std(ddof=1):.0f}, which at late August's ~15 degree days a day is {dd.std(ddof=1) / 15:.1f} days. A date places it no worse than degree days.",
        "",
        "## The flight after the main flight's week",
        "",
    ]
    grid = np.arange(0, 1201, 1.0)
    cdfs = []
    for d, w in after:
        order = np.argsort(d)
        cdfs.append(np.interp(grid, d[order], np.cumsum(w[order]), left=0.0, right=1.0))
    pooled = np.mean(cdfs, axis=0)
    pct = {p: float(np.interp(p / 100, pooled, grid)) for p in (5, 10, 25, 50, 75, 90, 95)}
    lines.append(
        f"Degree days (55/92 °F) from the first day of the main flight's week to each later week's middle, each site-year's catch from then on counting alike ({len(after)} site-years): "
        + ", ".join(f"{p} % at {v:.0f}" for p, v in pct.items())
        + ". Traps come down in mid to late September, so the tail is cut short."
    )
    a = np.array(to_oct15)
    lines += [
        "",
        f"Degree days from {date(2001, *default):%B %-d} to October 15 at these sites: median {np.median(a):.0f}, range {a.min():.0f}–{a.max():.0f} ({len(a)} site-years).",
    ]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-30:]))
    print("median main week", statistics.median(main_doy))


if __name__ == "__main__":
    main()
