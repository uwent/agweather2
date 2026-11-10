"""Static map images (PLAN.md Phase 5 G3, D60) on the fixture archive (Fayette County, Iowa, July 2025)."""

import io
import os
import time

import numpy as np
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


def test_prune_stale_deletes_old_images_and_temporary_files(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    (tmp_path / "maps").mkdir()
    old, new, tmp = (tmp_path / "maps" / n for n in ("old.png", "new.png", "x.123.tmp"))
    for path in (old, new, tmp):
        path.write_bytes(b"x")
    stale = time.time() - (maps.KEEP_DAYS + 1) * 86400
    for path in (old, tmp):
        os.utime(path, (stale, stale))
    assert maps.prune_stale() == 1
    assert not old.exists() and not tmp.exists() and new.exists()
    assert maps.prune_stale() == 0


def test_a_draw_over_the_cap_deletes_the_least_recently_used(settings, tmp_path, monkeypatch):
    settings.DATA_DIR = tmp_path
    monkeypatch.setattr(maps, "MAX_KEPT", 3)
    (tmp_path / "maps").mkdir()
    now = time.time()
    for age, name in enumerate(["newest", "middle", "oldest", "newer"]):
        path = tmp_path / "maps" / f"{name}.png"
        path.write_bytes(b"x")
        os.utime(path, (now - age * 10, now - age * 10))
    just_drawn = tmp_path / "maps" / "drawn.png"
    just_drawn.write_bytes(b"x")
    maps._enforce_cap(keep=just_drawn)
    left = {p.stem for p in (tmp_path / "maps").glob("*.png")}
    assert left == {"drawn", "newest", "middle"}


@pytest.mark.django_db
def test_a_computed_layer_is_drawn_with_its_title(client, archive):
    response = client.get("/api/v2/maps/water_balance.png", {"date": "2025-07-08"})
    assert _image(response).size[0] == 800
    tile_json = client.get("/api/v2/tiles/water_balance.json", {"time": "2025-07-08"}).json()
    assert tile_json["name"].startswith("Water balance (precipitation minus reference evapotranspiration), daily total")


@pytest.mark.django_db
def test_isolines_a_middle_and_the_name_a_saved_map_takes(client, archive):
    asked = {"date": "2025-07-08", "scale": "60,75,90", "isolines": "auto"}
    drawn = client.get("/api/v2/maps/air_temperature_max.png", asked)
    assert _image(drawn).size[0] == 800
    disposition = drawn["Content-Disposition"]
    assert disposition == 'inline; filename="air_temperature_max_2025-07-08_scale-60-75-90_isolines-auto.png"'
    ranged = client.get(
        "/api/v2/maps/precipitation_sum.png", {"stat": "sum", "start": "2025-07-01", "end": "2025-07-08"}
    )
    assert ranged["Content-Disposition"] == 'inline; filename="precipitation_sum_sum_2025-07-01_2025-07-08.png"'
    tags = {
        client.get("/api/v2/maps/air_temperature_max.png", {"date": "2025-07-08", "isolines": s})["ETag"]
        for s in ("off", "auto", "2")
    }
    assert len(tags) == 3  # each is its own image
    assert _image(client.get("/api/v2/maps/air_temperature_max.png", {"date": "2025-07-08", "isolines": "2.5"}))

    def error(layer="air_temperature_max", **params):
        return client.get(f"/api/v2/maps/{layer}.png", {"date": "2025-07-08", **params}).json()["errors"][0]

    assert error(isolines="every")["code"] == "invalid" and error(isolines="-5")["code"] == "invalid"
    with pytest.raises(maps.ApiError) as refused:  # the fixture's day is one value everywhere, so tried directly
        maps.check_isoline_count(np.array([0.0, 40.0, np.nan]), 0.1, lambda v: v)
    assert refused.value.code == "too_large" and "isolines=2" in refused.value.message
    maps.check_isoline_count(np.array([0.0, 40.0]), 0.5, lambda v: v)  # 80 lines: drawn
    assert error("late-blight-dsv", isolines="auto")["code"] == "not_applicable"
