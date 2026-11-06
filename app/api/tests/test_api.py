import pytest


@pytest.mark.django_db
def test_status(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path  # an empty archive, not the real one
    response = client.get("/api/v2/status")
    assert response.status_code == 200
    body = response.json()
    assert (body["data"]["service"], body["data"]["version"]) == ("agweather", "dev")
    assert body["meta"]["api_version"] == "2.0"
    # Nothing that would keep a shared cache from storing it
    assert "Cookie" not in response.get("Vary", "") and not response.cookies


def test_an_unknown_path_under_the_api_is_a_404_envelope(client):
    response = client.get("/api/v2/nothing-here")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"meta", "errors"} and body["errors"][0]["code"] == "not_found"


def test_openapi_schema(client):
    schema = client.get("/api/v2/openapi.json").json()
    assert schema["info"]["title"] == "AgWeather API"
    status = schema["paths"]["/api/v2/status"]["get"]["responses"]
    assert set(status) == {"200", "404", "422", "500", "503"}
    assert "ErrorResponse" in schema["components"]["schemas"]
