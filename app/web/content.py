"""Topic and model pages (PLAN.md Phase 3 E, D31, D35): Markdown with YAML front matter.

- `content/topics/<id>.md`: a disease, insect, crop or other subject (front matter: id, title, kind, crops,
  scientific_name, summary, image, image_credit, status, sources); its models are the specs naming the topic, so the
  page never lists them by hand.
- A model's page is the `.md` beside its module in `agmodels` (`agmodels.registry.page_path`): its prose (how it
  works, how to read it, validation, caveats; front matter: id, status, sources). Inputs, outputs, risk criteria,
  citations, changelog, region and season come from the spec.
- `content/images/`: the topics' images.

Seeded as drafts by `scripts/import_content.py`; written in Phase 6.
"""

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from agmodels.registry import all_models, page_path

CONTENT = Path(__file__).resolve().parents[2] / "content"
TOPIC_KINDS = ("disease", "insect", "crop", "agronomic", "weather")
TOPIC_FIELDS = ("id", "title", "kind", "crops", "scientific_name", "summary", "image", "image_credit", "status")
STATUSES = ("draft", "reviewed")


@dataclass(frozen=True)
class Page:
    id: str
    front: dict[str, Any] = field(hash=False)
    body: str


def read_page(path: Path, page_id: str | None = None) -> Page:
    """The page at `path`, whose front matter id must be `page_id` (default the file name)."""
    page_id = page_id or path.stem
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: no front matter")
    front_text, body = text[4:].split("\n---\n", 1)
    front = yaml.safe_load(front_text) or {}
    if front.get("id") != page_id:
        raise ValueError(f"{path}: front matter id {front.get('id')!r} isn't {page_id!r}")
    return Page(page_id, front, body.strip())


@cache
def topics() -> dict[str, Page]:
    return {p.stem: read_page(p) for p in sorted((CONTENT / "topics").glob("*.md"))}


@cache
def model_pages() -> dict[str, Page]:
    """Every model's page that exists, by model id."""
    paths = {model_id: page_path(model_id) for model_id in all_models()}
    return {model_id: read_page(path, model_id) for model_id, path in paths.items() if path.is_file()}
