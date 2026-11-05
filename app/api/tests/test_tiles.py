"""Map tiles (PLAN.md Phase 5 G) on the fixture archive: 2 × 3 cells in Fayette County, Iowa, July 2025."""

import io

import numpy as np
import pytest
from PIL import Image

from agdata import tiles
from agdata.grid import NDFD
from agdata.testing import WINDOW
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
Z = 8
X, Y = tiles._tile_of(LNG, LAT, Z)


def _pixels(response) -> np.ndarray:
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    return np.asarray(Image.open(io.BytesIO(response.content)))


def _tile(client, layer, when, z=Z, x=X, y=Y, **params):
    return client.get(f"/api/v2/tiles/{layer}/{when}/{z}/{x}/{y}.png", params)


def _cells_seen(rgba, step) -> dict[int, float]:
    """The value each window cell shows, from the pixels over it."""
    cells = tiles.index(WINDOW, Z, X, Y)
    assert cells is not None
    values = tiles.decode(rgba, step).ravel()
    return {int(c): float(values[k]) for k, c in enumerate(cells) if c >= 0}


@pytest.mark.django_db
def test_a_tile_holds_the_grid_values(client, archive):
    rgba = _pixels(_tile(client, "air_temperature_max", "2025-07-08"))
    grid = client.get("/api/v2/grids/air_temperature_max", {"date": "2025-07-08", "units": "metric", "cells": "true"})
    rows = grid.json()["data"]
    by_cell = {
        (j - WINDOW.j0) * WINDOW.shape[1] + (i - WINDOW.i0): v
        for j, i, v in zip(rows["j"], rows["i"], rows["air_temperature_max"], strict=True)
    }
    seen = _cells_seen(rgba, step=0.1)
    assert set(seen) == set(by_cell)  # every cell shows at zoom 8
    for cell, value in seen.items():
        assert value == pytest.approx(by_cell[cell], abs=0.051)
    assert (rgba[..., 3] == 0).sum() > 0  # around the window: transparent


@pytest.mark.django_db
def test_a_tile_is_revalidated_and_a_far_one_is_empty(client, archive):
    first = _tile(client, "precipitation_sum", "2025-07-08")
    again = client.get(first.wsgi_request.get_full_path(), headers={"If-None-Match": first["ETag"]})
    assert again.status_code == 304
    far = _pixels(_tile(client, "precipitation_sum", "2025-07-08", x=X + 30))
    assert (far[..., 3] == 0).all()


@pytest.mark.django_db
def test_model_degree_day_and_range_tiles(client, archive):
    risk = _cells_seen(_pixels(_tile(client, "late-blight-dsv", "2025-07-08")), step=1)
    assert set(risk.values()) <= {0, 1, 2, 3, 4}
    dd = _tile(client, "degree_days", "2025-07-01..2025-07-07", dd="sine_50_86", stat="sum")
    week = client.get(
        "/api/v2/grids/degree_days", {"start": "2025-07-01", "end": "2025-07-07", "dd": "sine_50_86", "stat": "sum"}
    ).json()["data"]["degree_days"]
    seen = _cells_seen(_pixels(dd), step=0.1)
    assert sorted(round(v, 1) for v in seen.values()) == pytest.approx(sorted(week), abs=0.06)  # both in °F·d
    assert _tile(client, "degree_days", "2025-07-01..2025-07-07", dd="sine_50_86").status_code == 422  # no stat
    assert _tile(client, "precipitation_sum", "2025-26").json()["errors"][0]["param"] == "season"
    assert _tile(client, "precipitation_sum", "latest").status_code == 200
    assert _tile(client, "precipitation_sum", "2025-07-08", z=9).status_code == 404


@pytest.mark.django_db
def test_tilejson_gives_the_url_and_decoding(client, archive):
    body = client.get("/api/v2/tiles/degree_days.json", {"time": "2025-07-08", "dd": "sine_50_86"}).json()
    assert body["tilejson"] == "3.0.0" and body["maxzoom"] == tiles.MAX_ZOOM
    assert body["tiles"][0].endswith("/api/v2/tiles/degree_days/2025-07-08/{z}/{x}/{y}.png?dd=sine_50_86")
    enc = body["encoding"]
    assert enc["unit"] == "degF_day" and enc["blueFactor"] == pytest.approx(0.1)
    assert enc["baseShift"] == pytest.approx(-(2**23) * 0.1)
    lat, lon = NDFD.window_latlon(WINDOW)
    assert body["bounds"] == pytest.approx([float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())])
