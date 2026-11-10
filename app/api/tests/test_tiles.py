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
X, Y = tiles.tile_of(LNG, LAT, Z)


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


@pytest.mark.django_db
def test_a_styled_tile_colors_the_values_with_the_palette(client, archive):
    from agdata import palettes

    data = _cells_seen(_pixels(_tile(client, "air_temperature_max", "2025-07-08")), step=0.1)
    styled = _pixels(_tile(client, "air_temperature_max", "2025-07-08", style="default", scale="default"))
    cells = tiles.index(WINDOW, Z, X, Y)
    assert cells is not None
    p = palettes.PALETTES["BuYlRd"]
    for k, cell in enumerate(cells):
        if cell >= 0:
            expected = palettes.colorize(np.array([data[int(cell)]]), p, (-30, 40))[0]
            assert tuple(styled.reshape(-1, 4)[k]) == tuple(expected)
            break
    risk = _pixels(_tile(client, "late-blight-dsv", "2025-07-08", style="default"))
    colors = {tuple(c[:3]) for c in risk.reshape(-1, 4) if c[3]}
    assert colors <= {palettes.rgb(c) for c in palettes.PALETTES["BuYlRd_5"].colors}


@pytest.mark.django_db
def test_legends_palettes_and_domains(client, archive):
    bar = Image.open(io.BytesIO(client.get("/api/v2/tiles/air_temperature_max/legend.png", {"units": "us"}).content))
    assert bar.size[0] == 320 and 60 <= bar.size[1] <= 100
    levels = client.get("/api/v2/tiles/late-blight-dsv/legend.png", {"time": "2025-07-08"})
    assert levels.status_code == 200 and Image.open(io.BytesIO(levels.content)).size[1] > 80  # a swatch per level
    total = client.get("/api/v2/tiles/dd_modified_50_86/legend.png", {"time": "2025-07-08"})
    assert total.status_code == 200  # its domain from the map
    found = {p["id"]: p for p in client.get("/api/v2/palettes").json()}
    assert found["BuYlRd"]["kind"] == "diverging" and found["BuYlRd_4"]["colors"][0] == "#4575b4"
    assert not found["rainbow"]["colorblind_safe"] and found["BuYlRd"]["source"] == "ColorBrewer RdYlBu, reversed"
    layers = {layer["id"]: layer for layer in client.get("/api/v2/layers").json()["data"]}
    assert layers["air_temperature_max"]["domain"] == [-30, 40]
    assert layers["dd_modified_50_86"]["domain"] is None and layers["late-blight-dsv"]["domain"] == [0, 4]


@pytest.mark.django_db
def test_recent_and_latest_tiles_expire_soon_and_settled_ones_later(client, archive):
    recent = _tile(client, "precipitation_sum", "2025-07-08")
    assert recent["Cache-Control"] == "public, max-age=300, stale-while-revalidate=300"
    assert _tile(client, "precipitation_sum", "latest")["Cache-Control"].startswith("public, max-age=300")
    old = _tile(client, "precipitation_sum", "2025-06-01")  # before the archive: missing, but settled
    assert old["Cache-Control"] == "public, max-age=86400, stale-while-revalidate=86400"


def test_a_tile_of_a_range_is_limited_as_a_grid_is(client, archive):
    response = _tile(client, "air_temperature_max", "2016-01-01..2025-07-08", stat="mean")
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "too_large"


@pytest.mark.django_db
def test_scale_sets_what_the_colors_span(client, archive):
    from agdata import palettes

    data = _cells_seen(_pixels(_tile(client, "air_temperature_max", "2025-07-08")), step=0.1)
    styled = _pixels(_tile(client, "air_temperature_max", "2025-07-08", style="default", scale="60,90"))  # °F
    cells = tiles.index(WINDOW, Z, X, Y)
    assert cells is not None
    k, cell = next((k, int(c)) for k, c in enumerate(cells) if c >= 0)
    stored = ((60 - 32) / 1.8, (90 - 32) / 1.8)  # the same range in °C, as the values are stored
    expected = palettes.colorize(np.array([data[cell]]), palettes.PALETTES["BuYlRd"], stored)[0]
    assert tuple(styled.reshape(-1, 4)[k]) == tuple(expected)

    described = client.get("/api/v2/tiles/air_temperature_max.json", {"style": "default", "scale": "60,90"}).json()
    assert described["palette"] == "BuYlRd" and described["domain"] == [60.0, 90.0] and described["domain_unit"] == "°F"
    fixed = {"style": "default", "units": "metric", "scale": "default"}
    metric = client.get("/api/v2/tiles/air_temperature_max.json", fixed).json()
    assert metric["domain"] == [-30.0, 40.0] and metric["domain_unit"] == "°C"  # the use's own
    fitted = client.get("/api/v2/tiles/air_temperature_max.json", {"style": "default", "units": "metric"}).json()
    low, high = fitted["domain"]  # without scale: from the map's values (Ben, 2026-11-10)
    assert -30 < low < high < 40 and "domain_middle" not in fitted
    open_end = client.get("/api/v2/tiles/air_temperature_max.json", {"style": "default", "scale": "60,"}).json()
    assert open_end["domain"][0] == 60.0 and open_end["domain"][1] > 60.0  # the high end from the map

    def error(**params):
        return client.get("/api/v2/maps/air_temperature_max.png", params).json()["errors"][0]

    assert error(scale="90,60")["code"] == "out_of_order"
    assert error(scale="0,50,40")["code"] == "out_of_order" and error(scale="0,,40")["code"] == "invalid"
    assert error(scale="1,2,3,4")["code"] == "invalid"
    assert error(scale="warm")["code"] == "invalid" and error(scale=",")["code"] == "invalid"
    risk = client.get("/api/v2/maps/late-blight-dsv.png", {"date": "2025-07-08", "scale": "auto"}).json()["errors"][0]
    assert risk["code"] == "not_applicable"
    tags = {client.get("/api/v2/maps/air_temperature_max.png", {"scale": s})["ETag"] for s in ("auto", "60,90", "")}
    assert len(tags) == 3  # each scale is its own image


def test_palette_chooses_the_colors(client, archive):
    from agdata import palettes

    data = _cells_seen(_pixels(_tile(client, "air_temperature_max", "2025-07-08")), step=0.1)
    styled = _pixels(
        _tile(client, "air_temperature_max", "2025-07-08", style="default", palette="viridis_r", scale="default")
    )
    cells = tiles.index(WINDOW, Z, X, Y)
    assert cells is not None
    k, cell = next((k, int(c)) for k, c in enumerate(cells) if c >= 0)
    expected = palettes.colorize(np.array([data[cell]]), palettes.palette("viridis", reverse=True), (-30, 40))[0]
    assert tuple(styled.reshape(-1, 4)[k]) == tuple(expected)

    described = client.get("/api/v2/tiles/air_temperature_max.json", {"style": "default", "palette": "viridis_r"})
    assert described.json()["palette"] == "viridis_r" and described.json()["request"]["palette"] == "viridis_r"
    legend = client.get("/api/v2/tiles/air_temperature_max/legend.png", {"palette": "magma"})
    assert legend.status_code == 200 and legend["Content-Type"] == "image/png"
    tags = {
        client.get("/api/v2/maps/air_temperature_max.png", {"palette": p})["ETag"] for p in ("viridis", "", "BuYlRd")
    }
    assert len(tags) == 3  # each palette is its own image (BuYlRd, the default, asked by name, too)

    # A categorical map takes a categorical palette with as many levels, reversed or not
    risk = client.get("/api/v2/tiles/late-blight-dsv.json", {"style": "default", "time": "2025-07-08"}).json()
    levels = palettes.palette(risk["palette"])
    flipped = client.get("/api/v2/maps/late-blight-dsv.png", {"date": "2025-07-08", "palette": f"{levels.id}_r"})
    assert flipped.status_code == 200

    def error(layer="air_temperature_max", **params):
        return client.get(f"/api/v2/maps/{layer}.png", params).json()["errors"][0]

    assert error(palette="plaid")["code"] == "unknown_palette"
    assert error(palette="BuYlRd_3")["code"] == "not_applicable"  # categorical on a range of values
    assert error(layer="late-blight-dsv", date="2025-07-08", palette="viridis")["code"] == "not_applicable"


@pytest.mark.django_db
def test_a_middle_in_scale_pins_the_palettes_middle_color(client, archive):
    from agdata import palettes

    data = _cells_seen(_pixels(_tile(client, "air_temperature_max", "2025-07-08")), step=0.1)
    styled = _pixels(_tile(client, "air_temperature_max", "2025-07-08", style="default", scale="60,75,90"))
    cells = tiles.index(WINDOW, Z, X, Y)
    assert cells is not None
    k, cell = next((k, int(c)) for k, c in enumerate(cells) if c >= 0)
    stored = ((60 - 32) / 1.8, (90 - 32) / 1.8)
    expected = palettes.colorize(np.array([data[cell]]), palettes.PALETTES["BuYlRd"], stored, middle=(75 - 32) / 1.8)
    assert tuple(styled.reshape(-1, 4)[k]) == tuple(expected[0])
    described = client.get("/api/v2/tiles/air_temperature_max.json", {"style": "default", "scale": "60,75,90"}).json()
    assert described["domain"] == [60.0, 90.0] and described["domain_middle"] == 75.0
    # The data's ends, but a middle below every value: the low end becomes the middle, so only the warm half shows
    above = client.get("/api/v2/tiles/air_temperature_max.json", {"style": "default", "scale": ",-40,"}).json()
    assert above["domain"][0] == -40.0 and above["domain"][1] > 50 and above["domain_middle"] == -40.0
    legend = client.get("/api/v2/tiles/air_temperature_max/legend.png", {"time": "2025-07-08", "scale": "0,32,100"})
    assert legend.status_code == 200 and legend["Content-Type"] == "image/png"
