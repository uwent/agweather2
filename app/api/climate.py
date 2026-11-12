"""What the climate endpoints share (`/climate/*`; PLAN.md Phase 6 E, D82, D86): the reference period, the pooling
window and percentiles a request asks for, and each point's years read for it.

Points compute from the period's own years (`agdata.climatology.read_point`: the archive's past-years copies, and
gridMET's derived years before 2016, on the archive's basis, D84), never from the stored normal maps, so any
percentile, degree-day setting, pooling window and area (`radius`, D83) works. A cell's 30 years read in ~0.5 s.
Normals exist only inside the area we cover: there is no gridded record outside it to compute them from.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

import numpy as np
from django.conf import settings
from ninja import Schema
from pydantic import model_validator

from agdata import climatology
from agdata.areas import Area
from agdata.grid import NDFD
from agdata.series import archive_years
from api.errors import ApiError, day_text
from api.params import PointsQuery, fail
from ops.points import AllWater, AreaAsk, in_box

MIN_POOL, MAX_POOL = 1, 61
PERIOD_TEXT = {"last30": "30-year", "last10": "10-year", "last5": "5-year"}


class PeriodQuery(Schema):
    """The reference period (D82)."""

    period: Literal["last30", "last10", "last5"] = "last30"

    def echo(self) -> dict[str, Any]:
        return {"period": self.period}


class ClimateQuery(PeriodQuery):
    """The period, the days pooled around each day (`window`), and the percentiles wanted."""

    window: int = climatology.POOL_DAYS
    percentiles: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "ClimateQuery":
        if not MIN_POOL <= self.window <= MAX_POOL:
            raise fail(
                "out_of_range",
                "window",
                f"A window of {self.window} days can't be used. Give a number of days from {MIN_POOL} to {MAX_POOL}; "
                f"the default is {climatology.POOL_DAYS}.",
            )
        self.percentile_list()
        return self

    def percentile_list(self) -> list[float]:
        return percents(self.percentiles, "percentiles", "percentiles=10,50,90", fail_with=fail)

    def echo(self) -> dict[str, Any]:
        return {"period": self.period, "window": self.window, "percentiles": self.percentile_list()}


def percents(text: str | None, param: str, example: str, fail_with=None) -> list[float]:
    """A list of percentages over 0 and under 100 (`10,50,90`), each once, in the order given; empty for none.
    Raises `fail_with`'s error (a validator's) or an ApiError."""
    if text is None or not text.strip():
        return []
    found: list[float] = []
    for part in (t.strip() for t in text.split(",") if t.strip()):
        try:
            p = float(part)
        except ValueError:
            p = float("nan")
        if not 0 < p < 100:
            message = (
                f"The {param.rstrip('s')} {part!r} can't be used. Give numbers over 0 and under 100, separated by "
                f"commas, such as {example}."
            )
            if fail_with is not None:
                raise fail_with("invalid", param, message)
            raise ApiError("invalid", message, param)
        if p not in found:
            found.append(p)
    return found


def suffix(p: float) -> str:
    """A percentile column's suffix: `p10`, `p2.5`."""
    return f"p{p:g}"


@dataclass(kw_only=True)
class PeriodAsk:
    """A request's period: its years, and the cells each point reads (its own, or its area's)."""

    period: climatology.Period
    pool_days: int | None = None
    sites: list[tuple[float, float]]
    places: list[tuple[tuple[int, int], Area | None]]

    @property
    def years(self) -> tuple[int, ...]:
        return self.period.years

    def cells(self) -> list[tuple[int, int]]:
        return [c for cell, area in self.places for c in (area.cells if area is not None else [cell])]

    def read(self, names: list[str]) -> list[dict[str, np.ndarray]]:
        """Each point's years of `names`, (years, 366) per name (`climatology.read_point`)."""
        return [
            climatology.read_point(settings.DATA_DIR, j, i, list(self.years), names, area=area)
            for (j, i), area in self.places
        ]

    def stamp(self, names: list[str], now) -> str:
        return climatology.stamp(settings.DATA_DIR, self.years, names, self.cells(), now=now)

    def sources(self) -> list[str]:
        archive = set(archive_years(settings.DATA_DIR))
        found = []
        if any(y in archive for y in self.years):
            found.append("agweather")
        if any(y not in archive for y in self.years):
            found.append("gridmet")
        return found

    def summary(self) -> dict[str, Any]:
        p = self.period
        return {
            "period": p.name,
            "first_year": p.asked[0],
            "last_year": p.asked[-1],
            "years": len(p.years),
            "missing_years": list(p.missing),
        } | ({"pool_days": self.pool_days} if self.pool_days is not None else {})


def ask(
    where: PointsQuery, q: PeriodQuery, today: date, area: AreaAsk | None, pool_days: int | None = None
) -> tuple[PeriodAsk, list[str]]:
    """The period for `today`'s year and each point's place in it, with warnings; ApiError for a point outside the
    area we cover."""
    sites = where.locations()
    outside = [k for k, (lat, lng) in enumerate(sites) if not in_box(lat, lng)]
    if outside:
        lat, lng = sites[outside[0]]
        raise ApiError(
            "not_applicable",
            (
                f"({lat}, {lng}) is outside the area we cover. Normals come from our own gridded records, which "
                "exist only inside it."
                if len(sites) == 1
                else f"{len(outside)} of these {len(sites)} locations are outside the area we cover, starting with "
                f"({lat}, {lng}). Normals come from our own gridded records, which exist only inside it. Leave those "
                "locations out."
            ),
            "points" if where.points is not None else "lat",
        )
    period = climatology.period(q.period, today, climatology.available_years(settings.DATA_DIR))
    warnings = []
    if period.missing:
        missing = period.missing
        warnings.append(
            f"The {PERIOD_TEXT[q.period]} period runs from {period.asked[0]} through {period.asked[-1]}, and we "
            f"don't yet have {len(missing)} of its years ({_years_text(missing)}), so the normals come from the "
            f"other {len(period.years)}."
        )
    if not period.years:
        raise ApiError(
            "no_data",
            f"We don't yet have any of the years of the {PERIOD_TEXT[q.period]} period. Try a shorter period, such "
            "as period=last5.",
            "period",
            status=503,
        )
    places = []
    for lat, lng in sites:
        cell = NDFD.cell_of(lat, lng)
        assert cell is not None  # in_box
        try:
            places.append((cell, area.at(lat, lng) if area is not None else None))
        except AllWater:
            raise ApiError(
                "no_data",
                f"Every grid cell within the radius of ({lat}, {lng}) is open water, so land_only leaves none. "
                "Choose a larger radius, or leave out land_only.",
                "land_only",
            ) from None
    return PeriodAsk(period=period, pool_days=pool_days, sites=sites, places=places), warnings


def one_year(first: date, last: date) -> None:
    """Normals run within one calendar year: their running totals start and end in it."""
    if first.year != last.year:
        raise ApiError(
            "invalid",
            f"Normals are given within one calendar year, and {day_text(first)} and {day_text(last)} are in "
            "different years. Choose a start and end in the same year.",
            "end",
        )


def years_counted(found: np.ndarray) -> int:
    """How many of a point's years have any value (years, 366)."""
    return int(np.isfinite(found).any(axis=1).sum()) if found.size else 0


def few_years_warning(counted: int, period: climatology.Period, where: str) -> str | None:
    need = climatology.enough_years(len(period.years))
    if counted >= need:
        return None
    return (
        f"{where.capitalize()} has data for {counted} of the period's {len(period.years)} years, fewer than the "
        f"{need} a normal needs, so its normals are missing. Over the Great Lakes, our 30-year records begin in "
        "2016."
    )


def _years_text(years: tuple[int, ...]) -> str:
    if len(years) > 2 and years == tuple(range(years[0], years[-1] + 1)):
        return f"{years[0]}–{years[-1]}"
    return ", ".join(str(y) for y in years)
