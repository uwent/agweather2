"""Pages: Markdown with YAML front matter, a model's beside its module (D35) and the topics' in `content/`."""

import re
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


# A citation in a page's text: a Markdown footnote marker naming a source's key, `[^holland-2026]`
CITATION = re.compile(r"\[\^([^\]\s]+)\]")
KEY = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def source_problems(page: Page) -> list[str]:
    """What's wrong with a page's sources and citations (empty if nothing).

    A page lists its sources in front matter either keyed, `{key, text, url}` each (url optional), and then cites
    them in the text with footnote markers, `[^key]`, every marker a listed key and every key cited (by a marker, or
    by a link to its url, as in a page's further reading); or, for pages
    not yet rewritten, as plain strings, with no markers. The frontend renders a marker as a numbered link to the
    source (docs/frontend.md)."""
    sources = page.front.get("sources") or []
    cited = set(CITATION.findall(page.body))
    if all(isinstance(s, str) for s in sources):
        return [f"cites {sorted(cited)} but its sources aren't keyed"] if cited else []
    problems = []
    keys = []
    for s in sources:
        if not isinstance(s, dict) or not set(s) <= {"key", "text", "url"} or not s.get("key") or not s.get("text"):
            problems.append(f"a source isn't {{key, text, url}}: {s!r}")
            continue
        if not KEY.fullmatch(s["key"]):
            problems.append(f"source key {s['key']!r} isn't lowercase-with-hyphens")
        keys.append(s["key"])
    if len(keys) != len(set(keys)):
        problems.append("a source key is listed twice")
    problems += [f"cites [^{k}], which isn't a listed source" for k in sorted(cited - set(keys))]
    linked = {s["key"] for s in sources if isinstance(s, dict) and s.get("url") and f"({s['url']})" in page.body}
    problems += [f"lists {k!r} but never cites it" for k in keys if k not in cited | linked]
    return problems
