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
from typing import Literal

import numpy as np

from agmodels.accumulate import rolling_mean, rolling_sum, running_total
from agmodels.names import CumulativeName, UnitSymbol

DegreeDayMethod = Literal["sine", "average", "modified"]
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


@dataclass(frozen=True, kw_only=True)
class Accumulation:
    """An ingredient accumulated from the biofix (NaN before it), as `agmodels.accumulate` does: `total` over the
    season, `sum` or `mean` over the last `days` days (not before the biofix; a mean is over the days with values).
    `year_end`: the total stops growing after December 31 of the biofix's year (rye's fall rain)."""

    name: str
    of: str
    how: Literal["total", "sum", "mean"] = "total"
    days: int = 0
    year_end: bool = False

    def __post_init__(self):
        if (self.how == "total") != (self.days == 0):
            raise ValueError(f"{self.name}: a total takes no days, a sum or mean needs them")
        if self.year_end and self.how != "total":
            raise ValueError(f"{self.name}: year_end applies to a total")


CONTEXT = ("day_of_year", "year", "latitude")


def accumulate(
    values: Mapping[str, np.ndarray],
    accumulations: tuple[Accumulation, ...],
    biofix_index: int,
    day_of_year: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Each accumulation over the daily series (time on axis 0) from `biofix_index`."""
    out: dict[str, np.ndarray] = {}
    for a in accumulations:
        v = np.asarray(values[a.of], dtype=float)
        if a.how == "total":
            if a.year_end:
                v = v.copy()
                v[_after_year_end(v.shape[0], biofix_index, day_of_year) :] = 0.0
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
    full |= accumulate(values, accumulations, biofix_index, day_of_year=doy)
    full |= {name: np.asarray(inputs[name], dtype=float) for name in CONTEXT if name in inputs}
    if doy is not None:
        days = np.asarray(doy, dtype=float).reshape(-1)
        full["biofix_day_of_year"] = np.asarray(days[biofix_index] if days.size > biofix_index else np.nan)
    return finish(full, **options)


def _after_year_end(n: int, biofix_index: int, day_of_year: np.ndarray | None) -> int:
    """The index of the first January 1 after the biofix (n if the series doesn't reach one)."""
    if day_of_year is None:
        raise ValueError("a year_end total needs day_of_year in the inputs")
    doy = np.asarray(day_of_year, dtype=float).reshape(-1)
    new_year = np.flatnonzero(np.diff(doy[biofix_index:]) < 0)
    return biofix_index + int(new_year[0]) + 1 if new_year.size else n
