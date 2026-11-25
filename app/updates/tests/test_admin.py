import pytest

from updates.models import ApiUseReport, ChangelogEntry


@pytest.fixture
def report():
    return ApiUseReport.objects.create(name="Pat", uses="Degree days", email="pat@example.org")


@pytest.mark.django_db
def test_pages_open(admin_client, report):
    entry = ChangelogEntry.objects.create(title="Hello", body="Some <script>alert(1)</script> *news*")
    for path in [
        "/admin/updates/changelogentry/",
        "/admin/updates/changelogentry/add/",
        "/admin/updates/apiusereport/",
        f"/admin/updates/apiusereport/{report.pk}/change/",
    ]:
        assert admin_client.get(path).status_code == 200, path
    page = admin_client.get(f"/admin/updates/changelogentry/{entry.pk}/change/").content.decode()
    assert "<em>news</em>" in page and "&lt;script&gt;alert(1)" in page and "<script>alert(1)" not in page


@pytest.mark.django_db
def test_reports_cant_be_added_and_only_the_review_can_change(admin_client, report):
    assert admin_client.get("/admin/updates/apiusereport/add/").status_code == 403
    admin_client.post(
        f"/admin/updates/apiusereport/{report.pk}/change/",
        {"name": "Changed", "uses": "Changed", "reviewed": "on", "notes": "Replied."},
    )
    report.refresh_from_db()
    assert (report.name, report.uses, report.reviewed, report.notes) == ("Pat", "Degree days", True, "Replied.")


@pytest.mark.django_db
def test_actions(admin_client, report):
    entry = ChangelogEntry.objects.create(title="Draft")
    before = entry.updated_at
    admin_client.post("/admin/updates/changelogentry/", {"action": "publish", "_selected_action": [entry.pk]})
    entry.refresh_from_db()
    assert entry.published and entry.updated_at > before  # the API's ETag moves
    admin_client.post("/admin/updates/apiusereport/", {"action": "mark_reviewed", "_selected_action": [report.pk]})
    report.refresh_from_db()
    assert report.reviewed
