"""Projection past the forecast from the archive's own earlier years (D63; PLAN.md Phase 5 D, P1).

After a series' last day with data, each earlier year's days are spliced on by calendar date, shifted by whole
years, so a model can run on through the season once per past year (a scenario) and show the spread. A season that
crosses New Year carries on into the next year with the same shift. A target Feb 29 that its source year lacks
takes the source's Feb 28; a source Feb 29 that the target year lacks is skipped (only target days are walked).

A scenario counts only on the days its year has: missing source days stay NaN, for the runner's gap estimates
(D45) to bridge or not, and `coverage` counts, per projected day, the years with every variable present. A year
with nothing over the whole span is dropped. Labels are each scenario's source year for the first projected day.

Pure: the caller passes a reader of days (the archive's, through `agdata.series` or the past-years store)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

PROJECTION = "projection"
MAX_DAYS = 366  # a longer span would project a year from days the season itself covers


@dataclass(kw_only=True)
class Scenarios:
    """Projected days `dates`, and for each name an array (days × years) of the source years' values."""

    dates: list[date]
    years: list[int]  # each scenario's source year (of the first projected day), in order
    values: dict[str, np.ndarray] = field(default_factory=dict)
    coverage: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))  # years with every value, per day


def source_day(target: date, years_back: int) -> date:
    """The day `years_back` years before `target`, by calendar date (Feb 29 → Feb 28 in a common year)."""
    try:
        return target.replace(year=target.year - years_back)
    except ValueError:  # Feb 29 in a target leap year
        return date(target.year - years_back, 2, 28)


def projection_start(dates: Sequence[date], kinds: Sequence[str | None]) -> date | None:
    """The day after a series' last day with data (observed, partial or forecast), or None if it has none."""
    for k in range(len(kinds) - 1, -1, -1):
        if kinds[k] is not None:
            return dates[k] + timedelta(days=1)
    return None


def build(
    first: date,
    last: date,
    years: Sequence[int],
    names: list[str],
    read_days: Callable[[date, date, list[str]], dict[str, np.ndarray]],
) -> Scenarios:
    """Scenarios for the target days `first`..`last` from each of `years` (each before `first`'s year, or before
    the year a crossing season's last day falls in): `read_days(first, last, names)` gives a year's source days
    first..last, one array per name."""
    n = (last - first).days + 1
    if n > MAX_DAYS:
        raise ValueError(f"a projection spans up to {MAX_DAYS} days, not {n}")
    if n <= 0:
        return Scenarios(dates=[], years=[])
    targets = [first + timedelta(days=k) for k in range(n)]
    kept_years: list[int] = []
    columns: dict[str, list[np.ndarray]] = {name: [] for name in names}
    for year in years:
        back = first.year - year
        if back < 1 or source_day(last, back) >= first:
            continue  # a source day would overlap the season being projected
        sources = [source_day(t, back) for t in targets]
        found = read_days(sources[0], sources[-1], names)
        index = np.array([(s - sources[0]).days for s in sources])
        picked = {name: np.asarray(found[name], dtype=float)[index] for name in names}
        if not any(np.isfinite(v).any() for v in picked.values()):
            continue  # nothing from this year over the span
        kept_years.append(year)
        for name in names:
            columns[name].append(picked[name])
    if not kept_years:
        return Scenarios(dates=targets, years=[], coverage=np.zeros(n, dtype=int))
    values = {name: np.stack(columns[name], axis=1) for name in names}
    complete = np.all([np.isfinite(v) for v in values.values()], axis=0) if names else np.ones((n, len(kept_years)))
    return Scenarios(dates=targets, years=kept_years, values=values, coverage=complete.sum(axis=1).astype(int))


def stacked(
    current: dict[str, np.ndarray], kinds: Sequence[str | None], scenarios: Scenarios
) -> tuple[dict[str, np.ndarray], list[str | None]]:
    """This season's days (`current`, one array per name, the series through its last day with data) with each
    scenario's projected days after them: (days × years) arrays, the current days repeated in every column, and the
    days' kinds (`projection` for the projected ones)."""
    n_years = len(scenarios.years)
    out = {}
    for name, values in current.items():
        own = np.repeat(np.asarray(values, dtype=float)[:, None], n_years, axis=1)
        out[name] = np.concatenate([own, scenarios.values[name]], axis=0) if n_years else own
    return out, [*kinds, *([PROJECTION] * len(scenarios.dates))]
