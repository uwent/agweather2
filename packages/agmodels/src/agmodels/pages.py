"""Pages: Markdown with YAML front matter, a model's beside its module (D35) and the topics' in `content/`."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, kw_only=True)
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
    return Page(id=page_id, front=front, body=body.strip())
