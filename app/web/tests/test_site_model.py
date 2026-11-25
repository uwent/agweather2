"""A model at a site (`/sites/{lat},{lng}/models/{id}`, track 3 step 6): numbers only, a model we have and haven't
retired, and its content as props."""

import pytest
from django.test import Client
from django.urls import reverse

from agmodels.registry import all_models
from web.sitemodel import section

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db


def props(client: Client, path: str) -> dict:
    response = client.get(path, headers=INERTIA)
    assert response.status_code == 200, path
    body = response.json()
    assert body["component"] == "Sites/Model"
    return body["props"]


def test_late_blight_at_a_site():
    found = props(Client(), "/sites/44.12,-89.52/models/late-blight-dsv?name=%20North%20field")
    assert (found["lat"], found["lng"], found["name"]) == (44.12, -89.52, "North field")
    model = found["model"]
    assert model["id"] == "late-blight-dsv"
    assert model["risk_levels"] == ["Very low", "Low", "Moderate", "High", "Very high"]
    assert [q["name"] for q in model["outputs"]][:1] == ["dsv"]
    assert model["inputs"][0]["unit"] == "hour"
    # Its start is a date the reader gives, by default the potato's estimated emergence
    assert model["biofix"]["default"] == "05-15"
    assert model["biofix"]["stage"].endswith("(EM)")
    assert model["planting"]["crop"] == "Potato" and model["planting"]["typical_dates"]
    assert model["season"] == ["05-01", "09-30"]
    assert "<li>" in model["guidance_html"] and "18" in model["guidance_html"]
    assert found["years"][0] >= 2026 and found["years"] == sorted(found["years"], reverse=True)


def test_a_crop_model_lists_its_stages_and_takes_a_planting_date():
    model = props(Client(), "/sites/44.12,-89.52/models/corn-stages")["model"]
    assert model["stages"][0]["code"] and model["stages"][0]["name"]
    assert model["planting"] is not None and model["biofix"] is None  # its biofix is the planting
    assert model["risk_levels"] == []


def test_a_disease_gated_by_crop_stages_says_which():
    model = props(Client(), "/sites/44.12,-89.52/models/tar-spot")["model"]
    assert model["susceptible"].startswith("From ") and "(V10)" in model["susceptible"]


def test_every_model_but_retired_ones_has_a_page():
    client = Client()
    for model_id, m in all_models().items():
        path = f"/sites/43,-89/models/{model_id}"
        if m.SPEC.status == "retired":
            assert client.get(path).status_code == 404, model_id
        else:
            assert props(client, path)["model"]["id"] == model_id


@pytest.mark.parametrize(
    "path",
    [
        "/sites/43,-89/models/no-such-model",
        "/sites/91,-89/models/late-blight-dsv",
        "/sites/madison/models/late-blight-dsv",
        "/sites/43,-89/models/Late-Blight-DSV",
        "/sites/43,-89/models/late-blight-dsv/",
        "/sites/43,-89/models/",
    ],
)
def test_anything_else_is_not_found(path: str):
    assert Client().get(path).status_code == 404


def test_the_route_is_named_for_links():
    url = reverse("site-model", kwargs={"lat": "43.07", "lng": "-89.4", "model_id": "late-blight-dsv"})
    assert url == "/sites/43.07,-89.4/models/late-blight-dsv"


def test_a_section_of_a_page():
    body = "## One\n\nFirst.\n\n## Two\n\n- a\n- b\n\n## Three\nLast."
    assert section(body, "Two") == "- a\n- b"
    assert section(body, "Three") == "Last."
    assert section(body, "Four") is None
