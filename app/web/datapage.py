"""What `/data` needs from the server (Phase 7 track 7 step 7.1): the API's limits, the grid's projection and the
areas a map file can cover, so the page says how large a download is, and whether the API takes it, before asking.

The areas are measured as `/grids` measures them (`api.routes.grids._area`): a region's cells are those whose
county (`agdata.regions.cell_counties`) is in it, its file the rectangle around them over the archive's window, and
`clip=true` keeps only its cells. A state is listed when at least half its cells (`counties.csv`'s whole-grid
count) are in the window, so a development box over Wisconsin doesn't offer its neighbours' slivers; its counties
with any cell in the window come with it.
"""

from functools import cache

import numpy as np
from django.conf import settings

from agdata import regions, series
from agdata.grid import NDFD, Window
from agdata.places import counties
from agdata.regrid import MIN_LATLON_RES
from api import layermaps
from api.errors import ApiError
from api.params import MAX_POINTS
from api.routes import grids, weather
from web.props import DataAreas, DataLimits, GridArea, GridProjection

STATE_SHARE = 0.5  # of a state's cells in the window, for it to be offered


def limits() -> DataLimits:
    return DataLimits(
        points=MAX_POINTS,
        days=weather.MAX_DAYS,
        hours=weather.MAX_HOURS,
        rows=weather.MAX_ROWS,
        text_values=grids.MAX_TEXT_VALUES,
        file_values=grids.MAX_FILE_VALUES,
        map_days=layermaps.MAX_DAYS,
        map_hours=layermaps.MAX_HOURS,
        stride=grids.MAX_STRIDE,
        res=MIN_LATLON_RES,
    )


def projection() -> GridProjection:
    terms = dict(term.lstrip("+").split("=", 1) for term in NDFD.proj4.split() if "=" in term)
    assert terms["lat_0"] == terms["lat_1"] == terms["lat_2"]  # a tangent cone, as the page's formulas take it
    lon0 = float(terms["lon_0"])
    x0, y0 = NDFD.origin
    return GridProjection(
        lon0=lon0 - 360 if lon0 > 180 else lon0,
        lat1=float(terms["lat_1"]),
        radius=float(terms["R"]),
        x0=x0,
        y0=y0,
        dx=NDFD.dx,
    )


def areas() -> DataAreas | None:
    """The archive's window and its states and counties; None before the archive has a year."""
    try:
        window = layermaps.archive_window(settings.DATA_DIR, series.Stores([]))
    except ApiError:
        return None
    return _areas(window)


@cache
def _areas(window: Window) -> DataAreas:
    ids = regions.cell_counties(window)
    known = counties()
    n = len(known)
    flat = ids.ravel()
    rows = np.repeat(np.arange(window.shape[0]), window.shape[1])
    cols = np.tile(np.arange(window.shape[1]), window.shape[0])
    cells = np.bincount(flat, minlength=n)
    j0, j1 = _extremes(flat, rows, n)
    i0, i1 = _extremes(flat, cols, n)

    by_state: dict[str, list[int]] = {}
    for k, county in enumerate(known):
        if county is not None:
            by_state.setdefault(county.state, []).append(k)
    states: list[GridArea] = []
    found: list[GridArea] = []
    for code, ks in by_state.items():
        inside = [k for k in ks if cells[k] > 0]
        whole = sum(c.cells for k in ks if (c := known[k]) is not None)
        if not inside or whole == 0 or sum(int(cells[k]) for k in inside) < STATE_SHARE * whole:
            continue
        states.append(
            GridArea(
                id=code,
                name=regions.STATES[code],
                state=code,
                j0=window.j0 + int(j0[inside].min()),
                j1=window.j0 + int(j1[inside].max()) + 1,
                i0=window.i0 + int(i0[inside].min()),
                i1=window.i0 + int(i1[inside].max()) + 1,
                cells=sum(int(cells[k]) for k in inside),
            )
        )
        for k in inside:
            county = known[k]
            assert county is not None
            found.append(
                GridArea(
                    id=county.geoid,
                    name=county.name,
                    state=code,
                    j0=window.j0 + int(j0[k]),
                    j1=window.j0 + int(j1[k]) + 1,
                    i0=window.i0 + int(i0[k]),
                    i1=window.i0 + int(i1[k]) + 1,
                    cells=int(cells[k]),
                )
            )
    return DataAreas(
        window=[window.j0, window.j1, window.i0, window.i1],
        states=sorted(states, key=lambda a: a.name),
        counties=sorted(found, key=lambda a: (a.state, a.name)),
    )


def _extremes(ids: np.ndarray, index: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """The smallest and largest `index` of each id's cells (meaningless for an id with none)."""
    low = np.full(n, np.iinfo(np.int64).max, dtype=np.int64)
    high = np.full(n, -1, dtype=np.int64)
    np.minimum.at(low, ids, index)
    np.maximum.at(high, ids, index)
    return low, high
