"""Pages of text (`/about`, `/accessibility`, `/contact`, Phase 7 step 7.4): content/pages through web.contentpages."""

import re
from datetime import date

import pytest
from django.test import Client
from django.urls import Resolver404, resolve

from agmodels.pages import Page
from web.content import PAGE_FIELDS, STATUSES, content_pages
from web.contentpages import page_props

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}
PAGES = ("about", "accessibility", "contact")


def test_every_page_has_its_text_and_front_matter():
    assert set(content_pages()) == set(PAGES)
    for page in content_pages().values():
        f = page.front
        assert set(PAGE_FIELDS) <= set(f), page.id
        assert f["status"] in STATUSES and f["title"] and page.body, page.id
        assert isinstance(f["updated"], date), f"{page.id}: 'updated' is the date it last changed (YYYY-MM-DD)"


@pytest.mark.django_db
@pytest.mark.parametrize("page_id", PAGES)
def test_each_page_renders_its_markdown(client: Client, page_id: str):
    response = client.get(f"/{page_id}", headers=INERTIA)
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "Content"
    props = body["props"]
    front = content_pages()[page_id].front
    assert (props["id"], props["title"], props["draft"]) == (page_id, front["title"], front["status"] == "draft")
    assert props["updated"] == str(front["updated"])
    titles = [s["title"] for s in props["sections"]]
    assert titles and len(set(titles)) == len(titles)


def test_raw_html_in_a_page_comes_out_as_text():
    page = Page(
        id="x", front={"title": "X", "status": "draft"}, body="<script>alert(1)</script>\n\n## A\n\n[a](/about)"
    )
    props = page_props(page)
    assert "<script>" not in props.sections[0].html and "&lt;script&gt;" in props.sections[0].html
    assert props.sections[1].id == "a" and '<a href="/about">a</a>' in props.sections[1].html


def test_what_the_brief_asks_each_page_to_say():
    pages = content_pages()
    about = pages["about"].body
    for name in ("Allen Ballman", "Ken Frost", "Ben Bradford", "Russ Groves", "Amanda Gevens"):
        assert name in about
    assert "## Privacy" in about and "## How to cite AgWeather" in about and "(/methods)" in about
    assert "WCAG" in pages["accessibility"].body and "policy.wisc.edu/library/UW-519" in pages["accessibility"].body
    contact = pages["contact"].body
    assert "mailto:agweather@cals.wisc.edu" in contact and "(/api-use)" in contact and "(/changelog)" in contact


def test_links_from_the_pages_resolve():
    broken = []
    for page in content_pages().values():
        for path in re.findall(r"\]\((/[^)#\s]*)", page.body):
            try:
                resolve(path)
            except Resolver404:
                broken.append(f"{page.id}: {path}")
    assert not broken, "\n".join(broken)
