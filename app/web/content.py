"""Topic and model pages (Phase 3 E, D31, D35): Markdown with YAML front matter.

- `content/topics/<id>.md`: a disease, insect, crop or other subject (front matter: id, title, kind, crops,
  scientific_name, summary, image, image_credit, status, updated (set on commit by `scripts/stamp_updated.py`), sources, keyed and cited with `[^key]` markers once a page is
  rewritten: `agmodels.pages.source_problems`); its models are the specs naming the topic, so the
  page never lists them by hand.
- A model's page is the `.md` beside its module in `agmodels` (`agmodels.registry.page_path`): its prose (how it
  works, how to read it, validation, caveats; front matter: id, status, updated, sources, and an insect's summary). Inputs,
  outputs, risk criteria, citations, changelog, region and season come from the spec.
- `content/pages/<id>.md`: a page of text (`/about`, `/accessibility`, `/contact`; front matter: id, title, summary,
  status, updated), rendered by `web.contentpages`, so its text is edited without code.
- `content/images/`: the topics' images.

Seeded as drafts by `scripts/import_content.py`; written in Phase 6.
"""

from functools import cache
from pathlib import Path

from agmodels.pages import Page, read_page
from agmodels.registry import all_models, page_path

CONTENT = Path(__file__).resolve().parents[2] / "content"
TOPIC_KINDS = ("disease", "insect", "crop", "agronomic", "weather")
TOPIC_FIELDS = (
    "id",
    "title",
    "kind",
    "crops",
    "scientific_name",
    "summary",
    "image",
    "image_credit",
    "status",
    "updated",
)
STATUSES = ("draft", "reviewed")
PAGE_FIELDS = ("id", "title", "summary", "status", "updated")


@cache
def topics() -> dict[str, Page]:
    return {p.stem: read_page(p) for p in sorted((CONTENT / "topics").glob("*.md"))}


@cache
def model_pages() -> dict[str, Page]:
    """Every model's page that exists, by model id."""
    paths = {model_id: page_path(model_id) for model_id in all_models()}
    return {model_id: read_page(path, model_id) for model_id, path in paths.items() if path.is_file()}


@cache
def content_pages() -> dict[str, Page]:
    """The pages of text in `content/pages`, by id (the file name)."""
    return {p.stem: read_page(p) for p in sorted((CONTENT / "pages").glob("*.md"))}
