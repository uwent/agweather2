"""The crop GDD outlook (`/tools/crop-gdd`, track 5 P1): the corn stage model's content and the archive's years as
props; the place and its numbers come from the API in the browser."""

import pytest
from django.test import Client

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db


def test_the_crop_gdd_tool_has_the_corn_model_and_the_years():
    response = Client().get("/tools/crop-gdd", headers=INERTIA)
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "Tools/CropGdd"
    found = body["props"]
    model = found["model"]
    assert model["id"] == "corn-stages"
    maturity = next(o for o in model["options"] if o["name"] == "black_layer_gdd")
    assert "2700" in [c["value"] for c in maturity["choices"]]
    assert [s["code"] for s in model["stages"]][-1] == "R6"
    assert found["years"][0] >= 2026 and found["years"] == sorted(found["years"], reverse=True)
