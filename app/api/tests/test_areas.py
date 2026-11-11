"""Area averages at points (`radius`, `weighting`; `agdata.areas`) on the fixture archive: its 2 × 3 cells share one
day's weather, so an area's values are the point's own, while the area's cells, the echo and the refusals show."""

import pytest

from api.tests.fixture_archive import POINT

LAT, LNG = POINT
DULUTH = (46.79, -92.1)  # on the grid, outside the test box

AREA_ENDPOINTS = [
    ("weather/daily", {"start": "2025-07-08", "end": "2025-07-09"}),
    ("weather/hourly", {"start": "2025-07-08T00", "end": "2025-07-08T03"}),
    ("weather/totals", {"start": "2025-07-01", "end": "2025-07-09"}),
    ("degree-days", {"start": "2025-07-01", "end": "2025-07-09", "dd": "sine_50"}),
    ("degree-days/table", {"start": "2025-07-01", "end": "2025-07-09", "dd": "sine_50"}),
    ("freeze", {"start": "2025-07-01", "end": "2025-07-09"}),
    ("chill", {"start": "2025-07-01", "end": "2025-07-03"}),
    ("models/tar-spot/run", {"start": "2025-07-01", "end": "2025-07-09"}),
    ("models/run", {"models": "tar-spot", "start": "2025-07-01", "end": "2025-07-09"}),
    ("risk", {"date": "2025-07-09"}),
]


def get(client, path, **params):
    return client.get(f"/api/v2/{path}", {"lat": LAT, "lng": LNG, **params})


@pytest.mark.parametrize(("path", "params"), AREA_ENDPOINTS, ids=[p for p, _ in AREA_ENDPOINTS])
def test_every_point_endpoint_takes_an_area(client, archive, path, params):
    alone = get(client, path, **params)
    around = get(client, path, radius="2", **params)
    assert alone.status_code == around.status_code == 200, around.json()
    meta = around.json()["meta"]
    assert meta["request"]["radius"] == 2 and meta["request"]["weighting"] == "equal"
    assert meta["location"]["area"]["cells"] > 1 and meta["location"]["area"]["radius_km"] == pytest.approx(3.219)
    assert around.json()["data"] == alone.json()["data"]  # the fixture's cells share their weather
    assert around["ETag"] != alone["ETag"]


def test_an_area_is_clipped_to_our_cells_and_weighted(client, archive):
    small = get(client, "weather/daily", date="2025-07-08", radius="1").json()["meta"]["location"]["area"]
    assert small["cells"] == 1  # no other cell's center within a mile
    wide = get(client, "weather/daily", date="2025-07-08", radius="10", weighting="center").json()["meta"]
    # The test box's 20 cells (its stores hold 6, so the rest are missing and drop out of the average; in
    # production the box and the stores are one window)
    assert wide["location"]["area"]["cells"] == 20 and wide["location"]["area"]["weighting"] == "center"


def test_an_area_s_limits(client, archive):
    for params in ({"radius": "11"}, {"radius": "0"}, {"radius": "17", "units": "metric"}):
        response = get(client, "weather/daily", date="2025-07-08", **params)
        assert response.status_code == 422 and response.json()["errors"][0]["param"] == "radius", params
    assert get(client, "weather/daily", date="2025-07-08", radius="16", units="metric").status_code == 200
    response = get(client, "weather/daily", date="2025-07-08", radius="2", weighting="middle")
    assert response.status_code == 422


def test_an_area_outside_our_cells_is_refused(client, archive):
    response = client.get("/api/v2/weather/daily", {"lat": DULUTH[0], "lng": DULUTH[1], "radius": "2"})
    error = response.json()["errors"][0]
    assert response.status_code == 422 and error["param"] == "radius" and "This location" in error["message"]
    response = client.get("/api/v2/weather/daily", {"points": f"{LAT},{LNG};{DULUTH[0]},{DULUTH[1]}", "radius": "2"})
    assert "1 of these 2 locations" in response.json()["errors"][0]["message"]
    assert client.get("/api/v2/locate", {"lat": LAT, "lng": LNG, "radius": "2"}).status_code == 422  # not taken
