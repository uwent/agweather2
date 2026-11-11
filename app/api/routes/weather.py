"""Weather at points (docs/api.md, "Weather at points"; PLAN.md Phase 5 C): daily and hourly series, and totals
over a window. Several points come back as one long table with a `point` column indexing `meta.locations`.

Raw values show missing where they're missing (D45). Totals bridge gaps by each variable's method (`agdata.catalog`
GAP_FILL: interpolated up to 7 days), counting estimated and missing days; precipitation is never estimated: its
total sums the known days and counts the rest as missing (no rain)."""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

import numpy as np
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router, Schema

from agdata.catalog import DAILY_VARIABLES, GAP_FILL, VARIABLES
from agdata.computed import DAILY_COMPUTED, HOURLY_COMPUTED, adds_up
from agdata.series import FORECAST, PARTIAL
from agmodels.gaps import MAX_GAP_DAYS, fill_short_gaps
from api import clock, counts, events, points, rolled
from api.envelope import (
    SYSTEMS,
    Column,
    Result,
    catalog_column,
    etag_for,
    not_modified,
    respond,
    shown_unit,
    unit_overrides,
)
from api.errors import ApiError, counted
from api.locations import describe, describe_days
from api.params import (
    AreaQuery,
    DaysQuery,
    HoursQuery,
    OutputQuery,
    PointsQuery,
    RollQuery,
    SeriesQuery,
    check_vars,
)
from api.schemas import TableResponse, responses
from ops.points import AreaAsk, day_zone

router = Router(tags=["Weather"])

FORECAST_DAYS = 16  # a default end this far ahead reaches past every forecast; trailing empty days are dropped
MAX_DAYS = 3660  # per point and request: ten years of days
MAX_HOURS = 2 * 8784  # two years of hours
MAX_ROWS = 100_000  # points × steps
HOUR = timedelta(hours=1)
RADIUS_FROM = "2016"  # the archive's first year, for messages
MAX_OUTSIDE = 10  # points outside the box (or before the archive) per request: each may fetch from Open-Meteo
DAILY = {name: v for name, v in DAILY_VARIABLES.items() if name != "et0_sum_estimate"}  # that one's for totals
DAILY |= {name: c.variable for name, c in DAILY_COMPUTED.items()}  # computed when read (`agdata.computed`)
HOURLY = {**VARIABLES, **{name: c.variable for name, c in HOURLY_COMPUTED.items()}}
DAILY_DEFAULT = ["air_temperature_min", "air_temperature_max", "precipitation_sum"]
HOURLY_DEFAULT = ["air_temperature", "dew_point", "relative_humidity", "precipitation", "wind_speed"]
TOTALLED = {name: v for name, v in DAILY.items() if adds_up(name)}  # a computed one's inputs' gaps filled (D75)
TOTALS_DEFAULT = ["precipitation_sum", "et0_sum", "shortwave_radiation_sum"]


def located(
    where: PointsQuery, first: date, last: date, options: SeriesQuery | None = None, area: AreaAsk | None = None
) -> list[dict]:
    """`meta.location(s)` for the points, refusing more outside the archive than MAX_OUTSIDE, and any with `area`
    (`radius`); for days (`options` given), whose clock sets them (`day_basis`, `days`); with `area`, the cells
    averaged (`meta.location.area`)."""
    found = [
        describe(lat, lng) | ({} if options is None else describe_days(lat, lng, last.year, options.day_basis))
        for lat, lng in where.locations()
    ]
    outside = sum(not points.from_archive(lat, lng, first, last) for lat, lng in where.locations())
    if area is not None:
        if outside:
            raise ApiError(
                "not_applicable",
                "radius averages our gridded weather around a location, so it works only inside the area we cover "
                f"and from {RADIUS_FROM} on. "
                + (
                    "This location, or the dates asked for, is outside it, so leave out radius."
                    if len(found) == 1
                    else f"{outside} of these {len(found)} locations, or the dates asked for, are outside it, so "
                    "leave out radius, or ask for those locations separately."
                ),
                "radius",
            )
        for location, (lat, lng) in zip(found, where.locations(), strict=True):
            location["area"] = {
                "radius_km": round(area.radius_km, 3),
                "weighting": area.weighting,
                "cells": len(area.at(lat, lng).cells),
            }
    if outside > MAX_OUTSIDE:
        raise ApiError(
            "too_many",
            f"{outside} of these locations are outside our area or before our records begin, so their weather comes "
            f"from Open-Meteo; a request can include up to {MAX_OUTSIDE} such locations. Split them into several "
            "requests.",
            "points",
        )
    return found


def check_size(steps: int, n_points: int, limit: int, unit: str, param: str = "start") -> None:
    if steps > limit:
        raise ApiError(
            "too_large",
            f"This request asks for {steps:,} {unit}; a request can include up to {limit:,}. Choose a shorter period.",
            param,
        )
    if steps * n_points > MAX_ROWS:
        raise ApiError(
            "too_large",
            f"This request would return {steps * n_points:,} rows ({n_points} locations); a request can return up to "
            f"{MAX_ROWS:,}. Ask for fewer locations or a shorter period.",
            "points",
        )


def envelope_parts(where: PointsQuery, locations: list[dict]) -> dict:
    return {"location": locations[0]} if where.points is None else {"locations": locations}


def read_days(
    where: PointsQuery,
    first: date,
    last: date,
    names: list[str],
    options: SeriesQuery,
    trim_end: bool,
    now: datetime,
    area: AreaAsk | None = None,
):
    """Each point's days, trimmed (`points.keep`), with the warnings, sources and corrections they bring."""
    found, warnings, sources, corrections = [], [], [], []
    sites = where.locations()
    zones = [day_zone(lat, lng, options.day_basis) for lat, lng in sites]
    stores = points.shared_stores(names)
    for days in points.many_days(sites, first, last, names, now, zones, stores=stores, area=area):
        n = points.keep(days.kinds, options.forecast, trim_end)
        found.append((days, n))
        sources += [s for s in days.sources if s not in sources]
        corrections += [c for c in days.corrections if c not in corrections]
        if days.forecast.reason == "stale" and options.forecast:
            warnings.append("The forecast is out of date, so the series ends with the last observed day.")
    return found, sorted(set(warnings)), sources, corrections


def day_counts(found) -> dict:
    """Days returned, forecast and missing, over each series' first n rows (or the rows of a slice)."""
    kinds = [k for days, n in found for k in days.kinds[n if isinstance(n, slice) else slice(n)]]
    return {
        "days_returned": len(kinds),
        "days_forecast": sum(k in (FORECAST, PARTIAL) for k in kinds),
        "days_missing": sum(k is None for k in kinds),
    }


@router.get("/weather/daily", response=responses(TableResponse), summary="Daily weather at points")
def daily(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    rolls: Query[RollQuery],
    area: Query[AreaQuery],
    vars: str | None = None,
) -> HttpResponse:
    """One row per point and local day: `date`, `kind` (observed, partial, forecast, or null with no data), and each
    variable in `vars` (daily catalog names; `GET /variables`). Defaults: January 1 through the forecast. `roll=7,14`
    adds each variable's rolling window beside it (`<name>_7d`; D81, `api.rolled`)."""
    names = check_vars(vars, DAILY, DAILY_DEFAULT)
    now = clock.now()
    today = now.date()
    trim_end = when.end is None and when.date is None
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if options.forecast else today)
    check_size((last - first).days + 1, len(where.locations()), MAX_DAYS, "days")
    rolled.check_stat(rolls, {name: adds_up(name) for name in names})
    before, after = rolls.lead()
    read_first = rolled.read_start(where.locations(), first, before) if before else first
    read_last = last + timedelta(days=after)
    computed = {**where.echo(), "start": first, "end": last, "vars": names, "forecast": options.forecast}
    around = area.ask(output.units)
    computed |= {"units": output.units, **options.echo(), **rolls.echo(), **area.echo()}
    etag = answer_etag(request, computed, points.stamp(where.locations(), read_first, read_last, now, names=names))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, read_first, read_last, options, area=around)
    found, warnings, sources, corrections = read_days(
        where, read_first, read_last, names, options, trim_end, now, area=around
    )
    skip, asked = (first - read_first).days, (last - first).days + 1
    shown = [(days, slice(skip, max(skip, min(n, skip + asked)))) for days, n in found]
    roller = rolled.Roller(q=rolls)
    columns: dict[str, list] = {"point": [], "date": [], "kind": [], **{name: [] for name in names}}
    for k, ((days, n), (_, rows)) in enumerate(zip(found, shown, strict=True)):
        columns["point"] += [k] * (rows.stop - rows.start)
        columns["date"] += days.dates[rows]
        columns["kind"] += days.kinds[rows]
        for j, name in enumerate(names):
            columns[name] += list(days.values[name][rows])
            if rolls.specs():
                roller.add(
                    point=k if where.points is not None else None,
                    name=name,
                    values=np.asarray(days.values[name][:n], dtype=float),
                    kinds=days.kinds[:n],
                    dates=days.dates[:n],
                    shown=rows,
                    adds_up=adds_up(name),
                    variable=name,
                    note=j == 0,
                )
    table = [Column(name=name, values=columns[name]) for name in ("point", "date", "kind")]
    if where.points is None:
        table = table[1:]
    for name in names:
        table.append(catalog_column(name, columns[name]))
        for column in (c for c in roller.columns if roller.of[c] == name):
            table.append(replace(catalog_column(column, roller.columns[column], variable=name), summarize=False))
    if found and trim_end:
        computed["end"] = max(
            (days.dates[rows.stop - 1] for days, rows in shown if rows.stop > rows.start), default=last
        )
    summary = {"days_requested": (computed["end"] - first).days + 1, **day_counts(shown), "corrections": corrections}
    if rolls.specs():
        summary["roll"] = roller.summary()
        warnings += roller.warnings()
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            **envelope_parts(where, locations),
            summary=summary,
            sources=sources,
            warnings=warnings,
            filename=f"agweather-daily-{first}-{computed['end']}",
            etag=etag,
        ),
    )


@router.get("/weather/hourly", response=responses(TableResponse), summary="Hourly weather at points")
def hourly(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[HoursQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    area: Query[AreaQuery],
    vars: str | None = None,
) -> HttpResponse:
    """One row per point and hour: `time` (the hour's end, UTC), `kind`, each variable in `vars` (hourly catalog
    names), and `local_time` in the point's zone with `tz=local`. Defaults: the last 7 days through the forecast."""
    names = check_vars(vars, HOURLY, HOURLY_DEFAULT)
    if options.day_basis is not None:
        raise ApiError(
            "not_applicable",
            "Hourly values aren't grouped into days, so day_basis doesn't apply. Leave it out, and use tz=local to "
            "see each hour on the location's clock.",
            "day_basis",
        )
    now = clock.now()
    hour = now.replace(minute=0, second=0, microsecond=0)
    trim_end = when.end is None
    default_end = hour + timedelta(days=FORECAST_DAYS) if options.forecast else hour
    start, end = when.span(default_start=hour - timedelta(days=7), default_end=default_end)
    steps = (end - start) // timedelta(hours=1) + 1
    check_size(steps, len(where.locations()), MAX_HOURS, "hours")
    computed = {**where.echo(), "start": start, "end": end, "vars": names, "forecast": options.forecast}
    around = area.ask(output.units)
    computed |= {"tz": options.tz, "units": output.units, **area.echo()}
    etag = answer_etag(request, computed, points.hour_stamp(where.locations(), start, end, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, start.date(), end.date(), area=around)
    columns: dict[str, list] = {"point": [], "time": [], "local_time": [], "kind": [], **{name: [] for name in names}}
    sources: list[str] = []
    for k, found in enumerate(points.many_hours(where.locations(), start, end, names, now, area=around)):
        n = points.keep(found.kinds, options.forecast, trim_end)
        columns["point"] += [k] * n
        columns["time"] += found.times[:n]
        if options.tz == "local":
            from zoneinfo import ZoneInfo

            zone = ZoneInfo(found.zone)
            columns["local_time"] += [t.astimezone(zone).isoformat(timespec="minutes") for t in found.times[:n]]
        columns["kind"] += found.kinds[:n]
        for name in names:
            columns[name] += list(found.values[name][:n])
        sources += [s for s in found.sources if s not in sources]
    table = [Column(name="point", values=columns["point"]), Column(name="time", values=columns["time"])]
    if options.tz == "local":
        table.append(Column(name="local_time", values=columns["local_time"]))
    table.append(Column(name="kind", values=columns["kind"]))
    if where.points is None:
        table = table[1:]
    table += [catalog_column(name, columns[name]) for name in names]
    kinds = columns["kind"]
    summary = {
        "hours_requested": steps,
        "hours_returned": len(kinds),
        "hours_forecast": sum(k == FORECAST for k in kinds),
        "hours_missing": sum(k is None for k in kinds),
    }
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            **envelope_parts(where, locations),
            summary=summary,
            sources=sources,
            filename=f"agweather-hourly-{start:%Y%m%dT%H}-{end:%Y%m%dT%H}",
            etag=etag,
        ),
    )


def window_total(values: np.ndarray, name: str, gaps: str) -> tuple[float, int, int]:
    """A variable's total over a window, and its estimated and missing days: interior gaps up to MAX_GAP_DAYS are
    estimated by the variable's method (D45) unless `gaps=missing`; precipitation never is."""
    values = np.asarray(values, dtype=float)
    estimated = np.zeros(values.shape, dtype=bool)
    if gaps == "estimate" and GAP_FILL.get(name) == "interpolate":
        values, estimated = fill_short_gaps(values, MAX_GAP_DAYS)
    known = np.isfinite(values)
    total = float(values[known].sum()) if known.any() else float("nan")
    return total, int(estimated.sum()), int((~known).sum())


def computed_total(name: str, inputs: dict[str, np.ndarray], gaps: str) -> tuple[float, int, int]:
    """A computed variable's total over a window from its inputs' days (`agdata.computed`), and its estimated and
    missing days: each input's gaps filled its own way (water balance: no rain where it's missing, ET0 bridged)."""
    each, estimated = DAILY_COMPUTED[name].for_total(inputs, gaps)
    known = np.isfinite(each)
    total = float(each[known].sum()) if known.any() else float("nan")
    return total, int(estimated.sum()), int((~known).sum())


@dataclass(frozen=True, kw_only=True)
class CountColumn:
    """One `count=var:days_above_86` at points (`api.counts`, D75): the variable, what's counted, the column's name,
    and the bounds in the variable's stored unit."""

    variable: str
    count: counts.Count
    name: str  # `air_temperature_max_days_above_86`
    hourly: bool
    bounds: tuple[float | None, float | None]

    @property
    def missing(self) -> str:
        return f"{self.name}_missing_{self.count.axis}"


def count_columns(request: HttpRequest, units: str) -> list[CountColumn]:
    """Every `count=` (repeated, or separated by commas) as `variable:days_above_86`, checked."""
    given = [part.strip() for raw in request.GET.getlist("count") for part in raw.split(",") if part.strip()]
    system, overrides = SYSTEMS.get(units, "imperial"), unit_overrides(request)
    found: dict[str, CountColumn] = {}
    for text in given:
        variable, _, spec = text.partition(":")
        variable = variable.strip()
        if not spec:
            raise ApiError(
                "invalid",
                f"We can't read count={text}. Name the variable and what to count, such as "
                "count=air_temperature_max:days_above_86 or count=air_temperature:hours_above_86.",
                "count",
            )
        if variable in DAILY:
            v, axis = DAILY[variable], "day"
        elif variable in HOURLY:
            v, axis = HOURLY[variable], "hour"
        else:
            raise ApiError(
                "unknown_variable",
                f"We don't have a variable named {variable} to count. GET /api/v2/variables lists them.",
                "count",
            )
        count = counts.parse(spec)
        counts.check_axis(count, axis, variable, prefix=f"{variable}:")
        name = f"{variable}_{count.name}"
        shown = shown_unit(
            Column(name=name, values=[], unit=v.unit, step=v.scale, variable=variable), system, overrides
        )
        bounds = count.bounds(shown, v.unit, v.scale)
        found[name] = CountColumn(variable=variable, count=count, name=name, hourly=axis == "hour", bounds=bounds)
    return list(found.values())


class EventsQuery(Schema):
    """`first=`, `last=` and `since=` at points (`variable:frost`), each repeatable: read from `request.GET` by
    `event_columns`, declared here so they're documented and accepted."""

    first: str | None = None
    last: str | None = None
    since: str | None = None


@dataclass(frozen=True, kw_only=True)
class EventColumn:
    """One `first=`, `last=` or `since=` at points (`api.events`, D78): the daily variable, the event, the column's
    name, and the bounds in the variable's stored unit."""

    variable: str
    event: events.Event
    name: str  # `air_temperature_min_first_frost`
    bounds: tuple[float | None, float | None]

    @property
    def missing(self) -> str:
        return f"{self.name}_missing_days"


def event_columns(request: HttpRequest, units: str) -> list[EventColumn]:
    """Every `first=`, `last=` and `since=` (repeated, or separated by commas) as `variable:frost`, checked."""
    system, overrides = SYSTEMS.get(units, "imperial"), unit_overrides(request)
    found: dict[str, EventColumn] = {}
    for kind in events.KINDS:
        given = [part.strip() for raw in request.GET.getlist(kind) for part in raw.split(",") if part.strip()]
        for text in given:
            variable, _, spec = text.partition(":")
            variable = variable.strip()
            if not spec:
                raise ApiError(
                    "invalid",
                    f"We can't read {kind}={text}. Name the daily variable and the days to find, such as "
                    f"{kind}=air_temperature_min:frost or {kind}=soil_temperature_10cm_mean:above_50.",
                    kind,
                )
            if variable not in DAILY:
                hourly = " It's hourly: name a daily variable." if variable in HOURLY else ""
                raise ApiError(
                    "unknown_variable",
                    f"We don't have a daily variable named {variable}.{hourly} GET /api/v2/variables lists them.",
                    kind,
                )
            v = DAILY[variable]
            event = events.parse(kind=kind, text=spec)
            if event.named is not None and v.unit != "degC":
                raise ApiError(
                    "invalid",
                    f"{event.name.replace('_', ' ')} is a temperature, and {variable} isn't one. Give bounds such as "
                    f"{kind}={variable}:below_10.",
                    kind,
                )
            name = f"{variable}_{kind}_{event.name}"
            shown = shown_unit(
                Column(name=name, values=[], unit=v.unit, step=v.scale, variable=variable), system, overrides
            )
            found[name] = EventColumn(
                variable=variable, event=event, name=name, bounds=event.bounds(shown, v.unit, v.scale)
            )
    return list(found.values())


def _event_value(c: EventColumn, values: np.ndarray, first_day: date) -> tuple[Any, int]:
    """A point's first or last day (ISO) or days since the last, None if none or no data, and its missing days."""
    value, _, missing = events.find(
        np.asarray(values, dtype=float)[:, None],
        low=c.bounds[0],
        high=c.bounds[1],
        kind=c.event.kind,
        first_day=first_day,
    )
    found = value[0]
    if np.isnan(found):
        return None, int(missing[0])
    return (int(found) if c.event.kind == "since" else events.to_date(found).isoformat()), int(missing[0])


def _months(dates: list[date]) -> list[tuple[str, int, int]]:
    """(YYYY-MM, k0, k1): the dates' runs within each calendar month."""
    found: list[tuple[str, int, int]] = []
    for k, day in enumerate(dates):
        label = f"{day:%Y-%m}"
        if found and found[-1][0] == label:
            found[-1] = (label, found[-1][1], k + 1)
        else:
            found.append((label, k, k + 1))
    return found


def _hour_days(times: list[datetime], zone: str) -> list[date]:
    """The day each hour belongs to (an hour ending at midnight is the day before's, as the rollup counts it)."""
    tz = ZoneInfo(zone)
    return [(t - HOUR).astimezone(tz).date() for t in times]


@router.get("/weather/totals", response=responses(TableResponse), summary="Totals over a window at points")
def totals(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    found_days: Query[EventsQuery],
    area: Query[AreaQuery],
    vars: str | None = None,
    count: str | None = None,
    interval: Literal["month"] | None = None,
) -> HttpResponse:
    """One row per point (or point and month, `interval=month`): each variable's total from `start` to `end` (sums
    and hour counts: precipitation, ET0, shortwave, hours with RH ≥ 90%, …), with `<var>_estimated_days` and
    `<var>_missing_days`, and each `count` (`air_temperature_max:days_above_86`, repeatable) with its missing days or
    hours. Precipitation's missing days count as no rain and are never estimated; water balance's count as no rain
    and are estimated (D75); counts never estimate. Defaults:
    January 1 through the forecast (to today with `forecast=false`); only the counts when `count` is given alone."""
    wanted = count_columns(request, output.units)
    found_events = event_columns(request, output.units)
    alone = (wanted or found_events) and vars is None
    names = check_vars(vars, TOTALLED, [] if alone else TOTALS_DEFAULT)
    daily_counted = [c.variable for c in wanted if not c.hourly]
    hourly_counted = list(dict.fromkeys(c.variable for c in wanted if c.hourly))
    inputs = [i for name in names if name in DAILY_COMPUTED for i in DAILY_COMPUTED[name].inputs]  # for its total
    read = list(dict.fromkeys([*names, *inputs, *daily_counted, *(c.variable for c in found_events)]))
    read = read or ["air_temperature_min"]  # every day's kind
    now = clock.now()
    today = now.date()
    trim_end = when.end is None and when.date is None and options.forecast
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if trim_end else today)
    # An event without start looks back to its own default (a `below` one to the previous July 1), from the end
    # asked, or today when the end is the forecast's (`api.events`); with interval=month, over each month
    given_start = when.start is not None or when.date is not None
    event_first = {
        c.name: first if given_start or interval == "month" else c.event.default_start(today if trim_end else last)
        for c in found_events
    }
    read_from = min([first, *event_first.values()])
    check_size((last - read_from).days + 1, len(where.locations()), MAX_DAYS, "days")
    if hourly_counted:
        check_size(((last - first).days + 1) * 24, len(where.locations()), MAX_HOURS, "hours")
    computed = {**where.echo(), "start": first, "end": last, "vars": names, "forecast": options.forecast}
    around = area.ask(output.units)
    computed |= {"gaps": options.gaps, "units": output.units, **options.echo(), **area.echo()}
    if wanted:
        computed["count"] = [f"{c.variable}:{c.count.name}" for c in wanted]
    for kind in events.KINDS:
        asked_kind = [f"{c.variable}:{c.event.name}" for c in found_events if c.event.kind == kind]
        if asked_kind:
            computed[kind] = asked_kind
    if any(event_first[c.name] != first for c in found_events):
        computed["event_start"] = {c.name: event_first[c.name] for c in found_events}
    if interval is not None:
        computed["interval"] = interval
    stamped = [*read, *hourly_counted]
    etag = answer_etag(request, computed, points.stamp(where.locations(), read_from, last, now, names=stamped))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, first, last, options, area=around)
    found, warnings, sources, corrections = read_days(where, read_from, last, read, options, trim_end, now, area=around)
    hours: list[points.Hours] = []
    if hourly_counted:
        start, end = _midnight(first - timedelta(days=1)), _midnight(last + timedelta(days=2))
        hours = points.many_hours(where.locations(), start, end, hourly_counted, now, area=around)
        for h in hours:
            sources += [s for s in h.sources if s not in sources]

    keys = ["point", "month", "days", "forecast_days"]
    rows: dict[str, list] = {key: [] for key in keys}
    for name in names:
        rows[name], rows[f"{name}_estimated_days"], rows[f"{name}_missing_days"] = [], [], []
    for c in wanted:
        rows[c.name], rows[c.missing] = [], []
    for c in found_events:
        rows[c.name], rows[c.missing] = [], []
    for k, (days, n) in enumerate(found):
        skip = (first - read_from).days  # days read for an event's earlier start, before the totals' window
        spans = _months(days.dates[skip:n]) if interval == "month" else [("", 0, max(0, n - skip))]
        spans = [(label, k0 + skip, k1 + skip) for label, k0, k1 in spans]
        hour_days = _hour_days(hours[k].times, days.zone) if hours else []
        for label, k0, k1 in spans:
            rows["point"].append(k)
            rows["month"].append(label)
            rows["days"].append(k1 - k0)
            rows["forecast_days"].append(sum(kind in (FORECAST, PARTIAL) for kind in days.kinds[k0:k1]))
            for name in names:
                if name in DAILY_COMPUTED:
                    own = {i: np.asarray(days.values[i][k0:k1], dtype=float) for i in DAILY_COMPUTED[name].inputs}
                    total, estimated, missing = computed_total(name, own, options.gaps)
                else:
                    total, estimated, missing = window_total(days.values[name][k0:k1], name, options.gaps)
                rows[name].append(total)
                rows[f"{name}_estimated_days"].append(estimated)
                rows[f"{name}_missing_days"].append(missing)
            for c in wanted:
                if c.hourly:
                    inside = set(days.dates[k0:k1])
                    keep = np.array([day in inside for day in hour_days], dtype=bool)
                    values = np.asarray(hours[k].values[c.variable], dtype=float)[keep]
                else:
                    values = np.asarray(days.values[c.variable][k0:k1], dtype=float)
                hit, missing = counts.count_within(values[:, None], *c.bounds)
                rows[c.name].append(None if np.isnan(hit[0]) else int(hit[0]))
                rows[c.missing].append(int(missing[0]))
            for c in found_events:
                e0 = k0 if interval == "month" else (event_first[c.name] - read_from).days
                e1 = k1
                if c.event.kind == "since" and trim_end:  # days since, to today rather than the forecast's end
                    e1 = min(k1, (today - read_from).days + 1)
                values = np.asarray(days.values[c.variable][e0:e1], dtype=float)
                value, missing_days = _event_value(c, values=values, first_day=days.dates[e0] if e0 < k1 else first)
                rows[c.name].append(value)
                rows[c.missing].append(missing_days)
    table = [Column(name="point", values=rows["point"])] if where.points is not None else []
    if interval == "month":
        table.append(Column(name="month", values=rows["month"]))
    table += [Column(name="days", values=rows["days"]), Column(name="forecast_days", values=rows["forecast_days"])]
    for name in names:
        total = catalog_column(name, rows[name])
        total.summarize = False
        table += [
            total,
            Column(name=f"{name}_estimated_days", values=rows[f"{name}_estimated_days"]),
            Column(name=f"{name}_missing_days", values=rows[f"{name}_missing_days"]),
        ]
    for c in wanted:
        table += [Column(name=c.name, values=rows[c.name]), Column(name=c.missing, values=rows[c.missing])]
    for c in found_events:
        table += [Column(name=c.name, values=rows[c.name]), Column(name=c.missing, values=rows[c.missing])]
    missing_rain = sum(rows.get("precipitation_sum_missing_days", []))
    if missing_rain:
        warnings.append(
            f"Precipitation is missing on {counted(missing_rain, 'day')}. We never estimate precipitation, "
            "so the totals count those days as no rain."
        )
    uncounted = [c.name for c in wanted if sum(rows[c.missing])]
    if uncounted:
        warnings.append(
            f"Some days or hours have no data for {', '.join(uncounted)}. The counts leave them out, and "
            "each count's _missing column says how many."
        )
    if found and trim_end:
        computed["end"] = max((days.dates[n - 1] for days, n in found if n), default=last)
    summary = {"days_requested": (computed["end"] - first).days + 1, **day_counts(found), "corrections": corrections}
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            **envelope_parts(where, locations),
            summary=summary,
            sources=sources,
            warnings=warnings,
            filename=f"agweather-totals-{first}-{computed['end']}",
            etag=etag,
        ),
    )


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def answer_etag(request: HttpRequest, computed: dict, stamp: str | None) -> str | None:
    """None for answers read from Open-Meteo (`api.points`): computed each time."""
    return None if stamp is None else etag_for(request, computed, stamp)
