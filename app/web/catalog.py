"""The models and crops as pages list them (content, D117): the sites pages take them as props, so a card knows each
model's name, crops and risk scale without a request."""

from collections.abc import Iterable

from agmodels import croplist
from agmodels.registry import all_models
from agmodels.spec import ModelSpec
from web.props import CropEntry, ModelEntry


def specs(*, retired: bool = False) -> list[ModelSpec]:
    """Every model's spec but the degree-day calculator's (a tool, not a model a site shows), retired ones only if
    asked."""
    return [
        m.SPEC
        for m in all_models().values()
        if m.SPEC.group != "degree_days" and (retired or m.SPEC.status != "retired")
    ]


def shown_spec(model_id: str) -> ModelSpec | None:
    """The spec of a model that has pages (`/models/{id}`, a site's model, the feed): any but a retired one."""
    found = all_models().get(model_id)
    return None if found is None or found.SPEC.status == "retired" else found.SPEC


def model_entries(*, retired: bool = False) -> list[ModelEntry]:
    return [
        ModelEntry(
            id=spec.id,
            name=spec.name,
            group=spec.group,
            crops=list(spec.crops),
            status=spec.status,
            risk_levels=list(spec.risk.levels) if spec.risk else [],
            season=spec.season,
        )
        for spec in specs(retired=retired)
    ]


def crops_named(crop_ids: Iterable[str]) -> list[croplist.Crop]:
    """The crops among `crop_ids`, in the catalog's order (by category, then as listed); unknown ids left out."""
    named = set(crop_ids)
    order = list(croplist.CATEGORIES)
    return sorted((c for c in croplist.CROPS.values() if c.id in named), key=lambda c: order.index(c.category))


def crop_entries() -> list[CropEntry]:
    """The crops some model names, in the catalog's order (by category, then as listed)."""
    crops = crops_named(c for spec in specs() for c in spec.crops)
    return [CropEntry(id=c.id, name=c.name, category=croplist.CATEGORIES[c.category]) for c in crops]
