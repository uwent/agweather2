"""How the data is made, from the code (Phase 6 step 2, "Methods derived from the code"): the sources by date
(`agdata.provenance`) and the corrections we apply to them, with their held-out scores and fitted tables
(`agdata.corrections`), and how the normals are made (`normals`, Phase 7 step 6.5, from `agdata.climatology`,
`agdata.normals`, `agdata.climatestore`, `agdata.springfreeze` and `agdata.seasonopens`). Sources and corrections
depend only on the code (the tables are files in it); the normals' periods name their years, which follow today's
date, the archive's years and gridMET's fit, so those are the ETag's data stamp.
"""

import json
import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from ninja import Router, Schema

from agdata import (
    climatestore,
    climatology,
    corrections,
    normals,
    potatoplanting,
    provenance,
    seasonopens,
    springfreeze,
)
from agdata.corrections import Correction
from agdata.series import archive_years
from agmodels import registry
from agmodels.spec import ModelSpec, OpensOnCropStage, OpensOnDegreeDays
from api import clock
from api.envelope import Result, etag_for, not_modified, respond
from api.routes.discovery import DisplayUnits, display_units
from api.schemas import Meta, responses

router = Router(tags=["About the data"])

TABLE_META = ("version", "fitted", "source")  # a table file's own record, given in the correction's fields instead


class SourceInfo(Schema):
    source: str
    name: str
    role: str  # archive, provisional, forecast, outside, normals
    variables: list[str]
    first: str | None  # YYYY-MM-DD; None: from the archive's first day
    last: str | None  # None: still in use
    description: str
    url: str


class ScoreInfo(Schema):
    measure: str
    unit: str
    units: DisplayUnits
    before: float
    after: float
    tested: str


class CorrectionInfo(Schema):
    id: str
    title: str
    summary: str
    variables: list[str]
    version: str
    fitted: str | None  # YYYY-MM-DD
    scores: list[ScoreInfo]
    evidence: list[str]  # links to the validation reports


class CorrectionDetail(CorrectionInfo):
    table: dict | None  # the fitted values, as the correction reads them; None: no table


class NormalsPeriodInfo(Schema):
    period: str  # last30, last20, last10, last5
    first_year: int
    last_year: int
    archive_years: list[int]  # the period's years from our archive
    gridmet_years: list[int]  # from gridMET, adjusted to the archive (D84)
    missing_years: list[int]
    maps: bool  # whether its normals are kept as maps (D85); else at locations only


class NormalsCountInfo(Schema):
    variable: str
    above: float | None  # the count's days are at or above this, in `unit`
    below: float | None  # or at or below this
    unit: str


class NormalsAdjustInfo(Schema):
    variable: str
    kind: str  # add, ratio


class NormalsLeftOutInfo(Schema):
    variable: str
    years: list[int]


class NormalsGridmetInfo(Schema):
    correction: str  # the correction's id in `corrections`
    adjust: list[NormalsAdjustInfo]
    pool_days: int
    smooth_cells: int
    ratio_limits: list[float]
    left_out: list[NormalsLeftOutInfo]
    fit_years: list[int]  # empty until fitted
    fitted: str | None  # YYYY-MM-DD


class NormalsFreezeInfo(Schema):
    thresholds: list[float]  # °F
    spring: list[str]  # MM-DD: the spring season's first and last day
    fall: list[str]
    percentiles: list[float]
    max_missing_share: float


class NormalsAreaInfo(Schema):
    radius_km: float
    sigma_km: float
    period: str
    planting_freeze: float  # °F: the spring freeze typical planting follows
    planting_offsets: dict[str, int]  # days from that freeze to each tier's planting


class NormalsSeasonOpeningInfo(Schema):
    model: str
    name: str
    rule: str  # degree_days, crop_stage, calendar
    event: str | None
    lead_days: int
    method: str | None  # sine, average, modified, average_capped_mean
    base: float | None  # °F
    upper: float | None
    start: str | None  # MM-DD the degree days count from; None for a crop stage (its planting or January 1)
    degree_days: float | None  # °F degree days to the event (the crop model's to the stage)
    form_degree_days: float | None  # the one-flight form's, where it has one
    form_below: float | None  # its form applies where the 30-year normal degree days (the same method) are below this
    form_through: str | None  # MM-DD: … from January 1 through this day
    crop_model: str | None
    crop_model_name: str | None
    planting: str | None  # the typical planting tier a crop stage counts from; None: January 1
    first_day: str  # MM-DD: the season's calendar first day (a migrant's opening, and the fallback)


class NormalsInfo(Schema):
    periods: list[NormalsPeriodInfo]
    pool_days: int
    coverage: float
    running_max_missing: int
    daily_percentiles: list[float]
    daily_percentile_variables: list[str]
    decile_variables: list[str]
    decile_periods: list[str]
    counts: list[NormalsCountInfo]
    freeze: NormalsFreezeInfo
    gridmet: NormalsGridmetInfo
    area: NormalsAreaInfo
    season_opens: list[NormalsSeasonOpeningInfo]
    region_percentile: float
    evidence: list[str]


class MethodsData(Schema):
    sources: list[SourceInfo]
    corrections: list[CorrectionInfo]
    normals: NormalsInfo


class MethodsResponse(Schema):
    meta: Meta
    data: MethodsData


class CorrectionResponse(Schema):
    meta: Meta
    data: CorrectionDetail


def evidence_links(c: Correction) -> list[str]:
    return _links(c.evidence)


def _links(paths: str) -> list[str]:
    ref = "main" if settings.APP_VERSION == "dev" else settings.APP_VERSION
    return [f"{settings.REPOSITORY_URL}/blob/{ref}/{path.strip()}" for path in paths.split(",")]


def _source(u: provenance.SourceUse) -> SourceInfo:
    return SourceInfo(
        source=u.source,
        name=u.name,
        role=u.role,
        variables=list(u.variables),
        first=u.first.isoformat() if u.first is not None else None,
        last=u.last.isoformat() if u.last is not None else None,
        description=u.description,
        url=u.url,
    )


def _correction(c: Correction) -> dict:
    fitted = c.fitted_on
    return CorrectionInfo(
        id=c.id,
        title=c.title,
        summary=c.summary,
        variables=list(c.variables),
        version=c.current_version,
        fitted=fitted if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fitted) else None,
        scores=[
            ScoreInfo(
                measure=s.measure,
                unit=s.unit,
                units=display_units(s.unit),
                before=s.before,
                after=s.after,
                tested=s.tested,
            )
            for s in c.scores
        ],
        evidence=evidence_links(c),
    ).model_dump()


# --- How the normals are made ---------------------------------------------------------------------------------------

NORMALS_EVIDENCE = "docs/validation/weather/normals.md, docs/validation/weather/climate.md"


def _mmdd(slot: int) -> str:
    found = climatology.slot_date(slot, climatology.LEAP)
    assert found is not None
    return found.strftime("%m-%d")


def _threshold_of(stat: str) -> float:
    """28 from "freeze_28/spring_p50"."""
    return float(stat.split("/")[0].removeprefix("freeze_"))


def _opening(spec: ModelSpec) -> NormalsSeasonOpeningInfo:
    """How an insect's season opens (D128), from its rule."""
    rule = spec.opens
    found = NormalsSeasonOpeningInfo(
        model=spec.id,
        name=spec.name,
        rule="calendar",
        event=None,
        lead_days=0,
        method=None,
        base=None,
        upper=None,
        start=None,
        degree_days=None,
        form_degree_days=None,
        form_below=None,
        form_through=None,
        crop_model=None,
        crop_model_name=None,
        planting=None,
        first_day=spec.season[0] if spec.season is not None else "01-01",
    )
    if isinstance(rule, OpensOnDegreeDays):
        found.rule, found.event, found.lead_days = "degree_days", rule.event, rule.lead_days
        found.method, found.base, found.upper, found.start = rule.method, rule.base_f, rule.upper_f, rule.start
        found.degree_days = rule.dd
        if rule.form_dd is not None and rule.form_normal is not None:
            found.form_degree_days, found.form_below = rule.form_dd, rule.form_below
            found.form_through = rule.form_normal.through
    elif isinstance(rule, OpensOnCropStage):
        setting, dd = seasonopens.crop_stage_dd(rule)
        found.rule, found.event, found.lead_days = "crop_stage", rule.event, rule.lead_days
        found.method, found.base, found.upper = setting.method, setting.base_f, setting.upper_f
        found.degree_days = round(dd, 1)
        found.crop_model, found.crop_model_name = rule.crop, registry.model(rule.crop).SPEC.name
        found.planting = rule.planting
    return found


def season_openings() -> list[NormalsSeasonOpeningInfo]:
    """Every insect model in use whose season opens by a rule (D128), by name."""
    specs = [m.SPEC for m in registry.all_models().values() if m.SPEC.opens is not None and m.SPEC.status != "retired"]
    return [_opening(s) for s in sorted(specs, key=lambda s: s.name)]


def normals_info(data_dir: Path, today: date) -> NormalsInfo:
    """How the normals are made, from the constants that make them, with each period's years for `today` (the
    archive's and gridMET's, as `climatology.period` takes them) and gridMET's fit as kept."""
    available = climatology.available_years(data_dir)
    archive = set(archive_years(data_dir))
    periods = []
    for name in sorted(climatology.PERIODS, key=lambda n: -climatology.PERIODS[n]):
        p = climatology.period(name, today, available)
        periods.append(
            NormalsPeriodInfo(
                period=name,
                first_year=p.asked[0],
                last_year=p.asked[-1],
                archive_years=[y for y in p.years if y in archive],
                gridmet_years=[y for y in p.years if y not in archive],
                missing_years=list(p.missing),
                maps=name in climatology.MAPPED,
            )
        )
    fit = climatestore.fit_attrs(data_dir) or {}
    return NormalsInfo(
        periods=periods,
        pool_days=climatology.POOL_DAYS,
        coverage=climatology.COVERAGE,
        running_max_missing=climatology.MAX_MISSING,
        daily_percentiles=list(normals.SPREAD),
        daily_percentile_variables=list(normals.SPREAD_NAMES),
        decile_variables=list(normals.DECILE_NAMES),
        decile_periods=[p for p in climatology.MAPPED if p != "last5"],
        counts=[NormalsCountInfo(variable=c.variable, above=c.low, below=c.high, unit=c.unit) for c in normals.COUNTS],
        freeze=NormalsFreezeInfo(
            thresholds=[float(f) for f in normals.FREEZE_F],
            spring=[_mmdd(climatology.SPRING[0]), _mmdd(climatology.SPRING[1] - 1)],
            fall=[_mmdd(climatology.FALL[0]), _mmdd(climatology.FALL[1] - 1)],
            percentiles=[q * 100 for q in normals.FREEZE_QUANTILES],
            max_missing_share=climatology.SEASON_MISSING,
        ),
        gridmet=NormalsGridmetInfo(
            correction=corrections.GRIDMET_BASIS.id,
            adjust=[NormalsAdjustInfo(variable=v, kind=k) for v, k in climatestore.ADJUST.items()],
            pool_days=climatestore.POOL_DAYS,
            smooth_cells=climatestore.SMOOTH,
            ratio_limits=list(climatestore.RATIO_LIMITS),
            left_out=[NormalsLeftOutInfo(variable=v, years=list(y)) for v, y in climatestore.LEFT_OUT.items()],
            fit_years=[int(y) for y in fit.get("years") or []],
            fitted=str(fit["fitted"])[:10] if fit.get("fitted") else None,
        ),
        area=NormalsAreaInfo(
            radius_km=springfreeze.RADIUS_KM,
            sigma_km=springfreeze.SIGMA_KM,
            period=springfreeze.PERIOD,
            planting_freeze=_threshold_of(potatoplanting.FREEZE),
            planting_offsets=dict(potatoplanting.OFFSETS),
        ),
        season_opens=season_openings(),
        region_percentile=seasonopens.REGION_PERCENTILE,
        evidence=_links(NORMALS_EVIDENCE),
    )


@router.get(
    "/methods",
    response=responses(MethodsResponse),
    summary="Where the data come from, our corrections, and how normals are made",
)
def overview(request: HttpRequest) -> HttpResponse:
    found = normals_info(settings.DATA_DIR, clock.now().date())
    years = [(p.period, p.archive_years, p.gridmet_years, p.missing_years) for p in found.periods]
    etag = etag_for(request, {}, json.dumps([years, found.gridmet.fit_years, found.gridmet.fitted]))
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    data = {
        "sources": [_source(u).model_dump() for u in provenance.USES],
        "corrections": [_correction(c) for c in corrections.CORRECTIONS],
        "normals": found.model_dump(),
    }
    return respond(request, Result(request={}, data=data, etag=etag))


@router.get(
    "/methods/corrections/{correction_id}",
    response=responses(CorrectionResponse),
    summary="One correction, with its fitted values",
)
def correction(request: HttpRequest, correction_id: str) -> HttpResponse:
    found = corrections.BY_ID.get(correction_id)
    if found is None:
        raise Http404(
            f"We don't have a correction with the id {correction_id!r}. GET /api/v2/methods lists every correction and its id."
        )
    etag = etag_for(request, {"id": correction_id}, None)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    table = None
    if found.table is not None:
        table = {k: v for k, v in json.loads(found.table.read_text()).items() if k not in TABLE_META}
    data = {**_correction(found), "table": table}
    return respond(request, Result(request={"id": correction_id}, data=data, etag=etag))
