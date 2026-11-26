"""Days still missing after the gap fill (D56) at points and on maps, on the projection archive: 2023's July and
August have an 11-day hole (July 28 – August 7 UTC, 12 grid days with the partial ones at each end), 2024's none.
Posted weather's flags are in `test_station_runs`."""

import pytest

from api.tests.fixture_archive import POINT

LAT, LNG = POINT
HOLE_DAYS = 12
MAP_WARNING = "At 6 grid cells on this map, the weather data the model reads have days missing (up to 12 days), in gaps longer than the 7 days we fill with estimates. The model's running totals add nothing for those days, so its results there may be late."


def test_a_run_over_the_hole_flags_its_days_and_warns(client, projection_archive):
    body = client.get(
        "/api/v2/models/black-cutworm/run", {"lat": LAT, "lng": LNG, "start": "2023-07-15", "end": "2023-08-20"}
    ).json()
    data, meta = body["data"], body["meta"]
    flagged = [d for d, gone in zip(data["date"], data["air_temperature_max_missing"], strict=True) if gone]
    assert flagged[0] == "2023-07-27" and flagged[-1] == "2023-08-07" and len(flagged) == HOLE_DAYS
    assert data["air_temperature_min_missing"] == data["air_temperature_max_missing"]
    assert list(data)[2:6] == [  # after the inputs, as `_estimated` flags are
        "air_temperature_min",
        "air_temperature_max",
        "air_temperature_min_missing",
        "air_temperature_max_missing",
    ]
    assert meta["summary"]["missing_by_input"] == {"air_temperature_min": HOLE_DAYS, "air_temperature_max": HOLE_DAYS}
    assert any(w.startswith("The weather data have 12 days of 'air_temperature_min' and") for w in meta["warnings"])


def test_a_year_without_a_hole_has_no_flags(client, projection_archive):
    body = client.get(
        "/api/v2/models/black-cutworm/run", {"lat": LAT, "lng": LNG, "start": "2024-07-15", "end": "2024-08-20"}
    ).json()
    assert not any(name.endswith("_missing") for name in body["data"])
    assert "missing_by_input" not in body["meta"]["summary"]
    assert not any("gaps longer than" in w for w in body["meta"]["warnings"])


def test_several_points_name_the_one_with_the_hole(client, projection_archive):
    """The same cell twice: both have it, so the warning names neither."""
    points = f"{LAT},{LNG};{LAT},{LNG}"
    body = client.get(
        "/api/v2/models/black-cutworm/run", {"points": points, "start": "2023-08-10", "end": "2023-08-20"}
    ).json()
    warnings = [w for w in body["meta"]["warnings"] if "gaps longer than" in w]
    assert len(warnings) == 1 and warnings[0].startswith("The weather data have 12 days")  # all before the start
    assert body["meta"]["summary"]["missing_by_input"]["air_temperature_max"] == 2 * HOLE_DAYS


def test_risk_counts_each_models_days(client, projection_archive):
    models = "black-cutworm,early-blight-pdays"
    body = client.get("/api/v2/risk", {"lat": LAT, "lng": LNG, "date": "2023-08-20", "models": models}).json()
    assert body["data"]["missing_days"] == [HOLE_DAYS, HOLE_DAYS]
    assert (
        "The weather data that 'black-cutworm' and 'early-blight-pdays' read have days missing (up to 12 days), in gaps longer than the 7 days we fill with estimates, so the running totals add nothing for those days and the risk may be late. The 'missing_days' column gives each model's count."
        in body["meta"]["warnings"]
    )
    clean = client.get("/api/v2/risk", {"lat": LAT, "lng": LNG, "date": "2024-08-20", "models": models}).json()
    assert clean["data"]["missing_days"] == [0, 0] and not any("gaps longer" in w for w in clean["meta"]["warnings"])


@pytest.mark.parametrize("model", ["black-cutworm", "alfalfa-growth"])
def test_a_degree_day_map_over_the_hole_warns(client, projection_archive, model):
    hole = client.get(f"/api/v2/grids/{model}", {"date": "2023-08-20"}).json()
    assert MAP_WARNING in hole["meta"]["warnings"]
    before = client.get(f"/api/v2/grids/{model}", {"date": "2023-07-20"}).json()  # the days before it are whole
    clean = client.get(f"/api/v2/grids/{model}", {"date": "2024-08-20"}).json()
    assert not any("gaps longer" in w for w in before["meta"]["warnings"] + clean["meta"]["warnings"])


def test_a_summary_of_a_map_over_the_hole_warns(client, projection_archive):
    body = client.get(
        "/api/v2/summaries/black-cutworm", {"date": "2023-08-20", "region": "19065", "min_coverage": 0}
    ).json()
    assert MAP_WARNING in body["meta"]["warnings"]
