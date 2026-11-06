"""Unknown query parameters are a 422 naming each (`api.strict`), on every endpoint, before any work is done."""

from datetime import date

import pytest

from api.api import api
from api.errors import ApiError
from api.params import parse_hour, resolve_biofix
from api.tests.fixture_archive import POINT

EXAMPLES = {"model_id": "tar-spot", "layer": "air_temperature_max", "when": "latest", "z": "5", "x": "8", "y": "11"}


def _operations():
    for router in api._get_bound_routers():
        for path, view in router.path_operations.items():
            for operation in view.operations:
                for method in operation.methods:
                    url = "/api/v2/" + path.lstrip("/")
                    for name, value in EXAMPLES.items():
                        url = url.replace("{" + name + "}", value)
                    yield pytest.param(method, url, id=f"{method} {path}")


@pytest.mark.parametrize(("method", "url"), list(_operations()))
def test_every_endpoint_refuses_a_parameter_it_doesnt_take(client, method, url):
    response = client.generic(method, url + "?not_a_parameter=1", content_type="application/json")
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert errors == [
        {
            "code": "unknown_parameter",
            "param": "not_a_parameter",
            "message": "This request doesn't take a parameter named not_a_parameter. The parameters each request "
            "takes are listed at /api/v2/docs.",
        }
    ]


@pytest.mark.parametrize(
    ("url", "suggested"),
    [
        ("/api/v2/weather/daily?lat=43&lng=-89&start_date=2025-07-01", "start"),  # v1's name
        ("/api/v2/degree-days?lat=43&lng=-89&models=dd_50_86", "dd"),  # v1's dd_table
        ("/api/v2/maps/degree_days.png?dd=sine_50&biofixx=07-01", "biofix"),  # a typo
    ],
)
def test_a_close_name_is_suggested(client, url, suggested):
    error = client.get(url).json()["errors"][0]
    assert error["code"] == "unknown_parameter" and f"Did you mean {suggested}?" in error["message"]


def test_each_unknown_parameter_is_its_own_error(client):
    errors = client.get("/api/v2/status?one=1&two=2").json()["errors"]
    assert [e["param"] for e in errors] == ["one", "two"]


@pytest.mark.parametrize(
    "url",
    [
        "/api/v2/locate?latitude=43.07&longitude=-89.40",  # v1's names for a point
        "/api/v2/locate?lat=43.07&long=-89.40&_=1730000000",  # a JavaScript cache-buster
        "/api/v2/variables?precipitation=mm",  # a unit for one variable
    ],
)
def test_names_every_endpoint_takes_pass(client, url):
    assert client.get(url).status_code == 200


def test_a_models_own_options_pass_and_a_maps_refusals_keep_their_message(client, archive):
    # Neither is declared: the endpoint reads them from the query. Unknown model ids are the endpoint's 404.
    run = client.get("/api/v2/models/frogeye-leaf-spot/run?lat=43&lng=-89&maturity_group=2.0&nonsense=1")
    assert [e["param"] for e in run.json()["errors"]] == ["nonsense"]  # maturity_group is the crop model's
    refused = client.get("/api/v2/grids/tar-spot?black_layer_gdd=2500").json()["errors"][0]
    assert refused["code"] == "not_applicable"
    assert client.get("/api/v2/grids/not-a-layer?x=1").json()["errors"][0]["code"] == "unknown_layer"


@pytest.mark.parametrize(
    ("sent", "end", "expected"),
    [
        ("2026-04-15", date(2026, 11, 5), date(2026, 4, 15)),
        ("04-15", date(2026, 11, 5), date(2026, 4, 15)),
        ("4-5", date(2026, 11, 5), date(2026, 4, 5)),
        ("11-20", date(2026, 11, 5), date(2025, 11, 20)),  # after the end: last year's
        ("11-05", date(2026, 11, 5), date(2026, 11, 5)),  # on the end day: this year's
        (None, date(2026, 11, 5), None),
    ],
)
def test_a_biofix_is_a_date_or_the_latest_month_and_day(sent, end, expected):
    assert resolve_biofix(sent, end) == expected


@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        ("2025-07-08T15:00Z", "2025-07-08T15:00"),
        ("2025-07-08T15Z", "2025-07-08T15:00"),
        ("2025-07-08T15", "2025-07-08T15:00"),  # no zone: UTC
        ("2025-07-08 15:00", "2025-07-08T15:00"),
        ("2025-07-08T10:00-05:00", "2025-07-08T15:00"),
        ("20250708T15", "2025-07-08T15:00"),
        ("2025-07-08", "2025-07-08T00:00"),  # a date: its midnight
        ("1751986800", "2025-07-08T15:00"),  # Unix time, seconds
        ("1751986800000", "2025-07-08T15:00"),  # and milliseconds
        (1751986800, "2025-07-08T15:00"),  # a JSON number
    ],
)
def test_one_parser_takes_every_form_of_an_hour(sent, expected):
    assert parse_hour(sent, "start").strftime("%Y-%m-%dT%H:%M") == expected


@pytest.mark.parametrize("sent", ["nonsense", "1751986801", "2025-07-08T15:30Z"])
def test_a_time_that_isnt_a_whole_hour_is_refused(sent):
    with pytest.raises(ApiError) as found:
        parse_hour(sent, "start")
    assert found.value.param == "start" and found.value.message.startswith("The value of start (")


def test_points_and_maps_read_hours_alike(client, archive):
    hourly = client.get(
        "/api/v2/weather/hourly", {"lat": POINT[0], "lng": POINT[1], "start": "1751986800", "end": "2025-07-08T16"}
    ).json()
    assert hourly["meta"]["request"]["start"] == "2025-07-08T15:00Z"
    grid = client.get("/api/v2/grids/air_temperature_hourly", {"time": "1751986800"}).json()
    assert grid["meta"]["request"]["time"] == "2025-07-08T15:00Z"
