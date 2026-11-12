"""Water and terrain at points and over areas (D6): `meta.location`'s elevation and water share, and `land_only`
on an area (`radius`) and on `/grids`, with a small terrain store written into the fixture archive's folder."""

import shutil

import numpy as np
import pytest
from django.conf import settings

from agdata import terrain
from agdata.grid import NDFD
from agdata.testing import WINDOW, terrain_store
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
DAILY = {"start": "2025-07-08", "end": "2025-07-09"}
_cell = NDFD.cell_of(LAT, LNG)
assert _cell is not None
_j, _i = _cell
OWN = (_j - WINDOW.j0, _i - WINDOW.i0)  # the point's cell in the window
WATER = (OWN[0], OWN[1] + 1 if OWN[1] + 1 < WINDOW.shape[1] else OWN[1] - 1)  # its neighbour, all water


@pytest.fixture
def with_terrain(archive):
    share = np.zeros(WINDOW.shape, dtype=np.uint8)
    share[WATER] = 100
    share[1 - OWN[0], OWN[1]] = 99  # nearly all water: stays in
    terrain_store(
        settings.DATA_DIR, WINDOW, share, elevation_m=np.array([[250.0, 251.0, 252.0], [253.0, 254.0, 255.0]])
    )
    yield share
    shutil.rmtree(terrain.path(settings.DATA_DIR))


def get(client, path, **params):
    return client.get(f"/api/v2/{path}", params)


def test_a_point_says_its_elevation_and_its_cells_water(client, with_terrain):
    location = get(client, "weather/daily", lat=LAT, lng=LNG, **DAILY).json()["meta"]["location"]
    y, x = OWN
    assert location["cell_elevation_m"] == 250.0 + 3 * y + x == location["elevation_m"]
    assert location["water_percent"] == with_terrain[y, x]


def test_without_the_store_a_point_says_nothing_of_it(client, archive):
    location = get(client, "weather/daily", lat=LAT, lng=LNG, **DAILY).json()["meta"]["location"]
    assert location["elevation_m"] is location["water_percent"] is None


def test_land_only_leaves_cells_all_water_out_of_an_area(client, with_terrain):
    around = get(client, "weather/daily", lat=LAT, lng=LNG, radius="2", **DAILY).json()["meta"]
    land = get(client, "weather/daily", lat=LAT, lng=LNG, radius="2", land_only="true", **DAILY).json()["meta"]
    assert land["location"]["area"]["cells"] == around["location"]["area"]["cells"] - 1  # 99% water stays in
    assert land["request"]["land_only"] is True and land["location"]["area"]["land_only"] is True


def test_land_only_needs_a_radius_and_the_store(client, archive):
    alone = get(client, "weather/daily", lat=LAT, lng=LNG, land_only="true", **DAILY).json()["errors"][0]
    assert alone["code"] == "not_applicable" and alone["param"] == "land_only"
    unbuilt = get(client, "weather/daily", lat=LAT, lng=LNG, radius="2", land_only="true", **DAILY).json()
    assert unbuilt["errors"][0]["code"] == "no_data" and unbuilt["errors"][0]["param"] == "land_only"


def test_land_only_on_a_grid(client, with_terrain):
    whole = get(client, "grids/air_temperature_max", date="2025-07-05", cells="true").json()["data"]
    land = get(client, "grids/air_temperature_max", date="2025-07-05", cells="true", land_only="true").json()
    cells = set(zip(land["data"]["j"], land["data"]["i"], strict=True))
    assert len(cells) == len(whole["j"]) - 1 and (WINDOW.j0 + WATER[0], WINDOW.i0 + WATER[1]) not in cells
    assert land["meta"]["request"]["land_only"] is True
