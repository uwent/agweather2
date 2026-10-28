def test_status(client):
    response = client.get("/api/v2/status")
    assert response.status_code == 200
    assert response.json() == {"service": "agweather", "version": "dev", "service_box": "wisconsin"}


def test_openapi_schema(client):
    schema = client.get("/api/v2/openapi.json").json()
    assert schema["info"]["title"] == "AgWeather API"
    assert "/api/v2/status" in schema["paths"]
