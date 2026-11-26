"""One model across your sites (`/sites/models/{id}`, track 3 step 9): a model we have and haven't retired, its
content as props, and a route that the numbers-only site routes never take."""

import pytest
from django.test import Client
from django.urls import resolve, reverse

from agmodels.registry import all_models

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db


def props(client: Client, path: str) -> dict:
    response = client.get(path, headers=INERTIA)
    assert response.status_code == 200, path
    body = response.json()
    assert body["component"] == "Sites/Feed"
    return body["props"]


def test_late_blight_across_your_sites():
    model = props(Client(), "/sites/models/late-blight-dsv")["model"]
    assert model["id"] == "late-blight-dsv"
    assert model["risk_levels"] == ["Very low", "Low", "Moderate", "High", "Very high"]
    assert model["biofix"]["default"] == "05-15"


def test_retired_and_unknown_models_are_not_found():
    client = Client()
    retired = [i for i, m in all_models().items() if m.SPEC.status == "retired"]
    for model_id in [*retired, "no-such-model"]:
        assert client.get(f"/sites/models/{model_id}").status_code == 404, model_id


def test_the_route_is_named_and_not_taken_for_a_site():
    assert reverse("sites-model-feed", kwargs={"model_id": "tar-spot"}) == "/sites/models/tar-spot"
    assert resolve("/sites/models/tar-spot").url_name == "sites-model-feed"
    assert resolve("/sites/43.07,-89.4").url_name == "site"
    assert resolve("/sites/43.07,-89.4/models/tar-spot").url_name == "site-model"
