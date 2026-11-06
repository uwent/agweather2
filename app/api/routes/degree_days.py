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
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from agdata import projection
from agdata.grid import NDFD
from agdata.series import FORECAST, PARTIAL, archive_years, past_reader
from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine
from agmodels.gaps import MAX_GAP_DAYS, fill_short_gaps
from agmodels.scenarios import first_days, reached, spread
from api import clock, points
from api.envelope import Column, Result, catalog_column, not_modified, respond
from api.errors import ApiError, day_text
from api.params import (
    FREEZE,
    DaysQuery,
    DegreeDaySetting,
    OutputQuery,
    PointsQuery,
    SeriesQuery,
    degree_day_settings,
    resolve_biofix,
    setting,
    temperature_threshold,
)
from api.routes.models import NO_PROJECTION, projection_mode
from api.routes.weather import (
    FORECAST_DAYS,
    MAX_DAYS,
    answer_etag,
    check_size,
    day_counts,
    envelope_parts,
    located,
    read_days,
)
from api.schemas import TableResponse, responses

router = Router(tags=["Degree days and freezes"])

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
        raise ApiError("conflict", "Give either dd, or base (with upper and method), but not both.", "dd")
    if base is None:
        return degree_day_settings(dd, units, warnings)
    upper = request.GET.get("upper")
    try:
        base_value = float(base)
        upper_value = float(upper) if upper not in (None, "") else None
    except ValueError:
        raise ApiError("invalid", "base and upper must be numbers, such as base=50&upper=86.", "base") from None
    method = request.GET.get("method", "sine").lower()
    return [setting(method, base_value, upper_value, units, warnings, "base")]


def temperatures(days, n: int, gaps: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(min °F, max °F, estimated, usable) over a series' first n days, gaps bridged unless `gaps=missing`."""
    tmin = np.asarray(days.values["air_temperature_min"][:n], dtype=float)
    tmax = np.asarray(days.values["air_temperature_max"][:n], dtype=float)
    return temperatures_of(tmin, tmax, gaps)


def degree_days(s: DegreeDaySetting, lo_f: np.ndarray, hi_f: np.ndarray) -> np.ndarray:
    return METHOD[s.method](lo_f, hi_f, s.base_f, s.upper_f)


def running(daily: np.ndarray, usable: np.ndarray, start: int) -> np.ndarray:
    """A running total from index `start` (NaN before it), adding nothing for an unusable day (D56); time on axis 0."""
    total = np.cumsum(np.where(usable, daily, 0.0), axis=0)
    if start > 0:
        total = total - total[start - 1]
    total[:start] = np.nan
    return total


def dd_window(when: DaysQuery, options: SeriesQuery, sent_biofix: str | None):
    """(first day read, first day shown, last day, trim the end?, the biofix) for a degree-day request; a biofix sent
    as a month and day is the latest on or before the last day (`params.resolve_biofix`)."""
    today = clock.now().date()
    trim_end = when.end is None and when.date is None and options.forecast
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if trim_end else today)
    biofix = resolve_biofix(sent_biofix, last if not trim_end else today)
    read_from = min(first, biofix) if biofix is not None else first
    return read_from, first, last, trim_end, biofix


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
    biofix: str | None = None,
    targets: str | None = None,
    projection: str | None = None,
) -> HttpResponse:
    """One row per point and day: `date`, `kind`, the minimum and maximum temperature, `temperature_estimated` (the
    day's degree days use estimated temperatures), and for each setting `dd_<setting>` (that day's) and
    `dd_<setting>_cum` (the running total from `biofix`, default `start`). Settings: `dd=sine_48_86,modified_50_86,
    average_43` (method_base[_upper], in the request's units), or `base`, `upper` and `method` (sine, average,
    modified) for one. Defaults: January 1 through the forecast. `targets=1400,2000` (degree days in the request's
    units): when each setting's running total reaches each, in `meta.summary.targets`. `projection=true` carries
    the series past the forecast to `end` (default December 31) on each earlier archive year (D63), as
    `GET /models/{id}/run` does: P50 with `_p10` and `_p90` columns, or `projection=years` for each year's."""
    warnings: list[str] = []
    found_settings = settings_from(request, dd, output.units, warnings)
    goals = _targets(targets, output.units)
    mode = projection_mode(projection)
    read_from, first, last, trim_end, fixed = dd_window(when, options, biofix)
    if mode and when.end is None and when.date is None:
        last, trim_end = date(first.year, 12, 31), False
    check_size((last - read_from).days + 1, len(where.locations()), MAX_DAYS, "days")
    now = clock.now()
    computed = _computed(where, first, last, found_settings, fixed or first, options, output)
    computed |= {"targets": goals or None, "projection": mode}
    years = archive_years(settings.DATA_DIR) if mode else []
    stamp_from = min([read_from, *(date(y, 1, 1) for y in years if y < read_from.year)])
    etag = answer_etag(request, computed, points.stamp(where.locations(), stamp_from, last, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, read_from, last, options)
    found, read_warnings, sources, corrections = read_days(where, read_from, last, TEMPERATURES, options, trim_end, now)
    warnings += read_warnings
    skip = (first - read_from).days
    start_at = max(0, ((fixed or first) - read_from).days)
    if fixed is not None and fixed > last:
        warnings.append(
            f"The biofix ({day_text(fixed)}) is after the last day asked for ({day_text(last)}), so there are no "
            "running totals."
        )
    columns: dict[str, list] = {}
    reached_targets: list[dict] = []
    projections: list[dict] = []

    def add(name: str, values) -> None:
        columns.setdefault(name, []).extend(list(values))

    for k, (days, n) in enumerate(found):
        lat, lng = where.locations()[k]
        tmin = np.asarray(days.values["air_temperature_min"][:n], dtype=float)[:, None]
        tmax = np.asarray(days.values["air_temperature_max"][:n], dtype=float)[:, None]
        kinds, labels, cut = list(days.kinds[:n]), [None], n
        if mode:
            tmin, tmax, kinds, labels, cut, info, note = _project(days, n, lat, lng, last, years)
            projections.append({"point": k, **info})
            warnings += [note] if note and note not in warnings else []
        lo_f, hi_f, estimated, usable = temperatures_of(tmin, tmax, options.gaps)
        dds = {s.name: degree_days(s, lo_f, hi_f) for s in found_settings}
        totals = {name: running(values, usable, start_at) for name, values in dds.items()}
        rows = len(kinds)
        for target_f, shown_target in goals:
            for s in found_settings:
                days_hit = first_days(
                    days.dates[:cut] + _projected_dates(days.dates, cut, rows),
                    [totals[s.name][:, j] >= target_f for j in range(totals[s.name].shape[1])],
                )
                hit = reached("target", s.name, days_hit)
                reached_targets.append(
                    {"point": k, "setting": s.name, "target": shown_target, "reached": hit.reached, "of": hit.of}
                    | {"p10": hit.p10, "p50": hit.p50, "p90": hit.p90}
                )
        dates = days.dates[:cut] + _projected_dates(days.dates, cut, rows)
        shown = slice(skip, rows)
        temps = {"air_temperature_min": tmin, "air_temperature_max": tmax}
        sums = {}
        for s in found_settings:  # each setting's day, then its running total
            sums[f"dd_{s.name}"] = np.where(usable, dds[s.name], np.nan)
            sums[f"dd_{s.name}_cum"] = totals[s.name]
        before = np.arange(rows) < cut
        if mode == "band" and labels != [None]:  # projected: the line, P50, and the band
            add("point", [k] * (rows - skip))
            add("date", dates[shown])
            add("kind", kinds[shown])
            for group in (temps, sums):
                for name, values in group.items():
                    found_spread = spread([values[:, j] for j in range(values.shape[1])])
                    add(name, np.where(before, values[:, 0], found_spread.p50)[shown])
                    for suffix, side in (("p10", found_spread.p10), ("p90", found_spread.p90)):
                        add(f"{name}_{suffix}", np.where(before, np.nan, side)[shown])
                if group is temps:
                    add(
                        "temperature_estimated", [bool(estimated[d, 0]) if d < cut else None for d in range(skip, rows)]
                    )
            years_with = np.isfinite(tmin).sum(axis=1)
            add("projection_years", [int(years_with[d]) if d >= cut else None for d in range(skip, rows)])
        else:
            for j, year in enumerate(labels):
                add("point", [k] * (rows - skip))
                if mode == "years":
                    add("year", [year] * (rows - skip))
                add("date", dates[shown])
                add("kind", kinds[shown])
                for name, values in temps.items():
                    add(name, values[shown, j])
                add("temperature_estimated", estimated[shown, j].tolist())
                for name, values in sums.items():
                    add(name, values[shown, j])
    table = []
    for name, values in columns.items():
        base_name = name.removesuffix("_p10").removesuffix("_p90")
        if name == "point" and where.points is None:
            continue
        if base_name in TEMPERATURES:
            column = catalog_column(base_name, values)
            table.append(
                Column(
                    name=name,
                    values=values,
                    unit=column.unit,
                    step=column.step,
                    variable=column.variable,
                    summarize=name == base_name,
                )
            )
        elif base_name.startswith("dd_"):
            table.append(Column(name=name, values=values, unit="degF_day", step=DD_STEP, summarize=name == base_name))
        else:
            table.append(Column(name=name, values=values))
    if found and trim_end:
        computed["end"] = max((days.dates[n - 1] for days, n in found if n), default=last)
    summary = {
        **day_counts([(days, n) for days, n in found]),
        "days_estimated": sum(v for v in columns.get("temperature_estimated", []) if v),
        "corrections": corrections,
    }
    if goals:
        summary["targets"] = reached_targets
    if mode:
        summary["projection"] = projections if where.points is not None else (projections[0] if projections else None)
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


def _targets(raw: str | None, units: str) -> list[tuple[float, float]]:
    """(°F·d, as given) per target: degree days in the request's units."""
    if not raw:
        return []
    found = []
    for part in raw.split(","):
        try:
            value = float(part)
        except ValueError:
            raise ApiError(
                "invalid",
                "Give targets as degree-day totals separated by commas, such as targets=1400,2000.",
                "targets",
            ) from None
        if value <= 0:
            raise ApiError("out_of_range", f"The target {value:g} must be above 0.", "targets")
        found.append((value * 1.8 if units == "metric" else value, value))
    return found


def _projected_dates(dates: list[date], cut: int, rows: int) -> list[date]:
    start = dates[cut - 1] + timedelta(days=1) if cut else dates[0]
    return [start + timedelta(days=d) for d in range(rows - cut)]


def _project(days, n: int, lat: float, lng: float, last: date, years: list[int]):
    """The point's min and max, (days × years) with each earlier year's after the series' last day with data."""
    tmin = np.asarray(days.values["air_temperature_min"][:n], dtype=float)
    tmax = np.asarray(days.values["air_temperature_max"][:n], dtype=float)
    kinds = list(days.kinds[:n])
    begins = projection.projection_start(days.dates[:n], kinds)
    plain = (tmin[:, None], tmax[:, None], kinds, [None], n)
    if begins is None or begins > last:
        return (
            *plain,
            {"start": None, "years": []},
            f"The weather data runs through {day_text(last)}, the last day asked for, so there's nothing to project.",
        )
    cell = NDFD.cell_of(lat, lng)
    if cell is None or not points.from_archive(lat, lng, days.dates[0], begins - timedelta(days=1)):
        return *plain, {"start": None, "years": []}, NO_PROJECTION
    cut = (begins - days.dates[0]).days
    found = projection.build(
        begins, last, [y for y in years if y < last.year], TEMPERATURES, past_reader(settings.DATA_DIR, *cell)
    )
    if not found.years:
        return *plain, {"start": begins, "years": []}, "no earlier years in the archive to project with"
    values, all_kinds = projection.stacked(
        {"air_temperature_min": tmin[:cut], "air_temperature_max": tmax[:cut]}, kinds[:cut], found
    )
    note = (
        f"The archive has one earlier year ({found.years[0]}), so the projection follows that year alone, with no "
        "range."
        if len(found.years) == 1
        else None
    )
    return (
        values["air_temperature_min"],
        values["air_temperature_max"],
        all_kinds,
        found.years,
        cut,
        {"start": begins, "years": found.years},
        note,
    )


def temperatures_of(tmin: np.ndarray, tmax: np.ndarray, gaps: str):
    """(min °F, max °F, estimated, usable) from min and max in °C (days, or days × scenarios), each day's pair kept
    only where both are known, then gaps bridged unless `gaps=missing`."""
    known = np.isfinite(tmin) & np.isfinite(tmax)
    lo, hi = np.where(known, tmin, np.nan), np.where(known, tmax, np.nan)
    if gaps == "estimate":
        lo, _ = fill_short_gaps(lo, MAX_GAP_DAYS)
        hi, _ = fill_short_gaps(hi, MAX_GAP_DAYS)
    usable = np.isfinite(lo) & np.isfinite(hi)
    return lo * 1.8 + 32, hi * 1.8 + 32, usable & ~known, usable


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
    biofix: str | None = None,
) -> HttpResponse:
    """One row per point and setting: the total from `biofix` (default `start`) to `end`, and its estimated,
    missing and forecast days. What a daily report across many places and settings needs in one request
    (`points=` up to 50, `dd=` several). Defaults: January 1 through the forecast (to today with `forecast=false`)."""
    warnings: list[str] = []
    found_settings = settings_from(request, dd, output.units, warnings)
    read_from, first, last, trim_end, fixed = dd_window(when, options, biofix)
    check_size((last - read_from).days + 1, len(where.locations()), MAX_DAYS, "days")
    now = clock.now()
    computed = _computed(where, first, last, found_settings, fixed or first, options, output)
    etag = answer_etag(request, computed, points.stamp(where.locations(), read_from, last, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, read_from, last, options)
    found, read_warnings, sources, corrections = read_days(where, read_from, last, TEMPERATURES, options, trim_end, now)
    warnings += read_warnings
    begin = ((fixed or first) - read_from).days
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
            raise ApiError(
                "invalid",
                "Give thresholds as temperatures separated by commas, such as thresholds=32,28,24.",
                "thresholds",
            ) from None
        if not given:
            raise ApiError(
                "missing",
                "The thresholds list is empty. Give one or more temperatures separated by commas, "
                "such as thresholds=32,28.",
                "thresholds",
            )
    limits_f = [temperature_threshold(t, output.units, FREEZE, "thresholds", warnings) for t in given]
    today = clock.now().date()
    trim_end = when.end is None and when.date is None and options.forecast
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if trim_end else today)
    check_size((last - first).days + 1, len(where.locations()), MAX_DAYS, "days")
    now = clock.now()
    computed = {**where.echo(), "start": first, "end": last, "thresholds": given, "forecast": options.forecast}
    computed |= {"threshold_units": "°C" if output.units == "metric" else "°F", "units": output.units}
    computed |= options.echo()
    etag = answer_etag(request, computed, points.stamp(where.locations(), first, last, now))
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = located(where, first, last, options)
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
        **options.echo(),
    }
