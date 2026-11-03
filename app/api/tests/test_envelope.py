"""The plumbing every endpoint shares (PLAN.md Phase 5 A), through the test-only API on the fixture archive."""

import csv
import io

import pytest

from agdata import series
from agdata.grid import NDFD
from api import envelope, locations
from api.tests.conftest import NOW, POINT

pytestmark = pytest.mark.urls("api.tests.routes")
LAT, LNG = POINT


def get(client, http_headers=None, **params):
    return client.get("/api/test/days", {"lat": LAT, "lng": LNG, **params}, headers=http_headers)


def test_the_envelope_holds_the_request_as_computed_the_cell_units_summary_and_columns(client, archive):
    response = get(client, start="2025-07-08", end="2025-07-11")
    assert response.status_code == 200
    body = response.json()
    meta, data = body["meta"], body["data"]
    assert meta["request"] == {
        "lat": LAT,
        "lng": LNG,
        "start": "2025-07-08",
        "end": "2025-07-11",
        "vars": ["air_temperature_max", "precipitation_sum"],
        "units": "us",
    }
    assert meta["location"]["cell"] == {"j": 900, "i": 1401, "lat": LAT, "lng": LNG}
    assert meta["location"]["in_box"] is True and meta["location"]["timezone"] == "America/Chicago"
    assert meta["location"]["state"] is not None
    assert meta["units"] == {"air_temperature_max": "°F", "precipitation_sum": "in"}
    assert meta["api_version"] == "2.0" and "Copernicus" in meta["attribution"]
    assert meta["sources"] == ["urma", "nbm"] and meta["warnings"] == []
    assert isinstance(meta["compute_ms"], int) and meta["generated_at"].endswith("Z")
    assert data["date"] == ["2025-07-08", "2025-07-09", "2025-07-10", "2025-07-11"]
    assert data["kind"] == ["observed", "observed", "partial", "forecast"]
    assert data["air_temperature_max"][:2] == [69.8, 69.8]  # 21 °C, to the 0.1 °C stored (1 decimal in °F)
    assert data["precipitation_sum"][0] == 0.0945  # 2.4 mm, to the 0.01 mm stored (4 decimals in inches)
    summary = meta["summary"]
    assert summary["days_requested"] == 4
    assert summary["missing"] == {"air_temperature_max": 0, "precipitation_sum": 0}
    assert summary["stats"]["air_temperature_max"]["min"] == 69.8
    assert summary["stats"]["air_temperature_max"]["max"] == 87.8  # the forecast's 31 °C
    assert "total" in summary["stats"]["precipitation_sum"]
    assert "total" not in summary["stats"]["air_temperature_max"]


def test_metric_units_and_overrides_by_variable_or_its_prefix(client, archive):
    data = get(client, date="2025-07-08", units="metric").json()
    assert data["meta"]["units"] == {"air_temperature_max": "°C", "precipitation_sum": "mm"}
    assert data["data"]["air_temperature_max"] == [21.0] and data["data"]["precipitation_sum"] == [2.4]

    # precipitation (the hourly name) covers precipitation_sum; a unit's label works as well as its symbol
    data = get(client, date="2025-07-08", precipitation="mm", air_temperature_max="°C").json()
    assert data["meta"]["units"] == {"air_temperature_max": "°C", "precipitation_sum": "mm"}
    assert data["meta"]["request"]["units"] == "us"
    data = get(client, date="2025-07-08", units="metric", precipitation="us").json()
    assert data["meta"]["units"]["precipitation_sum"] == "in"


def test_an_override_in_a_unit_of_another_dimension_is_refused(client, archive):
    response = get(client, date="2025-07-08", precipitation="degF")
    assert response.status_code == 422
    (error,) = response.json()["errors"]
    assert error["code"] == "bad_unit" and error["param"] == "precipitation"
    assert "mm" in error["message"] and "in" in error["message"]


def test_missing_is_null_in_json_and_empty_in_csv(client, archive):
    # July 21 and 22 run past the run's last hour (July 21 13Z): no value, not 0
    body = get(client, start="2025-07-20", end="2025-07-22").json()
    assert body["data"]["air_temperature_max"][1:] == [None, None] and body["data"]["kind"][1:] == [None, None]
    assert body["meta"]["summary"]["missing"]["air_temperature_max"] == 2
    rows = list(
        csv.reader(io.StringIO(get(client, start="2025-07-22", end="2025-07-22", format="csv", headers="false").text))
    )
    assert rows == [["date", "kind", "air_temperature_max", "precipitation_sum"], ["2025-07-22", "", "", ""]]


def test_records_orient_gives_one_object_per_row(client, archive):
    data = get(client, start="2025-07-08", end="2025-07-09", orient="records").json()["data"]
    assert data == [
        {"date": "2025-07-08", "kind": "observed", "air_temperature_max": 69.8, "precipitation_sum": 0.0945},
        {"date": "2025-07-09", "kind": "observed", "air_temperature_max": 69.8, "precipitation_sum": 0.0945},
    ]


def test_csv_puts_meta_in_comment_lines_and_names_the_file(client, archive):
    response = get(client, start="2025-07-08", end="2025-07-09", format="csv")
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert response["Content-Disposition"] == 'attachment; filename="agweather-days-2025-07-08-2025-07-09.csv"'
    lines = response.text.splitlines()
    comments = [line for line in lines if line.startswith("#")]
    assert comments[0].startswith('# request: {"lat":')
    assert '# units: {"air_temperature_max":"°F","precipitation_sum":"in"}' in comments
    assert lines[len(comments)] == "date,kind,air_temperature_max,precipitation_sum"
    assert lines[len(comments) + 1] == "2025-07-08,observed,69.8,0.0945"

    # The Accept header picks CSV when format isn't given; format wins over it
    negotiated = get(client, date="2025-07-08", http_headers={"Accept": "text/csv"})
    assert negotiated["Content-Type"].startswith("text/csv") and "Accept" in negotiated["Vary"]
    assert (
        get(client, date="2025-07-08", format="json", http_headers={"Accept": "text/csv"})["Content-Type"]
        == "application/json"
    )


def test_a_format_not_offered_is_refused(client, archive):
    response = get(client, date="2025-07-08", format="xml")
    assert response.status_code == 422
    assert response.json()["errors"][0] | {"message": ""} == {
        "code": "format_unavailable",
        "param": "format",
        "message": "",
    }


def test_several_points_come_back_as_one_long_table(client, archive):
    other = tuple(round(float(v), 4) for v in NDFD.latlon(901, 1402))
    response = client.get("/api/test/days", {"points": f"{LAT},{LNG};{other[0]},{other[1]}", "date": "2025-07-08"})
    body = response.json()
    assert body["meta"]["request"]["points"] == [[LAT, LNG], list(other)]
    assert [loc["cell"]["j"] for loc in body["meta"]["locations"]] == [900, 901]
    assert "location" not in body["meta"]
    assert body["data"]["point"] == [0, 1] and body["data"]["date"] == ["2025-07-08"] * 2


@pytest.mark.parametrize("alias", ["lon", "long", "longitude"])
def test_v1_longitude_names_are_accepted_and_echoed_as_lng(client, archive, alias):
    response = client.get("/api/test/days", {"latitude": LAT, alias: LNG, "date": "2025-07-08"})
    assert response.status_code == 200
    assert response.json()["meta"]["request"]["lng"] == LNG


@pytest.mark.parametrize(
    ("params", "code", "param"),
    [
        ({"lng": -89.4}, "missing", "lat"),
        ({"lat": 43.0}, "missing", "lng"),
        ({"lat": 95, "lng": -89.4}, "out_of_range", "lat"),
        ({"lat": 43, "lng": -200}, "out_of_range", "lng"),
        ({"lat": "north", "lng": -89.4}, "float_parsing", "lat"),
        ({"lat": 43, "lng": -89.4, "points": "43,-89"}, "conflict", "points"),
        ({"points": ";".join(["43,-89"] * 51)}, "too_many", "points"),
        ({"points": "43,-89;43"}, "invalid", "points"),
        ({"lat": 43, "lng": -89.4, "start": "2025-07-09", "end": "2025-07-08"}, "out_of_order", "start"),
        ({"lat": 43, "lng": -89.4, "date": "2025-07-08", "end": "2025-07-09"}, "conflict", "date"),
        ({"lat": 43, "lng": -89.4, "start": "July 8"}, "date_from_datetime_parsing", "start"),
        ({"lat": 43, "lng": -89.4, "units": "imperial"}, "literal_error", "units"),
        ({"lat": 43, "lng": -89.4, "gaps": "fill"}, "literal_error", "gaps"),
        ({"lat": 43, "lng": -89.4, "vars": "air_temperature_max,tmax"}, "unknown_variable", "vars"),
    ],
)
def test_errors_name_their_parameter_in_the_envelope(client, archive, params, code, param):
    response = client.get("/api/test/days", params)
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"meta", "errors"} and "detail" not in body
    assert body["meta"]["api_version"] == "2.0" and body["meta"]["request"] == {k: str(v) for k, v in params.items()}
    assert [(e["code"], e["param"]) for e in body["errors"]] == [(code, param)]
    assert body["errors"][0]["message"]
    assert response["Cache-Control"] == "no-store"


def test_an_unknown_variable_lists_the_valid_ones(client, archive):
    message = get(client, vars="tmax").json()["errors"][0]["message"]
    assert "tmax" in message and "air_temperature_max" in message and "hours_rh_over_90" in message


def test_an_unexpected_error_is_a_500_envelope_without_internals(client, archive, caplog):
    response = client.get("/api/test/broken")
    assert response.status_code == 500
    error = response.json()["errors"][0]
    assert error["code"] == "internal_error" and "secret" not in error["message"]
    assert "secret internals" in caplog.text  # logged for us


def test_server_timing_and_cache_headers(client, archive):
    response = get(client, start="2025-07-08", end="2025-07-09")
    assert response["Server-Timing"].startswith("read;dur=1.5, total;dur=")
    assert response["Cache-Control"] == "public, no-cache"  # kept, but checked with us before each reuse
    etag = response["ETag"]
    assert get(client, start="2025-07-08", end="2025-07-09")["ETag"] == etag  # the same data, code and request
    assert get(client, start="2025-07-08", end="2025-07-10")["ETag"] != etag
    assert get(client, start="2025-07-08", end="2025-07-09", format="csv")["ETag"] != etag
    assert get(client, start="2025-07-08", end="2025-07-09", units="metric")["ETag"] != etag


def test_a_held_answer_is_confirmed_with_a_304_before_anything_is_read(client, archive, monkeypatch):
    etag = get(client, start="2025-07-08", end="2025-07-09")["ETag"]
    monkeypatch.setattr(series, "point_days", lambda *a, **k: pytest.fail("read the data for a 304"))
    unchanged = get(client, start="2025-07-08", end="2025-07-09", http_headers={"If-None-Match": etag})
    assert unchanged.status_code == 304 and unchanged["ETag"] == etag and not unchanged.content
    assert unchanged["Cache-Control"] == "public, no-cache"


def test_the_etag_changes_with_the_data_read_or_the_code(client, archive, monkeypatch):
    etag = get(client, start="2025-07-08", end="2025-07-09")["ETag"]
    monkeypatch.setattr(series, "last_written", lambda *a, **k: "rewritten")  # an ingest or rebuild touched them
    assert get(client, start="2025-07-08", end="2025-07-09", http_headers={"If-None-Match": etag}).status_code == 200
    monkeypatch.undo()
    monkeypatch.setattr("api.clock.now", lambda: NOW)
    assert get(client, start="2025-07-08", end="2025-07-09")["ETag"] == etag
    monkeypatch.setattr(envelope, "CODE_VERSION", "a-new-deploy")
    assert get(client, start="2025-07-08", end="2025-07-09")["ETag"] != etag


def test_a_point_off_the_grid_or_outside_the_box(archive):
    paris = locations.describe(48.85, 2.35)
    assert paris["cell"] is None and paris["in_box"] is False and paris["county"] is None
    madison = locations.describe(43.07, -89.4)
    assert madison["cell"] is not None and madison["in_box"] is False  # on the grid, outside the test box
    assert (madison["county"], madison["state"]) == ("Dane County", "WI")


@pytest.mark.parametrize(
    ("step", "stored", "shown", "digits"),
    [
        (0.1, "degC", "degC", 1),
        (0.1, "degC", "degF", 1),  # 0.18 °F
        (0.1, "mm", "in", 3),  # 0.0039 in
        (0.2, "mm", "in", 3),
        (1, "hour", "hour", 0),
        (0.5, "degF_day", "degC_day", 1),
        (0.1, "m_s", "mph", 1),  # 0.22 mph
        (0.01, "kPa", "inHg", 3),
    ],
)
def test_rounding_keeps_the_stored_precision_in_the_unit_shown(step, stored, shown, digits):
    assert envelope.digits_for(step, stored, shown) == digits


def test_dew_point_depression_converts_as_a_difference(client, archive):
    data = get(client, date="2025-07-08", vars="dew_point_depression_mean").json()
    assert data["meta"]["units"] == {"dew_point_depression_mean": "°F"}
    assert data["data"]["dew_point_depression_mean"] == [7.2]  # 4 °C apart is 7.2 °F apart, not 39.2
