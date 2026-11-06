"""Maps as data (docs/api.md, "Grids"; PLAN.md Phase 5 E): the layer catalog and any layer over an area.

`/layers` lists what can be mapped (`agdata.layers`) with each layer's time axis and the range the archive and
forecast hold. `/grids/{layer}` reads one step or a range over the service box, a bounding box or a state or
county (`agdata.regions`), every `stride`-th cell or resampled to a regular lat/lng grid (`agdata.regrid`), and
answers in JSON or CSV (long form, a row per cell and step), NetCDF or GeoTIFF (`api.gridfiles`). What the map is
and how it's computed (statistics, degree days, model layers, seasons) is `api.layermaps`, shared with the tiles
and static maps.
"""

import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Field, Query, Router, Schema

from agdata import modelgrid, palettes, regions, seasonal, series
from agdata import units as agunits
from agdata.catalog import DAILY_STATISTICS
from agdata.grid import NDFD, Box, Window
from agdata.layers import DEGREE_DAYS, LAYERS, Layer, LayerOutput
from agdata.regrid import MIN_LATLON_RES, LatLonIndex, latlon_index
from api import clock, layermaps, maptitles
from api.envelope import (
    Column,
    Result,
    digits_for,
    etag_for,
    not_modified,
    output_units,
    requested_format,
    respond,
    shown_unit,
)
from api.errors import ApiError, counted
from api.gridfiles import GridFile, geotiff, netcdf
from api.layermaps import LayerQuery
from api.params import OutputQuery
from api.routes.discovery import DisplayUnits, display_units
from api.schemas import Meta, TableResponse, responses
from ops.status import dataset_status

router = Router(tags=["Maps and grids"])

FORMATS = ("json", "csv", "netcdf", "geotiff")
MAX_TEXT_VALUES = 2_000_000  # JSON and CSV: ~70 MB and 1.5–2.5 s to write; NetCDF and GeoTIFF beyond it
MAX_FILE_VALUES = 22_000_000  # NetCDF and GeoTIFF: a leap year of days over Wisconsin (57,820 cells)
MAX_STRIDE = 50
HOUR = timedelta(hours=1)


# --- /layers -------------------------------------------------------------------------------------------------------


class LayerRange(Schema):
    first: str | None  # the first day (or hour, UTC end) the archive holds
    last: str | None  # the last observed day (or hour)
    forecast_through: str | None  # the last day (or hour) of the forecast in use; None without one


class LayerOutputInfo(Schema):
    name: str  # `output=`
    label: str
    unit: str
    units: DisplayUnits
    precision: float
    palette: str  # `/palettes`; an id ending `_r` is that palette reversed
    domain: list[float] | None  # what the palette's ends stand for, in the stored unit; None: from the map's values


class LayerInfo(Schema):
    id: str
    name: str
    title: str  # its name as a map's title gives it ("Air temperature, daily maximum")
    group: Literal["weather", "running_total", "degree_days", "model"]
    time_axis: Literal["day", "hour", "day_of_year"]
    variable: str | None  # the catalog variable (`/variables`); None where the layer is computed (degree days)
    unit: str  # stored unit symbol
    units: DisplayUnits
    precision: float  # the stored step, in `unit`
    palette: str  # `/palettes` (`_r`: reversed): a color scale, the same for layers of one kind
    domain: list[float] | None  # what the palette's ends stand for, in the stored unit; None: from the map's values
    stats: list[str]  # what a range can be reduced to (`stat=`); empty for running totals
    parameters: list[str]  # required beyond the time and area (`dd` for degree days)
    range: LayerRange
    description: str
    outputs: list[LayerOutputInfo] = Field(default_factory=list)  # a model layer's, the default first (`output=`)
    # a model layer's scenario options (`GET /models/{id}` describes them), and its planting tiers (`planting=`)
    options: list[str] = Field(default_factory=list)
    planting: list[str] = Field(default_factory=list)
    seasons: list[str] = Field(default_factory=list)  # a seasonal product's (`season=`), oldest first


class LayersResponse(Schema):
    meta: Meta
    data: list[LayerInfo]


@router.get("/layers", response=responses(LayersResponse), summary="Every mappable layer")
def layers(request: HttpRequest) -> HttpResponse:
    """Each layer `/grids/{layer}` serves, with its time axis and the range the archive and forecast hold now (from
    `/status`'s rows), and for a model its outputs and options. Normals and departures (time axis `day_of_year`)
    join later."""
    rows = dataset_status(settings.DATA_DIR)
    run = rows["forecast"]
    in_use = run.first is not None and clock.now() - run.first <= series.MAX_RUN_AGE
    hourly, daily = rows["hourly"], rows["daily"]
    observed = series.last_observed(settings.DATA_DIR, clock.now())
    ranges = {
        "hour": LayerRange(
            first=_hour(hourly.first),
            last=_hour(observed),
            forecast_through=_hour(run.last) if in_use else None,
        ),
        "day": LayerRange(
            first=daily.first.date().isoformat() if daily.first else None,
            last=series.last_closed_day(observed).isoformat() if observed else None,
            forecast_through=run.last.date().isoformat() if in_use and run.last else None,
        ),
    }
    found = [
        LayerInfo(
            id=layer.id,
            name=layer.name,
            title=maptitles.layer_title(layer),
            group=layer.group,
            time_axis=layer.time_axis,
            variable=layer.variable,
            unit=layer.unit,
            units=display_units(layer.unit),
            precision=layer.step,
            palette=palettes.use_palette(layer.use).id,
            domain=_layer_domain(layer),
            stats=list(layer.stats),
            parameters=["dd"] if layer.id == DEGREE_DAYS else [],
            range=ranges[layer.time_axis],
            description=layer.description,
            outputs=[_output_info(o) for o in layer.outputs],
            options=_map_options(layer),
            planting=["early", "mid", "late", "none"] if layer.planting else [],
            seasons=_seasons_held(layer, observed),
        )
        for layer in LAYERS.values()
    ]
    return respond(request, Result(request={}, data=[f.model_dump() for f in found]))


def _layer_domain(layer: Layer) -> list[float] | None:
    if layer.outputs:  # a model's: its default output's
        return _output_info(layer.outputs[0]).domain
    found = palettes.scale_for(layer.use, layer.time_axis, running=layer.source == "cumulative").domain
    return list(found) if found else None


def _output_info(o: LayerOutput) -> LayerOutputInfo:
    domain = palettes.scale_for(o.use, "day", running=True).domain
    return LayerOutputInfo(
        name=o.name,
        label=o.label,
        unit=o.unit,
        units=display_units(o.unit),
        precision=o.step,
        palette=palettes.use_palette(o.use).id,
        domain=list(domain) if domain else None,
    )


def _seasons_held(layer: Layer, observed: datetime | None) -> list[str]:
    spec = seasonal.seasonal_spec(layer.id) if layer.source == "model" else None
    if spec is None or observed is None:
        return []
    held = seasonal.held(spec, series.archive_years(settings.DATA_DIR), series.last_closed_day(observed))
    return [s.name for s in held]


def _map_options(layer: Layer) -> list[str]:
    """A model layer's options a map takes: the scenario's, not the place's (D66)."""
    if layer.source != "model":
        return []
    spec = modelgrid.mapped()[layer.id].SPEC
    return [o.name for o in spec.options if o.name not in modelgrid.PLACE_OPTIONS]


def _hour(when: datetime | None) -> str | None:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ") if when is not None else None


# --- /grids/{layer} ------------------------------------------------------------------------------------------------


class GridQuery(LayerQuery):
    """When, where and how: a layer's step or range (`LayerQuery`), its area, and the grid it's given on."""

    bbox: str | None = None
    region: str | None = None
    stride: int = Field(1, ge=1, le=MAX_STRIDE)
    grid: Literal["native", "latlon"] = "native"
    res: float | None = None
    method: Literal["nearest", "mean"] | None = None
    cells: bool = False


@router.get("/grids/{layer}", response=responses(TableResponse), summary="A layer over an area")
def grid(request: HttpRequest, layer: str, query: Query[GridQuery], output: Query[OutputQuery]) -> HttpResponse:
    """A layer (`/layers`) on one day or hour, each step of a range, or a range reduced by `stat`, over the service
    box, a `bbox` or a `region`. JSON and CSV are long form, a row per cell (and step): `date` or `time`, `kind`,
    `lat`, `lng` (the cell's center, or the lat/lng point), `j` and `i` with `cells=true`, the layer's value under
    its id, and with `stat` each cell's `estimated_days` and `missing_days`; up to 2 million values. NetCDF and
    GeoTIFF keep the native Lambert grid with its projection (or the lat/lng grid), a band per step."""
    started = time.perf_counter()
    fmt = requested_format(request, FORMATS)
    now = clock.now()
    data_dir = settings.DATA_DIR
    a = layermaps.ask(request, layer, query, output.units, now)
    found, model, first, last, stat, warnings = a.layer, a.model, a.first, a.last, a.stat, a.warnings
    archive = layermaps.archive_window(data_dir, a.stores)
    window, mask, area = _area(query, archive)
    grid_spec = _grid_spec(query, window, mask)
    steps_out = 1 if stat is not None else _steps(found, first, last)
    cells_out = grid_spec["cells"]
    _check_size(fmt, steps_out, cells_out, grid_spec["full"])

    computed: dict[str, Any] = {**a.echo(), **area, **grid_spec["echo"], "format": fmt}
    first_day = first.date() if isinstance(first, datetime) else first
    last_day = last.date() if isinstance(last, datetime) else last
    etag = etag_for(request, computed, layermaps.stamp(a, now))
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged

    c = layermaps.compute(a, window, now)
    values, kinds, extra, sources, run, step_labels = c.values, c.kinds, c.extra, c.sources, c.run, c.steps
    compute_ms = c.ms
    values = np.where(mask[None], values, np.nan)
    extra = {name: np.where(mask, v, np.nan) for name, v in extra.items()}
    if query.stride > 1:
        values = values[:, :: query.stride, :: query.stride]
        extra = {name: v[:: query.stride, :: query.stride] for name, v in extra.items()}

    missing_steps = sum(k is None for k in kinds)
    if missing_steps:
        warnings.append(
            f"{counted(missing_steps, found.time_axis)} of the {len(kinds)} asked for "
            f"{'has' if missing_steps == 1 else 'have'} no data yet and show as missing."
        )
    if run.reason == "stale" and any(k is None for k in kinds):
        warnings.append("The forecast is out of date, so the map ends with the last observed day.")
    summary: dict[str, Any] = {
        "steps": len(kinds),
        "kinds": {kind or "missing": kinds.count(kind) for kind in dict.fromkeys(kinds)},
        "cells": cells_out,
        **({"stat": stat} if stat else {}),
        "corrections": list(series.in_box_corrections(kinds, run, layermaps.hourly_of(found))),
    }
    if a.cubes and c.from_cubes:
        summary["from_running_totals"] = [name for name in a.cubes if name]

    if model is not None:
        summary["model"] = {"id": found.id, "version": model.spec.version, "output": model.output.name}
        if model.planted is not None:
            summary["planting"] = layermaps.planting_summary(model, mask, warnings)
        if model.season is not None:
            summary["season"] = seasonal.describe(
                data_dir, model.spec, model.season, last, series.last_closed_day(a.observed)
            )
        if model.projection is not None:
            projected: dict[str, Any] = {
                "seasons": [layermaps.season_name(model.spec, y) for y in model.projection.years]
            }
            if not model.projection.years:
                projected["note"] = "The season is over, so the map shows its own count rather than a projection."
            summary["projection"] = projected
    unit, step = a.unit, a.step
    column = Column(
        name=found.id,
        values=[],
        unit=unit,
        step=step,
        variable=found.variable or found.id,
        summarize=True,
        total=False,
    )
    result = Result(
        request=computed,
        summary=summary,
        sources=list(sources),
        warnings=warnings,
        etag=etag,
        filename=f"agweather-{found.id}-{first_day:%Y%m%d}" + (f"-{last_day:%Y%m%d}" if last_day != first_day else ""),
        formats=FORMATS,
        timings={"compute": compute_ms},
    )
    index = grid_spec.get("index")
    if fmt in ("netcdf", "geotiff"):
        system, overrides = output_units(request)
        shown_as = shown_unit(column, system, overrides)
        digits = digits_for(step, unit, shown_as)
        shown = np.round(agunits.convert(values, unit, shown_as), digits)
        long_name = a.label
        file = GridFile(
            name=found.id,
            long_name=long_name,
            unit=shown_as,
            values=shown if index is None else index.resample(shown),
            steps=None if stat is not None else step_labels,
            window=window if index is None else None,
            stride=query.stride,
            lats=index.lats if index is not None else None,
            lons=index.lons if index is not None else None,
            extra=extra if index is None else {k: index.resample(v[None])[0] for k, v in extra.items()},
            cell_methods=_cell_methods(found, stat),
        )
        result.binary_units = {found.id: agunits.unit(shown_as).label}

        def render(kind: str, meta: dict[str, Any]) -> bytes:
            file.attrs = {key: meta[key] for key in ("request", "sources", "warnings", "attribution", "api_version")}
            file.attrs["generated_at"] = meta["generated_at"]
            # One gridded variable a NetCDF file (D71): beside the counts GDAL opens it as subdatasets, which terra
            # on Windows then reads without its projection. The counts are in JSON, CSV and GeoTIFF's bands.
            return netcdf(replace(file, extra={})) if kind == "netcdf" else geotiff(file)

        result.render = render
    else:
        result.columns = _long_form(
            found, column, values, kinds, extra, step_labels, stat, window, mask, query, index, grid_spec.get("inside")
        )
    result.timings["read_and_shape"] = (time.perf_counter() - started) * 1000 - compute_ms
    return respond(request, result)


# --- Parsing -------------------------------------------------------------------------------------------------------


def _steps(layer: Layer, first, last) -> int:
    """Steps in the range (`layermaps.span` has checked its length)."""
    return (last - first) // HOUR + 1 if layer.time_axis == "hour" else (last - first).days + 1


def _area(q: GridQuery, archive: Window) -> tuple[Window, np.ndarray, dict[str, Any]]:
    """The smallest window holding the cells asked for, and which of its cells those are."""
    mask = np.ones(archive.shape, dtype=bool)
    echo: dict[str, Any] = {}
    if q.bbox is not None:
        box = _parse_bbox(q.bbox)
        lat, lon = NDFD.window_latlon(archive)
        mask &= (lat >= box.south) & (lat <= box.north) & (lon >= box.west) & (lon <= box.east)
        echo["bbox"] = [box.south, box.west, box.north, box.east]
        if not mask.any():
            raise ApiError(
                "outside_box",
                f"The bbox has no grid cells in the area we cover ({settings.SERVICE_BOX}, as south,west,north,east). "
                "Choose a box that overlaps it.",
                "bbox",
            )
    if q.region is not None:
        region = regions.find(q.region)
        if region is None:
            raise ApiError(
                "unknown_region",
                f"We don't recognize the region {q.region!r}. Give a state's name or postal code "
                "(wisconsin or WI), or a "
                "county's five-digit FIPS code (55025 for Dane County, Wisconsin).",
                "region",
            )
        mask &= regions.mask(region, archive)
        echo["region"] = {"id": region.id, "name": region.name}
        if not mask.any():
            raise ApiError(
                "outside_box", f"{region.name} is outside the area we cover, so it has no grid cells here.", "region"
            )
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    window = Window(
        j0=archive.j0 + int(rows[0]),
        j1=archive.j0 + int(rows[-1]) + 1,
        i0=archive.i0 + int(cols[0]),
        i1=archive.i0 + int(cols[-1]) + 1,
    )
    crop = mask[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]
    return window, crop, echo


def _parse_bbox(text: str) -> Box:
    try:
        south, west, north, east = (float(v) for v in text.split(","))
        return Box(south=south, west=west, north=north, east=east)
    except ValueError:
        raise ApiError(
            "invalid",
            f"The bbox ({text}) isn't four numbers. Give it as south,west,north,east in degrees, such as "
            "42.5,-92.9,47.1,-86.8.",
            "bbox",
        ) from None


def _grid_spec(q: GridQuery, window: Window, mask: np.ndarray) -> dict[str, Any]:
    """The output grid: how many cells each step has (rows in JSON and CSV, `cells`; the file's, `full`), and for
    a lat/lng grid its index."""
    if q.grid == "native":
        if q.res is not None or q.method is not None:
            raise ApiError(
                "invalid",
                "res and method apply only to grid=latlon. Leave them out, or add grid=latlon.",
                "res" if q.res is not None else "method",
            )
        kept = mask[:: q.stride, :: q.stride]
        return {
            "cells": int(kept.sum()),
            "full": kept.size,
            "index": None,
            "echo": {"grid": "native", "stride": q.stride, "window": [window.j0, window.j1, window.i0, window.i1]},
        }
    if q.stride != 1:
        raise ApiError(
            "invalid",
            "stride applies only to the native grid. For a coarser latitude and longitude grid, give a larger res.",
            "stride",
        )
    if q.res is None:
        raise ApiError(
            "missing", f"grid=latlon needs res, the grid's spacing in degrees (at least {MIN_LATLON_RES}).", "res"
        )
    if not MIN_LATLON_RES <= q.res <= 5:
        raise ApiError(
            "out_of_range",
            f"res={q.res:g} isn't between {MIN_LATLON_RES} and 5 degrees. Choose a spacing in that range.",
            "res",
        )
    method = q.method or ("mean" if q.res >= 0.05 else "nearest")
    lat, lon = NDFD.window_latlon(window)
    lat, lon = lat[mask], lon[mask]
    index = latlon_index(window, float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max()), q.res, method)
    inside = _points_inside(index, mask)
    return {
        "cells": int(inside.sum()),
        "full": inside.size,
        "index": index,
        "inside": inside,
        "echo": {"grid": "latlon", "res": q.res, "method": method, "shape": list(index.shape)},
    }


def _points_inside(index: LatLonIndex, mask: np.ndarray) -> np.ndarray:
    """Which lat/lng points take a value from a cell in the area: (ny * nx,)."""
    n = index.shape[0] * index.shape[1]
    if index.method == "nearest":
        assert index.cell is not None
        return (index.cell >= 0) & mask.ravel()[np.clip(index.cell, 0, None)]
    assert index.box is not None
    boxes = index.box[(index.box >= 0) & mask.ravel()]
    return np.bincount(boxes, minlength=n) > 0


def _check_size(fmt: str, steps: int, cells: int, full: int) -> None:
    if fmt in ("json", "csv"):
        if steps * cells > MAX_TEXT_VALUES:
            raise ApiError(
                "too_large",
                f"This request has {steps * cells:,} values ({steps} steps × {cells:,} cells); JSON and CSV hold up to "
                f"{MAX_TEXT_VALUES:,}. Ask for format=netcdf or geotiff, combine the days with "
                "stat, or choose a smaller "
                "area or a stride.",
                "format",
            )
    elif steps * full > MAX_FILE_VALUES:
        raise ApiError(
            "too_large",
            f"This request has {steps * full:,} values ({steps} steps × {full:,} cells); a file holds up to "
            f"{MAX_FILE_VALUES:,}. Choose a smaller area, a stride or a shorter range.",
            "start",
        )


_CF_STATS = {"min": "minimum", "max": "maximum", "mean": "mean", "sum": "sum"}


def _cell_methods(layer: Layer, stat: str | None) -> str | None:
    """CF's `cell_methods`: how a step summarizes its hours (a daily statistic, a total), then the range's `stat`."""
    method = None
    if layer.source == "daily" and layer.variable in DAILY_STATISTICS:
        method = f"time: {_CF_STATS[DAILY_STATISTICS[layer.variable].stat]}"
    elif layer.source == "cumulative" or (layer.source == "hourly" and layer.summable):
        method = "time: sum"
    if stat is not None:
        method = f"{method} " if method else ""
        method += f"time: {_CF_STATS[stat]}"
    return method


# --- Long form -----------------------------------------------------------------------------------------------------


def _long_form(layer, column, values, kinds, extra, steps, stat, window, mask, q, index, inside) -> list[Column]:
    """A row per cell (or lat/lng point) and step, cells south to north then west to east, steps in order."""
    if index is None:
        kept = mask[:: q.stride, :: q.stride].ravel()
        jj, ii = np.mgrid[window.j0 : window.j1 : q.stride, window.i0 : window.i1 : q.stride]
        jj, ii = jj.ravel()[kept], ii.ravel()[kept]
        lat, lng = NDFD.latlon(jj, ii)
        flat = values.reshape(values.shape[0], -1)[:, kept]
        counts = {name: v.ravel()[kept] for name, v in extra.items()}
    else:
        lat2, lng2 = np.meshgrid(index.lats, index.lons, indexing="ij")
        lat, lng = lat2.ravel()[inside], lng2.ravel()[inside]
        flat = index.resample(values).reshape(values.shape[0], -1)[:, inside]
        counts = {name: index.resample(v[None])[0].ravel()[inside] for name, v in extra.items()}
    n_cells = lat.size
    columns: list[Column] = []
    if stat is None:
        label = "time" if layer.time_axis == "hour" else "date"
        columns.append(Column(name=label, values=np.repeat(np.array(steps, dtype=object), n_cells).tolist()))
        columns.append(Column(name="kind", values=np.repeat(np.array(kinds, dtype=object), n_cells).tolist()))
    repeat = 1 if stat is not None else len(steps)
    columns.append(Column(name="lat", values=np.tile(np.round(lat, 4), repeat).tolist()))
    columns.append(Column(name="lng", values=np.tile(np.round(lng, 4), repeat).tolist()))
    if q.cells and index is None:
        columns.append(Column(name="j", values=np.tile(jj, repeat).tolist()))
        columns.append(Column(name="i", values=np.tile(ii, repeat).tolist()))
    column.values = flat.ravel()
    columns.append(column)
    for name, v in counts.items():
        # A lat/lng mean of cells' counts is the mean count; rounded, it stays a count of days
        columns.append(Column(name=name, values=[None if x != x else round(x) for x in v.tolist()]))
    return columns
