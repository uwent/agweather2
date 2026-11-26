"""The potato volunteer tool (`/tools/potato-volunteer`, track 5 P1): the model's content, the archive's years and
the topic's management advice as props; the place's numbers and the map come from the API in the browser."""

import pytest
from django.test import Client

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db


def test_the_potato_volunteer_tool_has_its_model_and_the_topics_advice():
    response = Client().get("/tools/potato-volunteer", headers=INERTIA)
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "Tools/PotatoVolunteer"
    found = body["props"]
    model = found["model"]
    assert model["id"] == "potato-volunteer"
    assert [q["name"] for q in model["outputs"]] == ["killing_hours_4cm", "killing_hours_10cm", "killing_hours_8in"]
    assert model["risk_levels"] == ["Low", "Moderate", "High", "Very high"]
    assert found["years"][0] >= 2026 and found["years"] == sorted(found["years"], reverse=True)
    # The topic's "Managing volunteers" section, without its citation markers
    html = found["management_html"]
    assert "<li>" in html and "cull" in html and "[^" not in html
