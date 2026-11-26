"""The alfalfa cutting plan at a point (F5; Phase 7 track 5): `GET /models/alfalfa-growth/plan`, `agmodels.alfalfa_plan`
on the year's weather (observed, then the forecast) and the period's normal after it.

The normal's part (each day's mean GDD 41/86 °F, and the killing freezes' dates in each of the period's years) is the
same for every plan at a cell and period, and a cell's 30 years take ~0.5 s to read, so it's kept in this process
(`_climate_parts`, keyed by the cell, the period's years and their data stamp) while a grower edits a plan."""

import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from agdata import climatology
from agdata.series import FORECAST, PARTIAL, archive_years
from agmodels import alfalfa_plan as planner
from agmodels.degree_days import degree_days_sine
from agmodels.models import alfalfa_growth
from api import climate, clock, points
from api.envelope import Column, Result, etag_for, not_modified, respond
from api.errors import ApiError, day_text, quoted
from api.params import OutputQuery, PointsQuery, SeriesQuery
from api.routes.degree_days import temperatures_of
from api.routes.weather import envelope_parts, located, read_days
from api.schemas import TableResponse, responses
from ops.points import in_box

router = Router(tags=["Models"])

TEMPERATURES = ["air_temperature_min", "air_temperature_max"]
KILL_C = (planner.KILL_F - 32) / 1.8
MAX_CUTS = 12
NORMAL = "normal"


@dataclass(frozen=True, kw_only=True)
class ClimateParts:
    """A cell's normal over a period, on the 366 calendar slots: each slot's mean daily GDD, and the killing freezes."""

    normal_gdd: np.ndarray  # (366,): the mean of each year's own daily GDD
    freezes: climatology.Freezes  # at 24 °F
    years_with_data: int


_CACHE_SIZE = 64
_cache: OrderedDict[tuple, ClimateParts] = OrderedDict()
_cache_lock = threading.Lock()


def _climate_parts(asked: climate.PeriodAsk, stamp: str) -> ClimateParts:
    (cell, area) = asked.places[0]
    key = (str(settings.DATA_DIR), cell, None if area is None else tuple(area.cells), asked.years, stamp)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    found = asked.read(TEMPERATURES)[0]
    tmin, tmax = found["air_temperature_min"], found["air_temperature_max"]
    days = np.full(tmin.shape, np.nan)
    for y, year in enumerate(asked.years):
        lo_f, hi_f = climatology.degree_day_temperatures(tmin[y], tmax[y], year)
        usable = np.isfinite(lo_f) & np.isfinite(hi_f)
        found_gdd = degree_days_sine(
            np.where(usable, lo_f, 0.0), np.where(usable, hi_f, 0.0), alfalfa_growth.BASE_F, alfalfa_growth.UPPER_F
        )
        days[y] = np.where(usable, found_gdd, np.nan)
    running = climatology.running(days, asked.years)
    normal = np.diff(running.mean, prepend=0.0)  # each slot's mean daily GDD (NaN where too few years count)
    parts = ClimateParts(
        normal_gdd=normal,
        freezes=climatology.freezes(tmin, KILL_C),
        years_with_data=climate.years_counted(tmin),
    )
    with _cache_lock:
        _cache[key] = parts
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return parts


@router.get("/models/alfalfa-growth/plan", response=responses(TableResponse), summary="An alfalfa cutting plan")
def plan(
    request: HttpRequest,
    where: Query[PointsQuery],
    q: Query[climate.PeriodQuery],
    output: Query[OutputQuery],
    year: int | None = None,
    interval: float | None = None,
    count: int | None = None,
    held: str | None = None,
    cuts: str | None = None,
) -> HttpResponse:
    """A season of alfalfa cuttings at one point in `year` (default this one): one row per day (`date`, `kind`:
    observed, forecast or normal; `gdd`, the day's GDD 41/86 °F; `gdd_since_cut`, the sawtooth; `kill_chance`, the
    chance in percent of a killing freeze, 24 °F, still to come in spring or come by the date in fall; `cut`), and
    the plan in `meta.summary.plan`: the season's start and end, each cut with its GDD and days since the last and
    where it falls against the 900–1100 window, and the fall rule over the period's years. `cuts=` checks dates as
    given; otherwise `held=` dates stay and the rest are scheduled by `interval=` (800–1200, default 1000) or
    `count=`. Inside the area we cover only (the normal is ours)."""
    _one_point(where)
    now = clock.now()
    today = now.date()
    the_year = _year(year, today)
    first, last = date(the_year, 1, 1), date(the_year, 12, 31)
    if interval is not None and count is not None:
        raise ApiError("conflict", "Give either 'interval' or 'count' to schedule cuts by, not both.", "count")
    if cuts is not None and (interval is not None or count is not None):
        raise ApiError(
            "conflict",
            "'cuts' checks the dates you give as they are, so it takes no 'interval' or 'count'. Leave out 'cuts' to schedule, or leave out 'interval' and 'count' to check your dates.",
            "cuts",
        )
    interval_f = None if interval is None else interval * 1.8 if output.units == "metric" else interval
    if interval_f is not None and not planner.INTERVAL_MIN - 0.5 <= interval_f <= planner.INTERVAL_MAX + 0.5:
        unit = "°C·d" if output.units == "metric" else "GDD"
        low, high, default = (_gdd(v, output.units) for v in planner.INTERVALS)
        raise ApiError(
            "out_of_range",
            f"An interval of {interval:g} {unit} can't be used. Give one from {low} to {high} {unit} (base 41 °F); the default is {default}.",
            "interval",
        )
    if count is not None and not planner.COUNT_MIN <= count <= planner.COUNT_MAX:
        raise ApiError(
            "out_of_range",
            f"A plan of {count} cuts can't be made. Give a number of cuts from {planner.COUNT_MIN} to {planner.COUNT_MAX}.",
            "count",
        )
    held_days = _dates(held, "held", the_year)
    cut_days = _dates(cuts, "cuts", the_year) if cuts is not None else None
    if cut_days is not None and not cut_days:
        raise ApiError("invalid", "Give at least one date in 'cuts', or leave it out to schedule cuts.", "cuts")
    if cut_days is not None and (stray := [d for d in held_days if d not in cut_days]):
        raise ApiError(
            "invalid",
            f"A held cut must be one of the cuts given: {day_text(stray[0])} is in 'held' but not in 'cuts'.",
            "held",
        )

    asked, warnings = climate.ask(where, q, today, area=None)
    options = SeriesQuery()
    computed: dict[str, Any] = {**where.echo(), "year": the_year, **q.echo(), "units": output.units}
    computed |= {
        "interval": None
        if cut_days is not None or count is not None
        else (interval or _gdd(planner.INTERVAL_DEFAULT, output.units)),
        "count": count,
        "held": held_days,
        "cuts": cut_days,
    }
    climate_stamp = asked.stamp(TEMPERATURES, now)
    weather_stamp = points.stamp(where.locations(), first, last, now, names=TEMPERATURES)
    etag = None if weather_stamp is None else etag_for(request, computed, f"{weather_stamp}|{climate_stamp}")
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    parts = _climate_parts(asked, climate_stamp)
    if not np.isfinite(parts.normal_gdd).any():
        raise ApiError(
            "no_data",
            f"We don't have enough of the {climate.PERIOD_TEXT[q.period]} period's years at this location to plan a season. Over the Great Lakes, our records begin in 2016; try 'period=last5'.",
            "period",
        )
    locations = located(where, first, last, options)
    found, read_warnings, sources, corrections = read_days(
        where, first, last, TEMPERATURES, options, trim_end=True, now=now
    )
    warnings += read_warnings
    days, kept = found[0]
    n = (last - first).days + 1
    tmin = np.full(n, np.nan)
    tmax = np.full(n, np.nan)
    tmin[:kept] = np.asarray(days.values["air_temperature_min"][:kept], dtype=float)
    tmax[:kept] = np.asarray(days.values["air_temperature_max"][:kept], dtype=float)
    lo_f, hi_f, estimated, usable = temperatures_of(tmin, tmax, options.gaps)
    gdd = np.where(
        usable,
        degree_days_sine(
            np.where(usable, lo_f, 0.0), np.where(usable, hi_f, 0.0), alfalfa_growth.BASE_F, alfalfa_growth.UPPER_F
        ),
        np.nan,
    )
    killed = np.where(np.isfinite(tmin), (tmin <= KILL_C).astype(float), np.nan)
    slots = np.array([climatology.slot(first + timedelta(days=k)) for k in range(n)])
    the_climate = _plan_climate(parts, slots, the_year)
    result = planner.plan(
        gdd=gdd,
        killed=killed,
        climate=the_climate,
        july_1=(date(the_year, 7, 1) - first).days,
        cuts=[(d - first).days for d in cut_days] if cut_days is not None else None,
        held=[(d - first).days for d in held_days],
        interval=interval_f,
        count=count,
    )
    kinds = [NORMAL if result.from_normal[k] else (days.kinds[k] if k < kept else NORMAL) or NORMAL for k in range(n)]
    fz = parts.freezes
    spring_end = climatology.SPRING[1]
    chance = np.where(slots < spring_end, fz.after_spring[slots], fz.by_fall[slots]) * 100
    dates = [first + timedelta(days=k) for k in range(n)]
    cut_set = {c.day for c in result.cuts}
    columns = [
        Column(name="date", values=dates),
        Column(name="kind", values=kinds),
        Column(name="gdd", values=result.gdd.tolist(), unit="degF_day", step=0.1),
        Column(name="gdd_since_cut", values=result.since_cut.tolist(), unit="degF_day", step=1),
        Column(name="kill_chance", values=chance.tolist(), unit="percent", step=1, summarize=False),
        Column(name="cut", values=[k in cut_set for k in range(n)]),
    ]
    estimated_days = int(np.sum(estimated[:kept])) if kept else 0
    gaps = int(np.sum(result.from_normal[:kept])) if kept else 0
    if gaps:
        warnings.append(
            f"{gaps} days of this year's weather are missing in gaps too long to estimate, so the plan uses the normal's degree days for them."
        )
    note = climate.few_years_warning(parts.years_with_data, asked.period, "this location")
    if note is not None:
        warnings.append(note)
    summary = {
        **asked.summary(),
        "plan": _plan_summary(result, first, output.units),
        "days_observed": sum(1 for k in kinds if k not in (NORMAL, FORECAST, PARTIAL)),
        "days_forecast": sum(1 for k in kinds if k in (FORECAST, PARTIAL)),
        "days_normal": sum(1 for k in kinds if k == NORMAL),
        "days_estimated": estimated_days,
        "corrections": corrections,
    }
    return respond(
        request,
        Result(
            request=computed,
            columns=columns,
            **envelope_parts(where, locations),
            summary=summary,
            sources=[*sources, *(s for s in asked.sources() if s not in sources)],
            warnings=warnings,
            filename=f"agweather-alfalfa-plan-{the_year}",
            etag=etag,
        ),
    )


def _one_point(where: PointsQuery) -> None:
    if where.points is not None:
        raise ApiError(
            "too_many",
            "A cutting plan is made for one location. Give 'lat' and 'lng', or make one request per location.",
            "points",
        )
    lat, lng = where.locations()[0]
    if not in_box(lat, lng):
        raise ApiError(
            "not_applicable",
            f"({lat}, {lng}) is outside the area we cover. A cutting plan reads the normal from our own gridded records, which exist only inside it.",
            "lat",
        )


def _year(year: int | None, today: date) -> int:
    if year is None:
        return today.year
    years = archive_years(settings.DATA_DIR)
    first = min(years) if years else today.year
    if not first <= year <= today.year:
        raise ApiError(
            "out_of_range",
            f"We can plan a season from {first} through {today.year}, not {year}. Choose a year in that range.",
            "year",
        )
    return year


def _dates(raw: str | None, param: str, year: int) -> list[date]:
    """Dates as YYYY-MM-DD separated by commas, in `year`, each once, in order."""
    if raw is None or not raw.strip():
        return []
    found: set[date] = set()
    for part in (p.strip() for p in raw.split(",") if p.strip()):
        try:
            day = date.fromisoformat(part)
        except ValueError:
            raise ApiError(
                "invalid",
                f"We can't read {quoted(part)} in {quoted(param)}. Give dates as YYYY-MM-DD separated by commas, such as {quoted(f'{param}={year}-06-01,{year}-07-10')}.",
                param,
            ) from None
        if day.year != year:
            raise ApiError(
                "invalid",
                f"{day_text(day)} in {quoted(param)} isn't in {year}, the year of the plan. Give dates in {year}, or choose that year with 'year'.",
                param,
            )
        found.add(day)
    if len(found) > MAX_CUTS:
        raise ApiError(
            "too_many", f"A plan can hold up to {MAX_CUTS} cuts, and {quoted(param)} has {len(found)}.", param
        )
    return sorted(found)


def _plan_climate(parts: ClimateParts, slots: np.ndarray, year: int) -> planner.Climate:
    """The period's normal and freezes as days of the plan's year."""
    fz = parts.freezes
    spring_typical, _ = fz.dates(planner.TYPICAL_SHARE)
    _, fall_end = fz.dates(planner.FALL_END_SHARE)
    _, fall_typical = fz.dates(planner.TYPICAL_SHARE)
    real = climatology.days_of(year)
    index = np.cumsum(real) - 1  # each slot's day in the year (February 29's is March 1's in a common year)

    def day(slot_value: float, spring: bool) -> int | None:
        if not np.isfinite(slot_value):
            return None
        s = round(float(slot_value))
        if s < 0 or s >= climatology.SLOTS:
            return None
        if not real[s]:  # February 29 in a common year: the 28th in spring, March 1 in fall
            return int(index[s]) if spring else int(index[s]) + 1
        return int(index[s])

    fall_freezes: list[int | None] = []
    for value in fz.fall:
        if not np.isfinite(value):
            continue  # a year left out for missing days
        fall_freezes.append(None if value == climatology.NONE_FALL else day(float(value), spring=False))
    return planner.Climate(
        normal_gdd=parts.normal_gdd[slots],
        spring_typical=day(float(spring_typical), spring=True),
        fall_end=day(float(fall_end), spring=False),
        fall_typical=day(float(fall_typical), spring=False),
        fall_freezes=tuple(fall_freezes),
    )


def _gdd(value: float | None, units: str) -> float | None:
    """GDD in the request's units (°C·d with `units=metric`), to a whole degree day."""
    if value is None:
        return None
    return round(value / 1.8 if units == "metric" else value)


def _plan_summary(p: planner.Plan, first: date, units: str) -> dict[str, Any]:
    def on(day: int | None) -> str | None:
        return None if day is None else (first + timedelta(days=day)).isoformat()

    kill = planner.KILL_F if units == "us" else round(KILL_C, 1)
    f = p.fall
    return {
        "spring_freeze": {"date": on(p.start - 1) if p.start > 0 else None, "basis": p.start_basis},
        "season_end": {"date": on(p.end), "basis": p.end_basis},
        "interval": _gdd(p.interval, units),
        "count": p.count,
        "cuts": [
            {
                "date": on(c.day),
                "held": c.held,
                "gdd": _gdd(c.gdd, units),
                "days": c.days,
                "status": c.status,
                "projected": c.projected,
            }
            for c in p.cuts
        ],
        "fall": {
            "last_cut": on(f.last_cut),
            "years": f.years,
            "under": f.under,
            "over": f.over,
            "between": f.between,
            "before_cut": f.before_cut,
            "typical_freeze": on(f.typical),
            "typical_regrowth": _gdd(f.typical_regrowth, units),
            "observed_freeze": on(f.observed),
            "observed_regrowth": _gdd(f.observed_regrowth, units),
        },
        "thresholds": {
            "cut_from": _gdd(alfalfa_growth.CUT_FROM, units),
            "cut_until": _gdd(alfalfa_growth.CUT_UNTIL, units),
            "fall_under": _gdd(planner.FALL_UNDER, units),
            "fall_over": _gdd(planner.FALL_OVER, units),
            "killing_freeze": kill,
        },
    }
