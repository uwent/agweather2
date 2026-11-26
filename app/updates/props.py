"""Props of the changelog and API-use pages. Types: frontend/types/generated/props.ts."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from updates.render import markdown_html
from web.inertia import Props

if TYPE_CHECKING:
    from updates.models import ChangelogEntry


class ChangelogEntryProps(Props):
    id: int
    date: date
    kind: str
    kind_label: str
    title: str
    body_html: str  # rendered from Markdown with raw HTML escaped (updates.render)
    model: str | None
    endpoint: str | None

    @classmethod
    def of(cls, entry: "ChangelogEntry") -> "ChangelogEntryProps":
        return cls(
            id=entry.pk,
            date=entry.date,
            kind=entry.kind,
            kind_label=entry.get_kind_display(),  # pyright: ignore[reportAttributeAccessIssue]
            title=entry.title,
            body_html=markdown_html(entry.body),
            model=entry.model_id or None,
            endpoint=entry.endpoint or None,
        )


class AnnouncementProps(Props):
    """An entry shown as a banner on every page until its `banner_until` (the shared `announcements` prop)."""

    id: int
    kind: str
    title: str
    body_html: str
    until: datetime


class ChangelogKind(Props):
    value: str
    label: str


class ChangelogProps(Props):
    entries: list[ChangelogEntryProps]
    kinds: list[ChangelogKind]  # every kind, in the admin's order, for the filter


class FrequencyChoice(Props):
    value: str
    label: str


class ApiUseProps(Props):
    areas: list[str]  # the API docs' groups of endpoints
    frequencies: list[FrequencyChoice]
    form_token: str  # signed when the page was made (updates.forms)
