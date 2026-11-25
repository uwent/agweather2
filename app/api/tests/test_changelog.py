"""`GET /api/v2/changelog` (D112): published entries, newest first, revalidated by ETag."""

from datetime import UTC, date, datetime

import pytest

from updates.models import ChangelogEntry


def entry(**fields) -> ChangelogEntry:
    return ChangelogEntry.objects.create(**{"title": "An entry", "published": True, **fields})


@pytest.mark.django_db
def test_lists_published_entries_newest_first(client):
    old = entry(date=date(2026, 3, 1), title="Old", kind="data")
    new = entry(
        date=date(2026, 4, 1),
        title="New",
        kind="api",
        body="**Bold**",
        endpoint="/degree-days",
        banner_until=datetime(2026, 4, 8, 17, tzinfo=UTC),
    )
    entry(date=date(2026, 5, 1), title="Draft", published=False)
    body = client.get("/api/v2/changelog").json()
    assert body["meta"]["api_version"]
    entries = body["data"]["entries"]
    assert [e["title"] for e in entries] == ["New", "Old"]
    assert entries[0] == {
        "id": new.pk,
        "date": "2026-04-01",
        "kind": "api",
        "title": "New",
        "body": "**Bold**",
        "model": None,
        "endpoint": "/degree-days",
        "banner_until": "2026-04-08T17:00Z",
        "url": f"http://testserver/changelog#entry-{new.pk}",
    }
    assert entries[1]["id"] == old.pk and entries[1]["banner_until"] is None


@pytest.mark.django_db
def test_etag_follows_what_is_published(client):
    first = entry(title="First")
    etag = client.get("/api/v2/changelog")["ETag"]
    assert client.get("/api/v2/changelog", headers={"If-None-Match": etag}).status_code == 304

    draft = entry(title="Draft", published=False)
    assert client.get("/api/v2/changelog", headers={"If-None-Match": etag}).status_code == 304  # drafts don't count

    draft.published = True
    draft.save()
    published = client.get("/api/v2/changelog", headers={"If-None-Match": etag})
    assert published.status_code == 200 and published["ETag"] != etag

    etag = published["ETag"]
    first.title = "First, corrected"
    first.save()
    assert client.get("/api/v2/changelog", headers={"If-None-Match": etag}).status_code == 200

    etag = client.get("/api/v2/changelog")["ETag"]
    first.delete()
    assert client.get("/api/v2/changelog", headers={"If-None-Match": etag}).status_code == 200


@pytest.mark.django_db
def test_empty(client):
    assert client.get("/api/v2/changelog").json()["data"] == {"entries": []}
