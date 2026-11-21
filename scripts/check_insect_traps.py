"""DATCP's field-crop moth traps, 2020–2026: first catch, flight percentiles and peak by species, site and year (models-plan part H, batch H2).

Reads docs/validation/data/datcp-blacklight-traps/ (its README says where each year's tables come from): DATCP's black
light trap network (`weekly.csv`, 6–13 sites a year, ten moth species) and its western bean cutworm pheromone trap
network (`wbc-pheromone-weekly.csv`, 36–83 sites a year). For each species, site and year it gives the weeks read,
the first week with a catch, the weeks a flight's cumulative catch first reaches 25, 50 and 75 % of its total, and
the peak week, each dated by the week's last day. It runs no AgWeather model; model comparisons come later.

Counts as published are read by each year's convention (README, "Caveats"): a blank is no report in 2020–2023's black
light tables (zeros are printed) but a zero in 2024–2025's; 2026's black light "NA" is a zero except in the weeks
DATCP's survey layer has no reading for; in the pheromone tables a blank or "NA" is no report. A pheromone count
marked * (two weeks) or ** / *** (three weeks) is counted whole in the week it's printed under.

Two flights: species with a spring and a summer flight are split at a fixed date (`FLIGHT_SPLITS`): weeks ending on or
before it belong to the first flight. The dates sit in the trough between the flights in the statewide weekly totals
of 2020–2026 (European corn borer's first flight ends late June, its second starts mid-July). A fixed date is a
simplification: the trough comes earlier in warm years and southern sites, and the univoltine north has one flight
around early July, which this rule cuts in two. Percentiles of a flight are given only when it caught at least
`MIN_FLIGHT` moths.

    uv run python scripts/check_insect_traps.py [--network blacklight|wbc|both] [--site-years] [--species NAME]
"""

import argparse
import csv
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "docs/validation/data/datcp-blacklight-traps"
BLACKLIGHT = DATA / "weekly.csv"
PHEROMONE = DATA / "wbc-pheromone-weekly.csv"

FLIGHT_SPLITS: dict[str, tuple[int, int]] = {
    "European corn borer": (7, 7),
    "black cutworm": (6, 30),
    "true armyworm": (6, 30),
    "variegated cutworm": (7, 7),
}
MIN_FLIGHT = 5
PERCENTS = (25, 50, 75)


@dataclass(kw_only=True)
class Week:
    end: date
    count: int | None  # None: no report
    multiweek: bool = False


@dataclass(kw_only=True)
class SiteYear:
    network: str
    species: str
    site: str
    county: str
    year: int
    weeks: list[Week] = field(default_factory=list)


@dataclass(kw_only=True)
class Flight:
    flight: str  # "all", "first" or "second"
    weeks_read: int
    first_read: date | None
    first_catch: date | None
    caught_in_first_week_read: bool
    total: int
    percent_weeks: dict[int, date | None]
    peak: date | None
    peak_count: int


def blacklight_count(year: int, published: str, note: str) -> int | None:
    """A black light count as published, by the year's convention (None: no report)."""
    if published.isdigit():
        return int(published)
    if published == "NA":
        return None if "not reported" in note else 0
    if published == "":
        return 0 if year in (2024, 2025) else None
    return None  # "-": no report (2020)


def pheromone_count(published: str) -> tuple[int | None, bool]:
    """A pheromone count as published, and whether it covers more than one week."""
    digits = published.rstrip("*")
    if digits.isdigit():
        return int(digits), published.endswith("*")
    return None, False


def read_blacklight(path: Path = BLACKLIGHT) -> list[SiteYear]:
    groups: dict[tuple[str, str, int], SiteYear] = {}
    with path.open() as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            key = (r["species"], r["site"], year)
            if key not in groups:
                groups[key] = SiteYear(
                    network="black light", species=r["species"], site=r["site"], county=r["county"], year=year
                )
            count = blacklight_count(year=year, published=r["count"], note=r["note"])
            groups[key].weeks.append(Week(end=date.fromisoformat(r["week_end"]), count=count))
    return _sorted(groups)


def read_pheromone(path: Path = PHEROMONE) -> list[SiteYear]:
    groups: dict[tuple[str, str, int], SiteYear] = {}
    with path.open() as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            key = ("western bean cutworm", f"{r['site']} ({r['county']})", year)
            if key not in groups:
                groups[key] = SiteYear(
                    network="WBC pheromone",
                    species="western bean cutworm",
                    site=r["site"],
                    county=r["county"],
                    year=year,
                )
            count, multi = pheromone_count(r["count"])
            groups[key].weeks.append(Week(end=date.fromisoformat(r["week_end"]), count=count, multiweek=multi))
    return _sorted(groups)


def _sorted(groups: dict) -> list[SiteYear]:
    out = list(groups.values())
    for sy in out:
        sy.weeks.sort(key=lambda w: w.end)
    return sorted(out, key=lambda s: (s.species, s.year, s.site))


def flights(sy: SiteYear) -> list[Flight]:
    """The site-year's whole season, then each flight where the species has two (FLIGHT_SPLITS)."""
    out = [flight_of(weeks=sy.weeks, name="all")]
    if sy.species in FLIGHT_SPLITS:
        month, day = FLIGHT_SPLITS[sy.species]
        split = date(sy.year, month, day)
        out.append(flight_of(weeks=[w for w in sy.weeks if w.end <= split], name="first"))
        out.append(flight_of(weeks=[w for w in sy.weeks if w.end > split], name="second"))
    return out


def flight_of(weeks: list[Week], name: str) -> Flight:
    read = [w for w in weeks if w.count is not None]
    total = sum(w.count for w in read if w.count)
    caught = [w for w in read if w.count]
    first_catch = caught[0].end if caught else None
    percent_weeks: dict[int, date | None] = dict.fromkeys(PERCENTS)
    peak, peak_count = None, 0
    if total >= MIN_FLIGHT:
        running = 0
        for w in read:
            running += w.count or 0
            for p in PERCENTS:
                if percent_weeks[p] is None and running >= total * p / 100:
                    percent_weeks[p] = w.end
        top = max(read, key=lambda w: w.count or 0)
        peak, peak_count = top.end, top.count or 0
    return Flight(
        flight=name,
        weeks_read=len(read),
        first_read=read[0].end if read else None,
        first_catch=first_catch,
        caught_in_first_week_read=bool(read) and first_catch == read[0].end,
        total=total,
        percent_weeks=percent_weeks,
        peak=peak,
        peak_count=peak_count,
    )


def median_day(days: Sequence[date | None]) -> str:
    """The median of dates in one year, as 'Mon D' (None left out)."""
    known = [d for d in days if d is not None]
    if not known:
        return "–"
    k = statistics.median_low(sorted(d.toordinal() for d in known))
    return f"{date.fromordinal(k):%b %-d}"


def show(d: date | None) -> str:
    return f"{d:%b %-d}" if d else "–"


def print_site_years(site_years: list[SiteYear]) -> None:
    print(
        "| Network | Species | Year | Site | Flight | Weeks read | First catch | 25 % | 50 % | 75 % | Peak (count) | Total |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for sy in site_years:
        for fl in flights(sy):
            first = show(fl.first_catch) + (" (first week read)" if fl.caught_in_first_week_read else "")
            pct = " | ".join(show(fl.percent_weeks[p]) for p in PERCENTS)
            peak = f"{show(fl.peak)} ({fl.peak_count})" if fl.peak else "–"
            print(
                f"| {sy.network} | {sy.species} | {sy.year} | {sy.site} | {fl.flight} | {fl.weeks_read} | {first} | {pct} | {peak} | {fl.total} |"
            )


def print_summary(site_years: list[SiteYear]) -> None:
    """Median dates across site-years, by species, flight and year."""
    print(
        f"Medians across site-years. First catch: site-years with a catch whose first week read had none. Percentiles and peak: site-years whose flight caught {MIN_FLIGHT} or more moths."
    )
    print()
    print(
        "| Network | Species | Flight | Year | Site-years read | With a catch | First catch | 25 % | 50 % | 75 % | Peak | Moths |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    table: dict[tuple[str, str, str, int], list[Flight]] = {}
    for sy in site_years:
        for fl in flights(sy):
            table.setdefault((sy.network, sy.species, fl.flight, sy.year), []).append(fl)
    for (network, species, flight, year), fls in sorted(table.items()):
        read = [f for f in fls if f.weeks_read]
        caught = [f for f in read if f.first_catch]
        firsts = [f.first_catch for f in caught if f.first_catch and not f.caught_in_first_week_read]
        big = [f for f in read if f.total >= MIN_FLIGHT]
        pct = " | ".join(median_day([f.percent_weeks[p] for f in big if f.percent_weeks[p]]) for p in PERCENTS)
        peaks = median_day([f.peak for f in big if f.peak])
        print(
            f"| {network} | {species} | {flight} | {year} | {len(read)} | {len(caught)} | {median_day(firsts)} (n={len(firsts)}) | {pct} | {peaks} | {sum(f.total for f in read)} |"
        )


def main():
    parser = argparse.ArgumentParser(
        description="DATCP's field-crop moth traps: first catch, flight percentiles and peak."
    )
    parser.add_argument("--network", choices=("blacklight", "wbc", "both"), default="both")
    parser.add_argument("--species", help="only this species (as written in the data, e.g. 'European corn borer')")
    parser.add_argument("--site-years", action="store_true", help="print every site-year rather than the summary")
    args = parser.parse_args()
    site_years: list[SiteYear] = []
    if args.network in ("blacklight", "both"):
        site_years += read_blacklight()
    if args.network in ("wbc", "both"):
        site_years += read_pheromone()
    if args.species:
        site_years = [s for s in site_years if s.species.lower() == args.species.lower()]
    print(f"DATCP moth traps: {len(site_years)} species-site-years from {DATA}")
    print()
    if args.site_years:
        print_site_years(site_years)
    else:
        print_summary(site_years)


if __name__ == "__main__":
    main()
