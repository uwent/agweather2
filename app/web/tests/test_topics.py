"""Topic pages (`/topics/{id}`), their index (`/topics`) and the methods page (`/methods`): content as props (D117)."""

import re

import pytest
from django.contrib.staticfiles import finders
from django.test import Client
from django.urls import Resolver404, resolve

from agdata import corrections, provenance
from agmodels.registry import all_models
from web import modelpages, topicpages
from web.content import model_pages, topics
from web.props import MethodsProps, SharedProps, TopicPageProps, TopicsIndexProps

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}
TOPICS = sorted(topics())

# Links in the Markdown to pages still to be built (Phase 7): listed so a new broken link fails
PENDING = {"/tools/degree-days"}


def page(client: Client, path: str) -> dict:
    response = client.get(path, headers=INERTIA)
    assert response.status_code == 200
    return response.json()


@pytest.mark.django_db
@pytest.mark.parametrize("topic_id", TOPICS)
def test_every_topic_has_a_page(client: Client, topic_id: str):
    body = page(client, f"/topics/{topic_id}")
    assert body["component"] == "Topics/Show"
    props = body["props"]
    front = topics()[topic_id].front
    assert (props["id"], props["title"], props["kind"]) == (topic_id, front["title"], front["kind"])
    assert props["sections"] and props["draft"] == (front["status"] == "draft")
    named = {i for i, m in all_models().items() if topic_id in m.SPEC.topics and m.SPEC.status != "retired"}
    assert {m["id"] for m in props["models"]} == named


@pytest.mark.django_db
def test_an_unknown_topic_has_no_page(client: Client):
    assert client.get("/topics/no-such-topic", headers=INERTIA).status_code == 404


@pytest.mark.django_db
def test_the_index_lists_every_topic_by_crop(client: Client):
    body = page(client, "/topics")
    assert body["component"] == "Topics/Index"
    props = body["props"]
    assert {t["id"] for t in props["topics"]} == set(TOPICS)
    assert {c["id"] for c in props["crops"]} == {c for t in props["topics"] for c in t["crops"]}
    assert [k["id"] for k in props["kinds"]][:3] == ["crop", "disease", "insect"]


@pytest.mark.django_db
def test_a_topic_page_has_its_photo_models_and_sources(client: Client):
    props = page(client, "/topics/late-blight")["props"]
    assert props["image_url"] == "/static/content/images/late-blight.jpg"
    assert props["image_alt"] == "Late blight spots on potato leaves"
    assert "Bugwood" in props["image_credit"]
    assert [m["id"] for m in props["models"]] == ["late-blight-dsv"]
    assert props["models"][0]["map_layer"] == "late-blight-dsv"
    assert "agweathers-models" in [s["id"] for s in props["sections"]]


def test_every_photo_is_a_static_file():
    # Served from content/images (settings.STATICFILES_DIRS), so collectstatic gives them to Caddy
    for topic in topics().values():
        if topic.front.get("image"):
            assert finders.find(f"{topicpages.IMAGE_PREFIX}/{topic.front['image']}"), topic.id


@pytest.mark.parametrize("topic_id", TOPICS)
def test_every_footnote_resolves(topic_id: str):
    props = topicpages.page_props(topics()[topic_id])
    keys = {s.key for s in props.sources}
    html = "".join(s.html for s in props.sections)
    cited = set(re.findall(r'href="#source-([^"]+)"', html))
    assert cited <= keys
    assert not re.search(r"\[\^[^\]\s]+\]", html), "a footnote marker left unrendered"
    assert [s.number for s in props.sources] == list(range(1, len(props.sources) + 1))


def test_links_between_pages_resolve():
    pages = [*topics().values(), *model_pages().values()]
    broken = []
    for p in pages:
        for path in re.findall(r"\]\((/[^)#\s]*)", p.body):
            if path in PENDING:
                continue
            try:
                match = resolve(path)
            except Resolver404:
                broken.append(f"{p.id}: {path}")
                continue
            if match.url_name == "topic" and match.kwargs["topic_id"] not in topics():
                broken.append(f"{p.id}: {path}")
            if match.url_name == "model" and modelpages.page_spec(match.kwargs["model_id"]) is None:
                broken.append(f"{p.id}: {path}")
    assert not broken, "\n".join(broken)


def test_an_apostrophe_joins_its_word_in_a_section_id():
    assert modelpages.slug("AgWeather's models") == "agweathers-models"
    assert modelpages.slug("How it works") == "how-it-works"


def test_an_image_credit_s_first_sentence_describes_the_photo():
    credit = "Tar spot on a corn leaf. Photo by A. B. Smith, Purdue University, CC BY 3.0 US."
    assert topicpages.image_alt(credit) == "Tar spot on a corn leaf"


# --- The methods page -------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_methods_page_is_made_from_the_code(client: Client):
    body = page(client, "/methods")
    assert body["component"] == "Methods"
    props = body["props"]
    assert len(props["sources"]) == len(provenance.USES)
    assert [c["id"] for c in props["corrections"]] == [c.id for c in corrections.CORRECTIONS]
    hrrr = next(c for c in props["corrections"] if c["id"] == "hrrr-shortwave")
    assert hrrr["scores"] and hrrr["evidence"][0].endswith("docs/validation/weather/shortwave-correction.md")
    assert props["grid"]["cell_km"] == 2.5 and props["grid"]["day_zone_abbreviation"] == "CST"
    assert props["grid"]["day_start_utc"] == 6
    assert props["api_methods_url"] == "/api/v2/methods"
    # Each kind's names are unique, so each has its own anchor
    for kind in ("hourly", "daily", "cumulative"):
        names = [v["name"] for v in props["variables"] if v["kind"] == kind]
        assert len(names) == len(set(names)) and names


@pytest.mark.django_db
def test_the_methods_page_matches_the_apis_variables(client: Client):
    props = page(client, "/methods")["props"]
    api = client.get("/api/v2/variables").json()["data"]
    assert [(v["name"], v["kind"]) for v in props["variables"]] == [(v["name"], v["kind"]) for v in api]


@pytest.mark.django_db
def test_the_methods_page_describes_how_normals_are_made_from_the_code(client: Client, monkeypatch):
    from agdata import climatology, normals, springfreeze

    props = page(client, "/methods")["props"]["normals"]
    assert props == client.get("/api/v2/methods").json()["data"]["normals"]  # the API and the page in step
    assert [p["period"] for p in props["periods"]] == ["last30", "last20", "last10", "last5"]
    assert props["pool_days"] == climatology.POOL_DAYS and props["area"]["radius_km"] == springfreeze.RADIUS_KM
    assert len(props["counts"]) == len(normals.COUNTS) and props["freeze"]["thresholds"] == [32, 28, 24]
    found = {o["model"]: o for o in props["season_opens"]}
    assert found["european-corn-borer"]["degree_days"] == 395 and found["european-corn-borer"]["form_below"] == 1500
    assert found["colorado-potato-beetle"]["rule"] == "crop_stage" and found["black-cutworm"]["rule"] == "calendar"
    assert "western-flower-thrips" not in found  # retired
    # A change in a constant changes the page
    monkeypatch.setattr(climatology, "POOL_DAYS", 21)
    monkeypatch.setattr(springfreeze, "RADIUS_KM", 40.0)
    changed = page(client, "/methods")["props"]["normals"]
    assert changed["pool_days"] == 21 and changed["area"]["radius_km"] == 40.0


def test_a_periods_years_come_from_the_archive_and_gridmet(monkeypatch, tmp_path):
    from datetime import date

    from agdata import climatology
    from api.routes import methods

    monkeypatch.setattr(climatology, "available_years", lambda data_dir: [*range(1996, 2016), 2016, 2018])
    monkeypatch.setattr(methods, "archive_years", lambda data_dir: [2016, 2018, 2026])
    found = {p.period: p for p in methods.normals_info(tmp_path, date(2026, 3, 1)).periods}
    assert (found["last30"].first_year, found["last30"].last_year) == (1996, 2025)
    assert found["last30"].archive_years == [2016, 2018] and found["last30"].gridmet_years == list(range(1996, 2016))
    assert found["last10"].missing_years == [2017, *range(2019, 2026)] and found["last10"].maps
    assert not found["last20"].maps


def test_the_variables_are_described_in_plain_words():
    # Public text (CLAUDE.md, "Writing for the public"): no code ids, "RH", "Jan 1" or "6 pm" in a name or its notes
    from web.methodspage import variables

    plain = re.compile(r"\b[a-z0-9]+_[a-z0-9_]+\b|\bRH\b|\b(Jan|Oct) 1\b|\b[ap]m\b")
    for v in variables():
        for text in (v.long_name, v.notes):
            assert not plain.search(text), (v.name, text)


def test_every_model_input_with_a_definition_has_an_entry_on_the_methods_page():
    # A model page links an input to /methods#variable-<name> when the catalog defines it
    from web.methodspage import variables

    daily = {v.name for v in variables() if v.kind == "daily"}
    for spec in (m.SPEC for m in all_models().values()):
        for i in spec.inputs:
            if modelpages.definition(i.name):
                assert i.name in daily, (spec.id, i.name)


def test_page_props_never_hide_the_shared_ones():
    shared = set(SharedProps.model_fields) | {"errors"}
    for props in (TopicPageProps, TopicsIndexProps, MethodsProps):
        assert not shared & set(props.model_fields), props.__name__


def test_footnotes_side_by_side_are_separated():
    html = modelpages.render_markdown("Text.[^a][^b]", {"a": 1, "b": 2})
    assert 'aria-label="Source 1">1</a>,<a href="#source-b" aria-label="Source 2">2</a></sup>' in html
