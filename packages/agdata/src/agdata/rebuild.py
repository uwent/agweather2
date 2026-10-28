"""Recomputing derived data written by an older version of its code (D29).

A derived variable is stale when the store records another version than the catalog's (its code changed), or
when the catalog added it after the store was written. Daily variables are rolled up again from the hourly store
over each year's days with data, and the year's running totals rebuilt; running totals are rebuilt from the
daily store. Stale hourly variables (RH, ET0) are only reported: they're derived at ingest, so a refetch or a
re-derivation step would be needed.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import rebuild_year, update_days
from agdata.grid import Window
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore, StoreLayout

KINDS: list[tuple[StoreLayout, dict]] = [
    (HOURLY, VARIABLES),
    (DAILY, DAILY_VARIABLES),
    (CUMULATIVE, CUMULATIVE_VARIABLES),
]


@dataclass
class StaleReport:
    stale: dict[str, list[str]] = field(default_factory=dict)  # "daily/2025" → variable names


def find_stale(data_dir: Path) -> StaleReport:
    """Every store's stale derived variables, read-only (for the health check)."""
    report = StaleReport()
    for layout, variables in KINDS:
        for year in _years(data_dir, layout):
            stale = GridStore.stale_variables(data_dir, layout, year, variables.values())
            if stale:
                report.stale[f"{layout.kind}/{year}"] = sorted(stale)
    return report


def rebuild_stale(data_dir: Path, window: Window, log=print) -> StaleReport:
    """Recomputes stale daily and cumulative variables; returns what's still stale (hourly ones)."""
    for year in _years(data_dir, DAILY):
        store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
        if not store.stale:
            continue
        days = _days_with_data(store)
        if days is not None:
            log(f"daily/{year}: rolling up {days[0]} to {days[1]} for {', '.join(sorted(store.stale))}")
            update_days(data_dir, window, *days)
        store.mark_current(list(store.stale))
    for year in _years(data_dir, CUMULATIVE):
        store = GridStore.open(data_dir, CUMULATIVE, year, CUMULATIVE_VARIABLES.values(), add_missing=True)
        if store.stale:
            log(f"cumulative/{year}: rebuilding for {', '.join(sorted(store.stale))}")
            rebuild_year(data_dir, window, year)
            store.mark_current(list(store.stale))
    return find_stale(data_dir)


def _years(data_dir: Path, layout: StoreLayout) -> list[int]:
    folder = Path(data_dir) / layout.kind
    return sorted(int(p.stem) for p in folder.glob("*.zarr")) if folder.exists() else []


def _days_with_data(store: GridStore) -> tuple[date, date] | None:
    written = np.flatnonzero(store.read_meta("air_temperature_min.source") > 0)
    if written.size == 0:
        return None
    first = date(store.year, 1, 1)
    return first + timedelta(days=int(written[0])), first + timedelta(days=int(written[-1]))
