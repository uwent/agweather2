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
from agdata.catalog import GAP_FILL
from agdata.computed import adds_up
from agdata.layers import DD_STEP
from agdata.rolling import label, roll
from agmodels.gaps import MAX_GAP_DAYS, fill_short_gaps
from api import climate, clock, points, rolled
from api.envelope import Column, Result, catalog_column, not_modified, respond
from api.errors import ApiError
from api.params import (
    AreaQuery,
    DaysQuery,
    OutputQuery,
    PointsQuery,
    RollQuery,
    SeriesQuery,
    check_vars,
    degree_day_settings,
)
from api.routes.degree_days import degree_days, freeze_thresholds, temperatures_of
from api.routes.weather import FORECAST_DAYS, answer_etag, check_size, envelope_parts, located, read_days
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
    asked, period_warnings = climate.ask(where, q, today, around, pool_days=q.window)
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
            pooled = climatology.pooled(values, asked.years, percentiles=percentiles, days=q.window)
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


# --- Freezes ------------------------------------------------------------------------------------------------------


def _freezes_at(found: dict[str, np.ndarray], limits_f: list[float]) -> list[climatology.Freezes]:
    """A point's freeze statistics at each threshold (°F), from its years' daily minimums (°C)."""
    tmin = found["air_temperature_min"]
    return [climatology.freezes(tmin, (f - 32) / 1.8) for f in limits_f]


def _slot_day(value: float, year: int, spring: bool) -> date | None:
    """A calendar slot (fractional, from a quantile) as a date in `year`; None for none. February 29 in a year
    without one is February 28 in spring and March 1 in fall (a freeze date can't fall on a day that isn't)."""
    if not np.isfinite(value):
        return None
    index = round(float(value))
    found = climatology.slot_date(index, year)
    if found is None:
        return date(year, 2, 28) if spring else date(year, 3, 1)
    return found


@router.get("/climate/frost", response=responses(TableResponse), summary="Freeze dates and season length at points")
def frost(
    request: HttpRequest,
    where: Query[PointsQuery],
    q: Query[climate.PeriodQuery],
    output: Query[OutputQuery],
    area: Query[AreaQuery],
    thresholds: str | None = None,
    probabilities: str | None = None,
) -> HttpResponse:
    """One row per point and threshold (default 32, 28 and 24 °F): `last_spring_p<N>`, the date by which N% of the
    period's years had had their last spring freeze (at or below the threshold, January–June), `first_fall_p<N>`,
    the date by which N% had had their first fall freeze (July–December), and `season_days_p<N>`, the frost-free
    season's length that N% of years were at or under, for each of `probabilities` (default 10, 50, 90); the years
    counted and the years with no freeze in each season. Dates are this year's. A date is null where N% of years
    reaches years with no freeze at all."""
    warnings: list[str] = []
    given, limits_f = freeze_thresholds(thresholds, output.units, warnings)
    chances = climate.percents(probabilities, "probabilities", "probabilities=10,50,90") or [10.0, 50.0, 90.0]
    now = clock.now()
    today = now.date()
    around = area.ask(output.units)
    asked, period_warnings = climate.ask(where, q, today, around)
    warnings += period_warnings
    computed = {**where.echo(), "thresholds": given, "probabilities": chances, **q.echo(), "units": output.units}
    computed |= {"threshold_units": "°C" if output.units == "metric" else "°F", **area.echo()}
    etag = answer_etag(request, computed, asked.stamp(["air_temperature_min"], now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, today, today, area=around)
    rows: dict[str, list] = {"point": [], "threshold": []}
    for p in chances:
        for key in ("last_spring", "first_fall", "season_days"):
            rows[f"{key}_{climate.suffix(p)}"] = []
    for key in ("years_spring", "years_fall", "years_without_spring", "years_without_fall"):
        rows[key] = []
    for k, found in enumerate(asked.read(["air_temperature_min"])):
        note = climate.few_years_warning(
            climate.years_counted(found["air_temperature_min"]),
            asked.period,
            "this location" if where.points is None else f"location {k}",
        )
        if note is not None and note not in warnings:
            warnings.append(note)
        for value, fz in zip(given, _freezes_at(found, limits_f), strict=True):
            rows["point"].append(k)
            rows["threshold"].append(value)
            for p in chances:
                spring, fall = fz.dates(p / 100)
                season = fz.season_length(p / 100)
                rows[f"last_spring_{climate.suffix(p)}"].append(_slot_day(float(spring), today.year, spring=True))
                rows[f"first_fall_{climate.suffix(p)}"].append(_slot_day(float(fall), today.year, spring=False))
                length = float(season) if np.isfinite(season) else None
                rows[f"season_days_{climate.suffix(p)}"].append(round(length) if length is not None else None)
            rows["years_spring"].append(int(fz.years_spring))
            rows["years_fall"].append(int(fz.years_fall))
            rows["years_without_spring"].append(int((fz.spring == climatology.NONE_SPRING).sum()))
            rows["years_without_fall"].append(int((fz.fall == climatology.NONE_FALL).sum()))
    columns = [Column(name=name, values=values) for name, values in rows.items()]
    if where.points is None:
        columns = columns[1:]
    return respond(
        request,
        Result(
            request=computed,
            columns=columns,
            **envelope_parts(where, locations),
            summary=asked.summary(),
            sources=asked.sources(),
            warnings=warnings,
            filename=f"agweather-frost-{q.period}",
            etag=etag,
        ),
    )


@router.get(
    "/climate/frost/chances", response=responses(TableResponse), summary="Chances of a freeze by date at points"
)
def frost_chances(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    q: Query[climate.PeriodQuery],
    output: Query[OutputQuery],
    area: Query[AreaQuery],
    thresholds: str | None = None,
) -> HttpResponse:
    """One row per point, threshold and date of one calendar year (default this year, January 1 to December 31):
    `season` and `chance`, in percent: January–June (`spring`), the chance of a freeze (at or below the threshold)
    after the date; July–December (`fall`), the chance one has come on or before it. Among the period's years that
    count."""
    warnings: list[str] = []
    given, limits_f = freeze_thresholds(thresholds, output.units, warnings)
    now = clock.now()
    today = now.date()
    first, last = when.span(default_end=date(today.year, 12, 31))
    climate.one_year(first, last)
    check_size((last - first).days + 1, len(where.locations()) * len(given), 366, "days")
    around = area.ask(output.units)
    asked, period_warnings = climate.ask(where, q, today, around)
    warnings += period_warnings
    computed = {**where.echo(), "start": first, "end": last, "thresholds": given, **q.echo(), "units": output.units}
    computed |= {"threshold_units": "°C" if output.units == "metric" else "°F", **area.echo()}
    etag = answer_etag(request, computed, asked.stamp(["air_temperature_min"], now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, today, today, area=around)
    dates = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    slots = np.array([climatology.slot(d) for d in dates])
    spring_end = climatology.SPRING[1]
    rows: dict[str, list] = {key: [] for key in ("point", "threshold", "date", "day_of_year", "season", "chance")}
    for k, found in enumerate(asked.read(["air_temperature_min"])):
        note = climate.few_years_warning(
            climate.years_counted(found["air_temperature_min"]),
            asked.period,
            "this location" if where.points is None else f"location {k}",
        )
        if note is not None and note not in warnings:
            warnings.append(note)
        for value, fz in zip(given, _freezes_at(found, limits_f), strict=True):
            chance = np.where(slots < spring_end, fz.after_spring[slots], fz.by_fall[slots]) * 100
            rows["point"] += [k] * len(dates)
            rows["threshold"] += [value] * len(dates)
            rows["date"] += dates
            rows["day_of_year"] += [int(s) + 1 for s in slots]
            rows["season"] += ["spring" if s < spring_end else "fall" for s in slots]
            rows["chance"] += chance.tolist()
    columns = [
        Column(name=name, values=values, unit="percent", step=1)
        if name == "chance"
        else Column(name=name, values=values)
        for name, values in rows.items()
    ]
    if where.points is None:
        columns = columns[1:]
    return respond(
        request,
        Result(
            request=computed,
            columns=columns,
            **envelope_parts(where, locations),
            summary=asked.summary(),
            sources=asked.sources(),
            warnings=warnings,
            filename=f"agweather-frost-chances-{q.period}-{first}-{last}",
            etag=etag,
        ),
    )


# --- This year against last year and normal ------------------------------------------------------------------------

COMPARE_VARIABLES = {name: name for name in normals.DAILY_NAMES if adds_up(name)}
OBSERVED = "observed"


def _this_year(name: str, values: np.ndarray, gaps: str) -> tuple[np.ndarray, np.ndarray]:
    """A variable's daily values for a running total, as `/weather/totals` sums them, and which were estimated:
    precipitation's missing days add nothing (D45); others' short gaps are bridged unless `gaps=missing`."""
    values = np.asarray(values, dtype=float)
    estimated = np.zeros(values.shape, dtype=bool)
    if gaps == "estimate" and GAP_FILL.get(name) == "interpolate":
        values, estimated = fill_short_gaps(values, MAX_GAP_DAYS)
    return values, estimated


def _rank(value: float, among: np.ndarray) -> float:
    """The percentile of `value` among the years' values (ties count half): 0 below them all, 100 above."""
    known = among[np.isfinite(among)]
    if not np.isfinite(value) or known.size == 0:
        return float("nan")
    return 100.0 * (float((known < value).sum()) + 0.5 * float((known == value).sum())) / known.size


def _days_ahead(total: float, normal: np.ndarray, lo: int, as_of: date) -> int | None:
    """Days ahead of normal (negative: behind): the day the normal running total (366 slots, from slot `lo`) is
    nearest `total` as it passes it, less `as_of`; None where the normal never reaches it within the year, or
    there's no total."""
    if not np.isfinite(total):
        return None
    reached = np.flatnonzero(np.nan_to_num(normal[lo:], nan=-np.inf) >= total - 1e-9)
    if reached.size == 0:
        return None
    s = lo + int(reached[0])
    if s > lo and np.isfinite(normal[s - 1]) and total - normal[s - 1] < normal[s] - total:
        s -= 1  # the nearer day: the normal passes the total between two days
    day = climatology.slot_date(s, as_of.year) or date(as_of.year, 3, 1)
    return (day - as_of).days


@router.get("/climate/compare", response=responses(TableResponse), summary="This year against normal at points")
def compare(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    q: Query[climate.PeriodQuery],
    output: Query[OutputQuery],
    area: Query[AreaQuery],
    vars: str | None = None,
    dd: str | None = None,
    percentiles: str | None = None,
    forecast: bool = True,
    gaps: Literal["estimate", "missing"] = "estimate",
) -> HttpResponse:
    """One row per point and day from `start` (default January 1) to `end` (default December 31), one calendar
    year: `kind`, and for each variable (`vars`: precipitation, ET0, sunlight) and degree-day setting (`dd=`), as
    `X` (`precipitation_sum` or `dd_<setting>`): this year's running total from `start` through the forecast
    (`X_cum`), last year's to the same date (`X_cum_last_year`), the period's normal (`X_cum_normal`, with
    `X_cum_normal_p10` … for `percentiles`, default 10 and 90), `X_departure`, `X_percent_of_normal`, and
    `X_percentile` among the period's years. `meta.summary.as_of` is each point's last observed day, with each
    total's percentile there and, for degree days, `days_ahead` of normal (negative: behind)."""
    warnings: list[str] = []
    settings_found = degree_day_settings(dd, output.units, warnings) if dd is not None else []
    names = check_vars(vars, COMPARE_VARIABLES, [] if settings_found and vars is None else ["precipitation_sum"])
    spread = (
        climate.percents(percentiles, "percentiles", "percentiles=10,90") if percentiles is not None else [10.0, 90.0]
    )
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
    options = SeriesQuery(forecast=forecast, gaps=gaps)
    computed = {**where.echo(), "start": first, "end": last, "vars": names, **q.echo(), "percentiles": spread}
    computed |= {"dd": [s.name for s in settings_found] or None, "forecast": forecast, "gaps": gaps}
    computed |= {"units": output.units, **area.echo()}
    stamp = points.stamp(
        where.locations(), first, min(last, today + timedelta(days=FORECAST_DAYS)), now, names=read, area=around
    )
    etag = answer_etag(request, computed, None if stamp is None else f"{stamp}|{asked.stamp(read, now)}")
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, today, today, area=around)
    found_now, read_warnings, sources, corrections = read_days(
        where, first, last, read, options, trim_end=False, now=now, area=around
    )
    warnings += read_warnings
    dates = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    slots = np.array([climatology.slot(d) for d in dates])
    lo = climatology.slot(first)
    last_year = asked.years.index(today.year - 1) if today.year - 1 in asked.years else None
    columns: dict[str, list] = {}
    units: dict[str, str] = {}
    summaries: list[dict] = []
    estimated_days = 0

    def add(name: str, values, of: str) -> None:
        columns.setdefault(name, []).extend(np.asarray(values, dtype=float).tolist())
        units[name] = of

    for k, ((days, n), past) in enumerate(zip(found_now, asked.read(read), strict=True)):
        kept = min(n, len(dates))  # without the forecast's days when forecast=false (`points.keep`)
        kinds = list(days.kinds[:kept]) + [None] * (len(dates) - kept)

        def own(name: str, kept: int = kept, days=days) -> np.ndarray:
            out = np.full(len(dates), np.nan)
            out[:kept] = np.asarray(days.values[name][:kept], dtype=float)
            return out

        known_rows = [r for r, kind in enumerate(kinds) if kind is not None]
        ends = known_rows[-1] + 1 if known_rows else 0
        observed = [r for r, kind in enumerate(kinds) if kind == OBSERVED]
        as_of = observed[-1] if observed else None
        if where.points is not None:
            columns.setdefault("point", []).extend([k] * len(dates))
        columns.setdefault("date", []).extend(dates)
        columns.setdefault("day_of_year", []).extend([int(s) + 1 for s in slots])
        columns.setdefault("kind", []).extend(kinds)
        note = climate.few_years_warning(
            climate.years_counted(past[read[0]]),
            asked.period,
            "this location" if where.points is None else f"location {k}",
        )
        if note is not None and note not in warnings:
            warnings.append(note)
        now_daily: dict[str, np.ndarray] = {}
        past_daily: dict[str, np.ndarray] = {}
        for name in names:
            values, estimated = _this_year(name, own(name), gaps)
            now_daily[name] = values
            estimated_days += int(estimated[:ends].sum())
            past_daily[name] = past[name]
        if settings_found:
            tmin = own("air_temperature_min")
            tmax = own("air_temperature_max")
            lo_f, hi_f, estimated, usable = temperatures_of(tmin, tmax, gaps)
            estimated_days += int(estimated[:ends].sum())
            temps = [
                climatology.degree_day_temperatures(
                    past["air_temperature_min"][y], past["air_temperature_max"][y], year
                )
                for y, year in enumerate(asked.years)
            ]
            for s in settings_found:
                now_daily[f"dd_{s.name}"] = np.where(usable, degree_days(s, lo_f, hi_f), np.nan)
                past_daily[f"dd_{s.name}"] = np.stack([_dd(s, a, b) for a, b in temps]) if temps else np.empty((0, 366))
        point_summary: dict = {"as_of": dates[as_of] if as_of is not None else None, "totals": {}}
        if where.points is not None:
            point_summary = {"point": k, **point_summary}
        for name, daily in now_daily.items():
            of = "dd" if name.startswith("dd_") else name
            total = np.cumsum(np.where(np.isfinite(daily), daily, 0.0))
            total[ends:] = np.nan
            r = climatology.running(past_daily[name], asked.years, start=lo, percentiles=spread)
            normal = r.mean[slots]
            mine = r.totals[last_year, slots] if last_year is not None else np.full(len(dates), np.nan)
            ranks = np.array([_rank(total[d], r.totals[:, slots[d]]) for d in range(len(dates))])
            with np.errstate(invalid="ignore", divide="ignore"):
                share = np.where(normal > 0, total / normal * 100, np.nan)
            add(f"{name}_cum", total, of)
            add(f"{name}_cum_last_year", mine, of)
            add(f"{name}_cum_normal", normal, of)
            for p in spread:
                add(f"{name}_cum_normal_{climate.suffix(p)}", r.percentiles[p][slots], of)
            add(f"{name}_departure", total - normal, of)
            add(f"{name}_percent_of_normal", share, "percent")
            add(f"{name}_percentile", ranks, "percent")
            if as_of is not None:
                entry: dict = {"percentile": None if np.isnan(ranks[as_of]) else round(float(ranks[as_of]))}
                if name.startswith("dd_"):
                    entry["days_ahead"] = _days_ahead(float(total[as_of]), r.mean, lo, dates[as_of])
                point_summary["totals"][name] = entry
        summaries.append(point_summary)
    table: list[Column] = [
        Column(name=name, values=columns[name]) for name in ("point", "date", "day_of_year", "kind") if name in columns
    ]
    for name, values in columns.items():
        if name in ("point", "date", "day_of_year", "kind"):
            continue
        of = units[name]
        if of == "percent":
            table.append(Column(name=name, values=values, unit="percent", step=1))
        elif of == "dd":
            table.append(Column(name=name, values=values, unit="degF_day", step=DD_STEP))
        else:
            table.append(replace(catalog_column(name, values, variable=of), summarize=False))
    summary = asked.summary() | {"estimated_days": estimated_days, "corrections": corrections}
    summary["compare"] = summaries if where.points is not None else summaries[0]
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            **envelope_parts(where, locations),
            summary=summary,
            sources=[*sources, *(s for s in asked.sources() if s not in sources)],
            warnings=warnings,
            filename=f"agweather-compare-{q.period}-{first}-{last}",
            etag=etag,
        ),
    )
