"""The model catalog (`/models`) and a model's page (`/models/{id}`), Phase 7 track 4: content as props (D117).

Everything here comes from the model's spec (`agmodels.spec.ModelSpec`, the same that `/api/v2/models/{id}` serves)
and its Markdown page beside its module (`agmodels.registry.page_path`), so a page never carries hand-written method
notes: change the spec or the page and the model page follows. The Markdown is rendered here with raw HTML off, so
the page's `{@html}` is safe, and a footnote marker, `[^key]`, becomes a numbered link to the front matter's keyed
source (docs/frontend.md).
"""

import re
from functools import cache

from markdown_it import MarkdownIt

from agdata.catalog import DAILY_VARIABLES
from agdata.computed import DAILY_COMPUTED
from agdata.layers import LAYERS
from agdata.places import counties
from agdata.regions import STATES
from agmodels import croplist
from agmodels.pages import CITATION, Page
from agmodels.registry import all_models
from agmodels.registry import model as find_model
from agmodels.spec import ModelSpec
from api.routes.discovery import report_link
from web.content import model_pages
from web.props import (
    CatalogModel,
    ModelBiofix,
    ModelChange,
    ModelCheck,
    ModelCitation,
    ModelInput,
    ModelOutput,
    ModelPageProps,
    ModelRisk,
    ModelSection,
    ModelsIndexProps,
    ModelSource,
    ModelSusceptibility,
    ModelTrainingArea,
    NamedId,
)

# The order the catalog lists a crop's models in, and the groups' public names (agronomic: field management)
GROUPS = {"disease": "Diseases", "insect": "Insects", "crop": "Crop growth stages", "agronomic": "Other"}


def validation_report(model_id: str) -> str:
    """The model's validation report on GitHub (D98), at the running version."""
    return report_link(f"docs/validation/models/{model_id}.md")


def catalog_specs() -> list[ModelSpec]:
    """The models the catalog lists: every one but the retired and the degree-day calculator (a tool)."""
    return [m.SPEC for m in all_models().values() if m.SPEC.status != "retired" and m.SPEC.group in GROUPS]


def page_spec(model_id: str) -> ModelSpec | None:
    """The spec of a model that has a page: any model but a retired one."""
    found = all_models().get(model_id)
    return None if found is None or found.SPEC.status == "retired" else found.SPEC


def index_props() -> ModelsIndexProps:
    specs = sorted(catalog_specs(), key=lambda s: s.name.lower())
    named = {c for s in specs for c in s.crops}
    order = list(croplist.CATEGORIES)
    crops = sorted((c for c in croplist.CROPS.values() if c.id in named), key=lambda c: order.index(c.category))
    return ModelsIndexProps(
        models=[
            CatalogModel(id=s.id, name=s.name, group=s.group, summary=s.summary, status=s.status, crops=list(s.crops))
            for s in specs
        ],
        crops=[NamedId(id=c.id, name=c.name) for c in crops],
        groups=[NamedId(id=k, name=v) for k, v in GROUPS.items()],
    )


# --- Markdown ------------------------------------------------------------------------------------------------------


@cache
def _parser() -> MarkdownIt:
    # Raw HTML off: a tag in a page comes out as text, so the page's {@html} is safe (as updates.render)
    return MarkdownIt("commonmark", {"html": False}).enable("table")


def slug(title: str) -> str:
    """'agweathers-models' for "AgWeather's models": an apostrophe joins its word."""
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"['\u2019]", "", title.lower())).strip("-")


def keyed_sources(page: Page) -> list[ModelSource]:
    """The page's keyed sources in the order the text first cites them, each numbered; uncited ones (linked from
    the text instead) follow. Empty for a page whose sources are plain strings."""
    raw = [s for s in page.front.get("sources") or [] if isinstance(s, dict) and s.get("key")]
    order = list(dict.fromkeys(CITATION.findall(page.body)))
    ranked = sorted(raw, key=lambda s: order.index(s["key"]) if s["key"] in order else len(order))
    return [
        ModelSource(key=s["key"], number=n, text=s["text"], url=s.get("url") or None) for n, s in enumerate(ranked, 1)
    ]


def render_markdown(text: str, numbers: dict[str, int]) -> str:
    """Markdown as HTML, its footnote markers as numbered links to the sources (`#source-<key>`)."""

    def marker(match: re.Match) -> str:
        key = match.group(1)
        if key not in numbers:
            return match.group(0)
        n = numbers[key]
        return f'<sup><a href="#source-{key}" aria-label="Source {n}">{n}</a></sup>'

    return CITATION.sub(marker, _parser().render(text))


def sections(page: Page, numbers: dict[str, int]) -> list[ModelSection]:
    """The page's text split at its `##` headings, each rendered; text before the first heading is an untitled
    section."""
    found: list[ModelSection] = []
    parts = re.split(r"^## +(.+?) *$", page.body, flags=re.MULTILINE)
    lead = parts[0].strip()
    if lead:
        found.append(ModelSection(id="introduction", title="", html=render_markdown(lead, numbers)))
    for title, text in zip(parts[1::2], parts[2::2], strict=True):
        found.append(ModelSection(id=slug(title), title=title, html=render_markdown(text.strip(), numbers)))
    return found


# --- A model's page ------------------------------------------------------------------------------------------------


def definition(name: str) -> str:
    """A daily variable's description in the catalog (`agdata.catalog`), as `/variables` gives it."""
    if name in DAILY_VARIABLES:
        return DAILY_VARIABLES[name].long_name
    computed = DAILY_COMPUTED.get(name)
    return computed.variable.long_name if computed is not None else ""


def county_names(fips: tuple[str, ...]) -> list[str]:
    """'Adams County, WI' for each five-digit FIPS code."""
    by_id = {c.geoid: c for c in counties() if c is not None}
    return [f"{by_id[f].name}, {by_id[f].state}" if f in by_id else f for f in fips]


def model_name(model_id: str) -> str:
    try:
        return find_model(model_id).SPEC.name
    except ValueError:
        return model_id


def page_props(spec: ModelSpec) -> ModelPageProps:
    page = model_pages().get(spec.id)
    sources = keyed_sources(page) if page else []
    numbers = {s.key: s.number for s in sources}
    t, s, b = spec.trained, spec.susceptible, spec.biofix
    return ModelPageProps(
        id=spec.id,
        name=spec.name,
        group=spec.group,
        group_name=GROUPS.get(spec.group, "Tools"),
        model_status=spec.status,
        version=spec.version,
        summary=spec.summary,
        crops=[NamedId(id=c, name=croplist.CROPS[c].name) for c in spec.crops if c in croplist.CROPS],
        sections=sections(page, numbers) if page else [],
        draft=bool(page and page.front.get("status") == "draft"),
        updated=str(page.front["updated"]) if page and page.front.get("updated") else None,
        acknowledgments=render_markdown(str(page.front["acknowledgments"]), numbers)
        if page and page.front.get("acknowledgments")
        else None,
        sources=sources,
        risk=None if spec.risk is None else ModelRisk(levels=list(spec.risk.levels), criteria=spec.risk.criteria),
        outputs=[ModelOutput(label=q.label, unit=q.unit, description=q.description) for q in spec.outputs],
        inputs=[
            ModelInput(
                name=i.name, label=i.label, unit=i.unit, description=i.description, definition=definition(i.name)
            )
            for i in spec.inputs
        ],
        region=[NamedId(id=code, name=STATES.get(code, code)) for code in spec.region],
        season=list(spec.season) if spec.season else None,
        seasonal_appears=spec.seasonal.appears if spec.seasonal else None,
        biofix=None
        if b is None
        else ModelBiofix(
            default=b.default,
            label=b.label,
            fixed=b.fixed,
            stage_model=NamedId(id=spec.biofix_stage[0], name=model_name(spec.biofix_stage[0]))
            if spec.biofix_stage
            else None,
            stage=spec.biofix_stage[1] if spec.biofix_stage else None,
        ),
        susceptible=None
        if s is None
        else ModelSusceptibility(
            crop_model=NamedId(id=s.crop, name=model_name(s.crop)),
            first=s.first,
            last=s.last,
            source=s.source,
            note=s.note,
        ),
        trained=None
        if t is None
        else ModelTrainingArea(
            description=t.description,
            years=list(t.years),
            states=[STATES.get(code, code) for code in t.states],
            counties=county_names(t.counties),
            calendar_curve=any(o.name == "clock" for o in spec.options),
        ),
        changelog=[ModelChange(version=c.version, date=c.date, note=c.note) for c in reversed(spec.changelog)],
        citations=[
            ModelCitation(text=c.text, doi=c.doi or None, url=c.doi_url or c.url or None) for c in spec.citations
        ],
        checks=[
            ModelCheck(kind=c.kind, against=c.against, result=c.result, report_url=report_link(c.report))
            for c in spec.checks
        ],
        report_url=validation_report(spec.id),
        map_layer=spec.id if spec.id in LAYERS else None,
    )
