"""The models and crops as pages list them (content, D117): the sites pages take them as props, so a card knows each
model's name, crops and risk scale without a request."""

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


def crop_entries() -> list[CropEntry]:
    """The crops some model names, in the catalog's order (by category, then as listed)."""
    named = {c for spec in specs() for c in spec.crops}
    order = list(croplist.CATEGORIES)
    crops = sorted((c for c in croplist.CROPS.values() if c.id in named), key=lambda c: order.index(c.category))
    return [CropEntry(id=c.id, name=c.name, category=croplist.CATEGORIES[c.category]) for c in crops]
