"""The first or last day within bounds, and the days since the last (D78; PLAN.md Phase 6 C step 4).

`first=above_50` on a daily layer maps each cell's first day in the window at or above 50 (in the request's units),
`last=below_32` the last day at or below 32, `since=below_32` the days from that last day to the window's end. Bounds
are `api.counts`' (`above_X`, `below_X`, `between_X_Y`, inclusive) or a named threshold of the daily minimum's kind:
`frost` (32 °F), `hard_freeze` (28 °F) and `killing_freeze` (24 °F), in °F whatever the request's units.

The window is `start`..`end`. Without `start`, a `below` event looks back to the previous July 1 (a cold season
runs July to June: in May, `first=frost` is last fall's first frost and `last=frost` this spring's last so far) and
any other from January 1, as counts do.

Only measured days count, never estimates (D45). A cell has three states: a day found; none, where the window has
values but none within the bounds (`found` 0); and no data, where it has no values at all (`found` missing). Dates
are days since 1970-01-01 (the `date` unit), which tiles, NetCDF and GeoTIFF carry as numbers and JSON and CSV as
ISO dates.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import numpy as np

from agdata import units as agunits
from api import counts
from api.errors import ApiError

Kind = Literal["first", "last", "since"]
KINDS: tuple[Kind, ...] = ("first", "last", "since")
EPOCH = date(1970, 1, 1)
# Named thresholds (°F, at or below), in the terms growers use (Ben, 2026-11-07)
NAMED_F = {"frost": 32.0, "hard_freeze": 28.0, "killing_freeze": 24.0}
_WORDS = {"frost": "frost", "hard_freeze": "hard freeze", "killing_freeze": "killing freeze"}
EXAMPLES = "above_50, below_32, between_50_86, or frost (32 °F), hard_freeze (28 °F) or killing_freeze (24 °F)"
SEASON_START = (7, 1)  # a `below` event's default start: the previous July 1


@dataclass(frozen=True, kw_only=True)
class Event:
    """`first=`, `last=` or `since=` as asked: what's found, its bounds in the unit they're in (`unit`; °F for a named
    threshold, else None: the unit the values are shown in), and its canonical name for the ETag."""

    kind: Kind
    low: float | None
    high: float | None
    named: str | None  # frost, hard_freeze, killing_freeze
    name: str  # `below_32`, `frost`

    @property
    def unit(self) -> str | None:
        return "degF" if self.named is not None else None

    @property
    def below(self) -> bool:
        return self.low is None

    def bounds(self, shown: str, stored: str, step: float) -> tuple[float | None, float | None]:
        """The bounds in the stored unit (`api.counts.stored_bounds`), from the request's unit or the name's °F."""
        return counts.stored_bounds(self.low, self.high, self.unit or shown, stored, step)

    def default_start(self, end: date) -> date:
        """The window's first day without `start`: the previous July 1 for a `below` event, else January 1."""
        if not self.below:
            return date(end.year, 1, 1)
        month, day = SEASON_START
        year = end.year if (end.month, end.day) >= SEASON_START else end.year - 1
        return date(year, month, day)

    def words(self, shown: str) -> str:
        """`first frost (32 °F)`, `first day at or above 50 °F`, `days since the last hard freeze (28 °F)`, with a
        named threshold in the request's units (`shown`: its temperature unit)."""
        if self.named is not None:
            assert self.high is not None
            value = float(agunits.convert(self.high, "degF", shown))
            what = f"{_WORDS[self.named]} ({value:.1f}".removesuffix(".0") + f" {agunits.unit(shown).label})"
        else:
            what = f"day {counts.bounds_words(self.low, self.high, shown)}"
        return f"days since the last {what}" if self.kind == "since" else f"{self.kind} {what}"

    @property
    def unit_out(self) -> str:
        """The unit of the map's values: a date, or a count of days."""
        return "day" if self.kind == "since" else "date"


def parse(kind: Kind, text: str) -> Event:
    """`first=above_50`, `last=frost` → an Event; ApiError naming the forms otherwise."""
    given = text.strip().lower()
    if given in NAMED_F:
        return Event(kind=kind, low=None, high=NAMED_F[given], named=given, name=given)
    if re.match(r"^(days|hours)_", given):
        raise ApiError(
            "invalid",
            f"{kind} finds a day, so it takes the bounds alone: {kind}={given.split('_', 1)[1]}, not {kind}={text}.",
            kind,
        )
    low, high = counts.parse_bounds(given, text, kind, EXAMPLES)
    return Event(kind=kind, low=low, high=high, named=None, name=given.replace(".", "p"))


def asked(first: str | None, last: str | None, since: str | None) -> Event | None:
    """The one event a request asks for, if any; ApiError for more than one."""
    given: list[tuple[Kind, str]] = [
        (kind, text) for kind, text in zip(KINDS, (first, last, since), strict=True) if text is not None
    ]
    if len(given) > 1:
        names = " and ".join(kind for kind, _ in given)
        raise ApiError("conflict", f"A map finds one kind of day. Give {names} in separate requests.", given[1][0])
    return parse(kind=given[0][0], text=given[0][1]) if given else None


def find(values: np.ndarray, low: float | None, high: float | None, kind: str, first_day: date):
    """(value, found, missing days) per cell from days (n, …) starting on `first_day`: the first or last day within
    the bounds as days since 1970-01-01, or the days since the last; `found` 1 where a day was found, 0 where the
    window has values but none within the bounds (none), NaN where it has no values (no data). Value is NaN unless
    found."""
    values = np.asarray(values)
    n = values.shape[0]
    known = np.isfinite(values)
    hit = known.copy()
    with np.errstate(invalid="ignore"):
        if low is not None:
            hit &= values >= low
        if high is not None:
            hit &= values <= high
    any_hit = hit.any(axis=0)
    index = np.argmax(hit, axis=0) if kind == "first" else n - 1 - np.argmax(hit[::-1], axis=0)
    start = (first_day - EPOCH).days
    value = (n - 1 - index) if kind == "since" else (start + index)
    value = np.where(any_hit, value.astype(np.float64), np.nan)
    has_data = known.any(axis=0)
    found = np.where(has_data, any_hit.astype(np.float64), np.nan)
    return value, found, (~known).sum(axis=0)


def to_date(days: float) -> date:
    """Days since 1970-01-01 → the date."""
    return EPOCH + timedelta(days=int(days))
