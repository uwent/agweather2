"""Static map images (PLAN.md Phase 5 G3, D60) on the fixture archive (Fayette County, Iowa, July 2025)."""

import io

import pytest
from PIL import Image

from api.routes import maps


def _image(response) -> Image.Image:
    assert response.status_code == 200 and response["Content-Type"] == "image/png", response.content[:300]
    return Image.open(io.BytesIO(response.content))


@pytest.mark.django_db
def test_a_map_is_drawn_once_and_kept(client, archive):
    first = client.get("/api/v2/maps/air_temperature_max.png", {"date": "2025-07-08"})
    assert _image(first).size[0] == 800
    kept = list((archive / "maps").glob("*.png"))
    assert kept
    again = client.get(
        "/api/v2/maps/air_temperature_max.png", {"date": "2025-07-08"}, headers={"If-None-Match": first["ETag"]}
    )
    assert again.status_code == 304
    assert client.get("/api/v2/maps/air_temperature_max.png", {"date": "2025-07-08"}).content == first.content


@pytest.mark.django_db
def test_days_regions_models_and_refusals(client, archive):
    week = client.get("/api/v2/maps/precipitation_sum.png", {"days": "3", "stat": "sum", "end": "2025-07-08"})
    assert _image(week).size[0] == 800
    assert (
        _image(
            client.get("/api/v2/maps/late-blight-dsv.png", {"date": "2025-07-08", "region": "IA", "width": "500"})
        ).size[0]
        == 500
    )
    assert client.get("/api/v2/maps/precipitation_sum.png", {"days": "3"}).json()["errors"][0]["param"] == "stat"
    assert client.get("/api/v2/maps/precipitation_sum.png", {"region": "atlantis"}).status_code == 422
    ranged = client.get("/api/v2/maps/air_temperature_max.png", {"start": "2025-07-01", "end": "2025-07-03"})
    assert ranged.status_code == 422  # a map is one step
    bad_end = client.get("/api/v2/maps/precipitation_sum.png", {"days": "3", "stat": "sum", "end": "2025-07-xx"})
    assert bad_end.status_code == 422 and bad_end.json()["errors"][0]["param"] == "end"
    years = client.get(
        "/api/v2/maps/precipitation_sum.png", {"start": "2016-01-01", "end": "2025-07-08", "stat": "sum"}
    )
    assert years.status_code == 422 and years.json()["errors"][0]["code"] == "too_large"


@pytest.mark.django_db
def test_the_job_draws_the_default_maps_once(archive):
    drawn = maps.render_default_maps()
    assert set(drawn) == {layer for layer, _ in maps.DEFAULT_MAPS}
    assert all(ms == 0 for ms in maps.render_default_maps().values())  # nothing new to draw


@pytest.mark.django_db
def test_a_computed_layer_is_drawn_with_its_title(client, archive):
    response = client.get("/api/v2/maps/water_balance.png", {"date": "2025-07-08"})
    assert _image(response).size[0] == 800
    tile_json = client.get("/api/v2/tiles/water_balance.json", {"time": "2025-07-08"}).json()
    assert tile_json["name"].startswith("Water balance (precipitation minus reference evapotranspiration), daily total")
