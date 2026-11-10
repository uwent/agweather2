"""Recomputing derived data written by an older version of its code (D29).

A derived variable is stale when the store records another version than the catalog's (its code changed), or when
the catalog added it after the store was written. A daily store written on each cell's local days is stale throughout
until it's rolled up again on grid days (D74).

Stale daily variables are rolled up again from the hourly store over each year's days with data: only they, reading
only the hours they need, and only what reads them follows (`cumulative.steps_for`: the timecopy, the running totals,
the models' ingredients), so a new feature leaves the rest as it was. Stale running totals are rebuilt from the daily
store, chill portions a season at a time from the hours, and the models' ingredients from January 1. The corrected
shortwave and ET0 are re-derived from the stored raw HRRR (`agdata.shortwave`), and the daily variables read from
them roll up again; other stale hourly variables are only reported: they're derived at ingest, so a refetch would be
needed.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata import chillseason, modelmaps, shortwave
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import rebuild_year, steps_for, update_days
from agdata.daily import hourly_read_for, move_to_grid_days, on_grid_days, year_on_grid_days
from agdata.grid import Window
from agdata.modelmaps import INGREDIENTS
from agdata.point import hourly_sources
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore, StoreLayout

KINDS: list[tuple[StoreLayout, dict]] = [
    (HOURLY, VARIABLES),
    (DAILY, DAILY_VARIABLES),
    (CUMULATIVE, CUMULATIVE_VARIABLES),
]


@dataclass(kw_only=True)
class StaleReport:
    stale: dict[str, list[str]] = field(default_factory=dict)  # "daily/2025" → variable names


def find_stale(data_dir: Path) -> StaleReport:
    """Every store's stale derived variables, read-only (for the health check)."""
    report = StaleReport()
    for layout, variables in KINDS:
        for year in _years(data_dir, layout):
            stale = GridStore.stale_variables(data_dir, layout, year, variables.values())
            if layout == DAILY and not year_on_grid_days(data_dir, year):
                stale = {"(local days, D74)"}
            if stale:
                report.stale[f"{layout.kind}/{year}"] = sorted(stale)
    for year in _years(data_dir, DAILY):  # the models' ingredients (D66): a year not built counts too
        if INGREDIENTS.path(data_dir, year).exists():
            stale = GridStore.stale_variables(data_dir, INGREDIENTS, year, modelmaps.variables())
            if stale:
                report.stale[f"ingredients/{year}"] = sorted(stale)
        elif modelmaps.status(data_dir, year) == "not built":
            report.stale[f"ingredients/{year}"] = ["(not built)"]
    return report


def plan(report: StaleReport) -> list[str]:
    """What `rebuild_stale` would do for the stale variables `report` lists, in words for `rebuild --check`: each
    year's daily roll-up (its variables, the hours they read, what follows), and what goes out of date after it."""
    lines: list[str] = []
    daily_years: list[int] = []
    rolled: set[str] = set()
    for store, names in report.stale.items():
        kind, year = store.split("/")
        if kind == "daily":
            daily_years.append(int(year))
            wanted = None if names == ["(local days, D74)"] else names
            rolled |= set(DAILY_VARIABLES if wanted is None else wanted)
            steps = steps_for(wanted)
            follows = [
                *(["the timecopy"] if steps.timecopy else []),
                *(["the running totals"] if steps.totals else []),
                *(["chill portions"] if steps.chill else []),
                *(
                    ["every ingredient"]
                    if steps.ingredients is None
                    else [f"{len(steps.ingredients)} ingredients"]
                    if steps.ingredients
                    else []
                ),
            ]
            what = (
                "every daily variable" if wanted is None else f"{len(wanted)} daily variable" + "s" * (len(wanted) > 1)
            )
            lines.append(
                f"daily/{year}: roll up {what} from {len(hourly_read_for(wanted))} hourly ones"
                + (f", then {', '.join(follows)}" if follows else ", and nothing else follows")
            )
        elif kind == "cumulative":
            chill = sorted(set(names) & set(chillseason.NAMES))
            totals = sorted(set(names) - set(chill))
            parts = [*(["the running totals"] if totals else []), *(["chill portions' seasons"] if chill else [])]
            lines.append(f"cumulative/{year}: rebuild {' and '.join(parts)}")
        elif kind == "ingredients":
            lines.append(f"ingredients/{year}: build again from January 1")
        else:
            lines.append(f"{store}: still stale after a rebuild (derived at ingest; needs a refetch)")
    if daily_years:
        years = ", ".join(str(y) for y in sorted(daily_years))
        lines.append(f"Afterwards out of date: the past-years copies ({years}; `pastyears`, ~75 s a year)")
        lines.append(f"and the downloads of {len(rolled)} daily variables in those years (`downloads`)")
    return lines


def rebuild_stale(data_dir: Path, window: Window, log=print) -> StaleReport:
    """Recomputes stale variables: the corrected hourly shortwave and ET0 (D48), then daily and cumulative ones
    (the days of a year whose shortwave changed included); returns what's still stale (other hourly ones)."""
    corrected = set(shortwave.correct_archive(data_dir, window, log=log))
    for year in _years(data_dir, DAILY):
        store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
        moved = not on_grid_days(store)
        if moved:
            log(f"daily/{year}: moving to grid days (CST, D74)")
            move_to_grid_days(store)
        names = daily_to_roll_up(store.stale, corrected=year in corrected, moved=moved)
        if names is not None and not names:
            continue
        days = _days_with_data(store)
        if days is not None:
            what = "every daily variable" if names is None else ", ".join(names)
            log(f"daily/{year}: rolling up {days[0]} to {days[1]} for {what}")
            update_days(data_dir, window, *days, names=names)
        store.mark_current(list(store.stale))
    chill_stale: dict[int, GridStore] = {}
    for year in _years(data_dir, CUMULATIVE):
        store = GridStore.open(data_dir, CUMULATIVE, year, CUMULATIVE_VARIABLES.values(), add_missing=True)
        totals = store.stale - set(chillseason.NAMES)
        if totals:
            log(f"cumulative/{year}: rebuilding for {', '.join(sorted(totals))}")
            rebuild_year(data_dir, window, year)
            store.mark_current(list(totals))
        if store.stale & set(chillseason.NAMES):
            chill_stale[year] = store
    if chill_stale:  # from hours, a season at a time (`agdata.chillseason`)
        log(f"chill portions: recomputing the seasons in {', '.join(str(y) for y in chill_stale)}")
        chillseason.rebuild(data_dir, window, list(chill_stale))
        for store in chill_stale.values():
            store.mark_current(list(chillseason.NAMES))
    for year in _years(data_dir, DAILY):
        reason = modelmaps.status(data_dir, year)
        if reason is not None:
            log(f"ingredients/{year}: building ({reason})")
            modelmaps.build(data_dir, window, year)
    return find_stale(data_dir)


# The hourly variables HRRR's correction rewrites (D48): the daily ones read from them roll up again
CORRECTED_HOURLY = frozenset({"shortwave_radiation", "et0"})


def daily_to_roll_up(stale: Iterable[str], corrected: bool = False, moved: bool = False) -> list[str] | None:
    """The daily variables a year's rebuild rolls up again: its stale ones, and with `corrected` those read from the
    corrected shortwave and ET0; None (every one) for a store just moved to grid days, whose every day changed."""
    if moved:
        return None
    names = set(stale)
    if corrected:
        sources = hourly_sources()  # each daily variable's hourly inputs, probed from the code
        names |= {name for name in DAILY_VARIABLES if CORRECTED_HOURLY & set(sources.get(name, CORRECTED_HOURLY))}
    return [name for name in DAILY_VARIABLES if name in names]


def _years(data_dir: Path, layout: StoreLayout) -> list[int]:
    folder = Path(data_dir) / layout.kind
    return sorted(int(p.stem) for p in folder.glob("*.zarr")) if folder.exists() else []


def _days_with_data(store: GridStore) -> tuple[date, date] | None:
    written = np.flatnonzero(store.read_meta("air_temperature_min.source") > 0)
    if written.size == 0:
        return None
    first = date(store.year, 1, 1)
    return first + timedelta(days=int(written[0])), first + timedelta(days=int(written[-1]))
