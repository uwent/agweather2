"""Degree days and freezes at points (docs/api.md; PLAN.md Phase 5 C), from each day's minimum and maximum
temperature, for any setting.

Thresholds follow the request's units (`units=us`: °F, `metric`: °C) and are checked by `api.params`: one no stored
temperature can reach is refused, an unusual one warned about. Degree days are computed in °F (`agmodels.
degree_days`; they scale exactly, so °C·d is the same answer × 5/9) and shown in the request's units.

Gaps (D45, D56): a missing day's min and max are interpolated across gaps up to MAX_GAP_DAYS (as the archive's
running totals do), and those days are flagged `temperature_estimated`; a longer gap adds nothing to a running
total and is counted missing. `gaps=missing` turns the estimate off. Freezes use the raw minimum only: a freeze
date isn't estimated."""

from collections.abc import Callable
from datetime import date, timedelta

import numpy as np
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from agdata.series import FORECAST, PARTIAL
from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine
from agmodels.gaps import MAX_GAP_DAYS, fill_short_gaps
from api import clock, points
from api.envelope import Column, Result, catalog_column, not_modified, respond
from api.errors import ApiError
from api.params import (
    FREEZE,
    DaysQuery,
    DegreeDaySetting,
    OutputQuery,
    PointsQuery,
    SeriesQuery,
    degree_day_settings,
    setting,
    temperature_threshold,
)
from api.routes.weather import (
    FORECAST_DAYS,
    MAX_DAYS,
    _etag,
    check_size,
    day_counts,
    envelope_parts,
    located,
    read_days,
)
from api.schemas import TableResponse, responses

router = Router(tags=["degree days"])

TEMPERATURES = ["air_temperature_min", "air_temperature_max"]
METHOD: dict[str, Callable] = {
    "sine": degree_days_sine,
    "average": degree_days_average,
    "modified": degree_days_modified,
}
DD_STEP = 0.1  # °F·d: daily values from temperatures stored to 0.1 °C (0.18 °F)
FREEZE_DEFAULT_F = (32, 28, 24)


def settings_from(request: HttpRequest, dd: str | None, units: str, warnings: list[str]) -> list[DegreeDaySetting]:
    """`dd=` settings, or one from `base` (and `upper`, `method`, default sine)."""
    base = request.GET.get("base")
    if dd is not None and base is not None:
        raise ApiError("conflict", "give either dd, or base (with upper and method), not both", "dd")
    if base is None:
        return degree_day_settings(dd, units, warnings)
    upper = request.GET.get("upper")
    try:
        base_value = float(base)
        upper_value = float(upper) if upper not in (None, "") else None
    except ValueError:
        raise ApiError("invalid", "base and upper must be numbers", "base") from None
    method = request.GET.get("method", "sine").lower()
    return [setting(method, base_value, upper_value, units, warnings, "base")]


def temperatures(days, n: int, gaps: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(min °F, max °F, estimated, usable) over a series' first n days, gaps bridged unless `gaps=missing`."""
    tmin = np.asarray(days.values["air_temperature_min"][:n], dtype=float)
    tmax = np.asarray(days.values["air_temperature_max"][:n], dtype=float)
    known = np.isfinite(tmin) & np.isfinite(tmax)
    lo, hi = np.where(known, tmin, np.nan), np.where(known, tmax, np.nan)
    if gaps == "estimate":
        lo, _ = fill_short_gaps(lo, MAX_GAP_DAYS)
        hi, _ = fill_short_gaps(hi, MAX_GAP_DAYS)
    usable = np.isfinite(lo) & np.isfinite(hi)
    return lo * 1.8 + 32, hi * 1.8 + 32, usable & ~known, usable


def degree_days(s: DegreeDaySetting, lo_f: np.ndarray, hi_f: np.ndarray) -> np.ndarray:
    return METHOD[s.method](lo_f, hi_f, s.base_f, s.upper_f)


def running(daily: np.ndarray, usable: np.ndarray, start: int) -> np.ndarray:
    """A running total from index `start` (NaN before it), adding nothing for an unusable day (D56)."""
    total = np.cumsum(np.where(usable, daily, 0.0))
    if start > 0:
        total = total - total[start - 1]
    total[:start] = np.nan
    return total


def dd_window(when: DaysQuery, options: SeriesQuery, biofix: date | None):
    """(first day read, first day shown, last day, trim the end?) for a degree-day request."""
    today = clock.now().date()
    trim_end = when.end is None and when.date is None and options.forecast
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if trim_end else today)
    read_from = min(first, biofix) if biofix is not None else first
    return read_from, first, last, trim_end


@router.get("/degree-days", response=responses(TableResponse), summary="Daily and running degree days at points")
def daily(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    dd: str | None = None,
    base: float | None = None,
    upper: float | None = None,
    method: str | None = None,
    biofix: date | None = None,
) -> HttpResponse:
    """One row per point and day: `date`, `kind`, the minimum and maximum temperature, `temperature_estimated` (the
    day's degree days use estimated temperatures), and for each setting `dd_<setting>` (that day's) and
    `dd_<setting>_cum` (the running total from `biofix`, default `start`). Settings: `dd=sine_48_86,modified_50_86,
    average_43` (method_base[_upper], in the request's units), or `base`, `upper` and `method` (sine, average,
    modified) for one. Defaults: January 1 through the forecast."""
    warnings: list[str] = []
    found_settings = settings_from(request, dd, output.units, warnings)
    read_from, first, last, trim_end = dd_window(when, options, biofix)
    check_size((last - read_from).days + 1, len(where.locations()), MAX_DAYS, "days")
    now = clock.now()
    computed = _computed(where, first, last, found_settings, biofix or first, options, output)
    etag = _etag(request, computed, points.stamp(where.locations(), read_from, last, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, read_from, last)
    found, read_warnings, sources, corrections = read_days(where, read_from, last, TEMPERATURES, options, trim_end, now)
    warnings += read_warnings
    skip = (first - read_from).days
    columns: dict[str, list] = {"point": [], "date": [], "kind": [], "temperature_estimated": []}
    columns |= {name: [] for name in TEMPERATURES}
    for s in found_settings:
        columns[f"dd_{s.name}"], columns[f"dd_{s.name}_cum"] = [], []
    start_at = (biofix or first) - read_from
    if biofix is not None and biofix > last:
        warnings.append(f"biofix {biofix} is after the last day ({last}): no running totals")
    for k, (days, n) in enumerate(found):
        lo_f, hi_f, estimated, usable = temperatures(days, n, options.gaps)
        shown = slice(skip, n)
        columns["point"] += [k] * max(0, n - skip)
        columns["date"] += days.dates[shown]
        columns["kind"] += days.kinds[shown]
        columns["temperature_estimated"] += estimated[shown].tolist()
        for name in TEMPERATURES:
            columns[name] += list(days.values[name][shown])
        for s in found_settings:
            values = degree_days(s, lo_f, hi_f)
            columns[f"dd_{s.name}"] += list(np.where(usable, values, np.nan)[shown])
            columns[f"dd_{s.name}_cum"] += list(running(values, usable, max(0, start_at.days))[shown])
    table = [Column(name=name, values=columns[name]) for name in ("point", "date", "kind")]
    if where.points is None:
        table = table[1:]
    table += [catalog_column(name, columns[name]) for name in TEMPERATURES]
    table.append(Column(name="temperature_estimated", values=columns["temperature_estimated"]))
    for s in found_settings:
        for name in (f"dd_{s.name}", f"dd_{s.name}_cum"):
            table.append(Column(name=name, values=columns[name], unit="degF_day", step=DD_STEP, summarize=True))
    if found and trim_end:
        computed["end"] = max((days.dates[n - 1] for days, n in found if n), default=last)
    summary = {
        **day_counts([(days, n) for days, n in found]),
        "days_estimated": sum(columns["temperature_estimated"]),
        "corrections": corrections,
    }
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            **envelope_parts(where, locations),
            summary=summary,
            sources=sources,
            warnings=warnings,
            filename=f"agweather-degree-days-{first}-{computed['end']}",
            etag=etag,
        ),
    )


@router.get("/degree-days/table", response=responses(TableResponse), summary="Degree-day totals at points")
def table(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    dd: str | None = None,
    base: float | None = None,
    upper: float | None = None,
    method: str | None = None,
    biofix: date | None = None,
) -> HttpResponse:
    """One row per point and setting: the total from `biofix` (default `start`) to `end`, and its estimated,
    missing and forecast days. What a daily report across many places and settings needs in one request
    (`points=` up to 50, `dd=` several). Defaults: January 1 to today (`forecast=true` adds the forecast's days)."""
    warnings: list[str] = []
    found_settings = settings_from(request, dd, output.units, warnings)
    read_from, first, last, trim_end = dd_window(when, options, biofix)
    check_size((last - read_from).days + 1, len(where.locations()), MAX_DAYS, "days")
    now = clock.now()
    computed = _computed(where, first, last, found_settings, biofix or first, options, output)
    etag = _etag(request, computed, points.stamp(where.locations(), read_from, last, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, read_from, last)
    found, read_warnings, sources, corrections = read_days(where, read_from, last, TEMPERATURES, options, trim_end, now)
    warnings += read_warnings
    begin = ((biofix or first) - read_from).days
    rows: dict[str, list] = {key: [] for key in ("point", "setting", "dd", "estimated_days", "missing_days")}
    rows["forecast_days"] = []
    for k, (days, n) in enumerate(found):
        lo_f, hi_f, estimated, usable = temperatures(days, n, options.gaps)
        window = slice(max(0, begin), n)
        forecast_days = sum(kind in (FORECAST, PARTIAL) for kind in days.kinds[window])
        for s in found_settings:
            values = degree_days(s, lo_f, hi_f)
            rows["point"].append(k)
            rows["setting"].append(s.name)
            rows["dd"].append(float(np.where(usable, values, 0.0)[window].sum()) if n > begin else float("nan"))
            rows["estimated_days"].append(int(estimated[window].sum()))
            rows["missing_days"].append(int((~usable[window]).sum()))
            rows["forecast_days"].append(forecast_days)
    columns = [Column(name="point", values=rows["point"])] if where.points is not None else []
    columns += [
        Column(name="setting", values=rows["setting"]),
        Column(name="dd", values=rows["dd"], unit="degF_day", step=DD_STEP),
        Column(name="estimated_days", values=rows["estimated_days"]),
        Column(name="missing_days", values=rows["missing_days"]),
        Column(name="forecast_days", values=rows["forecast_days"]),
    ]
    if found and trim_end:
        computed["end"] = max((days.dates[n - 1] for days, n in found if n), default=last)
    return respond(
        request,
        Result(
            request=computed,
            columns=columns,
            **envelope_parts(where, locations),
            summary={**day_counts(found), "corrections": corrections},
            sources=sources,
            warnings=warnings,
            filename=f"agweather-degree-day-table-{first}-{computed['end']}",
            etag=etag,
        ),
    )


@router.get("/freeze", response=responses(TableResponse), summary="Freezes at points")
def freeze(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    thresholds: str | None = None,
) -> HttpResponse:
    """One row per point and threshold (default 32, 28 and 24 °F, or `thresholds=` in the request's units): the
    days whose minimum reached it (≤), the last such day before July 1 (`last_spring`) and the first from July 1
    (`first_fall`) within the window, and the days with no minimum (`missing_days`), which a freeze could hide.
    Defaults: January 1 through the forecast."""
    warnings: list[str] = []
    if thresholds is None:
        given = [float(t) for t in FREEZE_DEFAULT_F] if output.units == "us" else [0.0, -2.2, -4.4]
    else:
        try:
            given = [float(t) for t in thresholds.split(",") if t.strip()]
        except ValueError:
            raise ApiError("invalid", "thresholds must be numbers separated by commas", "thresholds") from None
        if not given:
            raise ApiError("missing", "give one or more thresholds, separated by commas", "thresholds")
    limits_f = [temperature_threshold(t, output.units, FREEZE, "thresholds", warnings) for t in given]
    today = clock.now().date()
    trim_end = when.end is None and when.date is None and options.forecast
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if trim_end else today)
    check_size((last - first).days + 1, len(where.locations()), MAX_DAYS, "days")
    now = clock.now()
    computed = {**where.echo(), "start": first, "end": last, "thresholds": given, "forecast": options.forecast}
    computed |= {"threshold_units": "°C" if output.units == "metric" else "°F", "units": output.units}
    etag = _etag(request, computed, points.stamp(where.locations(), first, last, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, first, last)
    found, read_warnings, sources, corrections = read_days(
        where, first, last, ["air_temperature_min"], options, trim_end, now
    )
    warnings += read_warnings
    rows: dict[str, list] = {key: [] for key in ("point", "threshold", "freeze_days", "last_spring", "first_fall")}
    rows["missing_days"] = []
    for k, (days, n) in enumerate(found):
        tmin_f = np.asarray(days.values["air_temperature_min"][:n], dtype=float) * 1.8 + 32
        dates = days.dates[:n]
        for value, limit in zip(given, limits_f, strict=True):
            hit = np.isfinite(tmin_f) & (tmin_f <= limit + 1e-9)
            spring = [d for d, h in zip(dates, hit, strict=True) if h and (d.month, d.day) < (7, 1)]
            fall = [d for d, h in zip(dates, hit, strict=True) if h and (d.month, d.day) >= (7, 1)]
            rows["point"].append(k)
            rows["threshold"].append(value)
            rows["freeze_days"].append(int(hit.sum()))
            rows["last_spring"].append(spring[-1] if spring else None)
            rows["first_fall"].append(fall[0] if fall else None)
            rows["missing_days"].append(int((~np.isfinite(tmin_f)).sum()))
    columns = [Column(name="point", values=rows["point"])] if where.points is not None else []
    columns += [Column(name=name, values=rows[name]) for name in rows if name != "point"]
    if found and trim_end:
        computed["end"] = max((days.dates[n - 1] for days, n in found if n), default=last)
    return respond(
        request,
        Result(
            request=computed,
            columns=columns,
            **envelope_parts(where, locations),
            summary={**day_counts(found), "corrections": corrections},
            sources=sources,
            warnings=warnings,
            filename=f"agweather-freeze-{first}-{computed['end']}",
            etag=etag,
        ),
    )


def _computed(where, first, last, found_settings, biofix, options, output) -> dict:
    return {
        **where.echo(),
        "start": first,
        "end": last,
        "dd": [s.name for s in found_settings],
        "threshold_units": "°C" if output.units == "metric" else "°F",
        "biofix": biofix,
        "forecast": options.forecast,
        "gaps": options.gaps,
        "units": output.units,
    }
