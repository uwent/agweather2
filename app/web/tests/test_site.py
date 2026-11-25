"""The site page's route (`/sites/{lat},{lng}`, F1): numbers only, inside latitude and longitude's ranges."""

import pytest
from django.test import Client
from django.urls import reverse

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}

pytestmark = pytest.mark.django_db


def page(client: Client, path: str) -> dict:
    response = client.get(path, headers=INERTIA)
    assert response.status_code == 200
    return response.json()


def test_a_site_page_takes_the_point_and_the_catalog(client: Client):
    body = page(client, "/sites/44.12,-89.52")
    assert body["component"] == "Sites/Show"
    props = body["props"]
    assert (props["lat"], props["lng"], props["name"]) == (44.12, -89.52, None)
    models = {m["id"]: m for m in props["models"]}
    assert models["late-blight-dsv"]["crops"] == ["potato", "tomato"]
    assert models["late-blight-dsv"]["group"] == "disease"
    assert models["late-blight-dsv"]["risk_levels"] == ["Very low", "Low", "Moderate", "High", "Very high"]
    assert not any(m["status"] == "retired" for m in props["models"])
    assert {"id": "corn", "name": "Corn"} in props["crops"]


def test_a_shared_links_name_is_trimmed_and_cut_short(client: Client):
    assert page(client, "/sites/43.07,-89.4?name=%20%20North%20%20field%20")["props"]["name"] == "North field"
    assert len(page(client, f"/sites/43,-89?name={'x' * 200}")["props"]["name"]) == 80
    assert page(client, "/sites/43,-89?name=%20")["props"]["name"] is None


@pytest.mark.parametrize("path", ["/sites/43,-89", "/sites/-43.5,89.25", "/sites/90,180", "/sites/-90,-180"])
def test_whole_and_signed_numbers(client: Client, path: str):
    assert page(client, path)["component"] == "Sites/Show"


@pytest.mark.parametrize(
    "path",
    [
        "/sites/91,-89",  # past the pole
        "/sites/43,-181",
        "/sites/43,-89/",
        "/sites/madison",
        "/sites/43,-89,1",
        "/sites/43;-89",
        "/sites/1e1,-89",
        "/sites/models",  # another page under /sites/ some day, never a site
    ],
)
def test_anything_but_a_point_is_not_found(client: Client, path: str):
    assert client.get(path).status_code == 404


def test_the_route_is_named_for_links():
    assert reverse("site", kwargs={"lat": "43.07", "lng": "-89.4"}) == "/sites/43.07,-89.4"
