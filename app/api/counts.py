"""Counts of days or hours within bounds (D75; PLAN.md Phase 6 C step 2): `count=days_above_86` on a map,
`count=air_temperature_max:days_above_86` at points.

A count names its time axis (`days_` on daily values, `hours_` on hourly ones, so the request reads like the column it
gives and a mismatch is refused) and its bounds: `above_X`, `below_X` or `between_X_Y`, both inclusive (≥, ≤), in the
units the values are shown in (the request's `units`, or a unit given for the variable). A decimal is `93.2` or
`93p2`, a negative `-2.2`. Missing steps are counted beside the count, never assumed (D45).

Stored values sit on their precision's grid (0.1 °C), and a bound converted from °F rarely does (86 °F is
30.000000000000004 °C; a float32 30.0 is 30.0), so each bound is widened by a quarter of the stored step: a value
on the bound counts, and no value a step away does.
"""

import re
from dataclasses import dataclass
from typing import Literal

import numpy as np

from agdata import units as agunits
from api.errors import ApiError

_NUMBER = r"(-?\d+(?:[.p]\d+)?)"
_ONE = re.compile(rf"^(above|below)_{_NUMBER}$")
_BETWEEN = re.compile(rf"^between_{_NUMBER}_{_NUMBER}$")
EXAMPLES = "days_above_86, days_below_32 or days_between_50_86 (hours_above_86 for hourly values)"

Axis = Literal["days", "hours"]


@dataclass(frozen=True, kw_only=True)
class Count:
    """A count as asked: its axis and bounds in the unit the values are shown in (None: open)."""

    axis: Axis
    low: float | None
    high: float | None
    name: str  # canonical, for a column and the ETag: `days_above_93p2`

    def bounds(self, shown: str, stored: str, step: float) -> tuple[float | None, float | None]:
        """The bounds in the stored unit, each widened by a quarter of the stored step (inclusive with float noise)."""
        return stored_bounds(self.low, self.high, shown, stored, step)

    def words(self, shown: str) -> str:
        """`days at or above 86 °F`, `hours between 50 and 86 °F`, in the unit the values are shown in."""
        return f"{self.axis} {bounds_words(self.low, self.high, shown)}"


def stored_bounds(
    low: float | None, high: float | None, shown: str, stored: str, step: float
) -> tuple[float | None, float | None]:
    """Bounds given in `shown` → the stored unit, each widened by a quarter of the stored step."""
    slack = step / 4
    low_stored = None if low is None else float(agunits.convert(low, shown, stored)) - slack
    high_stored = None if high is None else float(agunits.convert(high, shown, stored)) + slack
    return low_stored, high_stored


def bounds_words(low: float | None, high: float | None, shown: str) -> str:
    """`at or above 86 °F`, `between 50 and 86 °F`, `at or below 32 °F`, in the unit `shown`."""
    label = agunits.unit(shown).label
    unit = label if label == "%" else f" {label}" if label else ""
    if low is not None and high is not None:
        return f"between {_number(low)} and {_number(high)}{unit}"
    if low is not None:
        return f"at or above {_number(low)}{unit}"
    assert high is not None
    return f"at or below {_number(high)}{unit}"


def parse(text: str, param: str = "count") -> Count:
    """`days_above_86` → a Count; ApiError naming the forms otherwise."""
    given = text.strip().lower()
    m = re.match(r"^(days|hours)_(.*)$", given)
    if m is None:
        raise ApiError(
            "invalid",
            f"We can't read {param}={text}. Give a count as {EXAMPLES}; a decimal as 93.2 or 93p2.",
            param,
        )
    axis = m.group(1)
    low, high = parse_bounds(m.group(2), text, param, EXAMPLES, prefix=f"{axis}_")
    name = given.replace(".", "p")
    return Count(axis=axis, low=low, high=high, name=name)  # type: ignore[arg-type]


def parse_bounds(
    given: str, text: str, param: str, examples: str, prefix: str = ""
) -> tuple[float | None, float | None]:
    """`above_86`, `below_32` or `between_50_86` (lowercase, without an axis) → (low, high), None where open; `text`
    is what was sent and `examples` the forms to offer, for the messages."""
    if m := _ONE.match(given):
        value = _value(m.group(2))
        return (value, None) if m.group(1) == "above" else (None, value)
    if m := _BETWEEN.match(given):
        low, high = _value(m.group(1)), _value(m.group(2))
        if low > high:
            raise ApiError(
                "out_of_order",
                f"In {param}={text}, the lower bound ({_number(low)}) is above the upper one ({_number(high)}). "
                f"Give the lower bound first, such as {prefix}between_{_number(high)}_{_number(low)}.",
                param,
            )
        return low, high
    raise ApiError(
        "invalid",
        f"We can't read {param}={text}. Give it as {examples}; a decimal as 93.2 or 93p2.",
        param,
    )


def check_axis(found: Count, time_axis: str, what: str, param: str = "count", prefix: str = "") -> None:
    """A daily value takes `days_`, an hourly one `hours_` (`prefix`: what goes before it, `air_temperature:`)."""
    wanted = "hours" if time_axis == "hour" else "days"
    if found.axis != wanted:
        example = found.name.replace(found.axis, wanted, 1)
        raise ApiError(
            "invalid",
            f"{what} has a value for each {time_axis}, so it counts {wanted}, not {found.axis}. "
            f"Give {param}={prefix}{example}.",
            param,
        )


def count_within(values: np.ndarray, low: float | None, high: float | None) -> tuple[np.ndarray, np.ndarray]:
    """(steps within [low, high], steps missing) along axis 0; the count is NaN where no step has a value."""
    values = np.asarray(values)
    known = np.isfinite(values)
    hit = known.copy()
    with np.errstate(invalid="ignore"):
        if low is not None:
            hit &= values >= low
        if high is not None:
            hit &= values <= high
    count = np.where(known.any(axis=0), hit.sum(axis=0).astype(np.float64), np.nan)
    return count, (~known).sum(axis=0)


def _value(text: str) -> float:
    return float(text.replace("p", "."))


def _number(value: float) -> str:
    return f"{value:g}"
