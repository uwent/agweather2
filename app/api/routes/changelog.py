"""The changelog (D112): what we've announced about the API, the models, the data and outages, newest first.

Entries are written in the admin (`updates.models.ChangelogEntry`); only published ones are served. The ETag follows
each published entry's id and last edit, so publishing, editing, unpublishing or deleting one changes it.
"""

from datetime import date, datetime
from typing import Literal

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema

from api.envelope import Result, etag_for, not_modified, respond
from api.schemas import Meta, responses
from updates.models import ChangelogEntry

router = Router(tags=["About the data"])


class ChangelogEntryInfo(Schema):
    id: int
    date: date
    kind: Literal["api", "model", "data", "outage", "announcement"]
    title: str
    body: str  # Markdown
    model: str | None  # a model id (`/models/{id}`)
    endpoint: str | None  # an endpoint's path, as `/degree-days`
    banner_until: datetime | None
    url: str  # the entry on the changelog page


class ChangelogData(Schema):
    entries: list[ChangelogEntryInfo]


class ChangelogResponse(Schema):
    meta: Meta
    data: ChangelogData


def entry_info(request: HttpRequest, entry: ChangelogEntry) -> ChangelogEntryInfo:
    return ChangelogEntryInfo(
        id=entry.pk,
        date=entry.date,
        kind=entry.kind,  # pyright: ignore[reportArgumentType]  # one of Kind's values
        title=entry.title,
        body=entry.body,
        model=entry.model_id or None,
        endpoint=entry.endpoint or None,
        banner_until=entry.banner_until,
        url=request.build_absolute_uri(f"/changelog#entry-{entry.pk}"),
    )


@router.get("/changelog", response=responses(ChangelogResponse), summary="Changes and announcements")
def entries(request: HttpRequest) -> HttpResponse:
    stamp = list(ChangelogEntry.objects.visible().order_by("id").values_list("id", "updated_at"))
    etag = etag_for(request, {}, str(stamp))
    unchanged = not_modified(request, etag)
    if unchanged is not None:
        return unchanged
    data = ChangelogData(entries=[entry_info(request, e) for e in ChangelogEntry.objects.visible()])
    return respond(request, Result(request={}, data=data.model_dump(), etag=etag))
