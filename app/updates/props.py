"""Props of the changelog and API-use pages. Types: frontend/types/generated/props.ts."""

from datetime import date

from web.inertia import Props


class ChangelogEntryProps(Props):
    id: int
    date: date
    kind: str
    kind_label: str
    title: str
    body_html: str  # rendered from Markdown with raw HTML escaped (updates.render)
    model: str | None
    endpoint: str | None


class ChangelogProps(Props):
    entries: list[ChangelogEntryProps]


class FrequencyChoice(Props):
    value: str
    label: str


class ApiUseProps(Props):
    areas: list[str]  # the API docs' groups of endpoints
    frequencies: list[FrequencyChoice]
    form_token: str  # signed when the page was made (updates.forms)
