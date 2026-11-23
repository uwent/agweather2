"""Black and variegated cutworm against DATCP's moth traps on the archive (models plan part H, batch H2).

1. Black cutworm's default biofix. DATCP's black cutworm pheromone network (docs/validation/data/datcp-blacklight-traps/
   bcw-pheromone-weekly.csv, 2021–2023 and 2026, 30–102 sites a year, read weekly from late March or April to early
   June) times DATCP's "significant capture". The weekly tables can't show a two-night count, so the first week with
   9 or more moths (`SIGNIFICANT`, DATCP's two-night threshold) stands in for it: the earliest week a significant
   capture could have happened. For each site-year whose first week read had fewer, the week's middle day (its end
   less 3 days) is dated by day of year and by single-sine degree days 50/86 °F from January 1 on the archive at the
   site's cell. A fixed date and a fixed degree-day total are compared as defaults: each one's error in days against
   the observed week, over all site-years (in sample: the default is their median).
2. Variegated cutworm's flights. DATCP's black light network (weekly.csv, 2020–2026) counts variegated cutworm moths
   weekly; each moth is dated by single-sine degree days 45 °F without an upper threshold from January 1 (Simonet et
   al. 1981's method) at its week's middle day, and the moths of each flight (split at July 7, as
   scripts/check_insect_traps.py does) give the flight's percentiles in degree days, against the model's curves.
   Few moths are caught (11–72 a year), so these are rough.

    uv run python scripts/check_cutworms.py [--out docs/validation/models/black-cutworm/traps.md]

Its summaries are in docs/validation/models/black-cutworm.md and variegated-cutworm.md.
"""

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from check_insect_traps import read_blacklight

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_sine
from agmodels.insects.variegated_cutworm import INSECT as VCW
from agmodels.phenology import evaluate

DATA = Path("docs/validation/data/datcp-blacklight-traps")
SIGNIFICANT = 9
SPLIT = (7, 7)


class Archive:
    """Daily degree days from January 1 at a cell, by year, from the archive's daily min and max."""

    def __init__(self, data: Path):
        self.data = data
        self.stores: dict[int, GridStore] = {}
        self.cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def temps(self, year: int, cell: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
        key = (year, cell)
        if key not in self.cache:
            if year not in self.stores:
                variables = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
                self.stores[year] = GridStore.open(self.data, DAILY, year, variables)
            store = self.stores[year]
            lo, hi = (store.read_point(n, *cell) * 1.8 + 32 for n in ("air_temperature_min", "air_temperature_max"))
            self.cache[key] = (lo, hi)
        return self.cache[key]

    def total(self, year: int, cell: tuple[int, int], base: float, upper: float | None) -> np.ndarray:
        lo, hi = self.temps(year=year, cell=cell)
        good = np.isfinite(lo) & np.isfinite(hi)
        dd = degree_days_sine(np.where(good, lo, 0.0), np.where(good, hi, 0.0), base=base, upper=upper)
        return np.cumsum(np.where(good, dd, 0.0))


def mid(week_end: date) -> int:
    """The week's middle day, as an index from January 1."""
    return (week_end - timedelta(days=3) - date(week_end.year, 1, 1)).days


def sites(path: Path) -> dict[tuple[str, str], tuple[float, float]]:
    with path.open() as f:
        return {(r["county"], r["site"]): (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)}


def black_cutworm(archive: Archive, lines: list[str]) -> None:
    where = sites(DATA / "bcw-pheromone-sites.csv")
    weeks: dict[tuple[int, str, str], list[tuple[date, int | None]]] = defaultdict(list)
    with (DATA / "bcw-pheromone-weekly.csv").open() as f:
        for r in csv.DictReader(f):
            count = int(r["count"]) if r["count"].isdigit() else None
            weeks[(int(r["year"]), r["county"], r["site"])].append((date.fromisoformat(r["week_end"]), count))
    lines += [
        "## 1. Black cutworm: the first week with 9 or more moths in DATCP's pheromone traps",
        "",
        f"Each site-year's first week with {SIGNIFICANT} or more moths, dated by its middle day; degree days single sine 50/86 °F from January 1 on the archive at the site's cell. Left out: site-years that never reached {SIGNIFICANT}, or reached it in their first week read.",
        "",
        "| Year | County | Site | First week ≥ 9 (its last day) | Moths | Day of year | DD50/86 from January 1 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    found: list[tuple[int, int, float, tuple[int, int]]] = []  # (year, day index, DD, cell)
    skipped = {"never": 0, "first week": 0}
    for (year, county, site), ws in sorted(weeks.items()):
        ws = sorted((d, c) for d, c in ws if c is not None)
        if not ws or d_index(ws, SIGNIFICANT) is None:
            skipped["never"] += 1
            continue
        k = d_index(ws, SIGNIFICANT)
        assert k is not None
        if k == 0:
            skipped["first week"] += 1
            continue
        end, count = ws[k]
        cell = NDFD.cell_of(*where[(county, site)])
        assert cell is not None
        day = mid(end)
        dd = float(archive.total(year=year, cell=cell, base=50, upper=86)[day])
        found.append((year, day, dd, cell))
        lines.append(f"| {year} | {county} | {site} | {end:%b %-d} | {count} | {day + 1} | {dd:.0f} |")
    days = np.array([f[1] for f in found], dtype=float)
    dds = np.array([f[2] for f in found])
    by_year = defaultdict(list)
    for year, day, dd, _ in found:
        by_year[year].append((day, dd))
    lines += ["", "### Summary", ""]
    lines.append(
        f"- Site-years with a week of {SIGNIFICANT} or more: {len(found)}; never reached: {skipped['never']}; reached in the first week read (left out): {skipped['first week']}."
    )
    lines.append(
        f"- Day of year: median {np.median(days) + 1:.0f} ({date(2025, 1, 1) + timedelta(days=int(np.median(days))):%B %-d} in a common year), 10th–90th percentile {np.percentile(days, 10) + 1:.0f}–{np.percentile(days, 90) + 1:.0f}, SD {days.std(ddof=1):.1f} days."
    )
    lines.append(
        f"- DD50/86 from January 1: median {np.median(dds):.0f}, 10th–90th percentile {np.percentile(dds, 10):.0f}–{np.percentile(dds, 90):.0f}, SD {dds.std(ddof=1):.0f}."
    )
    for year, rows in sorted(by_year.items()):
        d = [r[0] for r in rows]
        lines.append(
            f"- {year}: n = {len(rows)}, median day {statistics.median(d) + 1:.0f} ({date(year, 1, 1) + timedelta(days=int(statistics.median(d))):%b %-d}), median DD {statistics.median(r[1] for r in rows):.0f}."
        )
    # Each default's error in days: a fixed date (the median day) and a fixed total (the median DD) at each site-year
    median_day = round(float(np.median(days)))
    median_dd = float(np.median(dds))
    by_date = days - median_day
    by_dd = []
    for year, day, _, cell in found:
        total = archive.total(year=year, cell=cell, base=50, upper=86)
        by_dd.append(int(np.argmax(total >= median_dd)) - day)
    by_dd = np.array(by_dd, dtype=float)
    lines += [
        "",
        "| Default | Median error, days | Mean absolute error, days | Within 7 days | 10th–90th percentile |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, err in (
        (f"A fixed date, day {median_day + 1}", by_date),
        (f"A fixed total, {median_dd:.0f} DD50/86 from January 1", by_dd),
    ):
        lines.append(
            f"| {name} | {np.median(err):+.0f} | {np.mean(np.abs(err)):.1f} | {np.sum(np.abs(err) <= 7)} of {len(err)} | {np.percentile(err, 10):+.0f} to {np.percentile(err, 90):+.0f} |"
        )
    lines.append("")


def d_index(ws: Sequence[tuple[date, int | None]], threshold: int) -> int | None:
    for k, (_, c) in enumerate(ws):
        if c is not None and c >= threshold:
            return k
    return None


def variegated_cutworm(archive: Archive, lines: list[str]) -> None:
    by_site = {}
    with (DATA / "sites.csv").open() as f:
        for r in csv.DictReader(f):
            if r["network"] == "black light":
                by_site[r["site"]] = (float(r["lat"]), float(r["lon"]))
    moths: dict[str, list[tuple[float, int]]] = {"first": [], "second": []}
    per_year: dict[tuple[int, str], list[tuple[float, int]]] = defaultdict(list)
    for sy in read_blacklight():
        if sy.species != "variegated cutworm":
            continue
        loc = by_site.get(sy.site)
        if loc is None:
            raise KeyError(f"no location for the black light site {sy.site!r}")
        cell = NDFD.cell_of(*loc)
        assert cell is not None
        total = archive.total(year=sy.year, cell=cell, base=45, upper=None)
        for w in sy.weeks:
            if not w.count:
                continue
            flight = "first" if w.end <= date(sy.year, *SPLIT) else "second"
            dd = float(total[mid(w.end)])
            moths[flight].append((dd, w.count))
            per_year[(sy.year, flight)].append((dd, w.count))
    x = np.arange(0.0, 4001.0)
    curves = evaluate(insect=VCW, dd_total=x)
    done = curves["generations_adult_flight"]
    lines += [
        "## 2. Variegated cutworm: moths in DATCP's black light traps by degree days",
        "",
        "Each moth dated by single-sine degree days 45 °F without an upper threshold from January 1 at its week's middle day, on the archive at the trap's cell; flights split at July 7. The model's flight percentiles are read off its curves.",
        "",
        "| Flight | Moths | Site-weeks with moths | 10 % | 25 % | 50 % | 75 % | 90 % | Model's 10 / 50 / 90 % |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for g, flight in enumerate(("first", "second")):
        rows = moths[flight]
        dd = np.repeat([r[0] for r in rows], [r[1] for r in rows])
        pct = [np.percentile(dd, p) for p in (10, 25, 50, 75, 90)]
        model = [float(np.interp(g + p, done, x)) for p in (0.1, 0.5, 0.9)]
        lines.append(
            f"| {flight} | {len(dd)} | {len(rows)} | "
            + " | ".join(f"{v:,.0f}" for v in pct)
            + f" | {' / '.join(f'{v:,.0f}' for v in model)} |"
        )
    lines += ["", "By year (moths, median degree days):", ""]
    for (year, flight), rows in sorted(per_year.items()):
        dd = np.repeat([r[0] for r in rows], [r[1] for r in rows])
        lines.append(f"- {year}, {flight} flight: {len(dd)} moths, median {np.median(dd):,.0f}")
    lines.append("")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/black-cutworm/traps.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    archive = Archive(Path(args.data))
    lines = [
        "# Black and variegated cutworm against DATCP's moth traps",
        "",
        "Written by `scripts/check_cutworms.py` from DATCP's trap tables (`docs/validation/data/datcp-blacklight-traps/`) and the archive's daily temperatures.",
        "",
    ]
    black_cutworm(archive=archive, lines=lines)
    variegated_cutworm(archive=archive, lines=lines)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines))
    print("\n".join(line for line in lines if not line.startswith("| 20")))


if __name__ == "__main__":
    main()
