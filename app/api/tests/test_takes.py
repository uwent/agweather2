"""`meta.params` (`api.takes`): every parameter an endpoint takes, each with the value used."""

import pytest

from api.tests.fixture_archive import POINT

LAT, LNG = POINT


def _params(client, url, **query):
    return client.get(url, query).json()["meta"]["params"]


def test_each_value_is_the_one_computed_else_as_given_else_the_default(client, archive):
    found = _params(client, "/api/v2/weather/daily", lat=LAT, lng=LNG, headers="false", roll_coverage="50", roll="7")
    # Computed: the defaults filled for this request (dates from the archive's clock), and the canonical values
    assert found["start"] == "2025-01-01" and found["end"] is not None
    assert found["vars"] == ["air_temperature_min", "air_temperature_max", "precipitation_sum"]
    # As given, parsed by the field's type
    assert found["headers"] is False and found["roll_coverage"] == 50
    # The schema's default, or null where there's none
    assert found["gaps"] == "estimate" and found["weighting"] == "equal" and found["radius"] is None
    # Settled while answering: the format used and the location's day basis
    assert found["format"] == "json" and found["day_basis"] == "central"
    assert list(found)[:3] == ["lat", "lng", "points"]  # the docs' order


def test_v1s_names_for_a_point_count_as_lat_and_lng_and_a_unit_for_one_variable_is_listed(client, archive):
    found = _params(client, "/api/v2/locate", latitude=LAT, long=LNG)
    assert (found["lat"], found["lng"]) == (LAT, LNG)
    found = _params(client, "/api/v2/weather/daily", lat=LAT, lng=LNG, precipitation="mm")
    assert found["precipitation"] == "mm"


def test_an_error_lists_the_parameters_with_what_could_be_read(client, archive):
    body = client.get("/api/v2/weather/daily", {"lat": LAT, "lng": LNG, "start": "2025-07-0x"}).json()
    assert body["errors"][0]["param"] == "start"
    found = body["meta"]["params"]
    assert found["start"] == "2025-07-0x"  # as sent: it doesn't parse
    assert found["lat"] == LAT and found["end"] is None and found["gaps"] == "estimate"


@pytest.mark.django_db
def test_a_models_options_and_its_crop_models_are_listed(client, archive, monkeypatch):
    from ops import openmeteo

    def unavailable(*args, **kwargs):
        raise openmeteo.Unavailable("not in tests")

    # Days before the archive's come from Open-Meteo: tar spot's and white mold's runs read from their seasons' start,
    # and their options are listed whether or not they could run. A crop's options are used only with a planting date.
    monkeypatch.setattr(openmeteo, "cell_hours", unavailable)
    days = {"start": "2025-07-01", "end": "2025-07-03"}
    found = _params(
        client,
        "/api/v2/models/frogeye-leaf-spot/run",
        lat=LAT,
        lng=LNG,
        maturity_group="2.5",
        planting_date="2025-07-01",
        **days,
    )
    assert found["maturity_group"] == "2.5"  # the soybean stage model's option, as used
    found = _params(client, "/api/v2/models/frogeye-leaf-spot/run", lat=LAT, lng=LNG, maturity_group="2.5", **days)
    assert found["maturity_group"] == "2.0"  # without a planting date: left out with a warning, the default used
    found = _params(client, "/api/v2/models/run", lat=LAT, lng=LNG, models="tar-spot,white-mold", **days)
    # Each option's default; corn's for tar spot, soybean's for white mold
    assert found["black_layer_gdd"] == "2500" and found["irrigation"] == "dry" and "maturity_group" in found
    assert "maturity_group" not in _params(client, "/api/v2/models/run", lat=LAT, lng=LNG, models="tar-spot")


def test_a_model_layers_map_lists_the_options_it_takes_not_those_it_refuses(client, archive):
    found = _params(client, "/api/v2/grids/white-mold", date="2025-07-08")
    assert found["irrigation"] == "dry"
    assert not {"planting_date", "black_layer_gdd", "maturity_group"} & set(found)  # each place's own on a map


@pytest.mark.parametrize("url", ["/api/v2/status", "/api/v2/variables"])
def test_an_endpoint_without_parameters_lists_none(client, archive, url):
    assert client.get(url).json()["meta"]["params"] == {}


def test_tilejson_and_csv_carry_them_too(client, archive):
    tilejson = client.get("/api/v2/tiles/air_temperature_max.json").json()
    assert tilejson["params"]["units"] == "us" and tilejson["params"]["stat"] is None
    csv = client.get("/api/v2/weather/daily", {"lat": LAT, "lng": LNG, "format": "csv"}).content.decode()
    assert '\n# params: {"lat":' in csv and '"format":"csv"' in csv
