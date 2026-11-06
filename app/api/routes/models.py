"""Models at points (docs/api.md, "Models"; PLAN.md Phase 5 D, D64): a model's three layers at a point through the
forecast, from our weather.

One row per day (and option set, with `option_set` indexing `meta.summary.option_sets`): `date`, `kind`, the model's
inputs as read (missing where missing, D45) with `<input>_estimated` where its gaps were filled, the outputs, and the
risk as `risk_level` (an index into the spec's levels), `risk_label` and, for a continuous risk (insects, D36),
`risk_value`. A disease gated by crop stage (D33) adds `susceptibility` only when a planting date is given; a model with
a season adds `in_season`. Insects' action windows go in `meta.summary.windows`.

Response shapes for model runs stay provisional until Phase 6's frontend uses them (D64)."""

import itertools
import json
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Field, Query, Router, Schema

from agdata import seasonal, series
from agdata import units as agunits
from agdata.point import hourly_sources
from agdata.projection import PROJECTION
from agdata.series import FORECAST, PARTIAL, DailySeries, Forecast, archive_years, days_needed, runs_at_point, sliced
from agdata.timezones import zone_at
from agmodels import seasons
from agmodels.crops import MARGIN, NOT_SUSCEPTIBLE, SUSCEPTIBLE
from agmodels.registry import all_models
from agmodels.runner import ModelRun, default_biofix
from agmodels.scenarios import milestones, spread
from agmodels.seasons import Season
from agmodels.spec import Model
from api import clock, points, runs, stations
from api.envelope import SYSTEMS, Column, Result, catalog_column, etag_for, not_modified, respond, table
from api.errors import ApiError, day_text
from api.locations import describe
from api.params import DaysQuery, OutputQuery, PointsQuery, SeriesQuery
from api.routes.weather import FORECAST_DAYS, MAX_DAYS, check_size, located
from api.schemas import TableResponse, responses
from ops.points import models_at_point, projected_at_point

router = Router(tags=["Models"])


class EvaluateBody(Schema):
    inputs: dict[str, float | list[float]] = Field(
        default_factory=dict,
        description="The model's inputs by name (`/models/{model_id}` lists them under `explorer`), in the request's "
        "units. Each is a number, or a list of numbers to try in turn; several lists give a row for every combination. "
        "Inputs you leave out take their usual values.",
    )


MAX_RUNS = 200  # model runs (models × option sets) per request
MAX_EVALUATIONS = 10_000  # rows of POST /models/{id}/evaluate

NO_PROJECTION = (
    "We can project only within our area and the years our records cover, so the series ends with the forecast."
)
# The runner's reasons for a run without outputs (`ModelRun.reason`, kept as they are in /risk's `reason`), as
# warnings say them
REASONS = {
    "outside the model's region": "This location is outside the area the model was developed for, so it gives no "
    "output here.",
    "biofix after the series": "The model starts at its biofix, which comes after these dates, so it has no output "
    "yet.",
    "biofix not in the series": "The model starts at its biofix, which comes before the weather read, so it has no "
    "output. Choose a start date on or before the biofix.",
}


def reason_text(reason: str) -> str:
    """A run's reason for no outputs as a sentence (a crop stage not reached says which)."""
    if reason in REASONS:
        return REASONS[reason]
    if reason.endswith("isn't reached in the series"):
        stage = reason.removesuffix(" isn't reached in the series")
        return f"The crop hasn't reached {stage}, where the model starts, by the last day, so it has no output yet."
    return f"The model has no output: {reason}."


def too_many_runs(count: int) -> str:
    return (
        f"This request asks for {count:,} model runs (models times their option sets); a request can include up to "
        f"{MAX_RUNS}. Ask for fewer models or options."
    )


SUSCEPTIBILITY = {NOT_SUSCEPTIBLE: "not susceptible", MARGIN: "margin", SUSCEPTIBLE: "susceptible"}


@router.get("/models/{model_id}/run", response=responses(TableResponse), summary="A model at a point")
def run(
    request: HttpRequest,
    model_id: str,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    biofix: date | None = None,
    planting_date: str | None = None,
    projection: str | None = None,
    season: str | None = None,
) -> HttpResponse:
    """The model at one point from `start` to `end` (default: from its biofix, or January 1, through the forecast;
    a seasonal product's current season, or `season=2025-26`, D68).
    `projection=true` carries it past the forecast to `end` (default: the season's end) once per earlier archive year
    (D63): projected days have kind `projection`, each number column their P50, with `<name>_p10` and `<name>_p90`
    beside it and `projection_years`; `projection=years` gives each year's path instead (a `year` column). When
    stages, risk levels and action windows come is in `meta.summary.projection.milestones`.
    `planting_date` (YYYY-MM-DD, or `early`, `mid`, `late` for the point's typical dates, or `all`) runs the crop's
    stages for a disease's susceptible window and a stage biofix; without it there's no window. The model's options
    and its crop model's are plain parameters (`GET /models/{id}` lists them); `all` runs every choice."""
    m = runs.model_or_404(model_id)
    lat, lng = _one_point(where)
    now = clock.now()
    today = now.date()
    planting_season = (when.date or when.start or when.end or today).year
    the_plan = runs.plan(m, request.GET, lat, lng, planting_season, biofix=biofix, planting=planting_date)
    mode = projection_mode(projection)
    trim_end = when.end is None and when.date is None
    default_end = today + timedelta(days=FORECAST_DAYS) if options.forecast else today
    first, last = _span(when, m, the_plan, default_end, today)
    the_season = None
    if m.SPEC.seasonal is not None:
        first, last, the_season = _season_days(m.SPEC, when, season, first, last, default_end, today)
    elif season is not None:
        raise ApiError(
            "not_applicable",
            f"{m.SPEC.name} isn't counted by season, so it takes no season. Give dates instead.",
            "season",
        )
    if mode and trim_end:
        last, trim_end = _season_end(m.SPEC, first), False
    check_size((last - first).days + 1, len(the_plan.runs), MAX_DAYS, "days")
    computed = {
        **where.echo(),
        **the_plan.request,
        "start": first,
        "end": last,
        "forecast": options.forecast,
        "projection": mode,
        "units": output.units,
        **({"season": the_season.name} if the_season is not None else {}),
    }
    etag, unchanged, needed = _revalidate(
        request, [the_plan], computed, lat, lng, first, last, now, projecting=bool(mode)
    )
    if unchanged is not None:
        return unchanged
    location = located(where, needed, last)[0]
    found, notes = _projected([the_plan], lat, lng, first, last, now, mode) if mode else (None, [])
    if found is not None:
        results = found[0].results
        table, summary, warnings = _table(
            m, results, len(results[0].dates), labels=found[0].labels, bands=found[0].bands
        )
        summary["projection"] = found[0].summary
    else:
        results = _execute([the_plan], lat, lng, first, last, now)[0]
        kept = max(points.keep(r.kinds, options.forecast, trim_end) for r in results)
        table, summary, warnings = _table(m, results, kept, labels=_labels(results))
    warnings = [*notes, *warnings]
    if trim_end and found is None and results and kept:
        computed["end"] = results[0].dates[kept - 1]
    if results[0].biofix is not None and len(results) == 1:
        computed["biofix"] = results[0].biofix
    if the_plan.option_sets:
        summary["option_sets"] = the_plan.option_sets
    summary["corrections"] = list(results[0].corrections)
    if the_season is not None:
        observed = series.last_observed(settings.DATA_DIR, now)
        observed_day = series.last_closed_day(observed) if observed is not None else first
        summary["season"] = seasonal.describe(settings.DATA_DIR, m.SPEC, the_season, computed["end"], observed_day)
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            location=location,
            summary=summary,
            sources=list(results[0].sources),
            warnings=[*the_plan.warnings, *warnings],
            filename=f"agweather-{m.SPEC.id}-{first}-{computed['end']}",
            etag=etag,
        ),
    )


@router.get("/models/run", summary="Several models at a point")
def run_several(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    options: Query[SeriesQuery],
    output: Query[OutputQuery],
    models: str = "all",
    planting_date: str | None = None,
    projection: str | None = None,
) -> HttpResponse:
    """Several models (`models=a,b`, or `all`) at one point on one read of the weather (and with `projection`, as
    `GET /models/{id}/run` takes it, to `end`, default December 31): `data` holds each model's
    answer under its id, with its own `meta` (`request`, `units`, `summary`, `warnings`) and `data`, as
    `GET /models/{id}/run` gives it (D64); the top-level `meta` has what they share (location, sources). Options are
    plain parameters and apply to every model that has them; `planting_date` applies to every model with a crop.
    Default start: January 1. JSON only: several tables don't make one CSV."""
    chosen = _models(models)
    lat, lng = _one_point(where)
    now = clock.now()
    today = now.date()
    season = (when.date or when.start or when.end or today).year
    plans = [
        runs.plan(m, request.GET, lat, lng, season, biofix=None, planting=planting_date, lenient=True) for m in chosen
    ]
    mode = projection_mode(projection)
    trim_end = when.end is None and when.date is None
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if options.forecast else today)
    if mode and trim_end:
        last, trim_end = max(last, date(first.year, 12, 31)), False
    total = sum(len(p.runs) for p in plans)
    if total > MAX_RUNS:
        raise ApiError("too_many", too_many_runs(total), "models")
    check_size((last - first).days + 1, total, MAX_DAYS, "days")
    computed = {
        **where.echo(),
        "models": [m.SPEC.id for m in chosen],
        "planting_date": planting_date,
        "start": first,
        "end": last,
        "forecast": options.forecast,
        "projection": mode,
        "units": output.units,
    }
    etag, unchanged, needed = _revalidate(request, plans, computed, lat, lng, first, last, now, projecting=bool(mode))
    if unchanged is not None:
        return unchanged
    location = located(where, needed, last)[0]
    found, notes = _projected(plans, lat, lng, first, last, now, mode) if mode else (None, [])
    if found is not None:
        grouped = [f.results for f in found]
        answers = _nested(request, plans, grouped, max(len(r.dates) for rs in grouped for r in rs), projected=found)
    else:
        grouped = _execute(plans, lat, lng, first, last, now)
        kept = max(points.keep(r.kinds, options.forecast, trim_end) for results in grouped for r in results)
        if trim_end and kept:
            computed["end"] = grouped[0][0].dates[kept - 1]
        answers = _nested(request, plans, grouped, kept)
    some = grouped[0][0]
    return respond(
        request,
        Result(
            request=computed,
            data=answers,
            location=location,
            summary={"corrections": list(some.corrections)},
            sources=list(some.sources),
            warnings=notes,
            etag=etag,
        ),
    )


@router.get("/risk", response=responses(TableResponse), summary="Every model's risk at a point on a day")
def risk(
    request: HttpRequest,
    where: Query[PointsQuery],
    output: Query[OutputQuery],
    date: date | None = None,
    models: str | None = None,
    planting_date: str | None = None,
    projection: str | None = None,
) -> HttpResponse:
    """One row per model with a risk layer: `model`, `name`, `group`, `version`, the day's `kind`, `risk_level`,
    `risk_label`, `risk_value` (continuous risk), `susceptibility` (with a planting date), `in_season` and `reason`
    (why there's no risk). `date` defaults to today. Without `models`, only those in season and in their region; with
    it (`models=a,b` or `all`), every one asked. The Crop Risk Tool's dashboard and the alerts' query. With
    `projection=true`, a `date` past the forecast takes each model's P50 across the archive's earlier years (D63),
    with `projection_years` saying how many."""
    lat, lng = _one_point(where)
    now = clock.now()
    day = date or now.date()
    asked = models is not None
    chosen = [m for m in _models(models or "all") if m.SPEC.risk is not None]
    plans = [
        runs.plan(m, request.GET, lat, lng, day.year, biofix=None, planting=planting_date, lenient=True) for m in chosen
    ]
    if sum(len(p.runs) for p in plans) > MAX_RUNS:
        raise ApiError("too_many", too_many_runs(sum(len(p.runs) for p in plans)), "models")
    computed = {**where.echo(), "date": day, "models": [m.SPEC.id for m in chosen] if asked else "in season"}
    mode = projection_mode(projection)
    computed |= {"planting_date": planting_date, "units": output.units, "projection": mode and "band"}
    etag, unchanged, needed = _revalidate(request, plans, computed, lat, lng, day, day, now, projecting=bool(mode))
    if unchanged is not None:
        return unchanged
    location = located(where, needed, day)[0]
    found, notes = _projected(plans, lat, lng, day, day, now, "band") if mode else (None, [])
    projected_years = [None] * len(plans)
    if found is not None:
        grouped = [f.results for f in found]
        projected_years = [f.bands for f in found]
    else:
        grouped = _execute(plans, lat, lng, day, day, now)
    rows: dict[str, list[Any]] = {
        name: []
        for name in (
            "model",
            "option_set",
            "name",
            "group",
            "version",
            "kind",
            "risk_level",
            "risk_label",
            "risk_value",
            "susceptibility",
            "in_season",
            "reason",
            "projection_years",
        )
    }
    for the_plan, results, bands in zip(plans, grouped, projected_years, strict=True):
        spec = the_plan.model.SPEC
        assert spec.risk is not None
        for k, r in enumerate(results):
            years_behind = int(bands[k].years[0]) if bands and bands[k].years.size and bands[k].years[0] > 0 else None
            in_season = None if r.in_season is None else bool(r.in_season[0])
            if not asked and (in_season is False or r.reason == "outside the model's region"):
                continue
            level = None if r.level is None or r.level[0] != r.level[0] else int(r.level[0])
            gate = None if r.susceptibility is None else r.susceptibility[0]
            rows["model"].append(spec.id)
            rows["option_set"].append(k if len(results) > 1 else None)
            rows["name"].append(spec.name)
            rows["group"].append(spec.group)
            rows["version"].append(spec.version)
            rows["kind"].append(r.kinds[0])
            rows["risk_level"].append(level)
            rows["risk_label"].append(None if level is None else spec.risk.levels[level])
            continuous = spec.risk.thresholds and r.risk is not None
            rows["risk_value"].append(float(r.risk[0]) if continuous and r.risk is not None else float("nan"))
            rows["susceptibility"].append(None if gate is None or gate != gate else SUSCEPTIBILITY.get(float(gate)))
            rows["in_season"].append(in_season)
            rows["reason"].append(r.reason)
            rows["projection_years"].append(years_behind)
    columns = [
        Column(name=name, values=values, unit="index" if name == "risk_value" else None)
        for name, values in rows.items()
    ]
    some = grouped[0][0] if grouped and grouped[0] else None
    sets = {p.model.SPEC.id: p.option_sets for p in plans if p.option_sets}
    return respond(
        request,
        Result(
            request=computed,
            columns=columns,
            location=location,
            summary={"models": len(rows["model"]), **({"option_sets": sets} if sets else {})},
            sources=list(some.sources) if some else [],
            warnings=[*notes, *sorted({w for p in plans for w in p.warnings})],
            filename=f"agweather-risk-{day}",
            etag=etag,
        ),
    )


@router.post("/models/{model_id}/evaluate", response=responses(TableResponse), summary="A model's core at values")
def evaluate(request: HttpRequest, model_id: str, body: EvaluateBody, output: Query[OutputQuery]) -> HttpResponse:
    """The model's core at single values of its explorer inputs (the model page's interactive chart, PLAN.md Phase 3
    A), from the same code as its runs: one row per combination, the inputs and what `explore` gives. Values outside
    an input's usual range run, with a warning."""
    m = runs.model_or_404(model_id)
    spec = m.SPEC
    explorer = {e.name: e for e in spec.explorer}
    unknown = sorted(set(body.inputs) - set(explorer))
    if unknown:
        raise ApiError(
            "unknown_input",
            f"{spec.name} has no input named {', '.join(unknown)}. Its inputs are {', '.join(explorer)}.",
            unknown[0],
        )
    system = SYSTEMS[output.units]
    warnings: list[str] = []
    given: dict[str, list[float]] = {}
    echo: dict[str, float | list[float]] = {}
    for name, e in explorer.items():
        raw = body.inputs.get(name)
        shown = agunits.display_unit(e.unit, system)
        if raw is None:
            values = [float(agunits.convert(float(e.default), e.unit, shown))]
        else:
            values = [float(v) for v in raw] if isinstance(raw, list) else [float(raw)]
        if not values or not all(np.isfinite(v) for v in values):
            raise ApiError("invalid", f"{name} must be a number, or a list of numbers.", name)
        stored = [float(agunits.convert(v, shown, e.unit)) for v in values]
        outside = [v for v, x in zip(values, stored, strict=True) if not e.minimum <= x <= e.maximum]
        if outside:
            lo, hi = (float(agunits.convert(b, e.unit, shown)) for b in (e.minimum, e.maximum))
            label = agunits.unit(shown).label
            warnings.append(f"{name} {outside[0]:g} is outside its usual {lo:g}–{hi:g} {label}".rstrip())
        given[name] = stored
        echo[name] = values if isinstance(raw, list) else values[0]
    count = 1
    for values in given.values():
        count *= len(values)
    if count > MAX_EVALUATIONS:
        raise ApiError(
            "too_large",
            f"This request asks for {count:,} combinations of inputs; a request can evaluate up to "
            f"{MAX_EVALUATIONS:,}. "
            "Give fewer values.",
            "inputs",
        )
    declared = {q.name: q for q in (*spec.outputs, *spec.explorer_outputs)}
    rows: dict[str, list[float]] = {name: [] for name in given}
    for combo in itertools.product(*given.values()):
        values = dict(zip(given, combo, strict=True))
        try:
            found = m.explore(**values)
        except ValueError as error:
            raise ApiError("invalid", str(error), "inputs") from None
        for name, v in values.items():
            rows[name].append(v)
        for name, v in found.items():
            rows.setdefault(name, []).append(v)
    columns = [Column(name=name, values=rows[name], unit=explorer[name].unit) for name in given]
    columns += [
        Column(name=name, values=values, unit=declared[name].unit if name in declared else None)
        for name, values in rows.items()
        if name not in given
    ]
    return respond(
        request,
        Result(
            request={"model": spec.id, "version": spec.version, "inputs": echo, "units": output.units},
            columns=columns,
            warnings=warnings,
            filename=f"agweather-{spec.id}-evaluate",
        ),
    )


# --- Runs on your own weather (D58) -----------------------------------------------------------------------------

POST_FIELDS = ("lat", "lng", "units", "start", "end", "fill", "extend", "models", "biofix", "planting_date")


@router.post("/models/{model_id}/run", response=responses(TableResponse), summary="A model on your weather")
def run_posted(request: HttpRequest, model_id: str) -> HttpResponse:
    """The model on weather you send (`api.stations`: hourly and/or daily, JSON or CSV), as `GET /models/{id}/run`
    gives it on ours. JSON: `{"location": {"lat", "lng"}, "units", "input_units", "hourly", "daily", "start",
    "end", "options", "fill", "extend"}`; CSV: the body is the hourly or daily table and the rest are query
    parameters. `kind` per day: provided, estimated (a gap the model's inputs bridged), grid (`fill=grid`: our
    archive at the cell), forecast (`extend=forecast`). Nothing sent is stored."""
    return _run_posted(request, [runs.model_or_404(model_id)], single=True)


@router.post("/models/run", summary="Several models on your weather")
def run_posted_several(request: HttpRequest) -> HttpResponse:
    """Several models (`"models": ["tar-spot", …]` or `"all"`) on weather you send, shaped as `GET /models/run`."""
    body, _ = _posted(request)
    raw = body.get("models", "all")
    return _run_posted(request, _models(raw if isinstance(raw, str) else ",".join(map(str, raw))), single=False)


def _posted(request: HttpRequest) -> tuple[dict[str, Any], dict[str, str]]:
    """(the weather and settings, the model options as strings) from a JSON body, or a CSV body and the query."""
    kind = request.content_type or ""
    if kind == "text/csv":
        body: dict[str, Any] = stations.parse_csv(request.body.decode("utf-8-sig"))
        query = {key: request.GET[key] for key in request.GET}
        body |= {key: query[key] for key in POST_FIELDS if key in query}
        if "lat" in query and "lng" in query:
            body["location"] = {"lat": query["lat"], "lng": query["lng"]}
        options = {key: value for key, value in query.items() if key not in POST_FIELDS}
        return body, options | {k: query[k] for k in ("biofix", "planting_date") if k in query}
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        raise ApiError(
            "invalid",
            "The request body isn't valid JSON. To send a CSV instead, set the Content-Type header to text/csv.",
            "body",
        ) from None
    if not isinstance(body, dict):
        raise ApiError(
            "invalid", "The request body must be a JSON object, with the weather under hourly or daily.", "body"
        )
    options = {str(k): str(v) for k, v in (body.get("options") or {}).items()}
    return body, options


def _date_field(body: dict[str, Any], name: str) -> date | None:
    value = body.get(name)
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ApiError("invalid", f"{name} must be a date, as YYYY-MM-DD.", name) from None


def _run_posted(request: HttpRequest, chosen: list[Model], single: bool) -> HttpResponse:
    body, options = _posted(request)
    location = body.get("location") or {}
    try:
        lat, lng = float(location["lat"]), float(location["lng"])
    except (KeyError, TypeError, ValueError):
        raise ApiError(
            "missing",
            "Give the location as lat and lng. It sets the local days and the region the models check.",
            "location",
        ) from None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ApiError(
            "out_of_range",
            f"The location ({lat:g}, {lng:g}) isn't valid: latitude runs from -90 to 90 and "
            "longitude from -180 to 180.",
            "location",
        )
    units = str(body.get("units") or request.GET.get("units") or "us")
    fill, extend = str(body.get("fill") or "none"), str(body.get("extend") or "none")
    if fill not in ("none", "grid"):
        raise ApiError("invalid", "Give fill as none or grid.", "fill")
    if extend not in ("none", "forecast"):
        raise ApiError("invalid", "Give extend as none or forecast.", "extend")
    overrides = {str(k): str(v) for k, v in (body.get("input_units") or {}).items()}
    overrides |= {k: request.GET[k] for k in request.GET if k in stations.HOURLY or k in stations.DAILY}
    station = stations.parse(body, units, overrides)
    zone = zone_at(lat, lng)
    sent = station.local_days(zone)
    if sent is None:
        raise ApiError(
            "missing", "The request has no weather values. Send hourly values, daily values or both.", "body"
        )
    now = clock.now()
    start, end = _date_field(body, "start"), _date_field(body, "end")
    first = start or sent[0]
    trim_end = end is None
    last = end or (now.date() + timedelta(days=FORECAST_DAYS) if extend == "forecast" else sent[1])
    if first > last:
        raise ApiError(
            "out_of_order",
            f"The start date ({day_text(first)}) is after the end date ({day_text(last)}). Choose a "
            "start date on or before "
            "the end date.",
            "start",
        )
    biofix = _date_field({"biofix": options.pop("biofix", None)}, "biofix")
    planting = options.pop("planting_date", None)
    plans = [
        runs.plan(m, options, lat, lng, first.year, biofix=biofix, planting=planting, lenient=not single)
        for m in chosen
    ]
    available = station.available()
    skipped: dict[str, str] = {}
    if fill != "grid":
        runnable = []
        for p in plans:
            lacking = [name for name in days_needed(p.runs, first)[1] if name not in available]
            if not lacking:
                runnable.append(p)
                continue
            message = _cannot_make(lacking)
            if single:
                raise ApiError("missing_inputs", message, "body")
            skipped[p.model.SPEC.id] = message
        if not runnable:
            raise ApiError(
                "missing_inputs",
                "None of the models asked for can run on the weather sent. Send the inputs they "
                "need, or add fill=grid to "
                "fill the rest from our data.",
                "body",
            )
        plans = runnable
    every = [r for p in plans for r in p.runs]
    if len(every) > MAX_RUNS:
        raise ApiError("too_many", too_many_runs(len(every)), "models")
    needed, names = days_needed(every, first)
    if (last - needed).days + 1 > MAX_DAYS:
        raise ApiError(
            "too_large",
            f"These models need {(last - needed).days + 1:,} days of weather; a request can cover up to {MAX_DAYS:,}. "
            "Choose a shorter period.",
            "start",
        )
    warnings = list(station.warnings)
    lacking = [name for name in names if name not in available]
    if lacking:
        warnings.append(f"{', '.join(lacking)} from our archive at the cell (fill=grid): the station didn't send them")
    days, sources = _station_days(station, zone, needed, last, names, lat, lng, now, fill, extend, sent[1])
    results = runs_at_point(
        lambda first_day, _last, wanted: sliced(days, first_day, wanted),
        lat,
        lng,
        every,
        first,
        last,
        planting_default=False,
    )
    for r in results:  # a provided day whose inputs the model bridged is estimated
        for k, kind in enumerate(r.kinds):
            if kind == "provided" and any(flags[k] for flags in r.estimated.values()):
                r.kinds[k] = "estimated"
    grouped, k = [], 0
    for p in plans:
        grouped.append(results[k : k + len(p.runs)])
        k += len(p.runs)
    kept = max(points.keep(r.kinds, True, trim_end) for r in results)
    kinds = [kind for r in results[:1] for kind in r.kinds[:kept]]
    counts = {f"days_{name}": kinds.count(name) for name in ("provided", "estimated", "grid", "forecast")}
    counts["days_missing"] = kinds.count(None)
    computed = {
        "lat": lat,
        "lng": lng,
        "units": units,
        "start": first,
        "end": results[0].dates[kept - 1] if kept else last,
        "fill": fill,
        "extend": extend,
        "sent": {
            "first_day": sent[0],
            "last_day": sent[1],
            "hourly": sorted(station.hourly),
            "daily": sorted(station.daily),
        },
    }
    if single:
        the_plan = plans[0]
        columns, summary, table_warnings = _table(the_plan.model, results, kept, labels=_labels(results))
        if the_plan.option_sets:
            summary["option_sets"] = the_plan.option_sets
        summary |= counts
        computed |= the_plan.request
        if len(results) == 1 and results[0].biofix is not None:
            computed["biofix"] = results[0].biofix
        return respond(
            request,
            Result(
                request=computed,
                columns=columns,
                location=describe(lat, lng),
                summary=summary,
                sources=sources,
                warnings=[*warnings, *the_plan.warnings, *table_warnings],
                filename=f"agweather-{the_plan.model.SPEC.id}-{first}",
                units=units,
            ),
        )
    computed["models"] = [m.SPEC.id for m in chosen]
    return respond(
        request,
        Result(
            request=computed,
            data=_nested(request, plans, grouped, kept, units=units),
            location=describe(lat, lng),
            summary={**counts, **({"skipped": skipped} if skipped else {})},
            sources=sources,
            warnings=warnings,
            units=units,
        ),
    )


def _cannot_make(lacking: list[str]) -> str:
    sources = hourly_sources()
    needs = "; ".join(f"{n} (hourly: {', '.join(sources.get(n, ())) or 'none'})" for n in lacking)
    return (
        f"We can't make {needs} from the weather sent. Send them, daily or hourly, or add fill=grid to fill them "
        "from our data."
    )


def _station_days(
    station, zone, first, last, names, lat, lng, now, fill, extend, last_sent
) -> tuple[DailySeries, list[str]]:
    """The days a POSTed run reads: the station's, with our archive's where `fill=grid` (kind grid) and our
    forecast after the station's last day with `extend=forecast` (grid for the archive's days, forecast after)."""
    n = (last - first).days + 1
    dates = [first + timedelta(days=k) for k in range(n)]
    values = station.daily_series(zone, first, last, names)
    kinds: list[str | None] = [
        "provided" if any(np.isfinite(values[name][k]) for name in names) else None for k in range(n)
    ]
    sources = ["provided"]
    if fill == "grid" or extend == "forecast":
        ours = points.days(lat, lng, first, last, names, now)
        used = False
        for k, day in enumerate(dates):
            theirs = ours.kinds[k]
            if theirs is None:
                continue
            ours_kind = "forecast" if theirs in (FORECAST, PARTIAL) else "grid"
            if kinds[k] == "provided":
                if fill != "grid":
                    continue
                gaps = [
                    name for name in names if not np.isfinite(values[name][k]) and np.isfinite(ours.values[name][k])
                ]
                for name in gaps:
                    values[name][k] = ours.values[name][k]
                if gaps:
                    kinds[k], used = "grid", True
            elif fill == "grid" or (extend == "forecast" and day > last_sent):
                for name in names:
                    values[name][k] = ours.values[name][k]
                kinds[k], used = ours_kind, True
        if used:
            sources += [s for s in ours.sources if s not in sources]
    return DailySeries(dates=dates, values=values, kinds=kinds, forecast=Forecast(path=None), zone=zone), sources


def _nested(
    request: HttpRequest,
    plans,
    grouped,
    kept: int,
    units: str | None = None,
    projected: "list[Projected] | None" = None,
) -> dict[str, Any]:
    """Each model's answer under its id: its `meta` (`request`, `units`, `summary`, `warnings`) and `data`."""
    answers = {}
    for k, (the_plan, results) in enumerate(zip(plans, grouped, strict=True)):
        if projected is not None:
            p = projected[k]
            columns, summary, warnings = _table(the_plan.model, results, kept, labels=p.labels, bands=p.bands)
            summary["projection"] = p.summary
        else:
            columns, summary, warnings = _table(the_plan.model, results, kept, labels=_labels(results))
        if the_plan.option_sets:
            summary["option_sets"] = the_plan.option_sets
        request_echo = {**the_plan.request}
        if len(results) == 1 and results[0].biofix is not None:
            request_echo["biofix"] = results[0].biofix
        found = table(request, columns, summary, units=units)
        answers[the_plan.model.SPEC.id] = {
            "meta": {
                "request": request_echo,
                "units": found["units"],
                "summary": found["summary"],
                "warnings": [*the_plan.warnings, *warnings],
            },
            "data": found["data"],
        }
    return answers


def _models(raw: str) -> list[Model]:
    if raw.strip() == runs.ALL:
        return list(all_models().values())
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not ids:
        raise ApiError("missing", "The models list is empty. Give model ids separated by commas, or all.", "models")
    unknown = [i for i in ids if i not in all_models()]
    if unknown:
        raise ApiError(
            "not_found",
            f"We don't have a model with the id {', '.join(unknown)}. GET /api/v2/models lists every model and its id.",
            "models",
        )
    return [all_models()[i] for i in dict.fromkeys(ids)]


def _one_point(where: PointsQuery) -> tuple[float, float]:
    if len(where.locations()) > 1:
        raise ApiError(
            "too_many",
            "This endpoint takes one location. Give lat and lng, or make one request per location.",
            "points",
        )
    return where.locations()[0]


def _revalidate(request, plans, computed, lat, lng, first, last, now, projecting: bool = False):
    """(ETag, a 304 if the client holds it, the first day read): before any read or run. A projection reads the
    archive's earlier years too, so their writes count."""
    needed, _ = days_needed([r for p in plans for r in p.runs], first)
    years = archive_years(settings.DATA_DIR) if projecting else []
    stamp = points.stamp([(lat, lng)], min([needed, *(date(y, 1, 1) for y in years if y < needed.year)]), last, now)
    etag = None if stamp is None else etag_for(request, computed, stamp)
    unchanged = None if etag is None else not_modified(request, etag)
    return etag, unchanged, needed


def _execute(plans: list[runs.Plan], lat: float, lng: float, first: date, last: date, now) -> list[list[ModelRun]]:
    """Every plan's runs on one read of the weather, split back per plan."""
    every = [r for p in plans for r in p.runs]
    results = models_at_point(lat, lng, every, first, last, now, planting_default=False)
    grouped, k = [], 0
    for p in plans:
        grouped.append(results[k : k + len(p.runs)])
        k += len(p.runs)
    return grouped


def _season_days(
    spec, when: DaysQuery, name: str | None, first: date, last: date, default_end: date, today: date
) -> tuple[date, date, Season | None]:
    """A seasonal product's days (D68): `season=` or, with no dates, the current season (its start through its end
    or the default end); dates as asked, in the season their last day falls in."""
    if name is not None and (when.date or when.start or when.end):
        raise ApiError("conflict", "Give either a season, or a date or range of dates, but not both.", "season")
    if name is None and (when.date or when.start or when.end):
        return first, last, seasons.season_of(spec, last)
    try:
        found = seasons.season_named(spec, name) if name is not None else seasons.current_season(spec, today)
    except ValueError as error:
        raise ApiError("invalid", str(error), "season") from None
    end = min(found.last, default_end)
    if end < found.first:
        raise ApiError(
            "not_yet", f"The {found.label} season hasn't started yet. Choose an earlier season.", "season", status=404
        )
    return found.first, end, found


def _span(when: DaysQuery, m: Model, the_plan: runs.Plan, default_end: date, today: date) -> tuple[date, date]:
    """(first, last) shown: as asked, else from the earliest run's biofix or planting (the spec's default biofix for
    this season if neither is given and it has come), else January 1."""
    if when.date is not None or when.start is not None:
        return when.span(default_end=default_end)
    last = when.end or default_end
    anchors = [d for r in the_plan.runs for d in (r.biofix, r.planting) if d is not None]
    if not anchors and m.SPEC.biofix is not None:
        typical = default_biofix(m.SPEC, date(last.year, 1, 1) if when.end else today)
        if typical is not None and typical <= last:
            anchors = [typical]
    first = min(anchors) if anchors else date(last.year, 1, 1)
    return min(first, last), last


@dataclass(kw_only=True)
class Band:
    """A projected run's spread: per number column, its P10 and P90 per day (NaN before the projection), and how
    many years each day has."""

    low: dict[str, np.ndarray]
    high: dict[str, np.ndarray]
    years: np.ndarray


def _labels(results: list[ModelRun]) -> list[dict[str, Any]] | None:
    return [{"option_set": k} for k in range(len(results))] if len(results) > 1 else None


def _table(
    m: Model,
    results: list[ModelRun],
    n: int,
    labels: list[dict[str, Any]] | None = None,
    bands: list[Band] | None = None,
) -> tuple[list[Column], dict, list[str]]:
    """One row per day of each run, in order: `labels[k]` adds columns naming run k (`option_set`, `year`), and
    `bands[k]` its P10 and P90 beside each number column (`projection=true`)."""
    spec = m.SPEC
    warnings: list[str] = []
    columns: dict[str, list[Any]] = {}

    def add(name: str, values) -> None:
        columns.setdefault(name, []).extend(list(values))

    def numbers(name: str, values: list[float], k: int, count: int) -> None:
        add(name, values)
        if bands is not None:
            for suffix, side in (("p10", bands[k].low), ("p90", bands[k].high)):
                add(f"{name}_{suffix}", _values(side.get(name), count))

    estimated = sorted({name for r in results for name in r.estimated})
    gated = any(r.susceptibility is not None for r in results)
    is_crop = spec.group == "crop"
    stages = [s.code for s in m.stages()] if is_crop else []  # type: ignore[attr-defined]
    windows: list[dict[str, Any]] = []
    for k, r in enumerate(results):
        rows = r.dates[:n]
        count = len(rows)
        label = labels[k] if labels else {}
        for key, value in label.items():
            add(key, [value] * count)
        add("date", rows)
        add("kind", r.kinds[:n])
        for q in spec.inputs:
            numbers(q.name, _values(r.inputs.get(q.name), count), k, count)
        for name in estimated:
            flags = r.estimated.get(name)
            add(f"{name}_estimated", [False] * count if flags is None else [bool(f) for f in flags[:n]])
        for q in spec.outputs:
            numbers(q.name, _values(r.outputs.get(q.name), count), k, count)
        if is_crop:
            stage = _values(r.outputs.get("stage"), count)
            add("stage_code", [stages[int(s)] if s == s and s >= 0 else None for s in stage])
        if spec.risk is not None:
            level = _values(r.level, count)
            add("risk_level", [None if v != v else int(v) for v in level])
            add("risk_label", [None if v != v else spec.risk.levels[int(v)] for v in level])
            if spec.risk.thresholds:
                numbers("risk_value", _values(r.risk, count), k, count)
        if gated:
            gate = _values(r.susceptibility, count)
            add("susceptibility", [SUSCEPTIBILITY.get(float(v)) if v == v else None for v in gate])
        if spec.season is not None:
            add("in_season", [None] * count if r.in_season is None else [bool(v) for v in r.in_season[:n]])
        if bands is not None:
            add("projection_years", [int(v) if v > 0 else None for v in _values(bands[k].years, count)])
        if r.reason:
            named = ", ".join(f"{key} {value}" for key, value in label.items())
            text = reason_text(r.reason)
            warnings.append(f"For {named}: {text[0].lower()}{text[1:]}" if named else text)
        if r.windows:
            windows.append(
                {
                    **label,
                    "windows": {
                        name: [[a.isoformat(), b.isoformat()] for a, b in periods]
                        for name, periods in r.windows.items()
                    },
                }
            )

    inputs = {q.name for q in spec.inputs}
    outputs = {q.name: q for q in spec.outputs}
    table: list[Column] = []
    for name, values in columns.items():
        base = name.removesuffix("_p10").removesuffix("_p90")
        summarize = base == name
        if base in inputs:
            v = catalog_column(base, values)
            table.append(
                Column(name=name, values=values, unit=v.unit, step=v.step, variable=v.variable, summarize=summarize)
            )
        elif base in outputs:
            table.append(Column(name=name, values=values, unit=outputs[base].unit, summarize=summarize))
        elif base == "risk_value":
            table.append(Column(name=name, values=values, unit="index"))
        else:
            table.append(Column(name=name, values=values))
    kinds = [kind for r in results for kind in r.kinds[:n]]
    summary: dict[str, Any] = {
        "days_returned": len(kinds),
        "days_forecast": sum(kind in (FORECAST, PARTIAL) for kind in kinds),
        "days_missing": sum(kind is None for kind in kinds),
        "estimated_by_input": {
            name: sum(int(np.sum(r.estimated[name][:n])) for r in results if name in r.estimated) for name in estimated
        },
    }
    if bands is not None:
        summary["days_projected"] = sum(kind == PROJECTION for kind in kinds)
    if windows:
        summary["windows"] = windows
    return table, summary, warnings


def _median(m: Model, runs: list[ModelRun], begins: date) -> tuple[ModelRun, Band]:
    """A run's scenarios as one: P50 per day (the line), with their P10 and P90 (the band) on projected days; a
    level, stage or susceptibility code is the P50 rounded down. Before `begins` every scenario is the same."""
    first = runs[0]
    k = min(max(0, (begins - first.dates[0]).days), len(first.dates)) if first.dates else 0  # the first projected row
    low: dict[str, np.ndarray] = {}
    high: dict[str, np.ndarray] = {}

    def middle(name: str, series: list[np.ndarray | None]) -> np.ndarray | None:
        if any(v is None for v in series):
            return None
        found = spread([np.asarray(v, dtype=float) for v in series if v is not None])
        p50 = found.p50.copy()
        p50[:k] = np.asarray(series[0], dtype=float)[:k]
        low[name] = np.where(np.arange(p50.size) >= k, found.p10, np.nan)
        high[name] = np.where(np.arange(p50.size) >= k, found.p90, np.nan)
        return p50

    def coded(series: list[np.ndarray | None]) -> np.ndarray | None:
        if any(v is None for v in series):
            return None
        found = spread([np.asarray(v, dtype=float) for v in series if v is not None]).p50
        return np.floor(found)

    inputs = {name: middle(name, [r.inputs.get(name) for r in runs]) for name in first.inputs}
    outputs = {name: middle(name, [r.outputs.get(name) for r in runs]) for name in first.outputs}
    if "stage" in outputs and outputs["stage"] is not None:
        outputs["stage"] = coded([r.outputs.get("stage") for r in runs])
    risk = middle("risk_value", [r.risk for r in runs]) if first.risk is not None else None
    years = spread([next(iter(r.outputs.values())) if r.outputs else np.full(len(first.dates), np.nan) for r in runs])
    biofixes = {r.biofix for r in runs}
    reasons = {r.reason for r in runs}
    merged = replace(
        first,
        inputs={name: v for name, v in inputs.items() if v is not None},
        outputs={name: v for name, v in outputs.items() if v is not None},
        risk=risk,
        level=coded([r.level for r in runs]),
        susceptibility=coded([r.susceptibility for r in runs]),
        biofix=first.biofix if len(biofixes) == 1 else None,
        reason=first.reason if len(reasons) == 1 else None,
        windows={},
    )
    counts = np.where(np.arange(len(first.dates)) >= k, years.count, 0)
    return merged, Band(low=low, high=high, years=counts)


# --- Projection (D63) ---------------------------------------------------------------------------------------------


@dataclass(kw_only=True)
class Projected:
    """One plan's runs ready for `_table`: rows, their labels and bands, and `meta.summary.projection`."""

    results: list[ModelRun]
    labels: list[dict[str, Any]] | None
    bands: list[Band] | None
    summary: dict[str, Any]


def projection_mode(raw: str | None) -> str | None:
    """None (off), "band" (P10/P50/P90) or "years" (each past year's path)."""
    if raw in (None, "", "false", "none"):
        return None
    if raw in ("true", "band"):
        return "band"
    if raw == "years":
        return "years"
    raise ApiError(
        "invalid",
        "Give projection as true, for the middle and range across past years, or years, for each year's path.",
        "projection",
    )


def _season_end(spec, first: date) -> date:
    """The last day of the season `first` falls in (the spec's, a crossing one in the next year), else December 31."""
    if spec.season is None:
        return date(first.year, 12, 31)
    month, day = (int(p) for p in spec.season[1].split("-"))
    end = date(first.year, month, day)
    return end if end >= first else date(first.year + 1, month, day)


def _projected(
    plans: list[runs.Plan], lat: float, lng: float, first: date, last: date, now, mode: str
) -> tuple[list[Projected] | None, list[str]]:
    """Each plan's runs carried past the forecast on the archive's earlier years, or None outside the archive."""
    every = [r for p in plans for r in p.runs]
    found = projected_at_point(lat, lng, every, first, last, now)
    if found is None:
        return None, [NO_PROJECTION]
    warnings = []
    if found.start is None:
        warnings.append(
            f"The weather data runs through {day_text(last)}, the last day asked for, so there's nothing to project."
        )
    elif not found.years:
        warnings.append("The archive has no earlier years to project with, so the series ends with the forecast.")
    elif len(found.years) == 1:
        warnings.append(
            f"The archive has one earlier year ({found.years[0]}), so the projection follows that year alone, with no "
            "range."
        )
    out, k = [], 0
    for p in plans:
        groups = found.runs[k : k + len(p.runs)]
        k += len(p.runs)
        sets = len(groups) > 1
        info: dict[str, Any] = {"mode": mode, "start": found.start, "years": found.years}
        if found.start is not None and found.years:
            reached = [[_milestone(r) for r in milestones(p.model, rs)] for rs in groups]
            info["milestones"] = reached if sets else reached[0]
        if mode == "band" and found.years and found.start is not None:
            pairs = [_median(p.model, rs, found.start) for rs in groups]
            out.append(
                Projected(
                    results=[a for a, _ in pairs],
                    labels=_labels([a for a, _ in pairs]),
                    bands=[b for _, b in pairs],
                    summary=info,
                )
            )
        else:
            results, labels = [], []
            for s_index, rs in enumerate(groups):
                for year, r in zip(found.years or [None], rs, strict=False):
                    results.append(r)
                    labels.append(
                        {**({"option_set": s_index} if sets else {}), **({"year": year} if found.years else {})}
                    )
            out.append(Projected(results=results, labels=labels if any(labels) else None, bands=None, summary=info))
    return out, warnings


def _milestone(r) -> dict[str, Any]:
    return {"what": r.what, "name": r.name, "reached": r.reached, "of": r.of, "p10": r.p10, "p50": r.p50, "p90": r.p90}


def _values(array, count: int) -> list[float]:
    """The first `count` values, or NaN where the run has none (no output: outside the region, not started)."""
    if array is None:
        return [float("nan")] * count
    values = np.asarray(array, dtype=float)
    if values.ndim == 0:
        return [float(values)] * count
    return values[:count].tolist() + [float("nan")] * max(0, count - values.shape[0])
