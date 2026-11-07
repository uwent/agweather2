"""Map tiles (docs/api.md, "Tiles"; PLAN.md Phase 5 G): any layer as 256-pixel web-mercator tiles.

`/tiles/{layer}/{time}/{z}/{x}/{y}.png` packs each value into its pixel's color (`agdata.tiles`) for the frontend
to color on the GPU and read under the pointer; `/tiles/{layer}.json` is its TileJSON, with the decoding. `{time}` is
one step: a day (2025-07-08), an hour (2025-07-08T15), a range of days reduced by `stat` (2025-07-01..2025-07-07), a
seasonal product's season (2025-26), or `latest` (what `/grids` shows without a time). The layer's settings (`dd`,
`output`, `planting`, a model's options) are query parameters, as on `/grids`.

A tile reads its layer's map over the whole archive window, kept (`layermaps.cached`) so the 12–20 tiles of a
screen compute it once.
"""

import re
import threading
import time
from typing import Any, Literal

import numpy as np
from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import Query, Router, Schema

from agdata import mapimage, palettes, tiles
from agdata import units as agunits
from agdata.grid import NDFD
from api import clock, layermaps
from api.envelope import Column, etag_for, not_modified, output_units, shown_unit
from api.errors import ApiError
from api.layermaps import LayerQuery
from api.params import EPOCH_DIGITS, UnitsQuery

router = Router(tags=["Maps and grids"])

SEASON = re.compile(r"^\d{4}-\d{2}$")
RANGE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")


class TileQuery(Schema):
    """A layer's settings, as on `/grids`."""

    stat: Literal["sum", "mean", "min", "max", "count", "first", "last", "since"] | None = None
    count: str | None = None  # `days_above_86`, implying stat=count (`api.counts`)
    first: str | None = None  # `frost`, `above_50`: the first day within (`api.events`)
    last: str | None = None
    since: str | None = None
    dd: str | None = None
    gaps: Literal["estimate", "missing"] = "estimate"
    output: str | None = None
    planting: Literal["early", "mid", "late", "none"] | None = None
    style: Literal["default"] | None = None
    scale: str | None = None  # colored tiles and legends: default, auto or low,high (`layermaps.parse_scale`)
    palette: str | None = None  # colored tiles and legends: any of `/palettes`, `_r` reversed
    day_basis: Literal["central", "local"] | None = None  # maps' days are grid days (CST); `local` is refused


def _layer_query(when: str, q: TileQuery) -> LayerQuery:
    """`{time}` and the settings as `/grids` takes them."""
    fields: dict[str, Any] = q.model_dump(exclude={"style", "scale", "palette"})
    event = q.first is not None or q.last is not None or q.since is not None
    if when == "latest":
        pass
    elif event and RANGE.match(when) is None and SEASON.match(when) is None and "T" not in when:
        fields["end"] = when  # a first or last day as of `when`, over its default window (`api.events`)
    elif (span := RANGE.match(when)) is not None:
        if q.stat is None and q.count is None and not event:
            raise ApiError(
                "invalid",
                "A tile shows one map, so a range of days needs stat to combine them (sum, mean, min or max), or "
                "count to count days.",
                "stat",
            )
        fields |= {"start": span.group(1), "end": span.group(2)}
    elif SEASON.match(when):
        fields["season"] = when
    elif "T" in when or (when.isdigit() and len(when) >= EPOCH_DIGITS):  # an hour, ISO or Unix time
        fields["time"] = when
    else:
        fields["date"] = when
    if (q.stat is not None or q.count is not None) and RANGE.match(when) is None:
        param = "stat" if q.stat is not None else "count"
        raise ApiError(
            "invalid",
            f"{param} combines a range of days. Give the time as START..END, such as 2025-07-01..2025-07-07.",
            param,
        )
    return LayerQuery(**fields)


def _ask(request: HttpRequest, layer: str, when: str, q: TileQuery, units: str):
    now = clock.now()
    a = layermaps.ask(request, layer, _layer_query(when, q), units, now)
    if a.first != a.last and a.stat is None:
        raise ApiError("invalid", "A tile shows one map. Give one day or hour, or a range of days with stat.", "time")
    return a, now


# A screen's tiles ask the same of the same data: the checked request, its window and data stamp are kept briefly
# (checking and stamping were ~25 of a tile's ~35 ms), so new data reaches tiles within PREPARED_SECONDS
PREPARED_SECONDS = 15
_prepared_cache: dict[tuple, tuple[float, Any]] = {}
_prepared_lock = threading.Lock()


def _prepared(request: HttpRequest, layer: str, when: str, q: TileQuery, units: str):
    key = (str(_data_dir()), layer, when, tuple(sorted((k, tuple(request.GET.getlist(k))) for k in request.GET)))
    now = time.monotonic()
    with _prepared_lock:
        held = _prepared_cache.get(key)
        if held is not None and now - held[0] < PREPARED_SECONDS:
            return held[1]
    a, at = _ask(request, layer, when, q, units)
    found = (a, at, layermaps.archive_window(_data_dir(), a.stores), layermaps.stamp(a, at))
    with _prepared_lock:
        for k in [k for k, (t, _) in _prepared_cache.items() if now - t >= PREPARED_SECONDS]:
            del _prepared_cache[k]
        _prepared_cache[key] = (now, found)
    return found


@router.get(
    "/tiles/{layer}/{when}/{z}/{x}/{y}.png",
    summary="A data tile",
    response={200: None},
    openapi_extra={"responses": {200: {"content": {"image/png": {}}}}},
)
def tile(
    request: HttpRequest,
    layer: str,
    when: str,
    z: int,
    x: int,
    y: int,
    query: Query[TileQuery],
    output: Query[UnitsQuery],
) -> HttpResponse:
    """A 256-pixel tile whose pixels hold the layer's values (`/tiles/{layer}.json` gives the decoding): value =
    (R·65536 + G·256 + B) × step − 8,388,608 × step, in the layer's stored unit; transparent where missing."""
    started = time.perf_counter()
    if not (0 <= z <= tiles.MAX_ZOOM and 0 <= x < 2**z and 0 <= y < 2**z):
        raise ApiError(
            "out_of_range", f"There's no tile {z}/{x}/{y}. Tiles run from zoom 0 to {tiles.MAX_ZOOM}.", "z", status=404
        )
    a, now, window, data_stamp = _prepared(request, layer, when, query, output.units)
    cells = tiles.index(window, z, x, y)
    etag = etag_for(request, a.echo(), data_stamp)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    if cells is None:
        body = tiles.empty_png()
    else:
        found = layermaps.cached(a, window, now, data_stamp)
        states = layermaps.event_states(found)  # a first or last day's none and no data (D78)
        if query.style is None:
            body = tiles.png(tiles.data_tile(found.values[0], cells, a.step, states))
        else:
            scale = a.scale
            colors = palettes.colorize(tiles.pick(found.values[0], cells), scale.palette, a.domain(found.values[0]))
            if states is not None:
                picked = tiles.pick(states, cells)
                for state, color, _ in mapimage.EMPTY:
                    colors[picked == state] = (*palettes.rgb(color), 255)
            body = tiles.png(colors)
    response = HttpResponse(body, content_type="image/png")
    response["ETag"] = etag
    response["Cache-Control"] = layermaps.cache_control(a, now, latest=when == "latest")
    response["Server-Timing"] = f"total;dur={(time.perf_counter() - started) * 1000:.1f}"
    return response


@router.get("/tiles/{layer}.json", summary="A layer's TileJSON", response={200: None})
def tilejson(
    request: HttpRequest,
    layer: str,
    query: Query[TileQuery],
    output: Query[UnitsQuery],
    time: str = "latest",
) -> HttpResponse:
    """TileJSON 3.0 for a layer at `time` (default `latest`) with its settings: the tile URL, the box's bounds, the
    zooms, and `encoding`, the decoding of a pixel (MapLibre's `raster-dem` custom factors, in the layer's stored
    unit)."""
    a, _ = _ask(request, layer, time, query, output.units)
    window = layermaps.archive_window(_data_dir(), a.stores)
    colored = {}
    if query.style == "default":  # what the colors stand for, for a client's own legend
        _, now, kept_window, data_stamp = _prepared(request, layer, time, query, output.units)
        stored = a.domain(layermaps.cached(a, kept_window, now, data_stamp).values[0])
        column = Column(name=a.layer.id, values=[], unit=a.unit, step=a.step, variable=a.layer.variable or a.layer.id)
        system, overrides = output_units(request)
        shown_as = shown_unit(column, system, overrides)
        shown = [round(float(agunits.convert(np.float64(v), a.unit, shown_as)), 4) for v in stored]
        colored = {"palette": a.scale.palette.id, "domain": shown, "domain_unit": agunits.unit(shown_as).label}
    lat, lon = NDFD.window_latlon(window)
    params = request.GET.copy()
    params.pop("time", None)
    suffix = f"?{params.urlencode()}" if params else ""
    base = request.build_absolute_uri(f"/api/v2/tiles/{layer}/{time}")
    encoding = tiles.Encoding(step=a.step, unit=a.unit)
    return JsonResponse(
        {
            "tilejson": "3.0.0",
            "name": a.label,
            "description": a.layer.description,
            "attribution": "AgWeather, UW–Madison; NOAA NDFD grid",
            "tiles": [f"{base}/{{z}}/{{x}}/{{y}}.png{suffix}"],
            "minzoom": tiles.MIN_ZOOM,
            "maxzoom": tiles.MAX_ZOOM,
            "bounds": [float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())],
            "request": a.echo(),
            **colored,
            "encoding": {
                "scheme": "rgb24",
                "unit": a.unit,
                "step": a.step,
                "missing": "alpha 0",
                **({"none": "code 1 (R 0, G 0, B 1)"} if a.event is not None else {}),
                **({"dates": "days since 1970-01-01"} if a.unit == "date" else {}),
                **encoding.factors,
            },
        },
        json_dumps_params={"default": str},
    )


def _data_dir():
    from django.conf import settings

    return settings.DATA_DIR


@router.get(
    "/tiles/{layer}/legend.png",
    summary="A layer's legend",
    response={200: None},
    openapi_extra={"responses": {200: {"content": {"image/png": {}}}}},
)
def legend(
    request: HttpRequest,
    layer: str,
    query: Query[TileQuery],
    output: Query[UnitsQuery],
    time: str = "latest",
) -> HttpResponse:
    """The legend of `?style=default` tiles at `time` (default `latest`) with the same settings: a color bar with
    ticks in the request's units (`units=`), or a swatch per level for a categorical map. A map whose domain comes
    from its values (running totals, reduced ranges, model outputs) takes the same domain as its tiles."""
    a, now, window, data_stamp = _prepared(request, layer, time, query, output.units)
    etag = etag_for(request, a.echo(), data_stamp)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    scale = a.scale
    domain = scale.domain
    found = layermaps.cached(a, window, now, data_stamp) if domain is None or a.scale_asked or a.event else None
    if found is not None and (domain is None or a.scale_asked is not None):  # from the values, or `scale=`
        domain = a.domain(found.values[0])
    states = layermaps.event_states(found) if found is not None else None
    assert domain is not None
    column = Column(name=a.layer.id, values=[], unit=a.unit, step=a.step, variable=a.layer.variable or a.layer.id)
    system, overrides = output_units(request)
    shown_as = shown_unit(column, system, overrides)
    body = mapimage.legend_png(
        scale.palette,
        domain,
        a.label,
        agunits.unit(shown_as).label,
        lambda v: agunits.convert(v, a.unit, shown_as),
        categories=a.categories,
        dates=a.unit == "date",
        empties=[s for s, _, _ in mapimage.EMPTY if states is not None and (states == s).any()],
    )
    response = HttpResponse(body, content_type="image/png")
    response["ETag"] = etag
    response["Cache-Control"] = layermaps.cache_control(a, now, latest=time == "latest")
    return response


class PaletteInfo(Schema):
    id: str
    kind: Literal["sequential", "diverging", "categorical", "cyclic"]
    colors: list[str]  # low to high, hex
    description: str
    source: str  # where the colors come from (ColorBrewer, matplotlib, AgWeather v1, VDIFN)
    colorblind_safe: bool  # False: offered to readers who want it, never a layer's default


@router.get("/palettes", response=list[PaletteInfo], summary="Map palettes")
def palette_list(request: HttpRequest) -> list[PaletteInfo]:
    """Every palette, named by its colors from low to high: those a layer's `palette` names (`/layers`) and others the
    frontend can offer a reader (`colorblind_safe` false). The frontend colors data tiles with them over each
    layer's `domain`, as `?style=default` tiles and static maps do."""
    return [
        PaletteInfo(
            id=p.id,
            kind=p.kind,
            colors=list(p.colors),
            description=p.description,
            source=p.source,
            colorblind_safe=p.colorblind_safe,
        )
        for p in palettes.PALETTES.values()
    ]
