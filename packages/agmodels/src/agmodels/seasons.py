"""Seasons of a once-a-season product (`ModelSpec.seasonal`, PLAN.md Phase 4 H, D68): their names, days, and which
one is current.

A season runs over the spec's `season` (MM-DD to MM-DD, crossing New Year or not) and is named by the year it
starts in, with the year it ends in when that differs: potato volunteer's November 1, 2025 to March 31, 2026 is
"2025-26" (shown "2025–26"). The current season is the newest whose product has appeared (`Seasonal.appears`, the
first such MM-DD on or after its start): potato volunteer's 2025-26 from January 1, 2026, so in November and
December the settled 2024-25 is current, while 2025-26's partial count is there when asked for.
"""

import re
from dataclasses import dataclass
from datetime import date

from agmodels.spec import ModelSpec

NAME = re.compile(r"^(\d{4})(?:-(\d{2}))?$")


@dataclass(frozen=True, kw_only=True)
class Season:
    name: str  # as requests give it: 2025-26, or 2025
    first: date
    last: date
    appears: date  # when its product is first shown

    @property
    def label(self) -> str:
        """As shown: 2025–26 (an en dash)."""
        return self.name.replace("-", "–")


def season_starting(spec: ModelSpec, year: int) -> Season:
    """The season that starts in `year`."""
    if spec.season is None or spec.seasonal is None:
        raise ValueError(f"{spec.name} isn't counted by season.")
    first = _on(spec.season[0], year)
    last = _on(spec.season[1], year)
    if last < first:
        last = _on(spec.season[1], year + 1)
    appears = _on(spec.seasonal.appears, year)
    if appears < first:
        appears = _on(spec.seasonal.appears, year + 1)
    name = str(year) if last.year == year else f"{year}-{last.year % 100:02d}"
    return Season(name=name, first=first, last=last, appears=appears)


def season_named(spec: ModelSpec, name: str) -> Season:
    """The season `name` (2025-26, or 2025 for one within a year); ValueError if it isn't one of the spec's."""
    match = NAME.match(name.strip())
    if match is None:
        raise ValueError(f"Seasons are named by their years, such as {season_starting(spec, 2025).name}, not {name!r}.")
    found = season_starting(spec, int(match.group(1)))
    if found.name != name.strip():
        raise ValueError(f"{spec.name}'s seasons are named by their years, such as {found.name}, not {name!r}.")
    return found


def season_of(spec: ModelSpec, day: date) -> Season | None:
    """The season `day` falls in, or None between seasons."""
    for year in (day.year - 1, day.year):
        found = season_starting(spec, year)
        if found.first <= day <= found.last:
            return found
    return None


def current_season(spec: ModelSpec, today: date) -> Season:
    """The newest season whose product has appeared by `today`."""
    found = season_starting(spec, today.year)
    while found.appears > today:
        found = season_starting(spec, found.first.year - 1)
    return found


def _on(mmdd: str, year: int) -> date:
    month, day = (int(p) for p in mmdd.split("-"))
    return date(year, month, day)
