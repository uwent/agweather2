"""Weather at points (docs/api.md, "Weather at points"; PLAN.md Phase 5 C): daily and hourly series, and totals
over a window. Several points come back as one long table with a `point` column indexing `meta.locations`.

Raw values show missing where they're missing (D45). Totals bridge gaps by each variable's method (`agdata.catalog`
GAP_FILL: interpolated up to 7 days), counting estimated and missing days; precipitation is never estimated: its
total sums the known days and counts the rest as missing (no rain)."""

from datetime import date, datetime, timedelta

import numpy as np
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from agdata.catalog import DAILY_STATISTICS, DAILY_VARIABLES, GAP_FILL, VARIABLES
from agdata.series import FORECAST, PARTIAL
from agmodels.gaps import MAX_GAP_DAYS, fill_short_gaps
from api import clock, points
from api.envelope import Column, Result, catalog_column, etag_for, not_modified, respond
from api.errors import ApiError, counted
from api.locations import describe, describe_days
from api.params import DaysQuery, HoursQuery, OutputQuery, PointsQuery, SeriesQuery, check_vars
from api.schemas import TableResponse, responses
from ops.points import day_zone

router = Router(tags=["Weather"])

FORECAST_DAYS = 16  # a default end this far ahead reaches past every forecast; trailing empty days are dropped
MAX_DAYS = 3660  # per point and request: ten years of days
MAX_HOURS = 2 * 8784  # two years of hours
MAX_ROWS = 100_000  # points × steps
MAX_OUTSIDE = 10  # points outside the box (or before the archive) per request: each may fetch from Open-Meteo
DAILY = {name: v for name, v in DAILY_VARIABLES.items() if name != "et0_sum_estimate"}  # that one's for totals
DAILY_DEFAULT = ["air_temperature_min", "air_temperature_max", "precipitation_sum"]
HOURLY_DEFAULT = ["air_temperature", "dew_point", "relative_humidity", "precipitation", "wind_speed"]
TOTALLED = {
    name: v
    for name, v in DAILY.items()
    if (name in DAILY_STATISTICS and DAILY_STATISTICS[name].stat == "sum") or v.unit == "hour"
}
TOTALS_DEFAULT = ["precipitation_sum", "et0_sum", "shortwave_radiation_sum"]


def located(where: PointsQuery, first: date, last: date, options: SeriesQuery | None = None) -> list[dict]:
    """`meta.location(s)` for the points, refusing more outside the archive than MAX_OUTSIDE; for days (`options`
    given), whose clock sets them (`day_basis`, `days`)."""
    found = [
        describe(lat, lng) | ({} if options is None else describe_days(lat, lng, last.year, options.day_basis))
        for lat, lng in where.locations()
    ]
    outside = sum(not points.from_archive(lat, lng, first, last) for lat, lng in where.locations())
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
    where: PointsQuery, first: date, last: date, names: list[str], options: SeriesQuery, trim_end: bool, now: datetime
):
    """Each point's days, trimmed (`points.keep`), with the warnings, sources and corrections they bring."""
    found, warnings, sources, corrections = [], [], [], []
    sites = where.locations()
    zones = [day_zone(lat, lng, options.day_basis) for lat, lng in sites]
    for days in points.many_days(sites, first, last, names, now, zones, stores=points.shared_stores(names)):
        n = points.keep(days.kinds, options.forecast, trim_end)
        found.append((days, n))
        sources += [s for s in days.sources if s not in sources]
        corrections += [c for c in days.corrections if c not in corrections]
        if days.forecast.reason == "stale" and options.forecast:
            warnings.append("The forecast is out of date, so the series ends with the last observed day.")
    return found, sorted(set(warnings)), sources, corrections


def day_counts(found) -> dict:
    kinds = [k for days, n in found for k in days.kinds[:n]]
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
    vars: str | None = None,
) -> HttpResponse:
    """One row per point and local day: `date`, `kind` (observed, partial, forecast, or null with no data), and each
    variable in `vars` (daily catalog names; `GET /variables`). Defaults: January 1 through the forecast."""
    names = check_vars(vars, DAILY, DAILY_DEFAULT)
    now = clock.now()
    today = now.date()
    trim_end = when.end is None and when.date is None
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if options.forecast else today)
    check_size((last - first).days + 1, len(where.locations()), MAX_DAYS, "days")
    computed = {**where.echo(), "start": first, "end": last, "vars": names, "forecast": options.forecast}
    computed |= {"units": output.units, **options.echo()}
    etag = answer_etag(request, computed, points.stamp(where.locations(), first, last, now, names=names))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, first, last, options)
    found, warnings, sources, corrections = read_days(where, first, last, names, options, trim_end, now)
    columns: dict[str, list] = {"point": [], "date": [], "kind": [], **{name: [] for name in names}}
    for k, (days, n) in enumerate(found):
        columns["point"] += [k] * n
        columns["date"] += days.dates[:n]
        columns["kind"] += days.kinds[:n]
        for name in names:
            columns[name] += list(days.values[name][:n])
    table = [Column(name=name, values=columns[name]) for name in ("point", "date", "kind")]
    if where.points is None:
        table = table[1:]
    table += [catalog_column(name, columns[name]) for name in names]
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
    vars: str | None = None,
) -> HttpResponse:
    """One row per point and hour: `time` (the hour's end, UTC), `kind`, each variable in `vars` (hourly catalog
    names), and `local_time` in the point's zone with `tz=local`. Defaults: the last 7 days through the forecast."""
    names = check_vars(vars, VARIABLES, HOURLY_DEFAULT)
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
    computed |= {"tz": options.tz, "units": output.units}
    etag = answer_etag(request, computed, points.hour_stamp(where.locations(), start, end, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, start.date(), end.date())
    columns: dict[str, list] = {"point": [], "time": [], "local_time": [], "kind": [], **{name: [] for name in names}}
    sources: list[str] = []
    for k, found in enumerate(points.many_hours(where.locations(), start, end, names, now)):
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


@router.get("/weather/totals", response=responses(TableResponse), summary="Totals over a window at points")
def totals(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    vars: str | None = None,
) -> HttpResponse:
    """One row per point: each variable's total from `start` to `end` (sums and hour counts: precipitation, ET0,
    shortwave, hours with RH ≥ 90%, …), with `<var>_estimated_days` and `<var>_missing_days`. Precipitation's
    missing days count as no rain and are never estimated. Defaults: January 1 through the forecast (to today with
    `forecast=false`)."""
    names = check_vars(vars, TOTALLED, TOTALS_DEFAULT)
    now = clock.now()
    today = now.date()
    trim_end = when.end is None and when.date is None and options.forecast
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if trim_end else today)
    check_size((last - first).days + 1, len(where.locations()), MAX_DAYS, "days")
    computed = {**where.echo(), "start": first, "end": last, "vars": names, "forecast": options.forecast}
    computed |= {"gaps": options.gaps, "units": output.units, **options.echo()}
    etag = answer_etag(request, computed, points.stamp(where.locations(), first, last, now, names=names))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, first, last, options)
    found, warnings, sources, corrections = read_days(where, first, last, names, options, trim_end, now)
    rows: dict[str, list] = {"point": list(range(len(found))), "days": [], "forecast_days": []}
    for name in names:
        rows[name], rows[f"{name}_estimated_days"], rows[f"{name}_missing_days"] = [], [], []
    for days, n in found:
        rows["days"].append(n)
        rows["forecast_days"].append(sum(k in (FORECAST, PARTIAL) for k in days.kinds[:n]))
        for name in names:
            total, estimated, missing = window_total(days.values[name][:n], name, options.gaps)
            rows[name].append(total)
            rows[f"{name}_estimated_days"].append(estimated)
            rows[f"{name}_missing_days"].append(missing)
    table = [Column(name="point", values=rows["point"])] if where.points is not None else []
    table += [Column(name="days", values=rows["days"]), Column(name="forecast_days", values=rows["forecast_days"])]
    for name in names:
        total = catalog_column(name, rows[name])
        total.summarize = False
        table += [
            total,
            Column(name=f"{name}_estimated_days", values=rows[f"{name}_estimated_days"]),
            Column(name=f"{name}_missing_days", values=rows[f"{name}_missing_days"]),
        ]
    missing_rain = sum(rows.get("precipitation_sum_missing_days", []))
    if missing_rain:
        warnings.append(
            f"Precipitation is missing on {counted(missing_rain, 'day')}. We never estimate precipitation, "
            "so the totals count those days as no rain."
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


def answer_etag(request: HttpRequest, computed: dict, stamp: str | None) -> str | None:
    """None for answers read from Open-Meteo (`api.points`): computed each time."""
    return None if stamp is None else etag_for(request, computed, stamp)
