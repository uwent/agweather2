"""Models at a point (PLAN.md Phase 5 D, D64) on the fixture archive: observed days July 1–10, 2025 (to 10 am
on the 10th), then the forecast to about July 21. Days before July 1 have no data."""

import pytest

from agmodels.models.early_blight import pdays
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
OBSERVED_PDAYS = float(pdays(9.0, 21.0))  # the fixture's observed days run 9–21 °C


def get(client, model_id, **params):
    return client.get(f"/api/v2/models/{model_id}/run", {"lat": LAT, "lng": LNG, **params})


def test_a_disease_model_from_its_biofix_through_the_forecast(client, archive):
    response = get(client, "early-blight-pdays", biofix="2025-07-02", units="metric")
    assert response.status_code == 200
    body = response.json()
    data, meta = body["data"], body["meta"]
    assert list(data) == [
        "date",
        "kind",
        "air_temperature_min",
        "air_temperature_max",
        "pdays",
        "pdays_total",
        "pdays_7_day_mean",
        "risk_level",
        "risk_label",
        "in_season",
    ]
    assert data["date"][0] == "2025-07-02"  # the default start is the biofix
    assert data["kind"][:8] == ["observed"] * 8 and data["kind"][8] == "partial" and data["kind"][-1] == "forecast"
    assert data["pdays_total"][0] == pytest.approx(OBSERVED_PDAYS, abs=0.001)
    assert data["pdays_total"][1] == pytest.approx(2 * OBSERVED_PDAYS, abs=0.001)
    assert data["risk_label"][0] == "Very low" and data["risk_level"][0] == 0
    assert data["in_season"][0] is True
    assert meta["request"]["model"] == "early-blight-pdays" and meta["request"]["version"] == "0.2"
    assert meta["request"]["biofix"] == "2025-07-02" and meta["request"]["planting_date"] is None
    assert meta["units"]["air_temperature_min"] == "°C" and "risk_label" not in meta["units"]
    assert meta["sources"][:1] == ["urma"] and meta["location"]["in_box"] is True


def test_a_revalidated_run_is_not_recomputed(client, archive):
    first = get(client, "early-blight-pdays", biofix="2025-07-02")
    etag = first["ETag"]
    again = client.get(
        "/api/v2/models/early-blight-pdays/run",
        {"lat": LAT, "lng": LNG, "biofix": "2025-07-02"},
        HTTP_IF_NONE_MATCH=etag,
    )
    assert again.status_code == 304


def test_csv(client, archive):
    response = get(client, "early-blight-pdays", biofix="2025-07-02", format="csv", headers="false")
    lines = response.content.decode().splitlines()
    assert lines[0].startswith("date,kind,air_temperature_min") and lines[1].startswith("2025-07-02,observed,")


def test_options_are_checked_and_all_runs_every_choice(client, archive):
    response = get(client, "white-mold", irrigation="sometimes")
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["param"] == "irrigation" and "must be one of" in error["message"]
    body = get(client, "white-mold", irrigation="all", start="2025-07-05", end="2025-07-06").json()
    assert body["data"]["option_set"] == [0, 0, 1, 1]
    assert [s["irrigation"] for s in body["meta"]["summary"]["option_sets"]] == body["meta"]["request"]["options"][
        "irrigation"
    ]
    assert isinstance(body["meta"]["request"]["options"]["irrigation"], list)


def test_a_numeric_option_takes_any_number_with_a_warning_outside_its_choices(client, archive):
    body = get(client, "corn-stages", planting_date="2025-07-01", black_layer_gdd="9000", end="2025-07-05").json()
    assert any("black_layer_gdd=9000" in w for w in body["meta"]["warnings"])


def test_without_a_planting_date_there_is_no_susceptible_window(client, archive):
    plain = get(client, "tar-spot", start="2025-07-05", end="2025-07-08").json()
    assert "susceptibility" not in plain["data"] and plain["meta"]["request"]["planting_date"] is None
    planted = get(client, "tar-spot", planting_date="2025-05-01", start="2025-07-05", end="2025-07-08").json()
    assert set(planted["data"]["susceptibility"]) <= {"not susceptible", "margin", "susceptible", None}
    assert planted["meta"]["request"]["planting_date"] == {"date": "2025-05-01"}


def test_a_typical_planting_date_comes_with_its_source(client, archive):
    body = get(client, "tar-spot", planting_date="mid", start="2025-07-05", end="2025-07-06").json()
    echo = body["meta"]["request"]["planting_date"]
    assert echo["tier"] == "mid" and echo["date"].startswith("2025-0") and echo["source"]
    every = get(client, "tar-spot", planting_date="all", start="2025-07-05", end="2025-07-06").json()
    assert every["data"]["option_set"] == [0, 0, 1, 1, 2, 2]
    assert [s["planting_date"] for s in every["meta"]["summary"]["option_sets"]] == every["meta"]["request"][
        "planting_date"
    ]["date"]


def test_planting_dates_that_cannot_apply_are_refused(client, archive):
    no_crop = get(client, "late-blight-dsv", planting_date="early")  # potato: no typical dates near this point
    assert no_crop.status_code == 422 and no_crop.json()["errors"][0]["code"] == "no_estimate"
    none = get(client, "degree-days", planting_date="2025-05-01")
    assert none.status_code == 422 and none.json()["errors"][0]["code"] == "not_applicable"
    bad = get(client, "tar-spot", planting_date="soon")
    assert bad.status_code == 422 and bad.json()["errors"][0]["param"] == "planting_date"


def test_a_crop_model_shows_its_stage_codes(client, archive):
    data = get(client, "corn-stages", planting_date="2025-07-01", end="2025-07-05").json()["data"]
    assert data["date"][0] == "2025-07-01" and "stage_code" in data and "risk_level" not in data


def test_a_stage_biofix_not_reached_is_a_warning(client, archive):
    emerging = get(client, "early-blight-pdays", planting_date="2025-07-08").json()  # the warm forecast: up July 19
    assert emerging["meta"]["request"]["biofix"] == "2025-07-19" and emerging["meta"]["warnings"] == []
    body = get(client, "early-blight-pdays", planting_date="2025-07-18").json()  # not up by the forecast's end
    assert body["meta"]["warnings"] == ["no output: EM isn't reached in the series"]
    assert all(v is None for v in body["data"]["pdays_total"])


def test_unknown_models_and_several_points(client, archive):
    missing = client.get("/api/v2/models/no-such-model/run", {"lat": LAT, "lng": LNG})
    assert missing.status_code == 404 and missing.json()["errors"][0]["code"] == "not_found"
    two = client.get("/api/v2/models/tar-spot/run", {"points": f"{LAT},{LNG};{LAT},{LNG}"})
    assert two.status_code == 422 and two.json()["errors"][0]["param"] == "points"
