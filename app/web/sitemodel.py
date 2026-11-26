"""A model at a site (`/sites/{lat},{lng}/models/{id}`, Phase 7 track 3 step 6): the model's content as the page
shows it, from its spec and its page's "How to read it" (D117). Its numbers come from the API in the browser."""

import re
from functools import cache

from agdata.planting import CROPS, planting_crop
from agmodels import croplist
from agmodels.registry import all_models
from agmodels.registry import model as find_model
from agmodels.spec import Input, ModelSpec, Option, Quantity
from updates.render import markdown_html
from web.content import model_pages
from web.props import (
    CropStageInfo,
    ModelChoice,
    ModelOption,
    ModelPlanting,
    ModelQuantity,
    ModelSettings,
    ModelTrained,
    SiteModelBiofix,
    SiteModelInfo,
)

GUIDANCE = "How to read it"


def shown_spec(model_id: str) -> ModelSpec | None:
    """The spec of a model a site's page shows: any but a retired one."""
    found = all_models().get(model_id)
    if found is None or found.SPEC.status == "retired":
        return None
    return found.SPEC


def _quantity(q: Quantity | Input) -> ModelQuantity:
    return ModelQuantity(name=q.name, label=q.label, unit=q.unit, description=q.description)


def _option(o: Option) -> ModelOption:
    return ModelOption(
        name=o.name,
        label=o.label,
        choices=[ModelChoice(value=v, label=label) for v, label in o.choices],
        default=o.default,
        date=not o.choices and o.name.endswith("_date"),
    )


def _stages(crop_model: str) -> list[CropStageInfo]:
    stages = find_model(crop_model).stages()  # type: ignore[attr-defined]
    return [CropStageInfo(code=s.code, name=s.name) for s in stages]


def _stage_words(crop_model: str, code: str) -> str:
    named = {s.code: s.name for s in _stages(crop_model)}
    return f"{named[code]} ({code})" if code in named else code


def section(body: str, heading: str) -> str | None:
    """A `## heading` section of a Markdown page, without its heading; None if the page has none."""
    match = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", body, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else None


def guidance_html(model_id: str) -> str | None:
    page = model_pages().get(model_id)
    text = section(page.body, GUIDANCE) if page else None
    return markdown_html(text) if text else None


def _settings(spec: ModelSpec) -> tuple[SiteModelBiofix | None, ModelPlanting | None]:
    """A model's date it counts from (None when it has none or it's fixed) and what a planting date gives it."""
    planting = planting_crop(spec)
    # A crop model whose biofix is its planting takes the planting date, not a second date
    planting_biofix = planting is not None and planting[0] == spec.id
    biofix = None
    if spec.biofix is not None and not spec.biofix.fixed and not planting_biofix:
        stage = _stage_words(*spec.biofix_stage) if spec.biofix_stage else None
        biofix = SiteModelBiofix(default=spec.biofix.default, label=spec.biofix.label, stage=stage)
    planting_info = None
    if planting is not None:
        crop_model, crop = planting
        crop_options = [] if crop_model == spec.id else [_option(o) for o in find_model(crop_model).SPEC.options]
        planting_info = ModelPlanting(
            crop=croplist.CROPS[crop].name if crop in croplist.CROPS else crop,
            typical_dates=crop in CROPS,
            options=crop_options,
        )
    return biofix, planting_info


@cache
def model_settings() -> list[ModelSettings]:
    """Every shown model that has a setting (a date it counts from, a planting date or an option), by name: what the
    preferences panels offer for all sites, a group or a site."""
    out: list[ModelSettings] = []
    for found in sorted(all_models().values(), key=lambda m: m.SPEC.name.lower()):
        spec = found.SPEC
        if spec.status == "retired":
            continue
        biofix, planting = _settings(spec)
        options = [_option(o) for o in spec.options]
        if biofix or planting or options:
            out.append(
                ModelSettings(
                    id=spec.id, name=spec.name, group=spec.group, biofix=biofix, planting=planting, options=options
                )
            )
    return out


def model_info(spec: ModelSpec) -> SiteModelInfo:
    is_crop = spec.group == "crop"
    biofix, planting_info = _settings(spec)
    s = spec.susceptible
    susceptible = None
    if s is not None:
        susceptible = f"From {_stage_words(s.crop, s.first)} through {_stage_words(s.crop, s.last)}"
        if s.extend_days:
            susceptible += f" and {s.extend_days} days after"
        susceptible += "."
    t = spec.trained
    return SiteModelInfo(
        id=spec.id,
        name=spec.name,
        group=spec.group,
        status=spec.status,  # type: ignore[arg-type]  # never retired here (shown_spec)
        version=spec.version,
        summary=spec.summary,
        crops=croplist.names(spec.crops),
        inputs=[_quantity(q) for q in spec.inputs],
        outputs=[_quantity(q) for q in spec.outputs],
        options=[_option(o) for o in spec.options],
        biofix=biofix,
        planting=planting_info,
        stages=_stages(spec.id) if is_crop and hasattr(find_model(spec.id), "stages") else [],
        risk_levels=list(spec.risk.levels) if spec.risk else [],
        risk_criteria=spec.risk.criteria if spec.risk else "",
        risk_thresholds=list(spec.risk.thresholds) if spec.risk else [],
        susceptible=susceptible,
        season=list(spec.season) if spec.season else None,
        region=list(spec.region),
        trained=None
        if t is None
        else ModelTrained(description=t.description, years=list(t.years), states=list(t.states)),
        guidance_html=guidance_html(spec.id),
    )
