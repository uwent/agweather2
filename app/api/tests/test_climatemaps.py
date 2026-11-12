"""Climate on maps (D86, `api.climatemaps`): `climate=normal`, `departure` and `percentile` on `/grids`, the freeze
maps and elevation, over the fixture archive's five gridMET years and their normal maps (`last5`, and `last10` from
the same years; `fixture_archive.climate_values`: a maximum of 22 °C on average, 1 mm of rain a day, freezes on
January 1–10 and from December 20)."""

import shutil
from datetime import date

import numpy as np
import pytest
from django.conf import settings

from agdata import normals, terrain
from agdata.testing import WINDOW, terrain_store
from api.tests.fixture_archive import BOX

METRIC = {"units": "metric", "format": "json", "bbox": BOX}


def grid(client, layer, **params):
    return client.get(f"/api/v2/grids/{layer}", {**METRIC, **params})


def values(response) -> list:
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    name = next(k for k in data if k not in ("date", "kind", "lat", "lng", "estimated_days", "missing_days"))
    return data[name]


def error(response) -> dict:
    assert response.status_code >= 400, response.json()
    return response.json()["errors"][0]


def test_a_normal_takes_any_year_and_a_departure_only_the_archives(client, climate_archive):
    # A normal's date names a day of the year; a departure needs the day's weather (the archive is 2025 here)
    assert values(grid(client, "air_temperature_max", date="2010-07-15", climate="normal", period="last5"))
    found = error(grid(client, "air_temperature_max", date="2024-07-05", climate="departure", period="last5"))
    assert (found["code"], found["param"]) == ("out_of_range", "date")


def test_a_normal_map_reads_no_weather(client, climate_archive):
    response = grid(client, "air_temperature_max", date="2026-07-15", climate="normal", period="last5")
    assert values(response) == [22.0] * WINDOW.shape[0] * WINDOW.shape[1]
    meta = response.json()["meta"]
    assert meta["request"]["climate"] == "normal" and meta["request"]["years"] == "2020–2024"
    assert response.json()["data"]["kind"][0] == "normal"
    assert meta["sources"] == ["gridmet"]  # a date with no weather yet: only the normals were read


def test_a_departure_is_the_map_less_its_normal(client, climate_archive):
    plain = values(grid(client, "air_temperature_max", date="2025-07-05"))
    response = grid(client, "air_temperature_max", date="2025-07-05", climate="departure", period="last5")
    assert values(response) == pytest.approx([v - 22.0 for v in plain], abs=0.051)
    assert response.json()["meta"]["units"]["air_temperature_max"] == "°C"  # a difference: no offset in °F
    us = client.get(
        "/api/v2/grids/air_temperature_max",
        {"bbox": BOX, "date": "2025-07-05", "climate": "departure", "period": "last5"},
    ).json()["data"]["air_temperature_max"]
    assert us == pytest.approx([(v - 22.0) * 1.8 for v in plain], abs=0.6)


def test_sums_and_running_totals_against_their_normal(client, climate_archive):
    on = {"climate": "normal", "period": "last5"}
    june = grid(client, "precipitation_sum", start="2025-06-01", end="2025-06-30", stat="sum", **on)
    assert values(june) == pytest.approx([30.0] * 6)  # from the normal running total of precipitation
    mean = grid(client, "air_temperature_max", start="2025-06-01", end="2025-06-30", stat="mean", **on)
    assert values(mean) == pytest.approx([22.0] * 6)
    dd = grid(client, "degree_days", dd="modified_10_30", start="2025-01-01", end="2025-01-10", stat="sum", **on)
    assert values(dd) == pytest.approx([60.0] * 6, abs=0.5)  # 6 °C·d a day (10.8 °F·d), from the stored cube
    cube = grid(client, "dd_modified_50_86", date="2025-01-10", units="us", **on)
    stored = normals.read_map(settings.DATA_DIR, "last5", "dd_modified_50_86/mean", date(2025, 1, 10))
    assert values(cube) == pytest.approx(sorted(stored.ravel()), abs=0.05) == [108.0] * 6  # 10.8 °F·d a day


def test_a_percentile_places_the_map_among_the_years(client, climate_archive):
    # This year's archive has July only, so a total from January 1 is far below every past year's
    response = grid(
        client,
        "degree_days",
        dd="modified_50_86",
        start="2025-01-01",
        end="2025-07-05",
        stat="sum",
        climate="percentile",
        period="last10",
        units="us",
    )
    assert values(response) == [5.0] * 6  # under the 10th percentile
    assert response.json()["meta"]["units"]["degree_days"] == "%"


def test_climate_refusals(client, climate_archive):
    on = {"date": "2025-07-05", "period": "last5"}
    assert error(grid(client, "air_temperature_hourly", time="2025-07-05T12", climate="normal"))["param"] == "climate"
    assert error(grid(client, "air_temperature_max", climate="percentile", **on))["param"] == "climate"
    ranged = {"start": "2025-07-01", "end": "2025-07-05", "period": "last5"}
    assert error(grid(client, "air_temperature_max", stat="max", climate="normal", **ranged))["param"] == "stat"
    assert error(grid(client, "air_temperature_max", count="days_above_30", climate="normal", **ranged))
    assert error(grid(client, "air_temperature_max", date="2025-07-05", period="last10"))["param"] == "period"
    dd = {"dd": "sine_48_86", "stat": "sum", "climate": "normal", **ranged}
    assert error(grid(client, "degree_days", **dd))["param"] == "dd"  # 48 °F isn't a kept threshold
    last30 = grid(client, "air_temperature_max", date="2025-07-05", climate="normal")
    assert last30.status_code == 503  # not built here
    percentile = {"dd": "modified_10_30", "stat": "sum", "climate": "percentile", "period": "last5"}
    assert error(grid(client, "degree_days", start="2025-01-01", end="2025-07-05", **percentile))["param"] == "climate"


def test_freeze_maps(client, climate_archive):
    chance = grid(client, "freeze_chance", date="2025-01-05", period="last5")
    assert values(chance) == [100.0] * 6
    assert "date" in chance.json()["data"]
    dates = grid(client, "freeze_dates", output="last_spring_p50", period="last5")
    assert values(dates) == ["2025-01-10"] * 6
    assert "date" not in dates.json()["data"]  # a map of no day
    season = grid(client, "freeze_dates", output="season_days_p50", period="last5")
    assert values(season) == [345.0] * 6
    assert error(grid(client, "freeze_chance", date="2025-01-05", threshold="30", period="last5"))["param"] == (
        "threshold"
    )
    assert error(grid(client, "freeze_dates", date="2025-01-05", period="last5"))["param"] == "date"
    assert error(grid(client, "freeze_dates", output="mean", period="last5"))["param"] == "output"


@pytest.fixture
def with_terrain(climate_archive):
    terrain_store(
        settings.DATA_DIR,
        WINDOW,
        np.zeros(WINDOW.shape, dtype=np.uint8),
        elevation_m=np.array([[250.0, 251.0, 252.0], [253.0, 254.0, 255.0]]),
    )
    yield
    shutil.rmtree(terrain.path(settings.DATA_DIR))


def test_elevation(client, with_terrain):
    response = grid(client, "elevation", output="max")
    assert sorted(values(response)) == pytest.approx([250.0, 251.0, 252.0, 253.0, 254.0, 255.0], abs=0.15)
    assert response.json()["meta"]["sources"] == ["nhdplus"]
    feet = client.get("/api/v2/grids/elevation", {"bbox": BOX})
    assert feet.json()["meta"]["units"]["elevation"] == "ft"


@pytest.mark.django_db
def test_layers_say_what_climate_they_take(client, climate_archive):
    found = {row["id"]: row for row in client.get("/api/v2/layers").json()["data"]}
    assert found["degree_days"]["climate"] == ["normal", "departure", "percentile"]
    assert found["air_temperature_hourly"]["climate"] == []
    assert found["freeze_chance"]["time_axis"] == "day_of_year"
    assert found["freeze_chance"]["parameters"] == ["threshold"]
    assert found["elevation"]["time_axis"] == "none"
    assert [o["name"] for o in found["elevation"]["outputs"]] == ["mean", "min", "max", "spread"]


def test_tiles_images_and_summaries(client, climate_archive):
    tile = client.get(
        "/api/v2/tiles/air_temperature_max/2025-07-05/6/15/23.png", {"climate": "departure", "period": "last5"}
    )
    assert tile.status_code in (200, 204)
    image = client.get("/api/v2/maps/freeze_dates.png", {"output": "first_fall_p50", "period": "last5"})
    assert image.status_code == 200 and image["Content-Type"] == "image/png"
    summary = client.get("/api/v2/summaries/freeze_chance", {"by": "county", "date": "2025-01-05", "period": "last5"})
    assert summary.status_code == 200, summary.json()
