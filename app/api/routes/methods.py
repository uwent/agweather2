"""How the data is made, from the code (Phase 6 step 2, "Methods derived from the code"): the sources by date
(`agdata.provenance`) and the corrections we apply to them, with their held-out scores and fitted tables
(`agdata.corrections`). Both depend only on the code (the tables are files in it), so the ETag is the code's.
"""

import json
import re

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from ninja import Router, Schema

from agdata import corrections, provenance
from agdata.corrections import Correction
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


class MethodsData(Schema):
    sources: list[SourceInfo]
    corrections: list[CorrectionInfo]


class MethodsResponse(Schema):
    meta: Meta
    data: MethodsData


class CorrectionResponse(Schema):
    meta: Meta
    data: CorrectionDetail


def evidence_links(c: Correction) -> list[str]:
    ref = "main" if settings.APP_VERSION == "dev" else settings.APP_VERSION
    return [f"{settings.REPOSITORY_URL}/blob/{ref}/{path.strip()}" for path in c.evidence.split(",")]


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


@router.get("/methods", response=responses(MethodsResponse), summary="Where the data come from, and our corrections")
def overview(request: HttpRequest) -> HttpResponse:
    etag = etag_for(request, {}, None)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    data = {
        "sources": [_source(u).model_dump() for u in provenance.USES],
        "corrections": [_correction(c) for c in corrections.CORRECTIONS],
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
