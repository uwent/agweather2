"""Models at points (docs/api.md, "Models"; PLAN.md Phase 5 D, D64): a model's three layers at a point through the
forecast, from our weather.

One row per day (and option set, with `option_set` indexing `meta.option_sets`): `date`, `kind`, the model's inputs
as read (missing where missing, D45) with `<input>_estimated` where its gaps were filled, the outputs, and the risk as
`risk_level` (an index into the spec's levels), `risk_label` and, for a continuous risk (insects, D36),
`risk_value`. A disease gated by crop stage (D33) adds `susceptibility` only when a planting date is given; a model
with a season adds `in_season`. Insects' action windows go in `meta.summary.windows`.

Response shapes for model runs stay provisional until Phase 6's frontend uses them (D64)."""

from datetime import date, timedelta
from typing import Any

import numpy as np
from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from agdata.series import FORECAST, PARTIAL, days_needed
from agmodels.crops import MARGIN, NOT_SUSCEPTIBLE, SUSCEPTIBLE
from agmodels.registry import all_models
from agmodels.runner import ModelRun, default_biofix
from agmodels.spec import Model
from api import clock, points, runs
from api.envelope import Column, Result, catalog_column, etag_for, not_modified, respond, table
from api.errors import ApiError
from api.params import DaysQuery, OutputQuery, PointsQuery, SeriesQuery
from api.routes.weather import FORECAST_DAYS, MAX_DAYS, check_size, located
from api.schemas import TableResponse, responses
from ops.points import models_at_point

router = Router(tags=["models"])

MAX_RUNS = 200  # model runs (models × option sets) per request

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
) -> HttpResponse:
    """The model at one point from `start` to `end` (default: from its biofix, or January 1, through the forecast).
    `planting_date` (YYYY-MM-DD, or `early`, `mid`, `late` for the point's typical dates, or `all`) runs the crop's
    stages for a disease's susceptible window and a stage biofix; without it there's no window. The model's options
    and its crop model's are plain parameters (`GET /models/{id}` lists them); `all` runs every choice."""
    m = runs.model_or_404(model_id)
    lat, lng = _one_point(where)
    now = clock.now()
    today = now.date()
    season = (when.date or when.start or when.end or today).year
    the_plan = runs.plan(m, request.GET, lat, lng, season, biofix=biofix, planting=planting_date)
    trim_end = when.end is None and when.date is None
    default_end = today + timedelta(days=FORECAST_DAYS) if options.forecast else today
    first, last = _span(when, m, the_plan, default_end, today)
    check_size((last - first).days + 1, len(the_plan.runs), MAX_DAYS, "days")
    computed = {
        **where.echo(),
        **the_plan.request,
        "start": first,
        "end": last,
        "forecast": options.forecast,
        "units": output.units,
    }
    etag, unchanged, needed = _revalidate(request, [the_plan], computed, lat, lng, first, last, now)
    if unchanged is not None:
        return unchanged
    location = located(where, needed, last)[0]
    results = _execute([the_plan], lat, lng, first, last, now)[0]
    kept = max(points.keep(r.kinds, options.forecast, trim_end) for r in results)
    table, summary, warnings = _table(m, results, kept, multiple=len(results) > 1)
    if trim_end and results and kept:
        computed["end"] = results[0].dates[kept - 1]
    if results[0].biofix is not None and len(results) == 1:
        computed["biofix"] = results[0].biofix
    if the_plan.option_sets:
        summary["option_sets"] = the_plan.option_sets
    summary["corrections"] = list(results[0].corrections)
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
) -> HttpResponse:
    """Several models (`models=a,b`, or `all`) at one point on one read of the weather: `data` holds each model's
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
    trim_end = when.end is None and when.date is None
    first, last = when.span(default_end=today + timedelta(days=FORECAST_DAYS) if options.forecast else today)
    total = sum(len(p.runs) for p in plans)
    if total > MAX_RUNS:
        raise ApiError("too_many", f"{total} model runs asked for; up to {MAX_RUNS} per request", "models")
    check_size((last - first).days + 1, total, MAX_DAYS, "days")
    computed = {
        **where.echo(),
        "models": [m.SPEC.id for m in chosen],
        "planting_date": planting_date,
        "start": first,
        "end": last,
        "forecast": options.forecast,
        "units": output.units,
    }
    etag, unchanged, needed = _revalidate(request, plans, computed, lat, lng, first, last, now)
    if unchanged is not None:
        return unchanged
    location = located(where, needed, last)[0]
    grouped = _execute(plans, lat, lng, first, last, now)
    kept = max(points.keep(r.kinds, options.forecast, trim_end) for results in grouped for r in results)
    if trim_end and kept:
        computed["end"] = grouped[0][0].dates[kept - 1]
    answers = {}
    for the_plan, results in zip(plans, grouped, strict=True):
        columns, summary, warnings = _table(the_plan.model, results, kept, multiple=len(results) > 1)
        if the_plan.option_sets:
            summary["option_sets"] = the_plan.option_sets
        request_echo = {**the_plan.request}
        if len(results) == 1 and results[0].biofix is not None:
            request_echo["biofix"] = results[0].biofix
        found = table(request, columns, summary)
        answers[the_plan.model.SPEC.id] = {
            "meta": {
                "request": request_echo,
                "units": found["units"],
                "summary": found["summary"],
                "warnings": [*the_plan.warnings, *warnings],
            },
            "data": found["data"],
        }
    some = grouped[0][0]
    return respond(
        request,
        Result(
            request=computed,
            data=answers,
            location=location,
            summary={"corrections": list(some.corrections)},
            sources=list(some.sources),
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
) -> HttpResponse:
    """One row per model with a risk layer: `model`, `name`, `group`, `version`, the day's `kind`, `risk_level`,
    `risk_label`, `risk_value` (continuous risk), `susceptibility` (with a planting date), `in_season` and `reason`
    (why there's no risk). `date` defaults to today. Without `models`, only those in season and in their region; with
    it (`models=a,b` or `all`), every one asked. The Crop Risk Tool's dashboard and the alerts' query."""
    lat, lng = _one_point(where)
    now = clock.now()
    day = date or now.date()
    asked = models is not None
    chosen = [m for m in _models(models or "all") if m.SPEC.risk is not None]
    plans = [
        runs.plan(m, request.GET, lat, lng, day.year, biofix=None, planting=planting_date, lenient=True) for m in chosen
    ]
    if sum(len(p.runs) for p in plans) > MAX_RUNS:
        raise ApiError("too_many", f"more than {MAX_RUNS} model runs asked for", "models")
    computed = {**where.echo(), "date": day, "models": [m.SPEC.id for m in chosen] if asked else "in season"}
    computed |= {"planting_date": planting_date, "units": output.units}
    etag, unchanged, needed = _revalidate(request, plans, computed, lat, lng, day, day, now)
    if unchanged is not None:
        return unchanged
    location = located(where, needed, day)[0]
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
        )
    }
    for the_plan, results in zip(plans, grouped, strict=True):
        spec = the_plan.model.SPEC
        assert spec.risk is not None
        for k, r in enumerate(results):
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
            warnings=sorted({w for p in plans for w in p.warnings}),
            filename=f"agweather-risk-{day}",
            etag=etag,
        ),
    )


def _models(raw: str) -> list[Model]:
    if raw.strip() == runs.ALL:
        return list(all_models().values())
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not ids:
        raise ApiError("missing", "models is empty: give model ids separated by commas, or all", "models")
    unknown = [i for i in ids if i not in all_models()]
    if unknown:
        raise ApiError("not_found", f"no model {', '.join(unknown)}; GET /api/v2/models lists them", "models")
    return [all_models()[i] for i in dict.fromkeys(ids)]


def _one_point(where: PointsQuery) -> tuple[float, float]:
    if len(where.locations()) > 1:
        raise ApiError("too_many", "one point per request", "points")
    return where.locations()[0]


def _revalidate(request, plans, computed, lat, lng, first, last, now):
    """(ETag, a 304 if the client holds it, the first day read): before any read or run."""
    needed, _ = days_needed([r for p in plans for r in p.runs], first)
    stamp = points.stamp([(lat, lng)], needed, last, now)
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


def _table(m: Model, results: list[ModelRun], n: int, multiple: bool) -> tuple[list[Column], dict, list[str]]:
    spec = m.SPEC
    warnings: list[str] = []
    columns: dict[str, list[Any]] = {}

    def add(name: str, values) -> None:
        columns.setdefault(name, []).extend(list(values))

    estimated = sorted({name for r in results for name in r.estimated})
    gated = any(r.susceptibility is not None for r in results)
    is_crop = spec.group == "crop"
    stages = [s.code for s in m.stages()] if is_crop else []  # type: ignore[attr-defined]
    windows: list[dict[str, Any]] = []
    for k, r in enumerate(results):
        rows = r.dates[:n]
        count = len(rows)
        if multiple:
            add("option_set", [k] * count)
        add("date", rows)
        add("kind", r.kinds[:n])
        for q in spec.inputs:
            add(q.name, _values(r.inputs.get(q.name), count))
        for name in estimated:
            flags = r.estimated.get(name)
            add(f"{name}_estimated", [False] * count if flags is None else [bool(f) for f in flags[:n]])
        for q in spec.outputs:
            add(q.name, _values(r.outputs.get(q.name), count))
        if is_crop:
            stage = _values(r.outputs.get("stage"), count)
            add("stage_code", [stages[int(s)] if s == s and s >= 0 else None for s in stage])
        if spec.risk is not None:
            level = _values(r.level, count)
            add("risk_level", [None if v != v else int(v) for v in level])
            add("risk_label", [None if v != v else spec.risk.levels[int(v)] for v in level])
            if spec.risk.thresholds:
                add("risk_value", _values(r.risk, count))
        if gated:
            gate = _values(r.susceptibility, count)
            add("susceptibility", [SUSCEPTIBILITY.get(float(v)) if v == v else None for v in gate])
        if spec.season is not None:
            add("in_season", [None] * count if r.in_season is None else [bool(v) for v in r.in_season[:n]])
        if r.reason:
            warnings.append(f"option set {k}: {r.reason}" if multiple else f"no output: {r.reason}")
        if r.windows:
            windows.append(
                {
                    **({"option_set": k} if multiple else {}),
                    "windows": {
                        label: [[a.isoformat(), b.isoformat()] for a, b in periods]
                        for label, periods in r.windows.items()
                    },
                }
            )

    table: list[Column] = []
    for name, values in columns.items():
        if name in {q.name for q in spec.inputs}:
            table.append(catalog_column(name, values))
        elif name in {q.name for q in spec.outputs}:
            q = next(q for q in spec.outputs if q.name == name)
            table.append(Column(name=name, values=values, unit=q.unit, summarize=True))
        elif name == "risk_value":
            table.append(Column(name=name, values=values, unit="index"))
        else:
            table.append(Column(name=name, values=values))
    kinds = [kind for r in results for kind in r.kinds[:n]]
    summary: dict[str, Any] = {
        "days_returned": len(kinds),
        "days_forecast": sum(kind in (FORECAST, PARTIAL) for kind in kinds),
        "days_missing": sum(kind is None for kind in kinds),
        "days_estimated": {
            name: sum(int(np.sum(r.estimated[name][:n])) for r in results if name in r.estimated) for name in estimated
        },
    }
    if windows:
        summary["windows"] = windows
    return table, summary, warnings


def _values(array, count: int) -> list[float]:
    """The first `count` values, or NaN where the run has none (no output: outside the region, not started)."""
    if array is None:
        return [float("nan")] * count
    values = np.asarray(array, dtype=float)
    if values.ndim == 0:
        return [float(values)] * count
    return values[:count].tolist() + [float("nan")] * max(0, count - values.shape[0])
