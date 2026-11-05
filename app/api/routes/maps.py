"""Static map images (docs/api.md, "Maps"; PLAN.md Phase 5 G3, D60): any layer as a finished PNG to embed by URL.

`/maps/{layer}.png` takes the layer's time and settings as `/grids` does, plus `days=N` (the N days ending on `end`
or the latest day, reduced by `stat`), `region` (a state or county: its cells, framed) and `units`. Without a time
it's the latest day, so a link such as "Today's growing degree day map" stays current. Drawn by
`agdata.mapimage` on the native grid with county and state outlines, the layer's palette (`agdata.palettes`), a
title, the date and a legend.

Images are kept under `data_dir/maps`, named by their ETag (what was asked and the data stamp), so a map is drawn
once per change of its data; `render_default_maps` (after each hourly ingest) draws `DEFAULT_MAPS` ahead of time.
"""

import hashlib
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from ninja import Field, Query, Router

from agdata import mapimage, regions, series
from agdata import units as agunits
from agdata.grid import Window
from api import clock, layermaps
from api.envelope import Column, etag_for, not_modified, output_units, shown_unit
from api.errors import ApiError
from api.layermaps import LayerQuery
from api.params import UnitsQuery

router = Router(tags=["Maps and grids"])

MAX_DAYS = 366
MARGIN_CELLS = 6  # around a region's cells
KEEP_DAYS = 14  # an image not drawn or read again in this long is deleted
# What the job draws ahead of time: v1's map set (degree days, temperatures, a week's rain and ET, sunlight, the
# season's totals)
DEFAULT_MAPS: list[tuple[str, dict[str, str]]] = [
    ("dd_modified_50_86", {}),
    ("air_temperature_max", {}),
    ("air_temperature_min", {}),
    ("precipitation_sum", {"days": "7", "stat": "sum"}),
    ("et0_sum", {"days": "7", "stat": "sum"}),
    ("shortwave_radiation_sum", {}),
    ("precipitation_total", {}),
    ("et0_total", {}),
]


class MapQuery(LayerQuery):
    """A layer's time and settings (as `/grids`), the area, and a shortcut for the last days."""

    days: int | None = Field(None, ge=1, le=MAX_DAYS)
    region: str | None = None
    width: int = Field(800, ge=400, le=2000)


@router.get(
    "/maps/{layer}.png",
    summary="A static map image",
    response={200: None},
    openapi_extra={"responses": {"200": {"content": {"image/png": {}}}}},
)
def static_map(request: HttpRequest, layer: str, query: Query[MapQuery], output: Query[UnitsQuery]) -> HttpResponse:
    """A finished map of a layer on one day (default the latest), an hour, a season, or a range with `stat` (`days=7`
    for the last week), over the service box or a `region`: outlines, title, date and legend, in `units`."""
    started = time.perf_counter()
    now = clock.now()
    a = layermaps.ask(request, layer, _layer_query(query, now), output.units, now)
    if a.first != a.last and a.stat is None:
        raise ApiError("invalid", "a map is one step: give one day or hour, or a range with stat", "stat")
    data_stamp = layermaps.stamp(a, now)
    etag = etag_for(request, a.echo(), data_stamp)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    path = _kept(etag)
    if path.exists():
        os.utime(path)  # read: kept another KEEP_DAYS
        body = path.read_bytes()
    else:
        body = _draw(request, a, query, now, data_stamp)
        _keep(path, body)
    response = HttpResponse(body, content_type="image/png")
    response["ETag"] = etag
    latest = not (query.date or query.time or query.start or query.end or query.season)
    response["Cache-Control"] = layermaps.cache_control(a, now, latest=latest)
    response["Server-Timing"] = f"total;dur={(time.perf_counter() - started) * 1000:.1f}"
    return response


def _layer_query(q: MapQuery, now: datetime) -> LayerQuery:
    fields: dict[str, Any] = q.model_dump(exclude={"days", "region", "width"})
    if q.days is not None:
        if q.start or q.date or q.time or q.season:
            raise ApiError(
                "conflict", "days counts back from end (default the latest day): give no other start", "days"
            )
        if q.stat is None:
            raise ApiError("invalid", "days needs stat (sum, mean, min or max)", "stat")
        if q.end is not None:
            end = date.fromisoformat(q.end)
        else:
            observed = series.last_observed(settings.DATA_DIR, now)
            if observed is None:
                raise ApiError("no_data", "the archive has no data yet", None, status=503)
            end = series.last_closed_day(observed)
        fields |= {"start": (end - timedelta(days=q.days - 1)).isoformat(), "end": end.isoformat()}
    return LayerQuery(**fields)


def _draw(request: HttpRequest, a: layermaps.LayerAsk, q: MapQuery, now: datetime, data_stamp: Any) -> bytes:
    archive = layermaps.archive_window(settings.DATA_DIR, a.stores)
    values = layermaps.cached(a, archive, now, data_stamp).values[0]
    window = archive
    if q.region is not None:
        region = regions.find(q.region)
        if region is None:
            raise ApiError(
                "unknown_region", f"{q.region!r} isn't a state (wisconsin, WI) or a county (55025)", "region"
            )
        inside = regions.mask(region, archive)
        if not inside.any():
            raise ApiError("outside_box", f"{region.name} has no cells in the service box", "region")
        values = np.where(inside, values, np.nan)
        window, values = _framed(archive, inside, values)
    column = Column(name=a.layer.id, values=[], unit=a.unit, step=a.step, variable=a.layer.variable or a.layer.id)
    system, overrides = output_units(request)
    shown_as = shown_unit(column, system, overrides)
    return mapimage.map_png(
        values,
        window,
        a.scale.palette,
        a.domain(values),
        a.label + (f" · {regions.find(q.region).name}" if q.region and regions.find(q.region) else ""),  # type: ignore[union-attr]
        _subtitle(a),
        agunits.unit(shown_as).label,
        lambda v: agunits.convert(v, a.unit, shown_as),
        categories=a.categories,
        width=q.width,
    )


def _framed(archive: Window, inside: np.ndarray, values: np.ndarray) -> tuple[Window, np.ndarray]:
    """The region's cells and a margin, as a window and its values."""
    rows, cols = np.flatnonzero(inside.any(axis=1)), np.flatnonzero(inside.any(axis=0))
    y0, y1 = max(0, rows[0] - MARGIN_CELLS), min(archive.shape[0], rows[-1] + 1 + MARGIN_CELLS)
    x0, x1 = max(0, cols[0] - MARGIN_CELLS), min(archive.shape[1], cols[-1] + 1 + MARGIN_CELLS)
    window = Window(j0=archive.j0 + y0, j1=archive.j0 + y1, i0=archive.i0 + x0, i1=archive.i0 + x1)
    return window, values[y0:y1, x0:x1]


def _subtitle(a: layermaps.LayerAsk) -> str:
    """When the map shows, as a reader says it."""
    model = a.model
    if model is not None and model.season is not None and a.first == a.last:
        return f"{model.season.label} season, through {_day(a.last)}"
    if isinstance(a.first, datetime):
        when = f"{a.first:%B} {a.first.day}, {a.first:%Y %H:%M} UTC"
    elif a.first == a.last:
        when = _day(a.first)
    else:
        first, last = a.first, a.last
        span = (
            f"{first:%B} {first.day}–{last.day}"
            if first.month == last.month
            else f"{_day(first, year=False)} to {_day(last, year=False)}"
        )
        when = f"{span}, {last.year} ({a.stat})"
    if a.layer.source == "cumulative":
        when = f"January 1 to {_day(a.last)}"
    return when


def _day(d: date, year: bool = True) -> str:
    return f"{d:%B} {d.day}" + (f", {d.year}" if year else "")


def _maps_dir() -> Path:
    return Path(settings.DATA_DIR) / "maps"


def _kept(etag: str) -> Path:
    return _maps_dir() / f"{hashlib.sha256(etag.encode()).hexdigest()[:24]}.png"


def _keep(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_bytes(body)
    tmp.replace(path)


def render_default_maps() -> dict[str, float]:
    """Draws `DEFAULT_MAPS` for the latest data where they're not drawn yet, and deletes images not drawn or read in
    KEEP_DAYS; returns each map's time in ms (0 if it was there already). For `ops.tasks`."""
    factory = RequestFactory()
    found: dict[str, float] = {}
    for layer, params in DEFAULT_MAPS:
        request = factory.get(f"/api/v2/maps/{layer}.png", params)
        started = time.perf_counter()
        before = {p.name for p in _maps_dir().glob("*.png")} if _maps_dir().exists() else set()
        static_map(request, layer, query=MapQuery(**params), output=UnitsQuery())  # type: ignore[arg-type]
        after = {p.name for p in _maps_dir().glob("*.png")}
        found[layer] = (time.perf_counter() - started) * 1000 if after - before else 0.0
    cutoff = time.time() - KEEP_DAYS * 86400
    for path in _maps_dir().glob("*.png"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
    return found
