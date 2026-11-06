"""Models at a point (PLAN.md Phase 5 D, D64) on the fixture archive: observed days July 1–10, 2025 (to 10 am
on the 10th), then the forecast to about July 21. Days before July 1 have no data."""

from datetime import timedelta

import numpy as np
import pytest

from agdata.series import DailySeries, Forecast
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
    assert body["meta"]["warnings"] == [
        "The crop hasn't reached EM, where the model starts, by the last day, so it has no output yet."
    ]
    assert all(v is None for v in body["data"]["pdays_total"])


def test_unknown_models_and_several_points(client, archive):
    missing = client.get("/api/v2/models/no-such-model/run", {"lat": LAT, "lng": LNG})
    assert missing.status_code == 404 and missing.json()["errors"][0]["code"] == "not_found"
    two = client.get("/api/v2/models/tar-spot/run", {"points": f"{LAT},{LNG};{LAT},{LNG}"})
    assert two.status_code == 422 and two.json()["errors"][0]["param"] == "points"


# --- Several models ------------------------------------------------------------------------------------------------


def several(client, **params):
    return client.get("/api/v2/models/run", {"lat": LAT, "lng": LNG, **params})


def test_several_models_each_with_its_own_table(client, archive):
    body = several(
        client, models="early-blight-pdays,tar-spot,corn-stages", start="2025-07-05", end="2025-07-12"
    ).json()
    assert list(body["data"]) == ["early-blight-pdays", "tar-spot", "corn-stages"]
    blight = body["data"]["early-blight-pdays"]
    assert blight["data"]["date"][0] == "2025-07-05" and "pdays_total" in blight["data"]
    assert blight["meta"]["request"]["model"] == "early-blight-pdays" and "pdays" in blight["meta"]["units"]
    assert "risk_level" not in body["data"]["corn-stages"]["data"]
    assert body["meta"]["request"]["models"] == ["early-blight-pdays", "tar-spot", "corn-stages"]
    assert body["meta"]["location"]["in_box"] is True and body["meta"]["sources"][:1] == ["urma"]
    # The same answer as one model alone
    alone = get(client, "early-blight-pdays", start="2025-07-05", end="2025-07-12").json()
    assert blight["data"] == alone["data"]


def test_a_planting_date_applies_to_models_with_a_crop(client, archive):
    body = several(
        client, models="tar-spot,degree-days,late-blight-dsv", planting_date="mid", start="2025-07-05", end="2025-07-06"
    ).json()
    assert "susceptibility" in body["data"]["tar-spot"]["data"]
    assert body["data"]["degree-days"]["meta"]["request"]["planting_date"] is None
    assert any("no typical potato" in w for w in body["data"]["late-blight-dsv"]["meta"]["warnings"])


def test_several_models_refuse_csv_and_unknown_ids(client, archive):
    csv = several(client, models="tar-spot,white-mold", format="csv", start="2025-07-05")
    assert csv.status_code == 422 and csv.json()["errors"][0]["code"] == "format_unavailable"
    unknown = several(client, models="tar-spot,nope")
    assert unknown.status_code == 404 or unknown.json()["errors"][0]["param"] == "models"


def test_models_run_is_not_taken_for_a_model_id(client, archive):
    response = client.get("/api/v2/models/run", {"lat": LAT, "lng": LNG, "models": "tar-spot", "start": "2025-07-05"})
    assert response.status_code == 200


# --- Risk ----------------------------------------------------------------------------------------------------------


@pytest.fixture
def no_open_meteo(monkeypatch):
    """Open-Meteo with nothing to give: potato volunteer's season begins October 1, before the fixture archive, so
    it alone reads Open-Meteo (ops.points), and gets missing days."""

    def point_days(lat, lng, first, last, names, now, zone=None):
        n = (last - first).days + 1
        dates = [first + timedelta(days=k) for k in range(n)]
        values = {name: np.full(n, np.nan) for name in names}
        return DailySeries(dates=dates, values=values, kinds=[None] * n, forecast=Forecast(path=None))

    monkeypatch.setattr("ops.points.openmeteo.point_days", point_days)


def test_risk_lists_models_in_season_and_in_region(client, archive, no_open_meteo):
    body = client.get("/api/v2/risk", {"lat": LAT, "lng": LNG, "date": "2025-07-08"}).json()
    data = body["data"]
    assert "tar-spot" in data["model"] and "early-blight-pdays" in data["model"]
    assert "pecan-scab" not in data["model"] and "corn-stages" not in data["model"]  # outside its region; no risk
    assert all(season is not False for season in data["in_season"])
    k = data["model"].index("early-blight-pdays")
    assert data["kind"][k] == "observed" and data["risk_label"][k] == "Very low" and data["reason"][k] is None
    assert body["meta"]["summary"]["models"] == len(data["model"]) and body["meta"]["request"]["models"] == "in season"


def test_risk_for_models_asked_includes_why_there_is_none(client, archive):
    data = client.get(
        "/api/v2/risk", {"lat": LAT, "lng": LNG, "date": "2025-07-08", "models": "pecan-scab,tar-spot"}
    ).json()["data"]
    assert data["model"] == ["pecan-scab", "tar-spot"]
    assert data["reason"][0] == "outside the model's region" and data["risk_level"][0] is None


def test_risk_with_a_planting_date_shows_susceptibility(client, archive):
    data = client.get(
        "/api/v2/risk",
        {"lat": LAT, "lng": LNG, "date": "2025-07-08", "models": "tar-spot", "planting_date": "2025-05-01"},
    ).json()["data"]
    assert data["susceptibility"][0] in ("not susceptible", "margin", "susceptible")


# --- Evaluate ------------------------------------------------------------------------------------------------------


def evaluate(client, model_id, inputs, **query):
    path = f"/api/v2/models/{model_id}/evaluate"
    if query:
        path += "?" + "&".join(f"{k}={v}" for k, v in query.items())
    return client.post(path, {"inputs": inputs}, content_type="application/json")


def test_evaluate_runs_the_models_core(client):
    body = evaluate(client, "early-blight-pdays", {"tmin": 9.0, "tmax": 21.0}, units="metric").json()
    assert body["data"]["pdays"] == [pytest.approx(OBSERVED_PDAYS, abs=0.001)]
    assert body["data"]["tmin"] == [9.0] and body["meta"]["units"]["tmin"] == "°C"
    assert body["meta"]["request"]["inputs"] == {"tmin": 9.0, "tmax": 21.0} and body["meta"]["warnings"] == []


def test_evaluate_takes_the_requests_units_and_sweeps_lists(client):
    body = evaluate(client, "degree-days", {"min_temp": 50, "max_temp": [70, 86, 100]}).json()  # °F by default
    data = body["data"]
    assert data["max_temp"] == [70, 86, 100] and len(data["sine"]) == 3
    assert data["average"][0] == pytest.approx(10, abs=0.1)  # (50 + 70) / 2 − 50, in °F·d
    assert body["meta"]["units"]["sine"] == "°F·d"
    metric = evaluate(client, "degree-days", {"min_temp": 10, "max_temp": 21.1111}, units="metric").json()
    assert metric["data"]["average"][0] == pytest.approx(10 / 1.8, abs=0.1)  # the same day, in °C·d


def test_evaluate_defaults_warnings_and_errors(client):
    defaults = evaluate(client, "late-blight-dsv", {}).json()
    assert all(len(v) == 1 for v in defaults["data"].values())
    assert all(v is not None for v in defaults["meta"]["request"]["inputs"].values())
    far = evaluate(client, "early-blight-pdays", {"tmin": 10, "tmax": 140}).json()  # °F: 140 is past its 40 °C
    assert any("tmax 140 is outside its usual" in w for w in far["meta"]["warnings"])
    unknown = evaluate(client, "early-blight-pdays", {"rain": 1})
    assert unknown.status_code == 422 and unknown.json()["errors"][0]["code"] == "unknown_input"
    big = evaluate(client, "early-blight-pdays", {"tmin": list(range(200)), "tmax": list(range(200))})
    assert big.status_code == 422 and big.json()["errors"][0]["code"] == "too_large"
    assert evaluate(client, "no-such-model", {}).status_code == 404


def test_crop_options_without_a_planting_date_run_once(client, archive):
    # The crop's stages need a planting date, so its options can't change the run: one run, with a warning
    body = get(client, "frogeye-leaf-spot", start="2025-07-01", end="2025-07-03", maturity_group="all").json()
    assert "option_sets" not in body["meta"]["summary"] and "option_set" not in body["data"]
    assert any("maturity_group" in w for w in body["meta"]["warnings"])


def test_a_biofix_for_a_model_without_one_and_too_many_option_sets_are_refused(client, archive):
    biofix = get(client, "cotton-planting", biofix="2025-05-01").json()["errors"][0]
    assert (biofix["code"], biofix["param"]) == ("not_applicable", "biofix")
    assert biofix["message"] == "The Cotton planting stand risk model doesn't take a biofix date. Leave out biofix."
    many = get(client, "soybean-stages", planting_date="2025-05-01", maturity_group="all", seeding_depth_in="all")
    error = many.json()["errors"][0]  # 9 maturity groups x 3 depths
    assert many.status_code == 422 and (error["code"], error["param"]) == ("too_many", "all")
    assert "27 combinations of options" in error["message"]


def test_all_needs_an_option_with_choices():
    from agmodels.spec import Option
    from api.errors import ApiError
    from api.runs import option_values

    typed = Option(name="threshold", label="Threshold", choices=(), default="10")
    assert option_values(typed, None, []) == ["10"] and option_values(typed, "12", []) == ["12"]
    with pytest.raises(ApiError, match="threshold has no list of choices, so it can't be set to all"):
        option_values(typed, "all", [])
