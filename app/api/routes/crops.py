"""The crops (`agmodels.croplist`, D93): each crop with everything we have for it, its models by group, its growth
stage model, degree-day preset and fall freeze, and whether typical planting dates exist. Code-only, so the ETag is
the code's.
"""

from django.http import Http404, HttpRequest, HttpResponse
from ninja import Router, Schema

from agdata.planting import CROPS as PLANTING_CROPS
from agmodels import croplist
from agmodels.croplist import Crop
from agmodels.presets import CROP_PRESETS
from agmodels.registry import all_models
from api.envelope import Result, etag_for, not_modified, respond
from api.routes.degree_days import FreezeInfo, freeze_info
from api.schemas import Meta, responses

router = Router(tags=["About the data"])


class CropModels(Schema):
    disease: list[str]
    insect: list[str]
    crop: list[str]  # growth stages
    agronomic: list[str]


class CropData(Schema):
    id: str
    name: str
    category: str
    category_name: str
    members: list[str]  # a group's crops
    groups: list[str]  # the groups it's in
    models: CropModels
    stage_models: list[str]
    presets: list[str]
    freeze: FreezeInfo | None
    typical_planting: bool


class CropsResponse(Schema):
    meta: Meta
    data: list[CropData]


class CropResponse(Schema):
    meta: Meta
    data: CropData


def _info(c: Crop) -> dict:
    found: dict[str, list[str]] = {"disease": [], "insect": [], "crop": [], "agronomic": []}
    for model_id, module in sorted(all_models().items()):
        spec = module.SPEC
        if spec.group in found and croplist.applies(spec.crops, c.id):
            found[spec.group].append(model_id)
    presets = [p for p in CROP_PRESETS if c.id in p.crops]
    freeze = next((p.freeze for p in presets if p.freeze is not None), None)
    return CropData(
        id=c.id,
        name=c.name,
        category=c.category,
        category_name=croplist.CATEGORIES[c.category],
        members=list(c.members),
        groups=croplist.groups_of(c.id),
        models=CropModels(**found),
        # A stage model names the crop itself or a member (`spring-wheat-stages` under wheat), not a group it's in
        stage_models=[m for m in found["crop"] if set(all_models()[m].SPEC.crops) & {c.id, *c.members}],
        presets=[p.id for p in presets],
        freeze=freeze_info(freeze) if freeze is not None else None,
        typical_planting=c.id in PLANTING_CROPS,
    ).model_dump()


@router.get("/crops", response=responses(CropsResponse), summary="Every crop, with what we have for it")
def crop_list(request: HttpRequest) -> HttpResponse:
    etag = etag_for(request, {}, None)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    order = list(croplist.CATEGORIES)
    found = sorted(croplist.CROPS.values(), key=lambda c: (order.index(c.category), c.name))
    return respond(request, Result(request={}, data=[_info(c) for c in found], etag=etag))


@router.get("/crops/{crop_id}", response=responses(CropResponse), summary="One crop, with what we have for it")
def crop(request: HttpRequest, crop_id: str) -> HttpResponse:
    found = croplist.CROPS.get(crop_id)
    if found is None:
        raise Http404(f"We don't have a crop with the id {crop_id!r}. GET /api/v2/crops lists every crop and its id.")
    etag = etag_for(request, {"id": crop_id}, None)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    return respond(request, Result(request={"id": crop_id}, data=_info(found), etag=etag))
