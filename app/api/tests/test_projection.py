"""Projection past the forecast (D63; PLAN.md Phase 5 D P3) on a fixture archive with this season (observed July
1–10, 2025, then a forecast to about July 21) and two earlier years' July and August: 2023 at 12 °C ± 6 with an
11-day hole (July 28 – August 7), 2024 at 18 °C ± 6."""

from datetime import date

import pytest

from api.tests.fixture_archive import POINT

LAT, LNG = POINT
BLIGHT = {"lat": LAT, "lng": LNG, "biofix": "2025-07-02", "end": "2025-08-20"}


def get(client, model_id, **params):
    return client.get(f"/api/v2/models/{model_id}/run", params)


def test_a_band_of_past_years_after_the_forecast(client, projection_archive):
    body = get(client, "early-blight-pdays", **BLIGHT, projection="true").json()
    data, meta = body["data"], body["meta"]
    projected = [k for k, kind in enumerate(data["kind"]) if kind == "projection"]
    assert projected and data["kind"][projected[0] - 1] == "forecast" and projected[-1] == len(data["date"]) - 1
    projection = meta["summary"]["projection"]
    assert projection["mode"] == "band" and projection["years"] == [2023, 2024]
    assert projection["start"] == data["date"][projected[0]]
    k = projected[0] + 2
    assert data["pdays_p10"][k] <= data["pdays"][k] <= data["pdays_p90"][k]
    assert data["pdays_p10"][k] < data["pdays_p90"][k]  # 2023 cooler than 2024
    assert data["pdays_p10"][0] is None and data["projection_years"][0] is None  # before the projection
    assert data["projection_years"][k] == 2
    hole = data["date"].index("2025-08-01")
    assert data["projection_years"][hole] == 1  # 2023 has nothing there, and 11 days is too long to bridge
    assert meta["units"]["pdays_p10"] == meta["units"]["pdays"]
    totals = data["pdays_total"]
    assert totals[projected[0]] > totals[projected[0] - 1]  # it carries on from this season's total
    assert {m["name"] for m in projection["milestones"]} == {"Low", "Moderate", "High", "Very high"}
    assert meta["warnings"] == [] and meta["request"]["projection"] == "band"


def test_each_past_years_path(client, projection_archive):
    data = get(client, "early-blight-pdays", **BLIGHT, projection="years").json()["data"]
    assert sorted(set(data["year"])) == [2023, 2024]
    n = data["year"].count(2023)
    assert n == data["year"].count(2024) and data["date"][:n] == data["date"][n:]
    k = data["kind"].index("projection") + 2
    assert data["pdays"][k] < data["pdays"][n + k]  # the cooler year's P-days
    assert "pdays_p10" not in data


def test_the_default_end_is_the_seasons(client, projection_archive):
    meta = get(client, "early-blight-pdays", lat=LAT, lng=LNG, biofix="2025-07-02", projection="true").json()["meta"]
    assert meta["request"]["end"] == "2025-09-30"  # early blight's season ends September 30


def test_nothing_to_project_and_bad_values(client, projection_archive):
    short = get(
        client, "early-blight-pdays", lat=LAT, lng=LNG, biofix="2025-07-02", end="2025-07-15", projection="true"
    )
    assert any("nothing to project" in w for w in short.json()["meta"]["warnings"])
    bad = get(client, "early-blight-pdays", lat=LAT, lng=LNG, projection="maybe")
    assert bad.status_code == 422 and bad.json()["errors"][0]["param"] == "projection"


def test_a_projected_run_revalidates(client, projection_archive):
    first = get(client, "early-blight-pdays", **BLIGHT, projection="true")
    again = client.get(
        "/api/v2/models/early-blight-pdays/run", {**BLIGHT, "projection": "true"}, HTTP_IF_NONE_MATCH=first["ETag"]
    )
    assert again.status_code == 304


@pytest.mark.parametrize("model_id", ["corn-stages", "tar-spot", "seedcorn-maggot", "degree-days", "late-blight-dsv"])
def test_models_of_each_kind_project(client, projection_archive, model_id):
    params = {"lat": LAT, "lng": LNG, "start": "2025-07-05", "end": "2025-08-20", "projection": "true"}
    if model_id == "corn-stages":
        params["planting_date"] = "2025-05-01"
    body = get(client, model_id, **params).json()
    assert "projection" in body["data"]["kind"], body["meta"]["warnings"]
    assert body["meta"]["summary"]["projection"]["years"] == [2023, 2024]
    assert date.fromisoformat(body["data"]["date"][-1]) == date(2025, 8, 20)


def test_several_models_project_together(client, projection_archive):
    body = client.get(
        "/api/v2/models/run",
        {
            "lat": LAT,
            "lng": LNG,
            "models": "early-blight-pdays,degree-days",
            "start": "2025-07-05",
            "end": "2025-08-20",
            "projection": "true",
        },
    ).json()
    for model_id in ("early-blight-pdays", "degree-days"):
        answer = body["data"][model_id]
        assert "projection" in answer["data"]["kind"] and answer["meta"]["summary"]["projection"]["years"] == [
            2023,
            2024,
        ]
    assert "dd_total_p90" in body["data"]["degree-days"]["data"]


def test_degree_days_project_with_targets(client, projection_archive):
    params = {
        "lat": LAT,
        "lng": LNG,
        "dd": "sine_50",
        "start": "2025-07-01",
        "end": "2025-08-31",
        "targets": "300,600",
    }
    plain = client.get("/api/v2/degree-days", params).json()
    assert [t["reached"] for t in plain["meta"]["summary"]["targets"]] == [1, 0]  # 300 within the forecast
    body = client.get("/api/v2/degree-days", {**params, "projection": "true"}).json()
    data, summary = body["data"], body["meta"]["summary"]
    k = data["kind"].index("projection") + 3
    assert data["dd_sine_50_cum_p10"][k] < data["dd_sine_50_cum"][k] < data["dd_sine_50_cum_p90"][k]
    assert data["projection_years"][k] == 2 and data["projection_years"][data["date"].index("2025-08-01")] == 1
    later = summary["targets"][1]
    assert later["target"] == 600 and later["of"] == 2 and later["reached"] >= 1 and later["p50"] > "2025-07-21"
    assert summary["projection"]["years"] == [2023, 2024]
    years = client.get("/api/v2/degree-days", {**params, "projection": "years"}).json()["data"]
    assert sorted(set(years["year"])) == [2023, 2024]


def test_risk_past_the_forecast(client, projection_archive):
    params = {"lat": LAT, "lng": LNG, "date": "2025-08-10", "models": "early-blight-pdays,tar-spot"}
    plain = client.get("/api/v2/risk", params).json()["data"]
    assert plain["kind"] == [None, None] and plain["risk_level"][1] is None  # past the forecast: no data
    data = client.get("/api/v2/risk", {**params, "projection": "true"}).json()["data"]
    assert data["kind"] == ["projection", "projection"] and data["projection_years"] == [2, 2]
    assert all(level is not None for level in data["risk_level"])
    hole = client.get("/api/v2/risk", {**params, "date": "2025-08-01", "projection": "true"}).json()["data"]
    # Inside 2023's hole: early blight's daily P-days need that day; tar spot's 30-day means span the gap
    assert hole["projection_years"] == [1, 2]


def test_the_copies_laid_out_for_points_give_the_same_projection(client, projection_archive, tmp_path):
    from agdata import pastyears

    first = get(client, "early-blight-pdays", **BLIGHT, projection="years")
    before = first.json()["data"]
    copy_dir = tmp_path / "with-copies"  # the archive (read only, so linked: 20,000 files) and the copies
    copy_dir.mkdir()
    for entry in projection_archive.iterdir():
        (copy_dir / entry.name).symlink_to(entry)
    for year in (2023, 2024):
        pastyears.build(copy_dir, year)
    from django.conf import settings

    settings.DATA_DIR = copy_dir
    answer = get(client, "early-blight-pdays", **BLIGHT, projection="years")
    assert answer["ETag"] != first["ETag"]  # past years are stamped by what's read: the copies now
    after = answer.json()["data"]
    # The copies hold the daily store's packed values: the same days, to the stored precision
    assert after["year"] == before["year"] and after["kind"] == before["kind"]
    assert after["pdays_total"] == pytest.approx(before["pdays_total"], abs=0.5, nan_ok=True)


def test_a_projection_at_several_points_has_each_points_summary(client, projection_archive):
    from agdata.grid import NDFD

    other = tuple(round(float(v), 4) for v in NDFD.latlon(901, 1402))
    params = {k: v for k, v in BLIGHT.items() if k not in ("lat", "lng")}
    body = get(client, "early-blight-pdays", points=f"{LAT},{LNG};{other[0]},{other[1]}", **params, projection="true")
    data, meta = body.json()["data"], body.json()["meta"]
    alone = get(client, "early-blight-pdays", **BLIGHT, projection="true").json()
    rows = [n for n, p in enumerate(data["point"]) if p == 0]
    assert [data["pdays_p90"][n] for n in rows] == alone["data"]["pdays_p90"]
    assert set(data["point"]) == {0, 1} and "projection" not in meta["summary"]
    for point in meta["summary"]["points"]:
        assert point["projection"]["years"] == [2023, 2024] and point["projection"]["milestones"]
