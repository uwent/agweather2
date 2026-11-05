"""Ingredients: what a model's outputs are finished from, so a map can combine them per cell (D47, D66).

A model with ingredients is three steps, and its `outputs()` is just their composition (`finished`), so a point and
a map run the same code:

1. `ingredients(inputs) -> dict`: daily series that need neither the biofix nor the options (a day's severity
   value, degree days, 30-day moving means, the insects' freeze factor). The grid keeps them (`agdata`, Phase 5 F).
2. Accumulations (`SPEC.accumulations`): an ingredient summed or averaged from the biofix, over the whole season or
   the last N days. At a point they're computed from the daily series here; on the grid from running totals since
   January 1 (`cum[d] − cum[b − 1]`), which is why they're declared rather than coded.
3. `finish(values, **options) -> dict`: the outputs, from each day's ingredients, accumulations and context alone.
   It must be elementwise in time (a day's outputs depend on that day's values only), so a map can finish one day
   without the others; `test_ingredients` checks every model for it.

Context passed to `finish` beside them: the runner's `day_of_year`, `year` and `latitude` where the spec asks for
them, and `biofix_day_of_year` (the biofix's day of year, NaN where there's none).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy as np

from agmodels.accumulate import rolling_mean, rolling_sum, running_total
from agmodels.names import CumulativeName, UnitSymbol

DegreeDayMethod = Literal["sine", "average", "modified"]
# The most days before its own any ingredient's value reads (30-day moving means and the day before), so the grid
# reads that many days of weather before the first day it recomputes; a running minimum reaches further, and is
# continued from the stored day before instead (`test_ingredients` checks every model against both)
LOOKBACK_DAYS = 31
Finish = Callable[..., dict[str, np.ndarray]]


@dataclass(frozen=True, kw_only=True)
class DegreeDays:
    """A degree-day setting (°F), for an ingredient the grid's shared running totals already hold."""

    method: DegreeDayMethod
    base_f: float
    upper_f: float | None = None


@dataclass(frozen=True, kw_only=True)
class Ingredient:
    """A daily series `ingredients()` returns."""

    name: str
    unit: UnitSymbol
    description: str = ""
    # The grid reads this ingredient's running total from the shared degree-day totals for this setting
    # (`agdata.cumulative`) rather than keeping one per model
    degree_days: DegreeDays | None = None
    # Or the grid's running total of this catalog variable (rye's fall rain from `precipitation`)
    cumulative: CumulativeName | None = None
    # Kept once under this name for every model that declares it (the insects' freeze factor)
    shared: str = ""
    # The days after its own a day's value reads (cotton's rain over the planting day and the two after: 2), so
    # the grid recomputes that many days before the first day whose weather changed
    ahead_days: int = 0
    # Held at its lowest since January 1 (the insects' freeze factor): the grid continues it from the day before
    # rather than recomputing the year
    running_minimum: bool = False
    # Of the code computing a shared ingredient: bump when its values change, so stores rebuild it (D29); an
    # unshared one takes its model's version
    version: int = 1


@dataclass(frozen=True, kw_only=True)
class Accumulation:
    """An ingredient accumulated from the biofix (NaN before it), as `agmodels.accumulate` does: `total` over the
    season, `sum` or `mean` over the last `days` days (not before the biofix; a mean is over the days with values).
    `until` (MM-DD): the total stops growing after the first such day from the biofix (rye's fall rain at December
    31, potato volunteer's winter at March 31); it needs `day_of_year` in the inputs, and `year` but for 12-31."""

    name: str
    of: str
    how: Literal["total", "sum", "mean"] = "total"
    days: int = 0
    until: str | None = None

    def __post_init__(self):
        if (self.how == "total") != (self.days == 0):
            raise ValueError(f"{self.name}: a total takes no days, a sum or mean needs them")
        if self.until is not None and self.how != "total":
            raise ValueError(f"{self.name}: until applies to a total")


CONTEXT = ("day_of_year", "year", "latitude")


def accumulate(
    values: Mapping[str, np.ndarray],
    accumulations: tuple[Accumulation, ...],
    biofix_index: int,
    day_of_year: np.ndarray | None = None,
    year: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Each accumulation over the daily series (time on axis 0) from `biofix_index`."""
    out: dict[str, np.ndarray] = {}
    for a in accumulations:
        v = np.asarray(values[a.of], dtype=float)
        if a.how == "total":
            if a.until is not None:
                v = v.copy()
                v[_after_until(a.until, v.shape[0], biofix_index, day_of_year, year) :] = 0.0
            out[a.name] = running_total(v, biofix_index)
        elif a.how == "sum":
            out[a.name] = rolling_sum(v, a.days, biofix_index)
        else:
            out[a.name] = rolling_mean(v, a.days, biofix_index)
    return out


def with_accumulations(
    outputs: Mapping[str, np.ndarray], accumulations: tuple[Accumulation, ...], biofix_index: int = 0
) -> dict[str, np.ndarray]:
    """`outputs` with any accumulation it lacks computed from its daily ingredient, for a `risk()` given only the
    daily values (a legacy tool's, a test's); those present are used as they are (a map's, from running totals)."""
    missing = tuple(a for a in accumulations if a.name not in outputs)
    return dict(outputs) | (accumulate(outputs, missing, biofix_index) if missing else {})


def finished(
    *,
    accumulations: tuple[Accumulation, ...],
    values: Mapping[str, np.ndarray],
    inputs: Mapping[str, np.ndarray],
    biofix_index: int,
    finish: Finish,
    options: Mapping[str, str],
) -> dict[str, np.ndarray]:
    """A model's outputs from its ingredients: accumulated from the biofix, with the context, then finished."""
    doy = inputs.get("day_of_year")
    full = dict(values)
    full |= accumulate(values, accumulations, biofix_index, day_of_year=doy, year=inputs.get("year"))
    full |= {name: np.asarray(inputs[name], dtype=float) for name in CONTEXT if name in inputs}
    if doy is not None:
        days = np.asarray(doy, dtype=float).reshape(-1)
        full["biofix_day_of_year"] = np.asarray(days[biofix_index] if days.size > biofix_index else np.nan)
    return finish(full, **options)


def until_day(until: str, biofix: date) -> date:
    """The first day on or after `biofix` that is `until` (MM-DD): where an `until` total stops growing."""
    month, day = (int(p) for p in until.split("-"))
    found = date(biofix.year, month, day)
    return found if found >= biofix else date(biofix.year + 1, month, day)


def _after_until(until: str, n: int, biofix_index: int, day_of_year: np.ndarray | None, year: np.ndarray | None) -> int:
    """The index of the first day after `until_day` from the biofix (n if the series doesn't reach it). December 31
    is where `day_of_year` wraps; any other day needs `year` too (March 31 is day 90 or 91)."""
    if day_of_year is None:
        raise ValueError("an until total needs day_of_year in the inputs")
    doy = np.asarray(day_of_year, dtype=float).reshape(-1)
    if until == "12-31" and year is None:
        new_year = np.flatnonzero(np.diff(doy[biofix_index:]) < 0)
        return biofix_index + int(new_year[0]) + 1 if new_year.size else n
    if year is None:
        raise ValueError(f"an until total to {until} needs year in the inputs")
    years = np.broadcast_to(np.asarray(year, dtype=float).reshape(-1), doy.shape)
    if biofix_index >= doy.size:
        return n
    ordinals = np.array([date(int(y), 1, 1).toordinal() + int(d) - 1 for y, d in zip(years, doy, strict=True)])
    stop = until_day(until, date.fromordinal(int(ordinals[biofix_index]))).toordinal()
    return int(np.searchsorted(ordinals, stop, side="right"))
