import json
import re

import pytest
from django.http import HttpRequest
from django.urls import path

from web.inertia import redirect_with_errors, render
from web.props import HomeProps

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}


def form_view(request: HttpRequest):
    return redirect_with_errors(request, "/form", {"site.name": ["Enter a name."]})


def form_page(request: HttpRequest):
    return render(request, "Home", HomeProps(api_docs_url="/docs"))


urlpatterns = [path("form/submit", form_view), path("form", form_page)]


def page_data(html: str) -> dict:
    match = re.search(r'<script data-page="app" type="application/json">(.*?)</script>', html, re.S)
    assert match
    return json.loads(match.group(1))


@pytest.mark.django_db
def test_first_load_embeds_page_with_shared_props(client):
    response = client.get("/")
    assert response.status_code == 200
    page = page_data(response.content.decode())
    assert page["component"] == "Home"
    assert page["props"]["api_docs_url"] == "/api/v2/docs"
    assert page["props"]["app"] == {"version": "dev", "service_box": "wisconsin"}
    assert page["props"]["errors"] == {}


@pytest.mark.django_db
def test_inertia_visit_returns_json(client):
    response = client.get("/", headers=INERTIA)
    assert response["X-Inertia"] == "true"
    assert response.json()["component"] == "Home"


@pytest.mark.django_db
def test_stale_asset_version_forces_a_full_reload(client):
    response = client.get("/", headers={**INERTIA, "X-Inertia-Version": "old"})
    assert response.status_code == 409
    assert response["X-Inertia-Location"].endswith("/")


@pytest.mark.django_db
@pytest.mark.urls("web.tests.test_inertia")
def test_errors_survive_the_redirect_once(client):
    redirect = client.post("/form/submit", headers=INERTIA)
    assert redirect.status_code == 302
    assert client.get("/form", headers=INERTIA).json()["props"]["errors"] == {"site.name": ["Enter a name."]}
    assert client.get("/form", headers=INERTIA).json()["props"]["errors"] == {}


@pytest.mark.django_db
def test_csrf_cookie_is_the_one_inertia_reads(client):
    response = client.get("/")
    assert "XSRF-TOKEN" in response.cookies


@pytest.mark.django_db
def test_theme_script_carries_the_csp_nonce(client):
    response = client.get("/")
    csp = response["Content-Security-Policy"]
    nonce = re.search(r"'nonce-([^']+)'", csp)
    assert nonce
    assert f'<script nonce="{nonce.group(1)}">' in response.content.decode()
