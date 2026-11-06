"""Seasonal products' maps (PLAN.md Phase 4 H, D68) on a winter archive (`agdata.testing.winters`): potato
volunteer's 2023-24 at one hour a day below 27 °F at every depth, 2024-25 at two, 2025-26 at three, observed
through December 15, 2025, with ERA5-Land's soil through the spring and IFS's after."""

from datetime import UTC, datetime

import numpy as np
import pytest

from agdata import testing

NOW = datetime(2025, 12, 17, 12, tzinfo=UTC)


@pytest.fixture
def winters(winters_dir, settings, monkeypatch):
    settings.DATA_DIR = winters_dir
    settings.SERVICE_BOX = "42.84,-91.69,42.866,-91.627"
    monkeypatch.setattr("api.clock.now", lambda: NOW)
    return winters_dir


def get(client, **params):
    return client.get("/api/v2/grids/potato-volunteer", params)


def test_the_default_map_is_the_settled_winter_until_january(client, winters):
    body = get(client, output="killing_hours_4cm").json()
    season = body["meta"]["summary"]["season"]
    assert season["name"] == "2024-25" and season["label"] == "2024–25" and season["final"] is True
    assert season["through"] == "2025-03-31" and body["meta"]["request"]["date"] == "2025-03-31"
    assert set(body["data"]["potato-volunteer"]) == {2 * 151}
    assert set(get(client).json()["data"]["potato-volunteer"]) == {0}  # Low: 120 hours at every depth


def test_the_open_winter_by_season_is_its_count_so_far(client, winters):
    body = get(client, season="2025-26", output="killing_hours_4cm").json()
    assert set(body["data"]["potato-volunteer"]) == {3 * 45}
    season = body["meta"]["summary"]["season"]
    assert season["through"] == "2025-12-15" and season["final"] is False and season["appears"] == "2026-01-01"
    by_date = get(client, date="2025-12-10", output="killing_hours_4cm").json()
    assert set(by_date["data"]["potato-volunteer"]) == {3 * 40}
    assert any("2025–26 season isn't over" in w for w in by_date["meta"]["warnings"])


def test_the_open_winter_projected_on_the_earlier_ones(client, winters):
    body = get(client, season="2025-26", output="projected_killing_hours_4cm").json()
    expected = np.median([3 * 45 + 2 * 106, 3 * 45 + 107])  # 2024-25's and 2023-24's December 16 to March 31
    assert set(body["data"]["potato-volunteer"]) == {expected}
    assert body["meta"]["summary"]["projection"]["seasons"] == ["2024-25", "2023-24"]
    chance = get(client, season="2025-26", output="chance_low").json()["data"]["potato-volunteer"]
    assert set(chance) == {100}


@pytest.mark.django_db
def test_seasons_are_listed_and_refused_where_they_dont_apply(client, winters):
    layers = {layer["id"]: layer for layer in client.get("/api/v2/layers").json()["data"]}
    assert layers["potato-volunteer"]["seasons"] == ["2023-24", "2024-25", "2025-26"]
    assert layers["late-blight-dsv"]["seasons"] == []
    outputs = [o["name"] for o in layers["potato-volunteer"]["outputs"]]
    assert outputs[0] == "risk_level" and "projected_risk_level" in outputs and "chance_very_high" in outputs

    def refused(**params):
        response = get(client, **params)
        assert response.status_code in (404, 422), params
        return response.json()["errors"][0]

    assert refused(date="2025-12-20")["code"] == "not_observed"  # observed days only
    assert refused(season="2025-26", date="2025-12-10")["code"] == "conflict"
    assert refused(season="2025")["param"] == "season"
    assert refused(season="2026-27")["code"] == "not_yet"
    assert refused(start="2025-12-01", end="2025-12-10", output="chance_low")["param"] == "output"
    assert refused(date="2025-07-04", output="chance_low")["param"] == "output"  # between seasons
    other = client.get("/api/v2/grids/late-blight-dsv", {"season": "2025-26"})
    assert other.status_code == 422 and other.json()["errors"][0]["param"] == "season"


def run(client, **params):
    lat, lng = _point()
    return client.get("/api/v2/models/potato-volunteer/run", {"lat": lat, "lng": lng, **params})


def _point():
    from agdata.grid import NDFD

    return tuple(round(float(v), 4) for v in NDFD.latlon(testing.WINDOW.j0, testing.WINDOW.i0 + 1))


@pytest.mark.django_db
def test_a_point_runs_the_current_season_and_agrees_with_the_map(client, winters):
    body = run(client).json()
    season = body["meta"]["summary"]["season"]
    assert season["name"] == "2024-25" and season["final"] is True
    assert body["meta"]["request"]["start"] == "2024-11-01" and body["meta"]["request"]["end"] == "2025-03-31"
    assert body["data"]["killing_hours_4cm"][-1] == 2 * 151
    open_one = run(client, season="2025-26", forecast="false").json()  # the archive's days only: no network
    assert open_one["meta"]["request"]["start"] == "2025-11-01"
    assert open_one["data"]["killing_hours_4cm"][-1] == 3 * 45
    assert run(client, season="2025-26", start="2025-11-01").status_code == 422
