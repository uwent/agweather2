"""Discovery (docs/api.md, "Discovery"; PLAN.md Phase 5 B): what the service holds and can compute.

`/variables`, `/models` and `/models/{id}` depend only on the code, and `/locate` on the code and the point, so their
ETags come from the request and the code's version alone and a client holding one gets a 304 without any work.
`/status` reads `DatasetStatus` rows, refreshed by every write, and has no ETag. The output schemas here are the
public contract: they're mapped from `agmodels`' specs and `agdata`'s catalog field by field, so a refactor inside
either doesn't change the API (it changes only by addition, docs/api.md).
"""

from datetime import UTC, datetime
from typing import Literal

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from ninja import Query, Router, Schema

from agdata import units as agunits
from agdata.catalog import (
    CUMULATIVE_VARIABLES,
    DAILY_STATISTICS,
    DAILY_VARIABLES,
    INTERNAL_TOTALS,
    VARIABLES,
    Variable,
)
from agdata.computed import DAILY_COMPUTED, HOURLY_COMPUTED
from agdata.computed import computed as computed_variable
from agdata.grid import NDFD
from agdata.planting import CROPS, planting_crop, typical_planting
from agdata.point import hourly_sources
from agdata.series import MAX_RUN_AGE
from agmodels.registry import all_models
from agmodels.registry import model as find_model
from agmodels.runner import crop_models
from agmodels.spec import Citation, Input, ModelSpec, Option, Quantity
from api import clock
from api.envelope import Result, etag_for, not_modified, respond
from api.errors import ApiError
from api.locations import describe
from api.params import PointsQuery
from api.schemas import Location, Meta, responses
from ops import downloads
from ops.status import dataset_status

router = Router(tags=["About the data"])


def _cached(request: HttpRequest, computed: dict) -> tuple[str, HttpResponse | None]:
    etag = etag_for(request, computed, None)
    return etag, not_modified(request, etag)


class DisplayUnits(Schema):
    us: str
    metric: str


def display_units(symbol: str) -> DisplayUnits:
    return DisplayUnits(
        us=agunits.unit(agunits.display_unit(symbol, "imperial")).label,
        metric=agunits.unit(agunits.display_unit(symbol, "metric")).label,
    )


# --- /status -------------------------------------------------------------------------------------------------------


class ForecastStatus(Schema):
    cycle: str | None
    last_hour: str | None
    in_use: bool  # fresh enough that series run through it (within MAX_RUN_AGE of its cycle)
    reason: str | None  # when not in use: "none" (no run published) or "stale"


class ArchiveStatus(Schema):
    first_hour: str | None
    last_hour_by_source: dict[str, str]  # urma, rtma, hrrr, era5land, ifs, …: each source's newest hour
    daily_through: str | None  # the last local day rolled up
    stale: list[str]  # stores with derived variables from older code, as "daily/2025: et0_sum, …"
    refreshed_at: str  # when this was read from the stores (after the last write, or the worker's start)


class DownloadsStatus(Schema):
    files: int  # yearly NetCDF files listed by /downloads
    built_at: str | None  # when the newest was built


class StatusData(Schema):
    service: str
    version: str
    service_box: str
    archive: ArchiveStatus
    forecast: ForecastStatus
    models: int
    downloads: DownloadsStatus


class StatusResponse(Schema):
    meta: Meta
    data: StatusData


def _iso(when: datetime | None) -> str | None:
    return None if when is None else when.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


@router.get("/status", response=responses(StatusResponse), summary="Service status: what the archive and forecast hold")
def status(request: HttpRequest) -> HttpResponse:
    """From `DatasetStatus`, which every write refreshes (`ops.status.refresh_dataset_status`): no store is opened."""
    rows = dataset_status(settings.DATA_DIR)
    files = downloads.read_index(settings.DATA_DIR)
    hourly, daily, run = rows["hourly"], rows["daily"], rows["forecast"]
    cycle = run.first
    in_use = cycle is not None and clock.now() - cycle <= MAX_RUN_AGE
    stale = [
        f"{kind}/{year}: {', '.join(names)}"
        for kind in ("hourly", "daily", "cumulative")
        for year, names in sorted(rows[kind].stale.items())
    ]
    data = StatusData(
        service="agweather",
        version=settings.APP_VERSION,
        service_box=settings.SERVICE_BOX,
        archive=ArchiveStatus(
            first_hour=_iso(hourly.first),
            last_hour_by_source={
                source: _iso(datetime.fromisoformat(hour)) or ""
                for source, hour in sorted(hourly.last_by_source.items())
            },
            daily_through=daily.last.date().isoformat() if daily.last else None,
            stale=stale,
            refreshed_at=_iso(hourly.refreshed_at) or "",
        ),
        forecast=ForecastStatus(
            cycle=_iso(cycle),
            last_hour=_iso(run.last),
            in_use=in_use,
            reason=None if in_use else ("none" if cycle is None else "stale"),
        ),
        models=len(all_models()),
        downloads=DownloadsStatus(files=len(files), built_at=max((e.built_at for e in files), default=None)),
    )
    return respond(request, Result(request={}, data=data.model_dump()))


# --- /downloads ----------------------------------------------------------------------------------------------------


class DownloadFile(Schema):
    variable: str  # a daily variable (`/variables`)
    year: int
    url: str
    bytes: int
    first: str  # the first and last day it holds
    last: str
    complete: bool  # every day of the year
    built_at: str


class DownloadsData(Schema):
    grid: str | None  # daily/grid.nc: each cell's latitude, longitude and time zone (which sets its days)
    files: list[DownloadFile]


class DownloadsResponse(Schema):
    meta: Meta
    data: DownloadsData


@router.get("/downloads", response=responses(DownloadsResponse), summary="Yearly NetCDF files")
def download_list(request: HttpRequest) -> HttpResponse:
    """`ops.downloads`' index, with each file's URL under /downloads/ (served by Caddy as static files, D69)."""
    index = downloads.folder(settings.DATA_DIR) / "index.json"
    etag, unchanged = _cached(request, {"index": index.stat().st_mtime if index.exists() else None})
    if unchanged is not None:
        return unchanged
    files = [
        DownloadFile(
            variable=e.variable,
            year=e.year,
            url=request.build_absolute_uri(f"/{downloads.FOLDER}/{e.path}"),
            bytes=e.bytes,
            first=e.first,
            last=e.last,
            complete=e.complete,
            built_at=e.built_at,
        )
        for e in downloads.read_index(settings.DATA_DIR)
    ]
    grid = downloads.folder(settings.DATA_DIR) / downloads.GRID_FILE
    data = DownloadsData(
        grid=request.build_absolute_uri(f"/{downloads.FOLDER}/{downloads.GRID_FILE}") if grid.exists() else None,
        files=files,
    )
    return respond(request, Result(request={}, data=data.model_dump(), etag=etag))


# --- /variables ----------------------------------------------------------------------------------------------------


class VariableInfo(Schema):
    name: str
    long_name: str
    kind: Literal["hourly", "daily", "cumulative"]
    unit: str  # the stored unit's symbol (`agdata.units`), as unit overrides take it
    units: DisplayUnits  # what us and metric show
    precision: float  # the stored step, in the stored unit
    valid_min: float | None
    valid_max: float | None
    statistic: str | None  # daily: min, max, mean or sum of `hourly_sources`; None for a feature or a total
    hourly_sources: list[str]  # daily: the hourly variables it's rolled up from
    computed_from: list[str]  # computed when read from these stored variables (same kind); empty if stored
    notes: str


class VariablesResponse(Schema):
    meta: Meta
    data: list[VariableInfo]


def _variable(v: Variable, kind: Literal["hourly", "daily", "cumulative"]) -> VariableInfo:
    statistic = DAILY_STATISTICS.get(v.name) if kind == "daily" else None
    return VariableInfo(
        name=v.name,
        long_name=v.long_name,
        kind=kind,
        unit=v.unit,
        units=display_units(v.unit),
        precision=v.scale,
        valid_min=v.valid_min if v.valid_min > float("-inf") else None,
        valid_max=v.valid_max if v.valid_max < float("inf") else None,
        statistic=statistic.stat if statistic is not None else None,
        hourly_sources=list(hourly_sources().get(v.name, ())) if kind == "daily" else [],
        computed_from=list(c.inputs) if (c := computed_variable(v.name)) is not None else [],
        notes=v.notes,
    )


@router.get("/variables", response=responses(VariablesResponse), summary="The variable catalog")
def variables(request: HttpRequest) -> HttpResponse:
    etag, unchanged = _cached(request, {})
    if unchanged is not None:
        return unchanged
    found = [_variable(v, "hourly") for v in [*VARIABLES.values(), *(c.variable for c in HOURLY_COMPUTED.values())]]
    found += [
        _variable(v, "daily") for v in [*DAILY_VARIABLES.values(), *(c.variable for c in DAILY_COMPUTED.values())]
    ]
    found += [_variable(v, "cumulative") for v in CUMULATIVE_VARIABLES.values() if v.name not in INTERNAL_TOTALS]
    return respond(request, Result(request={}, data=[v.model_dump() for v in found], etag=etag))


# --- /models -------------------------------------------------------------------------------------------------------


class CitationInfo(Schema):
    text: str
    doi: str | None
    url: str | None  # the DOI's link where there's a DOI, else a copy or a source without one


class ModelSummary(Schema):
    id: str
    name: str
    group: str  # disease, insect, crop, agronomic, degree_days
    status: str  # beta, stable, retired
    version: str
    summary: str
    crops: list[str]
    topics: list[str]
    region: list[str]  # state abbreviations; empty: anywhere
    season: list[str] | None  # [first, last] as MM-DD; None: all year
    # a once-a-season product (D68): MM-DD its season's map is first shown (the last one's until then); None: daily
    seasonal_appears: str | None = None
    citations: list[CitationInfo]


class ModelsResponse(Schema):
    meta: Meta
    data: list[ModelSummary]


class QuantityInfo(Schema):
    name: str
    label: str
    unit: str
    units: DisplayUnits
    description: str


class InputInfo(QuantityInfo):
    model: str  # the model that reads it: this one, or the crop model it's gated by


class Choice(Schema):
    value: str
    label: str


class OptionInfo(Schema):
    name: str
    label: str
    choices: list[Choice]  # empty: a date or number given by the user
    default: str


class BiofixInfo(Schema):
    default: str  # MM-DD
    label: str
    stage: list[str] | None  # [crop model, stage code] whose predicted date is the default instead, if any


class SusceptibilityInfo(Schema):
    crop: str
    first: str
    last: str
    source: str
    note: str


class RiskInfo(Schema):
    levels: list[str]
    criteria: str
    thresholds: list[float]


class ExplorerInputInfo(Schema):
    name: str
    label: str
    unit: str
    units: DisplayUnits
    minimum: float
    maximum: float
    step: float
    default: float


class CropInfo(Schema):
    """What `planting_date` adds (D64): the crop model it runs, whether typical dates exist (`early`, `mid`, `late`),
    and that model's options, which the run also takes as parameters. Optional: without a planting date a disease
    runs all season without its susceptible window."""

    model: str
    crop: str
    typical_dates: bool
    options: list[OptionInfo]


class ChangeInfo(Schema):
    version: str
    date: str
    note: str


class ModelDetail(ModelSummary):
    lookback_days: int
    inputs: list[InputInfo]
    derivable_from_hourly: dict[str, list[str]]
    context: list[str]  # values the runner supplies from the place and dates: day_of_year, latitude
    crop_models: list[str]
    outputs: list[QuantityInfo]
    options: list[OptionInfo]
    biofix: BiofixInfo | None
    susceptible: SusceptibilityInfo | None
    crop: CropInfo | None  # None: the model takes no planting date
    risk: RiskInfo | None
    explorer: list[ExplorerInputInfo]
    explorer_outputs: list[QuantityInfo]  # what POST /models/{id}/evaluate gives beyond `outputs`
    changelog: list[ChangeInfo]


class ModelResponse(Schema):
    meta: Meta
    data: ModelDetail


def _citation(c: Citation) -> CitationInfo:
    return CitationInfo(text=c.text, doi=c.doi or None, url=c.doi_url or c.url or None)


def _summary(spec: ModelSpec) -> dict:
    return {
        "id": spec.id,
        "name": spec.name,
        "group": spec.group,
        "status": spec.status,
        "version": spec.version,
        "summary": spec.summary,
        "crops": list(spec.crops),
        "topics": list(spec.topics),
        "region": list(spec.region),
        "season": list(spec.season) if spec.season else None,
        "seasonal_appears": spec.seasonal.appears if spec.seasonal else None,
        "citations": [_citation(c) for c in spec.citations],
    }


def _quantity(q: Quantity | Input) -> dict:
    return {
        "name": q.name,
        "label": q.label,
        "unit": q.unit,
        "units": display_units(q.unit),
        "description": q.description,
    }


def _option(o: Option) -> OptionInfo:
    return OptionInfo(
        name=o.name, label=o.label, choices=[Choice(value=v, label=label) for v, label in o.choices], default=o.default
    )


def _crop(spec: ModelSpec) -> CropInfo | None:
    found = planting_crop(spec)
    if found is None:
        return None
    crop_spec = find_model(found[0]).SPEC
    options = [] if crop_spec.id == spec.id else [_option(o) for o in crop_spec.options]
    return CropInfo(model=found[0], crop=found[1], typical_dates=found[1] in CROPS, options=options)


def _detail(spec: ModelSpec) -> ModelDetail:
    crops = crop_models(spec)
    inputs = [InputInfo(**_quantity(q), model=spec.id) for q in spec.inputs]
    for crop_id in crops:
        seen = {i.name for i in inputs}
        inputs += [
            InputInfo(**_quantity(q), model=crop_id) for q in find_model(crop_id).SPEC.inputs if q.name not in seen
        ]
    derivable = hourly_sources()
    biofix = None
    if spec.biofix is not None:
        stage = list(spec.biofix_stage) if spec.biofix_stage else None
        biofix = BiofixInfo(default=spec.biofix.default, label=spec.biofix.label, stage=stage)
    s = spec.susceptible
    return ModelDetail(
        **_summary(spec),
        lookback_days=spec.lookback_days,
        inputs=inputs,
        derivable_from_hourly={i.name: list(derivable.get(i.name, ())) for i in inputs},
        context=list(spec.context),
        crop_models=crops,
        outputs=[QuantityInfo(**_quantity(q)) for q in spec.outputs],
        options=[_option(o) for o in spec.options],
        biofix=biofix,
        susceptible=None
        if s is None
        else SusceptibilityInfo(crop=s.crop, first=s.first, last=s.last, source=s.source, note=s.note),
        crop=_crop(spec),
        risk=None
        if spec.risk is None
        else RiskInfo(
            levels=list(spec.risk.levels), criteria=spec.risk.criteria, thresholds=list(spec.risk.thresholds)
        ),
        explorer=[
            ExplorerInputInfo(
                name=e.name,
                label=e.label,
                unit=e.unit,
                units=display_units(e.unit),
                minimum=e.minimum,
                maximum=e.maximum,
                step=e.step,
                default=e.default,
            )
            for e in spec.explorer
        ],
        explorer_outputs=[QuantityInfo(**_quantity(q)) for q in spec.explorer_outputs],
        changelog=[ChangeInfo(version=c.version, date=c.date, note=c.note) for c in spec.changelog],
    )


@router.get("/models", response=responses(ModelsResponse), summary="Every model")
def models(request: HttpRequest) -> HttpResponse:
    etag, unchanged = _cached(request, {})
    if unchanged is not None:
        return unchanged
    found = [ModelSummary(**_summary(m.SPEC)).model_dump() for _, m in sorted(all_models().items())]
    return respond(request, Result(request={}, data=found, etag=etag))


@router.get("/models/{model_id}", response=responses(ModelResponse), summary="One model's spec")
def model(request: HttpRequest, model_id: str) -> HttpResponse:
    if model_id not in all_models():
        raise Http404(
            f"We don't have a model with the id {model_id!r}. GET /api/v2/models lists every model and its id."
        )
    etag, unchanged = _cached(request, {"id": model_id})
    if unchanged is not None:
        return unchanged
    spec = all_models()[model_id].SPEC
    return respond(request, Result(request={"id": model_id}, data=_detail(spec).model_dump(), etag=etag))


# --- /locate -------------------------------------------------------------------------------------------------------


class PlantingInfo(Schema):
    crop: str
    early: str  # MM-DD
    typical: str
    late: str
    level: str  # county or state
    source: str


class LocateData(Location):
    corners: list[list[float]] | None  # the cell's [lat, lng] corners, SW, SE, NE, NW; None off the grid
    planting: list[PlantingInfo]  # typical planting dates where known (D34)


class LocateResponse(Schema):
    meta: Meta
    data: LocateData


@router.get(
    "/locate", response=responses(LocateResponse), summary="The cell, zone, county and planting dates at a point"
)
def locate(request: HttpRequest, where: Query[PointsQuery]) -> HttpResponse:
    if where.points is not None:
        raise ApiError("conflict", "This endpoint takes one location. Give lat and lng.", "points")
    computed = where.echo()
    etag, unchanged = _cached(request, computed)
    if unchanged is not None:
        return unchanged
    lat, lng = where.locations()[0]
    location = describe(lat, lng)
    corners = None
    if location["cell"] is not None:
        j, i = location["cell"]["j"], location["cell"]["i"]
        corners = []
        for dj, di in ((-0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0.5, -0.5)):
            corner_lat, corner_lng = (float(v) for v in NDFD.latlon(j + dj, i + di))
            corners.append([round(corner_lat, 5), round(corner_lng, 5)])
    planting = []
    for crop in CROPS:
        found = typical_planting(crop, lat, lng)
        if found is not None:
            planting.append(
                PlantingInfo(
                    crop=crop,
                    early=found.early,
                    typical=found.typical,
                    late=found.late,
                    level=found.level,
                    source=found.source,
                )
            )
    data = LocateData(**location, corners=corners, planting=planting)
    return respond(request, Result(request=computed, data=data.model_dump(), location=location, etag=etag))
