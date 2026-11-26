"""Topic pages (`/topics/{id}`) and their index (`/topics`), Phase 7 track 4: content as props (D117).

A topic is `content/topics/<id>.md` (`web.content`): its front matter and Markdown, rendered as a model page's is
(`web.modelpages`: raw HTML off, `[^key]` markers as numbered links to the keyed sources). Its models are the specs
that name it (`ModelSpec.topics`), so the page never lists them by hand.
"""

import re

from django.templatetags.static import static

from agdata.layers import LAYERS
from agmodels import croplist
from agmodels.pages import Page
from agmodels.registry import all_models
from web.content import topics
from web.modelpages import keyed_sources, sections
from web.props import NamedId, TopicEntry, TopicModel, TopicPageProps, TopicsIndexProps

# The order the index lists a crop's topics in, with their public names (agronomic: field management)
KINDS = {
    "crop": "The crop",
    "disease": "Diseases",
    "insect": "Insects",
    "agronomic": "Field management",
    "weather": "Weather",
}
KIND_NAMES = {
    "crop": "Crop",
    "disease": "Disease",
    "insect": "Insect",
    "agronomic": "Field management",
    "weather": "Weather",
}
# Topic images are served as static files from `content/images` under this prefix (settings.STATICFILES_DIRS)
IMAGE_PREFIX = "content"


def image_url(image: str | None) -> str | None:
    """The static URL of a front matter `image` (`images/late-blight.jpg`, relative to `content/`)."""
    return static(f"{IMAGE_PREFIX}/{image}") if image else None


def image_alt(credit: str) -> str:
    """A credit's first sentence, which says what the photo shows ('Late blight spots on potato leaves.')."""
    first = re.split(r"(?<=\.)\s+(?=[A-Z])", credit.strip(), maxsplit=1)[0]
    return first.rstrip(".")


def index_props() -> TopicsIndexProps:
    found = sorted(topics().values(), key=lambda p: str(p.front["title"]).lower())
    named = {c for p in found for c in p.front.get("crops") or []}
    order = list(croplist.CATEGORIES)
    crops = sorted((c for c in croplist.CROPS.values() if c.id in named), key=lambda c: order.index(c.category))
    return TopicsIndexProps(
        topics=[
            TopicEntry(
                id=p.id,
                title=str(p.front["title"]),
                kind=p.front["kind"],
                scientific_name=p.front.get("scientific_name") or None,
                crops=list(p.front.get("crops") or []),
            )
            for p in found
        ],
        crops=[NamedId(id=c.id, name=c.name) for c in crops],
        kinds=[NamedId(id=k, name=v) for k, v in KINDS.items()],
    )


def topic_models(topic_id: str) -> list[TopicModel]:
    specs = [m.SPEC for m in all_models().values() if topic_id in m.SPEC.topics and m.SPEC.status != "retired"]
    return [
        TopicModel(
            id=s.id,
            name=s.name,
            summary=s.summary,
            model_status=s.status,
            map_layer=s.id if s.id in LAYERS else None,
        )
        for s in sorted(specs, key=lambda s: s.name.lower())
    ]


def page_props(page: Page) -> TopicPageProps:
    f = page.front
    sources = keyed_sources(page)
    numbers = {s.key: s.number for s in sources}
    credit = str(f.get("image_credit") or "")
    return TopicPageProps(
        id=page.id,
        title=str(f["title"]),
        kind=f["kind"],
        kind_name=KIND_NAMES[f["kind"]],
        scientific_name=f.get("scientific_name") or None,
        summary=str(f.get("summary") or ""),
        crops=[NamedId(id=c, name=croplist.CROPS[c].name) for c in f.get("crops") or [] if c in croplist.CROPS],
        image_url=image_url(f.get("image")),
        image_alt=image_alt(credit) if f.get("image") else "",
        image_credit=credit if f.get("image") else "",
        draft=f.get("status") == "draft",
        updated=str(f["updated"]) if f.get("updated") else None,
        sections=sections(page, numbers),
        sources=sources,
        models=topic_models(page.id),
    )
