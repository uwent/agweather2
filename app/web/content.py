"""Topic and model pages (PLAN.md Phase 3 E, D31): Markdown with YAML front matter in `content/` at the repo root.

- `content/topics/<id>.md`: a disease, insect, crop or other subject (front matter: id, title, kind, crops,
  scientific_name, summary, image, image_credit, status, sources); its models are the specs naming the topic, so the
  page never lists them by hand.
- `content/models/<id>.md`: a model's prose (how it works, how to read it, validation, caveats; front matter: id,
  status, sources). Inputs, outputs, risk criteria, citations, changelog, region and season come from the spec.
- `content/images/`: the topics' images.

Seeded as drafts by `scripts/import_content.py`; written in Phase 6.
"""

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONTENT = Path(__file__).resolve().parents[2] / "content"
TOPIC_KINDS = ("disease", "insect", "crop", "agronomic", "weather")
TOPIC_FIELDS = ("id", "title", "kind", "crops", "scientific_name", "summary", "image", "image_credit", "status")
STATUSES = ("draft", "reviewed")


@dataclass(frozen=True)
class Page:
    id: str
    front: dict[str, Any] = field(hash=False)
    body: str


def read_page(path: Path) -> Page:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: no front matter")
    front_text, body = text[4:].split("\n---\n", 1)
    front = yaml.safe_load(front_text) or {}
    if front.get("id") != path.stem:
        raise ValueError(f"{path}: front matter id {front.get('id')!r} isn't the file name")
    return Page(path.stem, front, body.strip())


@cache
def topics() -> dict[str, Page]:
    return {p.stem: read_page(p) for p in sorted((CONTENT / "topics").glob("*.md"))}


@cache
def model_pages() -> dict[str, Page]:
    return {p.stem: read_page(p) for p in sorted((CONTENT / "models").glob("*.md"))}
