"""Discovery endpoints (PLAN.md Phase 5 B) on the fixture archive."""

from datetime import timedelta

import pytest

from agmodels.registry import all_models
from api.tests.fixture_archive import NOW, POINT

LAT, LNG = POINT


@pytest.mark.django_db
def test_status_reports_what_the_archive_and_forecast_hold(client, archive):
    body = client.get("/api/v2/status").json()
    data = body["data"]
    assert data["service"] == "agweather" and data["models"] == len(all_models())
    assert data["archive"]["first_hour"] == "2025-07-01T00:00Z"
    assert data["archive"]["last_hour_by_source"] == {"urma": "2025-07-10T15:00Z"}
    assert data["archive"]["daily_through"] == "2025-07-09"
    assert data["archive"]["stale"] == [] and data["archive"]["refreshed_at"]
    assert data["forecast"] == {
        "cycle": "2025-07-10T13:00Z",
        "last_hour": "2025-07-21T13:00Z",
        "in_use": True,
        "reason": None,
    }
    assert "ETag" not in client.get("/api/v2/status")  # read fresh each time
    assert not {"jobs", "lock", "failures"} & set(data)  # internals stay on /up and manage.py jobs


@pytest.mark.django_db
def test_status_says_when_the_forecast_is_too_old_to_use(client, archive, monkeypatch):
    monkeypatch.setattr("api.clock.now", lambda: NOW + timedelta(hours=13))
    forecast = client.get("/api/v2/status").json()["data"]["forecast"]
    assert forecast["in_use"] is False and forecast["reason"] == "stale"


@pytest.mark.django_db
def test_status_of_an_empty_archive(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    data = client.get("/api/v2/status").json()["data"]
    assert data["archive"] | {"refreshed_at": ""} == {
        "first_hour": None,
        "last_hour_by_source": {},
        "daily_through": None,
        "stale": [],
        "refreshed_at": "",
    }
    assert data["forecast"]["reason"] == "none"


def test_variables_list_the_catalog_with_units_and_hourly_sources(client):
    response = client.get("/api/v2/variables")
    found = {(v["kind"], v["name"]): v for v in response.json()["data"]}
    tmax = found["daily", "air_temperature_max"]
    assert tmax["unit"] == "degC" and tmax["units"] == {"us": "°F", "metric": "°C"}
    assert tmax["statistic"] == "max" and tmax["hourly_sources"] == ["air_temperature"] and tmax["precision"] == 0.1
    humid = found["daily", "hours_rh_over_90"]
    assert humid["statistic"] is None and humid["hourly_sources"] == ["air_temperature", "dew_point"]
    precip = found["hourly", "precipitation"]
    assert (
        precip["units"] == {"us": "in", "metric": "mm"} and precip["valid_min"] == 0 and precip["hourly_sources"] == []
    )
    assert found["cumulative", "dd_sine_50"]["units"] == {"us": "°F·d", "metric": "°C·d"}
    assert found["daily", "dew_point_depression_max"]["unit"] == "delta_degC"


def test_discovery_answers_carry_an_etag_and_a_held_one_is_a_304(client):
    for path in ("/api/v2/variables", "/api/v2/models", "/api/v2/models/tar-spot"):
        response = client.get(path)
        assert response["Cache-Control"] == "public, no-cache"
        assert client.get(path, headers={"If-None-Match": response["ETag"]}).status_code == 304, path
    assert client.get("/api/v2/models/tar-spot")["ETag"] != client.get("/api/v2/models/frogeye-leaf-spot")["ETag"]


def test_models_list_every_model_with_its_citations(client):
    data = client.get("/api/v2/models").json()["data"]
    assert [m["id"] for m in data] == sorted(all_models())
    tar_spot = next(m for m in data if m["id"] == "tar-spot")
    assert tar_spot["group"] == "disease" and tar_spot["status"] in ("beta", "stable")
    assert tar_spot["citations"][0]["doi"] == "10.1038/s41598-023-44338-6"
    assert tar_spot["citations"][0]["url"] == "https://doi.org/10.1038/s41598-023-44338-6"
    assert "inputs" not in tar_spot  # the list is a summary; /models/{id} has the spec


def test_a_model_spec_names_its_inputs_and_the_hourly_variables_that_make_them(client):
    data = client.get("/api/v2/models/tar-spot").json()["data"]
    assert [i["name"] for i in data["inputs"]] == [
        "air_temperature_mean",
        "relative_humidity_max",
        "hours_rh_over_90_night",
        "air_temperature_min",
        "air_temperature_max",  # corn stages', which gate it
    ]
    assert data["inputs"][-1]["model"] == "corn-stages"
    assert data["inputs"][0]["units"] == {"us": "°F", "metric": "°C"} and data["inputs"][0]["model"] == "tar-spot"
    assert data["derivable_from_hourly"] == {
        "air_temperature_mean": ["air_temperature"],
        "relative_humidity_max": ["relative_humidity"],
        "hours_rh_over_90_night": ["air_temperature", "dew_point"],
        "air_temperature_min": ["air_temperature"],
        "air_temperature_max": ["air_temperature"],
    }
    assert data["risk"]["levels"] and data["outputs"] and data["changelog"]
    assert data["crop_models"] == ["corn-stages"] and data["susceptible"]["first"] == "V10"


def test_a_stage_gated_model_lists_its_crop_models_inputs_too(client):
    data = client.get("/api/v2/models/gray-leaf-spot").json()["data"]
    assert data["crop_models"] == ["corn-stages"]
    assert data["susceptible"]["crop"] == "corn-stages"
    from_crop = [i for i in data["inputs"] if i["model"] == "corn-stages"]
    assert from_crop and all(i["name"] in data["derivable_from_hourly"] for i in data["inputs"])


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_every_model_spec_is_served(client, model_id):
    response = client.get(f"/api/v2/models/{model_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert all(data["derivable_from_hourly"][i["name"]] for i in data["inputs"]), model_id


def test_an_unknown_model_is_a_404_envelope(client):
    response = client.get("/api/v2/models/no-such-model")
    assert response.status_code == 404
    (error,) = response.json()["errors"]
    assert error["code"] == "not_found" and "no-such-model" in error["message"]


def test_locate_gives_the_cell_its_corners_and_planting_dates(client, archive):
    body = client.get("/api/v2/locate", {"lat": LAT, "lng": LNG}).json()
    data = body["data"]
    assert data["cell"] == {"j": 900, "i": 1401, "lat": LAT, "lng": LNG} and data["in_box"] is True
    assert body["meta"]["location"]["cell"] == data["cell"]
    corners = data["corners"]
    assert len(corners) == 4
    lats, lngs = [c[0] for c in corners], [c[1] for c in corners]
    assert min(lats) < LAT < max(lats) and min(lngs) < LNG < max(lngs)  # around the center
    assert {p["crop"] for p in data["planting"]} >= {"corn", "soybean"}
    corn = next(p for p in data["planting"] if p["crop"] == "corn")
    assert corn["early"] < corn["typical"] < corn["late"] and corn["source"]


def test_locate_off_the_grid_and_with_several_points(client, archive):
    paris = client.get("/api/v2/locate", {"lat": 48.85, "lon": 2.35}).json()["data"]
    assert paris["cell"] is None and paris["corners"] is None and paris["planting"] == []
    response = client.get("/api/v2/locate", {"points": "43,-89;44,-90"})
    assert response.status_code == 422 and response.json()["errors"][0]["param"] == "points"


@pytest.mark.django_db
def test_status_answers_from_the_table_without_opening_a_store(client, archive, monkeypatch):
    client.get("/api/v2/status")  # the first answer fills the table
    monkeypatch.setattr("ops.status.find_stale", lambda data_dir: pytest.fail("opened the stores"))
    monkeypatch.setattr("ops.status.span", lambda *a: pytest.fail("opened the stores"))
    assert client.get("/api/v2/status").json()["data"]["archive"]["daily_through"] == "2025-07-09"
