"""The changelog page, its feed, and the API-use form's round trip (D112)."""

import json
import re
import time
from datetime import timedelta

import pytest
from django.core import signing
from django.test import Client
from django.utils import timezone

from updates import forms
from updates.models import ApiUseReport, ChangelogEntry
from updates.views import THANKS

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}
ADDRESS = "192.0.2.10"


def page_props(client: Client, path: str) -> dict:
    return client.get(path, headers=INERTIA).json()["props"]


def token(age: float = 60) -> str:
    """A form token made `age` seconds ago."""
    made = time.time() - age
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(time, "time", lambda: made)  # the signature's own timestamp
        return signing.dumps(made, salt=forms.SALT)


def valid(**fields) -> dict:
    return {
        "name": "Pat Grower",
        "organization": "Example Co-op",
        "email": "pat@example.org",
        "uses": "Degree days for our members' fields.",
        "areas": ["Weather", "Degree days, chill and freezes"],
        "endpoints": "/degree-days",
        "frequency": "daily",
        "notify": True,
        "website": "",
        "form_token": token(),
        **fields,
    }


def send(client: Client, data: dict):
    """As the Inertia client sends it: JSON."""
    return client.post(
        "/api-use", data=json.dumps(data), content_type="application/json", headers=INERTIA, REMOTE_ADDR=ADDRESS
    )


def flash(client: Client) -> list[str]:
    page = client.get("/api-use", headers=INERTIA).json()
    return [m["message"] for m in (page.get("flash") or {}).get("messages", [])]


@pytest.mark.django_db
def test_changelog_page_shows_published_entries_escaped(client):
    ChangelogEntry.objects.create(title="Shown", body="Hello <script>x</script> *there*", published=True, kind="data")
    ChangelogEntry.objects.create(title="Draft", published=False)
    response = client.get("/changelog", headers=INERTIA).json()
    assert response["component"] == "Updates/Changelog"
    (shown,) = response["props"]["entries"]
    assert shown["title"] == "Shown" and shown["kind_label"] == "Data and sources"
    assert "<script>" not in shown["body_html"] and "<em>there</em>" in shown["body_html"]


@pytest.mark.django_db
def test_feed(client):
    ChangelogEntry.objects.create(title="In the feed", body="Some *news*", published=True)
    ChangelogEntry.objects.create(title="A draft", published=False)
    response = client.get("/changelog.atom")
    assert response["Content-Type"].startswith("application/atom+xml")
    text = response.content.decode()
    assert "In the feed" in text and "A draft" not in text
    assert re.search(r"<link [^>]*href=\"http://testserver/changelog#entry-\d+\"", text)


@pytest.mark.django_db
def test_form_page_props(client):
    props = page_props(client, "/api-use")
    assert "Weather" in props["areas"]
    assert [f["value"] for f in props["frequencies"]] == ["occasionally", "weekly", "daily", "hourly", "more"]
    assert forms.token_age(props["form_token"]) is not None


@pytest.mark.django_db
def test_a_valid_report_is_saved_with_a_thank_you(client):
    response = send(client, valid())
    assert response.status_code == 302 and response["Location"] == "/api-use"
    report = ApiUseReport.objects.get()
    assert report.name == "Pat Grower" and report.notify and report.client == ADDRESS
    assert report.areas == ["Weather", "Degree days, chill and freezes"] and not report.reviewed
    assert flash(client) == [THANKS]


@pytest.mark.django_db
def test_a_plain_form_post_works_too(client):
    data = {k: v for k, v in valid().items() if k != "notify"}
    client.post("/api-use", data=data, REMOTE_ADDR="2001:db8:1:2:3::4")
    report = ApiUseReport.objects.get()
    assert report.areas == ["Weather", "Degree days, chill and freezes"] and not report.notify
    assert report.client == "2001:db8:1:2::/64"


@pytest.mark.django_db
def test_errors_come_back_once_by_field(client):
    send(client, valid(uses="", frequency="always", areas=["Nonsense"], email="", notify=True))
    errors = page_props(client, "/api-use")["errors"]
    assert errors["uses"] == ["Tell us what you use the API for."]
    assert set(errors) == {"uses", "frequency", "areas", "email"}
    assert page_props(client, "/api-use")["errors"] == {}
    assert not ApiUseReport.objects.exists()


@pytest.mark.django_db
def test_a_filled_honeypot_is_dropped_as_if_sent(client):
    send(client, valid(website="https://spam.example"))
    assert not ApiUseReport.objects.exists()
    assert flash(client) == [THANKS]


@pytest.mark.django_db
def test_a_form_sent_too_fast_is_dropped_quietly(client):
    send(client, valid(form_token=token(age=1)))
    assert not ApiUseReport.objects.exists()
    assert flash(client) == [THANKS]


@pytest.mark.django_db
@pytest.mark.parametrize("bad", ["", "nonsense", "expired"])
def test_an_old_or_missing_token_asks_for_a_reload(client, bad):
    sent = token(age=2 * 86400) if bad == "expired" else bad
    send(client, valid(form_token=sent))
    assert page_props(client, "/api-use")["errors"] == {"form": [forms.RELOAD]}
    assert not ApiUseReport.objects.exists()


@pytest.mark.django_db
def test_limits_per_address_and_per_day(client):
    for _ in range(forms.PER_CLIENT_PER_HOUR):
        send(client, valid())
    send(client, valid())
    assert ApiUseReport.objects.count() == forms.PER_CLIENT_PER_HOUR
    assert page_props(client, "/api-use")["errors"] == {"form": [forms.TOO_MANY]}

    ApiUseReport.objects.update(submitted_at=timezone.now() - timedelta(hours=2))  # the hour has passed
    send(client, valid())
    assert ApiUseReport.objects.count() == forms.PER_CLIENT_PER_HOUR + 1

    ApiUseReport.objects.bulk_create(
        [ApiUseReport(name="x", uses="x", client=f"198.51.100.{n}") for n in range(forms.PER_DAY)]
    )
    send(client, valid())
    assert page_props(client, "/api-use")["errors"] == {"form": [forms.BUSY]}


@pytest.mark.django_db
def test_csrf_is_enforced():
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        "/api-use", data=json.dumps(valid()), content_type="application/json", headers=INERTIA, REMOTE_ADDR=ADDRESS
    )
    assert response.status_code == 403
    assert not ApiUseReport.objects.exists()


@pytest.mark.django_db
def test_loopback_skips_the_per_address_limit(client):
    for _ in range(forms.PER_CLIENT_PER_HOUR + 1):
        client.post("/api-use", data=json.dumps(valid()), content_type="application/json", REMOTE_ADDR="127.0.0.1")
    assert ApiUseReport.objects.filter(client="127.0.0.1").count() == forms.PER_CLIENT_PER_HOUR + 1
