"""Climate at points (docs/api.md, "Climate"; PLAN.md Phase 6 E, D82, D86): normals from the period's own years.

`/climate/normals`: per point and day of a year, each variable's normal (`agdata.climatology.pooled`: the mean of
every year's days within a window centered on the day, wrapping the year), its percentiles, and for values that
add up the normal running total from `start` (each year's own total, then across years: D61); `dd=` gives degree
days the same way, from each year's own days (bridged as the cumulative store bridges them). `interval=month` or
`year` gives each span's normal from each year's own mean or total, never from averaged days. `roll=` rolls the
daily normal around the year (`agdata.rolling`, circular)."""

from dataclasses import replace
from datetime import date, timedelta
from typing import Literal

import numpy as np
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from agdata import climatology, normals
from agdata.computed import adds_up
from agdata.layers import DD_STEP
from agdata.rolling import label, roll
from api import climate, clock, rolled
from api.envelope import Column, Result, catalog_column, not_modified, respond
from api.errors import ApiError
from api.params import (
    AreaQuery,
    DaysQuery,
    OutputQuery,
    PointsQuery,
    RollQuery,
    check_vars,
    degree_day_settings,
)
from api.routes.degree_days import degree_days
from api.routes.weather import answer_etag, check_size, envelope_parts, located
from api.schemas import TableResponse, responses

router = Router(tags=["Climate"])

NORMAL_VARIABLES = {name: name for name in normals.DAILY_NAMES}
DEFAULT_VARS = ["air_temperature_min", "air_temperature_max", "precipitation_sum"]
TEMPERATURES = ["air_temperature_min", "air_temperature_max"]
NOT_IN_LAST30 = ("air_temperature_mean",)  # gridMET's years have no hourly mean (`agdata.normals`)


def _months(first: date, last: date) -> list[tuple[str, int, int]]:
    """(YYYY-MM, first slot, last slot + 1) of each month's days within first..last (one year)."""
    found = []
    day = first
    while day <= last:
        end = min(last, date(day.year + (day.month == 12), day.month % 12 + 1, 1) - timedelta(days=1))
        found.append((f"{day:%Y-%m}", climatology.slot(day), climatology.slot(end) + 1))
        day = end + timedelta(days=1)
    return found


@router.get("/climate/normals", response=responses(TableResponse), summary="Normals at points")
def normals_at_points(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    q: Query[climate.ClimateQuery],
    output: Query[OutputQuery],
    rolls: Query[RollQuery],
    area: Query[AreaQuery],
    vars: str | None = None,
    dd: str | None = None,
    interval: Literal["day", "month", "year"] = "day",
) -> HttpResponse:
    """One row per point and day (or month, or one per point with `interval=year`) of one calendar year, default
    this one: each variable's normal (`<var>`), its percentiles (`<var>_p10`), and for values that add up the normal
    running total from `start` (`<var>_cum`, `<var>_cum_p10`); with `dd=`, each setting's normal degree days
    (`dd_<setting>`) and running total (`dd_<setting>_cum`). Only the degree days when `dd` is given alone."""
    warnings: list[str] = []
    settings_found = degree_day_settings(dd, output.units, warnings) if dd is not None else []
    names = check_vars(vars, NORMAL_VARIABLES, [] if settings_found and vars is None else DEFAULT_VARS)
    if q.period == "last30" and (lacking := [n for n in names if n in NOT_IN_LAST30]):
        raise ApiError(
            "not_applicable",
            f"The 30-year normals have no {lacking[0]}: the records before 2016 give each day's minimum and maximum "
            "only. Ask for period=last10 or last5, or for air_temperature_min and air_temperature_max.",
            "vars",
        )
    percentiles = q.percentile_list()
    specs = rolls.specs()
    if specs and interval != "day":
        raise ApiError(
            "conflict",
            f"Rolling windows apply to daily normals, not to interval={interval}. Leave out roll, or interval.",
            "roll",
        )
    rolled.check_stat(rolls, {name: adds_up(name) for name in names})
    now = clock.now()
    today = now.date()
    first, last = when.span(default_end=date(today.year, 12, 31))
    climate.one_year(first, last)
    check_size((last - first).days + 1, len(where.locations()), 366, "days")
    around = area.ask(output.units)
    asked, period_warnings = climate.ask(where, q, today, around)
    warnings += period_warnings
    wanted: list[str] = [*names, *(TEMPERATURES if settings_found else [])]
    read: list[str] = list(dict.fromkeys(wanted))
    computed = {**where.echo(), "start": first, "end": last, "vars": names, "interval": interval, **q.echo()}
    computed |= {"dd": [s.name for s in settings_found] or None, "units": output.units}
    computed |= {**rolls.echo(), **area.echo()}
    etag = answer_etag(request, computed, asked.stamp(read, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, today, today, area=around)  # the dates are calendar days, not reads
    year = first.year
    dates = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    slots = np.array([climatology.slot(d) for d in dates])
    real = climatology.days_of(year)  # the year's own days on the slots, for rolling around it
    day_index = np.cumsum(real) - 1  # a slot's place among them
    lo, hi = climatology.slot(first), climatology.slot(last) + 1
    spans = _months(first, last) if interval == "month" else [("", lo, hi)]
    columns: dict[str, list] = {}
    kinds: dict[str, str] = {}  # each column's own variable, or "dd"
    summarized: set[str] = set()
    rolled_of: dict[str, tuple[str, int, str]] = {}
    years_with: list[int] = []

    def add(name: str, values, of: str, main: bool = False) -> None:
        columns.setdefault(name, []).extend(np.asarray(values, dtype=float).tolist())
        kinds[name] = of
        if main:
            summarized.add(name)

    for k, found in enumerate(asked.read(read)):
        rows = len(dates) if interval == "day" else len(spans)
        if where.points is not None:
            columns.setdefault("point", []).extend([k] * rows)
        if interval == "day":
            columns.setdefault("date", []).extend(dates)
            columns.setdefault("day_of_year", []).extend([int(s) + 1 for s in slots])
        elif interval == "month":
            columns.setdefault("month", []).extend([label_ for label_, _, _ in spans])
        counted = climate.years_counted(found[read[0]])
        years_with.append(counted)
        note = climate.few_years_warning(
            counted, asked.period, "this location" if where.points is None else f"location {k}"
        )
        if note is not None and note not in warnings:
            warnings.append(note)
        series: dict[str, tuple[np.ndarray, bool]] = {name: (found[name], adds_up(name)) for name in names}
        if settings_found:
            temps = [
                climatology.degree_day_temperatures(
                    found["air_temperature_min"][y], found["air_temperature_max"][y], yr
                )
                for y, yr in enumerate(asked.years)
            ]
            for s in settings_found:
                days = np.stack([_dd(s, lo_f, hi_f) for lo_f, hi_f in temps]) if temps else np.empty((0, 366))
                series[f"dd_{s.name}"] = (days, True)
        for name, (values, totals) in series.items():
            of = "dd" if name.startswith("dd_") else name
            if interval != "day":
                for _, a, b in spans:
                    span = climatology.over_span(values, asked.years, a, b, total=totals, percentiles=percentiles)
                    add(name, [span.mean], of, main=True)
                    for p in percentiles:
                        add(f"{name}_{climate.suffix(p)}", [span.percentiles[p]], of)
                continue
            pooled = climatology.pooled(values, asked.years, percentiles=percentiles, days=asked.pool_days)
            add(name, pooled.mean[slots], of, main=True)
            for p in percentiles:
                add(f"{name}_{climate.suffix(p)}", pooled.percentiles[p][slots], of)
            if totals:
                r = climatology.running(values, asked.years, start=lo, percentiles=percentiles)
                add(f"{name}_cum", r.mean[slots], of)
                for p in percentiles:
                    add(f"{name}_cum_{climate.suffix(p)}", r.percentiles[p][slots], of)
            year_days = pooled.mean[real]
            stat = rolled.stat_for(rolls, totals)
            for spec in specs:
                column = f"{name}_{label(spec.days)}"
                rolled_values = roll(year_days, replace(spec, partial=False), stat, circular=True).values
                add(column, rolled_values[day_index[slots]], of)
                rolled_of[column] = (name, spec.days, stat)
    table: list[Column] = []
    for name in ("point", "date", "day_of_year", "month"):
        if name in columns:
            table.append(Column(name=name, values=columns[name]))
    for name, values in columns.items():
        if name in ("point", "date", "day_of_year", "month"):
            continue
        of = kinds[name]
        if of == "dd":
            table.append(Column(name=name, values=values, unit="degF_day", step=DD_STEP, summarize=name in summarized))
        else:
            column = catalog_column(name, values, variable=of)
            table.append(replace(column, summarize=name in summarized))
    summary = asked.summary() | {
        "years_with_data": years_with if where.points is not None else (years_with[0] if years_with else 0)
    }
    if rolled_of:
        summary["roll"] = {
            "columns": {c: {"of": of, "days": n, "stat": st} for c, (of, n, st) in rolled_of.items()},
            "align": rolls.roll_align,
        }
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            **envelope_parts(where, locations),
            summary=summary,
            sources=asked.sources(),
            warnings=warnings,
            filename=f"agweather-normals-{q.period}-{first}-{last}",
            etag=etag,
        ),
    )


def _dd(s, lo_f: np.ndarray, hi_f: np.ndarray) -> np.ndarray:
    """A year's daily degree days (366 slots) for a setting, NaN where a day has no usable temperatures."""
    usable = np.isfinite(lo_f) & np.isfinite(hi_f)
    found = degree_days(s, np.where(usable, lo_f, 0.0), np.where(usable, hi_f, 0.0))
    return np.where(usable, found, np.nan)
