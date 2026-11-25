"""The model catalog (`/models`) and model pages (`/models/{id}`): content from the registry (web.modelpages)."""

import pytest
from django.test import Client

from agmodels.pages import Page
from agmodels.registry import all_models
from web import modelpages
from web.props import ModelPageProps, ModelsIndexProps, SharedProps

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db

RETIRED = sorted(i for i, m in all_models().items() if m.SPEC.status == "retired")
SHOWN = sorted(i for i, m in all_models().items() if m.SPEC.status != "retired")


def page(client: Client, path: str) -> dict:
    response = client.get(path, headers=INERTIA)
    assert response.status_code == 200
    return response.json()


def test_the_catalog_lists_every_model_but_retired_ones_and_the_calculator(client: Client):
    body = page(client, "/models")
    assert body["component"] == "Models/Index"
    props = body["props"]
    ids = {m["id"] for m in props["models"]}
    assert ids == {i for i in SHOWN if all_models()[i].SPEC.group != "degree_days"}
    assert not ids & set(RETIRED)
    tar = next(m for m in props["models"] if m["id"] == "tar-spot")
    assert tar["crops"] == ["corn"] and tar["group"] == "disease" and tar["summary"]
    assert [g["id"] for g in props["groups"]] == ["disease", "insect", "crop", "agronomic"]
    named = {c for m in props["models"] for c in m["crops"]}
    assert {c["id"] for c in props["crops"]} == named


@pytest.mark.parametrize("model_id", SHOWN)
def test_every_model_has_a_page(client: Client, model_id: str):
    body = page(client, f"/models/{model_id}")
    assert body["component"] == "Models/Show"
    props = body["props"]
    spec = all_models()[model_id].SPEC
    assert (props["id"], props["name"], props["version"]) == (spec.id, spec.name, spec.version)
    assert props["report_url"].endswith(f"/docs/validation/models/{model_id}.md")
    assert len(props["citations"]) == len(spec.citations)


@pytest.mark.parametrize("model_id", [*RETIRED, "no-such-model"])
def test_retired_and_unknown_models_have_no_page(client: Client, model_id: str):
    assert client.get(f"/models/{model_id}", headers=INERTIA).status_code == 404


def test_a_disease_page_takes_its_spec_and_markdown(client: Client):
    props = page(client, "/models/tar-spot")["props"]
    assert props["risk"]["levels"] == ["Very low", "Low", "Moderate", "High"]
    assert props["susceptible"]["crop_model"] == {"id": "corn-stages", "name": all_models()["corn-stages"].SPEC.name}
    assert props["season"] == ["07-01", "08-15"]
    assert props["map_layer"] == "tar-spot"
    assert [s["id"] for s in props["sections"]][:2] == ["what-it-predicts", "how-it-works"]
    assert any(
        c["doi"] == "10.1038/s41598-023-44338-6" and c["url"].startswith("https://doi.org/") for c in props["citations"]
    )
    assert props["changelog"][0]["version"] == all_models()["tar-spot"].SPEC.version  # newest first


def test_a_fitted_insect_names_its_training_area(client: Client):
    props = page(client, "/models/colorado-potato-beetle")["props"]
    assert props["group"] == "insect"
    assert "Adams County, WI" in props["trained"]["counties"]
    assert props["trained"]["calendar_curve"] is True


def test_markdown_is_rendered_without_raw_html_and_with_numbered_citations():
    page_ = Page(
        id="x",
        front={"sources": [{"key": "b-2020", "text": "B"}, {"key": "a-2019", "text": "A", "url": "https://a.org"}]},
        body="Lead.\n\n## How it works\n\nFirst[^a-2019], then[^b-2020] and again[^a-2019]. <script>x</script>\n\n## Notes\n\n- one",
    )
    sources = modelpages.keyed_sources(page_)
    assert [(s.key, s.number) for s in sources] == [("a-2019", 1), ("b-2020", 2)]
    found = modelpages.sections(page_, {s.key: s.number for s in sources})
    assert [(s.id, s.title) for s in found] == [
        ("introduction", ""),
        ("how-it-works", "How it works"),
        ("notes", "Notes"),
    ]
    html = found[1].html
    assert '<a href="#source-a-2019" aria-label="Source 1">1</a>' in html
    assert '<a href="#source-b-2020" aria-label="Source 2">2</a>' in html
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_page_props_never_hide_the_shared_ones():
    # Inertia merges a page's props over the shared props: a model's `status` once replaced the data's
    shared = set(SharedProps.model_fields) | {"errors"}
    assert not shared & set(ModelPageProps.model_fields)
    assert not shared & set(ModelsIndexProps.model_fields)


def test_plain_string_sources_give_no_numbered_list():
    assert modelpages.keyed_sources(Page(id="x", front={"sources": ["A paper"]}, body="Text.")) == []
