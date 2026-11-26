"""`/data`'s props (web.datapage): the API's limits, the grid's projection, and the areas a map file can cover,
measured as `/grids` measures them."""

import pytest

from agdata.grid import NDFD
from agdata.testing import WINDOW
from api.params import MAX_POINTS
from api.routes import grids
from web import datapage

INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}


@pytest.mark.django_db
def test_the_page_has_the_limits_at_once_and_the_areas_deferred(client, archive):
    page = client.get("/data", headers=INERTIA).json()
    props = page["props"]
    assert props["limits"]["text_values"] == grids.MAX_TEXT_VALUES
    assert props["limits"]["file_values"] == grids.MAX_FILE_VALUES
    assert props["projection"]["lon0"] == -95 and props["projection"]["lat1"] == 25
    assert any(m["id"] == "late-blight-dsv" for m in props["models"])
    assert "areas" not in props
    assert page["deferredProps"] == {"default": ["areas"]}
    partial = client.get(
        "/data",
        headers={**INERTIA, "X-Inertia-Partial-Data": "areas", "X-Inertia-Partial-Component": "Data/Index"},
    ).json()["props"]
    assert partial["areas"]["window"] == [WINDOW.j0, WINDOW.j1, WINDOW.i0, WINDOW.i1]


def test_the_point_downloads_limits_in_the_frontend_are_the_apis():
    """`lib/sites/dataRequest.ts` keeps its own copy (a site's page has no `limits` prop)."""
    import math
    import re
    from pathlib import Path

    from api.routes import weather

    source = (Path(__file__).parents[3] / "frontend/lib/sites/dataRequest.ts").read_text()
    found = {
        m[1]: math.prod(int(t) for t in m[2].replace("_", "").split("*"))
        for m in re.finditer(r"export const (MAX_\w+) = ([\d_ *]+)\n", source)
    }
    assert found == {
        "MAX_DAYS": weather.MAX_DAYS,
        "MAX_HOURS": weather.MAX_HOURS,
        "MAX_ROWS": weather.MAX_ROWS,
        "MAX_POINTS": MAX_POINTS,
    }


def test_the_projection_places_cells_as_the_grid_does():
    """The page's formulas, run here on the props: cell (j, i)'s center at NDFD's latitude and longitude."""
    import math

    p = datapage.projection()
    n = math.sin(math.radians(p.lat1))
    f = math.cos(math.radians(p.lat1)) * math.tan(math.pi / 4 + math.radians(p.lat1) / 2) ** n / n
    rho0 = p.radius * f / math.tan(math.pi / 4 + math.radians(p.lat1) / 2) ** n
    for j, i in [(0, 0), (900, 1400), (1596, 2344)]:
        x, y = p.x0 + i * p.dx, p.y0 + j * p.dx
        rho = math.copysign(math.hypot(x, rho0 - y), n)
        lat = math.degrees(2 * math.atan((p.radius * f / rho) ** (1 / n)) - math.pi / 2)
        lon = p.lon0 + math.degrees(math.atan2(x, rho0 - y) / n)
        want_lat, want_lon = NDFD.latlon(j, i)
        assert abs(lat - float(want_lat)) < 1e-7 and abs(lon - float(want_lon)) < 1e-7


@pytest.mark.django_db
def test_an_area_has_the_window_and_cells_the_api_gives_its_file(client, archive, monkeypatch):
    monkeypatch.setattr(datapage, "STATE_SHARE", 0)  # the fixture's 2 × 3 cells are a sliver of a state
    datapage._areas.cache_clear()
    areas = datapage.areas()
    assert areas is not None and areas.counties and areas.states
    for area in [areas.states[0], *areas.counties]:
        for clip in (False, True):
            body = client.get(
                f"/api/v2/grids/air_temperature_max?date=2025-07-01&region={area.id}&clip={str(clip).lower()}"
            ).json()
            assert body["meta"]["request"]["window"] == [area.j0, area.j1, area.i0, area.i1]
            full = (area.j1 - area.j0) * (area.i1 - area.i0)
            assert body["meta"]["summary"]["cells"] == (area.cells if clip else full)
    datapage._areas.cache_clear()


def test_a_state_mostly_outside_the_window_isnt_offered(archive):
    datapage._areas.cache_clear()
    areas = datapage.areas()
    assert areas is not None and areas.states == [] and areas.counties == []
    datapage._areas.cache_clear()
