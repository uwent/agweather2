"""Rolling windows at points (D81, `agdata.rolling`): the columns `roll=` adds beside a daily series' own, shared by
`/weather/daily` and `/degree-days`.

A request reads the days its windows reach beyond its range (`RollQuery.lead`) and rolls each point's whole read,
so its first row has a whole window. The series' ends are its first and last days with any data: windows reaching
past them are clipped (`roll_partial`) or have no value. `meta.summary.roll` says, per point and window, the dates
whose windows were clipped and the first date whose window holds a forecast day.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np

from agdata.rolling import Roll, Stat, any_in_window, label, roll
from agdata.series import FORECAST, PARTIAL
from api import points
from api.errors import ApiError
from api.params import RollQuery

ADDS_UP_TEXT = "precipitation, evapotranspiration, sunlight, hour counts and degree days"


def read_start(sites: list[tuple[float, float]], first: date, before: int) -> date:
    """The first day to read for windows reaching `before` days back: not into a year the archive lacks where the
    range itself is in it (a read before the archive goes to Open-Meteo whole; those windows are clipped instead)."""
    early = first - timedelta(days=before)
    if early.year == first.year:
        return early
    if any(
        points.from_archive(lat, lng, first, first) and not points.from_archive(lat, lng, early, early)
        for lat, lng in sites
    ):
        return date(first.year, 1, 1)
    return early


def stat_for(q: RollQuery, adds_up: bool) -> Stat:
    """`roll_stat`, or by default a sum for values that add up over days and a mean for the rest."""
    if q.roll_stat is not None:
        return q.roll_stat
    return "sum" if adds_up else "mean"


def check_stat(q: RollQuery, adds_up: dict[str, bool]) -> None:
    """`roll_stat=sum` only on values that add up (a sum of temperatures converts wrongly between units, and means
    nothing)."""
    if q.roll_stat != "sum":
        return
    others = [name for name, adds in adds_up.items() if not adds]
    if others:
        raise ApiError(
            "invalid",
            f"roll_stat=sum adds values up over days, which works only for values that add up ({ADDS_UP_TEXT}), "
            f"not {', '.join(others)}. Use roll_stat=mean, min or max for those, or ask for them separately.",
            "roll_stat",
        )


@dataclass(kw_only=True)
class Roller:
    """The rolled columns of one request, gathered point by point in the order the rows are."""

    q: RollQuery
    gaps: str = "estimate"
    columns: dict[str, list] = field(default_factory=dict)
    stats: dict[str, Stat] = field(default_factory=dict)  # per rolled column
    of: dict[str, str] = field(default_factory=dict)  # each rolled column's own
    days: dict[str, int] = field(default_factory=dict)  # each rolled column's window
    notes: list[dict[str, Any]] = field(default_factory=list)
    short: dict[str, int] = field(default_factory=dict)  # per window: values missing for too few days with data

    @property
    def specs(self) -> list[Roll]:
        return self.q.specs()

    def add(
        self,
        *,
        point: int | None,
        name: str,
        values: np.ndarray,
        kinds: list[str | None],
        dates: list[date],
        shown: slice,
        adds_up: bool,
        variable: str | None = None,
        note: bool = True,
    ) -> None:
        """Roll `values` (one per day read, `kinds` and `dates` alike) by each window and keep the `shown` rows as
        `<name>_<N>d`. `variable` is the catalog's (its gap method decides whether a sum bridges gaps); `note` adds
        the point's clipped and forecast dates to the summary (once per point, not per column)."""
        exists = [k for k, kind in enumerate(kinds) if kind is not None]
        extent = (exists[0], exists[-1] + 1) if exists else (0, 0)
        forecast = np.array([kind in (FORECAST, PARTIAL) for kind in kinds], dtype=bool)
        stat = stat_for(self.q, adds_up)
        for spec in self.specs:
            column = f"{name}_{label(spec.days)}"
            found = roll(
                np.asarray(values, dtype=float),
                spec,
                stat,
                name=variable,
                gaps="missing" if self.gaps == "missing" else "estimate",
                extent=extent,
            )
            self.columns.setdefault(column, []).extend(found.values[shown].tolist())
            self.stats[column], self.of[column], self.days[column] = stat, name, spec.days
            inside = np.zeros(len(kinds), dtype=bool)
            inside[extent[0] : extent[1]] = True
            usable = inside & (spec.partial | (found.held == spec.days))
            short = usable & ~np.isfinite(found.values) & (found.known > 0)
            self.short[label(spec.days)] = self.short.get(label(spec.days), 0) + int(short[shown].sum())
            if note:
                shown_dates = dates[shown]
                clipped = [d.isoformat() for d, c in zip(shown_dates, found.clipped[shown], strict=True) if c]
                touched = any_in_window(forecast, spec)[shown]
                first_forecast = next((d for d, t in zip(shown_dates, touched, strict=True) if t), None)
                entry: dict[str, Any] = {"window": label(spec.days)}
                if point is not None:
                    entry = {"point": point, **entry}
                self.notes.append(
                    entry
                    | {
                        "forecast_from": first_forecast.isoformat() if first_forecast else None,
                        "clipped": clipped,
                    }
                )

    def summary(self) -> dict[str, Any]:
        """`meta.summary.roll`: each rolled column's statistic and window, and the notes per point and window."""
        return {
            "columns": {
                column: {"of": self.of[column], "stat": self.stats[column], "days": self.days[column]}
                for column in self.columns
            },
            "align": self.q.roll_align,
            "windows": self.notes,
        }

    def warnings(self) -> list[str]:
        found = []
        for window, n in self.short.items():
            if n:
                days = int(window[:-1])
                found.append(
                    f"{n} {days}-day {'value is' if n == 1 else 'values are'} missing because fewer than "
                    f"{self.q.roll_coverage:g}% of the window's days had data. Lower roll_coverage to accept "
                    "windows with more missing days."
                )
        return found
