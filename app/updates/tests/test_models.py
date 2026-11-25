from datetime import UTC, date, datetime

import pytest
from django.core.exceptions import ValidationError

from updates.models import ChangelogEntry
from updates.render import markdown_html

NOW = datetime(2026, 6, 1, 12, tzinfo=UTC)


def entry(**fields) -> ChangelogEntry:
    return ChangelogEntry.objects.create(**{"title": "An entry", "published": True, **fields})


@pytest.mark.django_db
def test_visible_drops_drafts_and_orders_newest_first():
    a = entry(date=date(2026, 1, 1))
    b = entry(date=date(2026, 2, 1))
    c = entry(date=date(2026, 2, 1))
    entry(date=date(2026, 3, 1), published=False)
    assert list(ChangelogEntry.objects.visible()) == [c, b, a]


@pytest.mark.django_db
def test_banners_are_published_entries_still_up():
    up = entry(banner_until=datetime(2026, 6, 2, tzinfo=UTC))
    entry(banner_until=datetime(2026, 5, 31, tzinfo=UTC))  # over
    entry(banner_until=datetime(2026, 6, 2, tzinfo=UTC), published=False)
    entry()  # never a banner
    assert list(ChangelogEntry.objects.banners(now=NOW)) == [up]


def test_clean_checks_the_model_and_endpoint():
    ChangelogEntry(title="t", model_id="late-blight-dsv", endpoint="/degree-days").clean()
    with_prefix = ChangelogEntry(title="t", endpoint="/api/v2/models/{model_id}/")
    with_prefix.clean()
    assert with_prefix.endpoint == "/models/{model_id}"
    with pytest.raises(ValidationError) as caught:
        ChangelogEntry(title="t", model_id="no-such-model", endpoint="/no-such-endpoint").clean()
    assert set(caught.value.message_dict) == {"model_id", "endpoint"}


def test_markdown_escapes_raw_html():
    html = markdown_html("A [link](https://example.org) and <script>alert(1)</script>\n\n[bad](javascript:alert(1))")
    assert '<a href="https://example.org">link</a>' in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'href="javascript' not in html
