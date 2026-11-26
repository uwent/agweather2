"""Pages of text (`/about`, `/accessibility`, `/contact`), Phase 7 step 7.4: content as props (D117).

A page is `content/pages/<id>.md` (`web.content`): front matter (id, title, summary, status, updated) and Markdown,
rendered as a topic's is (`web.modelpages.sections`: raw HTML off, split at its `##` headings), so Ben edits the text
without touching code.
"""

from agmodels.pages import Page
from web.content import content_pages
from web.modelpages import sections
from web.props import ContentPageProps


def page_props(page: Page) -> ContentPageProps:
    f = page.front
    return ContentPageProps(
        id=page.id,
        title=str(f["title"]),
        summary=str(f.get("summary") or ""),
        draft=f.get("status") == "draft",
        updated=str(f["updated"]) if f.get("updated") else None,
        sections=sections(page, numbers={}),
    )


def props_for(page_id: str) -> ContentPageProps:
    return page_props(content_pages()[page_id])
