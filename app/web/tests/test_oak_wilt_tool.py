"""The oak wilt tool (`/tools/oak-wilt`, track 5 T1 d): the model's content, the archive's years and the topic's
management advice as props; the place and its numbers come from the API in the browser."""

import pytest
from django.test import Client

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db


def test_the_oak_wilt_tool_has_its_model_and_the_topics_advice():
    response = Client().get("/tools/oak-wilt", headers=INERTIA)
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "Tools/OakWilt"
    found = body["props"]
    model = found["model"]
    assert model["id"] == "oak-wilt-vectors"
    assert "dd_total" in [q["name"] for q in model["outputs"]]
    assert model["risk_levels"][2] == "Moderate"
    assert found["years"][0] >= 2026 and found["years"] == sorted(found["years"], reverse=True)
    # The topic's Management section, without its citation markers
    html = found["management_html"]
    assert "<li>" in html and "July 15" in html and "[^" not in html
