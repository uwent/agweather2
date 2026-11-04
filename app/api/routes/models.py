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
from agmodels.runner import ModelRun, default_biofix
from agmodels.spec import Model
from api import clock, points, runs
from api.envelope import Column, Result, catalog_column, etag_for, not_modified, respond
from api.errors import ApiError
from api.params import DaysQuery, OutputQuery, PointsQuery, SeriesQuery
from api.routes.weather import FORECAST_DAYS, MAX_DAYS, check_size, located
from api.schemas import TableResponse, responses
from ops.points import models_at_point

router = Router(tags=["models"])

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
    if len(where.locations()) > 1:
        raise ApiError("too_many", "one point per run", "points")
    lat, lng = where.locations()[0]
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
    needed, _ = days_needed(the_plan.runs, first)
    stamp = points.stamp([(lat, lng)], needed, last, now)
    etag = None if stamp is None else etag_for(request, computed, stamp)
    if etag is not None and (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    location = located(where, needed, last)[0]
    results = models_at_point(lat, lng, the_plan.runs, first, last, now, planting_default=False)
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
