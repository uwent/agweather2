"""Static map images (docs/api.md, "Static maps"; PLAN.md Phase 5 G3, D60): any layer as a finished PNG to embed by URL.

`/maps/{layer}.png` takes the layer's time and settings as `/grids` does, plus `days=N` (the N days ending on `end`
or the latest day, reduced by `stat`), `region` (a state or county: its cells, framed) and `units`. Without a time
it's the latest day, so a link such as "Today's growing degree day map" stays current. Drawn by
`agdata.mapimage` on the native grid with county and state outlines, the layer's palette (`agdata.palettes`), a
title, the date and a legend.

Images are kept under `data_dir/maps`, named by their ETag (what was asked and the data stamp), so a map is drawn
once per change of its data, on the first request (0.1–1.4 s on the real archive). Those unused for KEEP_DAYS are
deleted by the daily `housekeeping` job (`prune_stale`), and at most MAX_KEPT stay: a draw that goes over deletes the
least recently used.
"""

import hashlib
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Field, Query, Router

from agdata import mapimage, regions, series
from agdata import units as agunits
from agdata.grid import Window
from api import clock, layermaps, maptitles
from api.envelope import Column, etag_for, not_modified, output_units, shown_unit
from api.errors import ApiError
from api.layermaps import LayerQuery
from api.params import UnitsQuery

router = Router(tags=["Maps and grids"])

MARGIN_CELLS = 6  # around a region's cells
KEEP_DAYS = 14  # an image not drawn or read again in this long is deleted
MAX_KEPT = 1000  # most images kept; a new draw over this deletes the least recently used
TMP_HOURS = 1  # a temporary file (from a draw that crashed) older than this is deleted


class MapQuery(LayerQuery):
    """A layer's time and settings (as `/grids`), the area, and a shortcut for the last days."""

    days: int | None = Field(None, ge=1, le=layermaps.MAX_DAYS)
    region: str | None = None
    width: int = Field(800, ge=400, le=2000)
    scale: str | None = None  # the colors' range: default, auto or low,high (`layermaps.parse_scale`)
    palette: str | None = None  # the colors: any of `/palettes`, `_r` reversed (`layermaps._palette_asked`)
    isolines: str | None = None  # off, auto (at the legend's ticks) or N (every N in the map's units)


@router.get(
    "/maps/{layer}.png",
    summary="A static map image",
    response={200: None},
    openapi_extra={"responses": {200: {"content": {"image/png": {}}}}},
)
def static_map(request: HttpRequest, layer: str, query: Query[MapQuery], output: Query[UnitsQuery]) -> HttpResponse:
    """A finished map of a layer on one day (default the latest), an hour, a season, or a range with `stat` (`days=7`
    for the last week), over the service box or a `region`: outlines, title, date and legend, in `units`."""
    started = time.perf_counter()
    now = clock.now()
    a = layermaps.ask(request, layer, _layer_query(query, now), output.units, now)
    if a.first != a.last and a.stat is None:
        raise ApiError(
            "invalid", "A map image shows one map. Give one day or hour, or a range of days with stat.", "stat"
        )
    isolines = parse_isolines(query.isolines, a)
    data_stamp = layermaps.stamp(a, now)
    etag = etag_for(request, {**a.echo(), "isolines": isolines}, data_stamp)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    path = _kept(etag)
    if path.exists():
        os.utime(path)  # read: kept another KEEP_DAYS
        body = path.read_bytes()
    else:
        body = _draw(request, a, query, now, data_stamp, isolines)
        _keep(path, body)
        _enforce_cap(keep=path)
    response = HttpResponse(body, content_type="image/png")
    response["ETag"] = etag
    response["Content-Disposition"] = f'inline; filename="{download_name(a, query, output.units, isolines)}"'
    latest = not (query.date or query.time or query.start or query.end or query.season)
    response["Cache-Control"] = layermaps.cache_control(a, now, latest=latest)
    response["Server-Timing"] = f"total;dur={(time.perf_counter() - started) * 1000:.1f}"
    return response


def _layer_query(q: MapQuery, now: datetime) -> LayerQuery:
    fields: dict[str, Any] = q.model_dump(exclude={"days", "region", "width", "scale", "palette", "isolines"})
    if q.days is not None:
        if q.start or q.date or q.time or q.season or q.biofix or q.roll is not None:
            raise ApiError(
                "conflict",
                "days counts back from end (or the latest day), so it takes no start, biofix, date, time, season "
                "or roll. Leave those out.",
                "days",
            )
        if q.stat is None and q.count is None:
            raise ApiError(
                "invalid", "days needs stat to combine them (sum, mean, min or max), or count to count them.", "stat"
            )
        if q.end is not None:
            end = layermaps.parse_date(q.end, "end")
        else:
            observed = series.last_observed(settings.DATA_DIR, now)
            if observed is None:
                raise ApiError("no_data", layermaps.NO_DATA, None, status=503)
            end = series.last_closed_day(observed)
        fields |= {"start": (end - timedelta(days=q.days - 1)).isoformat(), "end": end.isoformat()}
    return LayerQuery(**fields)


def parse_isolines(text: str | None, a: layermaps.LayerAsk) -> mapimage.Isolines:
    """`isolines=off` (or left out), `auto` (at the legend's ticks) or a positive number (every N in the map's units:
    degrees, inches, days for a date map)."""
    if text is None or text.strip().lower() in ("", "off"):
        return None
    given = text.strip().lower()
    if a.scale.palette.kind == "categorical":
        raise ApiError(
            "not_applicable",
            f"{a.label} has a color for each level, so it takes no isolines. Leave out isolines.",
            "isolines",
        )
    if given == "auto":
        return "auto"
    try:
        every = float(given)
    except ValueError:
        every = float("nan")
    if not np.isfinite(every) or every <= 0:
        raise ApiError(
            "invalid",
            f"We can't read isolines={text}. Give isolines=auto for a line at each of the legend's values, a number "
            "for a line every so many units (isolines=5 for every 5 degrees), or isolines=off.",
            "isolines",
        )
    return every


def check_isoline_count(values: np.ndarray, every: float, shown: Any) -> None:
    """Refuses `isolines=N` that would draw more than `mapimage.MAX_LEVELS` lines over the values' range (`shown`
    converts stored values to the map's unit), suggesting a spacing that draws about 20."""
    if not np.isfinite(values).any():
        return
    ends = shown(np.array([np.nanmin(values), np.nanmax(values)]))
    span = abs(float(ends[1] - ends[0]))
    if span / every > mapimage.MAX_LEVELS:
        wider = float(f"{span / 20:.1g}")
        raise ApiError(
            "too_large",
            f"isolines={every:g} would draw about {span / every:,.0f} lines on this map, more than "
            f"{mapimage.MAX_LEVELS}. Choose a wider spacing, such as isolines={wider:g}.",
            "isolines",
        )


def download_name(a: layermaps.LayerAsk, q: MapQuery, units: str | None, isolines: mapimage.Isolines) -> str:
    """The name a browser offers when the map is saved: the layer and what was asked (`LayerAsk.echo`, the region,
    units, scale, palette and isolines), as `soil_temperature_4cm_mean_min_2025-07-01_2026-07-01.png`."""
    echo = a.echo()
    parts: list[Any] = [echo.pop("layer")]
    if "start" in echo:
        parts += [echo.pop("stat", None), echo.pop("start"), echo.pop("end")]
    parts += [echo.pop(key, None) for key in ("date", "time", "stat")]
    for key in ("gaps", "scale", "palette"):
        echo.pop(key, None)
    parts += [f"{key}-{value}" for key, value in echo.items() if value is not None]
    if q.region:
        parts.append(q.region)
    if units and units != "us":
        parts.append(units)
    if a.scale_asked is not None:
        parts.append(f"scale-{a.scale_asked.text}")
    if a.palette_asked is not None:
        parts.append(a.palette_asked.id)
    if isolines is not None:
        parts.append(f"isolines-{isolines if isolines == 'auto' else f'{isolines:g}'}")
    words = [re.sub(r"[^A-Za-z0-9._-]+", "-", str(p)).strip("-") for p in parts if p not in (None, "")]
    return "_".join(w for w in words if w)[:150] + ".png"


def _draw(
    request: HttpRequest,
    a: layermaps.LayerAsk,
    q: MapQuery,
    now: datetime,
    data_stamp: Any,
    isolines: mapimage.Isolines = None,
) -> bytes:
    archive = layermaps.archive_window(settings.DATA_DIR, a.stores)
    computed = layermaps.cached(a, archive, now, data_stamp)
    values = computed.values[0]
    states = layermaps.event_states(computed)  # a first or last day's none and no data (D78)
    window, region = archive, None
    if q.region is not None:
        region = regions.find(q.region)
        if region is None:
            raise ApiError(
                "unknown_region",
                f"We don't recognize the region {q.region!r}. Give a state's name or postal code "
                "(wisconsin or WI), or a "
                "county's five-digit FIPS code (55025).",
                "region",
            )
        inside = regions.mask(region, archive)
        if not inside.any():
            raise ApiError(
                "outside_box", f"{region.name} is outside the area we cover, so it has no grid cells here.", "region"
            )
        values = np.where(inside, values, np.nan)
        if states is not None:
            states = _framed(archive, inside, np.where(inside, states, np.nan))[1]
        window, values = _framed(archive, inside, values)
    column = Column(name=a.layer.id, values=[], unit=a.unit, step=a.step, variable=a.layer.variable or a.layer.id)
    system, overrides = output_units(request)
    shown_as = shown_unit(column, system, overrides)
    if isinstance(isolines, float):
        check_isoline_count(values, isolines, lambda v: agunits.convert(v, a.unit, shown_as))
    return mapimage.map_png(
        values,
        window,
        a.scale.palette,
        a.domain(values),
        a.label,
        maptitles.subtitle(a, region.name if region is not None else None),
        agunits.unit(shown_as).label,
        lambda v: agunits.convert(v, a.unit, shown_as),
        categories=a.categories,
        caption=maptitles.caption(a, computed),
        width=q.width,
        dates=a.unit == "date",
        states=states,
        middle=a.middle,
        isolines=isolines,
    )


def _framed(archive: Window, inside: np.ndarray, values: np.ndarray) -> tuple[Window, np.ndarray]:
    """The region's cells and a margin, as a window and its values."""
    rows, cols = np.flatnonzero(inside.any(axis=1)), np.flatnonzero(inside.any(axis=0))
    y0, y1 = max(0, rows[0] - MARGIN_CELLS), min(archive.shape[0], rows[-1] + 1 + MARGIN_CELLS)
    x0, x1 = max(0, cols[0] - MARGIN_CELLS), min(archive.shape[1], cols[-1] + 1 + MARGIN_CELLS)
    window = Window(j0=archive.j0 + y0, j1=archive.j0 + y1, i0=archive.i0 + x0, i1=archive.i0 + x1)
    return window, values[y0:y1, x0:x1]


def _maps_dir() -> Path:
    return Path(settings.DATA_DIR) / "maps"


def _kept(etag: str) -> Path:
    return _maps_dir() / f"{hashlib.sha256(etag.encode()).hexdigest()[:24]}.png"


def _keep(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_bytes(body)
    tmp.replace(path)


def prune_stale() -> int:
    """Deletes images not drawn or read in KEEP_DAYS and old temporary files; returns how many. For `ops.tasks`."""
    now = time.time()
    deleted = 0
    for path in _maps_dir().glob("*.png"):
        if _mtime(path) < now - KEEP_DAYS * 86400:
            path.unlink(missing_ok=True)
            deleted += 1
    for path in _maps_dir().glob("*.tmp"):
        if _mtime(path) < now - TMP_HOURS * 3600:
            path.unlink(missing_ok=True)
    return deleted


def _enforce_cap(keep: Path) -> None:
    """Deletes the least recently used images beyond MAX_KEPT, never `keep` (the one just drawn)."""
    kept = sorted(((_mtime(p), p) for p in _maps_dir().glob("*.png") if p != keep), key=lambda e: e[0])
    for _, path in kept[: max(0, len(kept) + 1 - MAX_KEPT)]:
        path.unlink(missing_ok=True)


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:  # another worker deleted it
        return float("inf")
