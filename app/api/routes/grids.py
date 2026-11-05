"""Maps as data (docs/api.md, "Grids"; PLAN.md Phase 5 E): the layer catalog and any layer over an area.

`/layers` lists what can be mapped (`agdata.layers`) with each layer's time axis and the range the archive and
forecast hold. `/grids/{layer}` reads one step or a range over the service box, a bounding box or a state or
county (`agdata.regions`), every `stride`-th cell or resampled to a regular lat/lng grid (`agdata.regrid`), and
answers in JSON or CSV (long form, a row per cell and step), NetCDF or GeoTIFF (`api.gridfiles`).

A range with `stat` becomes one map, reduced by `agdata.grids` with the points' gap rules (D45, D56), and each
cell's estimated and missing days beside it. Degree days for any setting are computed from each day's minimum and
maximum; a setting the archive keeps as a running total (`agdata.cumulative`) is read from it for `stat=sum`
when every day in the range has data, which is the same sum (to its stored 0.5 °F·d) in a fraction of the time.

A model's layer (its id is the model's) is finished per cell from its stored ingredients (`agdata.modelgrid`): one
output (`output=`, default the risk level or a crop's stage) with the model's scenario options. Maps take each
place's own settings (D66), so a biofix, planting date or maturity is refused, pointing to the point endpoints.

A daily variable that a newer version of its code hasn't rebuilt yet (D29: between a deploy and `rebuild --stale`)
is computed from the hours for up to MAX_STALE_DAYS days; a longer range is a 503 until the rebuild is done.
"""

import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Field, Query, Router, Schema

from agdata import modelgrid, modelmaps, regions, series
from agdata import units as agunits
from agdata.catalog import DAILY_STATISTICS
from agdata.daily import cell_timezones, days_from_hours
from agdata.grid import NDFD, Box, Window
from agdata.grids import cube_terms, degree_days, reduce
from agdata.layers import DEGREE_DAYS, LAYERS, SUSCEPTIBILITY, Layer, LayerOutput
from agdata.planting import planting_crop, planting_map
from agdata.regrid import MIN_LATLON_RES, LatLonIndex, latlon_index
from agdata.store import CUMULATIVE, DAILY
from agmodels.spec import ModelSpec
from api import clock
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
from api.errors import ApiError
from api.gridfiles import GridFile, geotiff, netcdf
from api.params import OutputQuery, degree_day_settings
from api.routes.discovery import DisplayUnits, _units
from api.runs import _option_values
from api.schemas import Meta, TableResponse, responses
from ops.status import dataset_status

router = Router(tags=["grids"])

FORMATS = ("json", "csv", "netcdf", "geotiff")
MAX_TEXT_VALUES = 2_000_000  # JSON and CSV: ~70 MB and 1.5–2.5 s to write; NetCDF and GeoTIFF beyond it
MAX_FILE_VALUES = 22_000_000  # NetCDF and GeoTIFF: a leap year of days over Wisconsin (57,820 cells)
MAX_DAYS = 366
MAX_HOURS = 31 * 24
MAX_STALE_DAYS = 7
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
    palette: str


class LayerInfo(Schema):
    id: str
    name: str
    group: Literal["weather", "running_total", "degree_days", "model"]
    time_axis: Literal["day", "hour", "day_of_year"]
    variable: str | None  # the catalog variable (`/variables`); None where the layer is computed (degree days)
    unit: str  # stored unit symbol
    units: DisplayUnits
    precision: float  # the stored step, in `unit`
    palette: str  # a color scale id, the same for layers of one kind
    stats: list[str]  # what a range can be reduced to (`stat=`); empty for running totals
    parameters: list[str]  # required beyond the time and area (`dd` for degree days)
    range: LayerRange
    description: str
    outputs: list[LayerOutputInfo] = Field(default_factory=list)  # a model layer's, the default first (`output=`)
    # a model layer's scenario options (`GET /models/{id}` describes them), and its planting tiers (`planting=`)
    options: list[str] = Field(default_factory=list)
    planting: list[str] = Field(default_factory=list)


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
            group=layer.group,
            time_axis=layer.time_axis,
            variable=layer.variable,
            unit=layer.unit,
            units=_units(layer.unit),
            precision=layer.step,
            palette=layer.palette,
            stats=list(layer.stats),
            parameters=["dd"] if layer.id == DEGREE_DAYS else [],
            range=ranges[layer.time_axis],
            description=layer.description,
            outputs=[_output_info(o) for o in layer.outputs],
            options=_map_options(layer),
            planting=["early", "mid", "late", "none"] if layer.planting else [],
        )
        for layer in LAYERS.values()
    ]
    return respond(request, Result(request={}, data=[f.model_dump() for f in found]))


def _output_info(o: LayerOutput) -> LayerOutputInfo:
    return LayerOutputInfo(
        name=o.name, label=o.label, unit=o.unit, units=_units(o.unit), precision=o.step, palette=o.palette
    )


def _map_options(layer: Layer) -> list[str]:
    """A model layer's options a map takes: the scenario's, not the place's (D66)."""
    if layer.source != "model":
        return []
    spec = modelgrid.mapped()[layer.id].SPEC
    return [o.name for o in spec.options if o.name not in modelgrid.PLACE_OPTIONS]


def _hour(when: datetime | None) -> str | None:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ") if when is not None else None


# --- /grids/{layer} ------------------------------------------------------------------------------------------------


class GridQuery(Schema):
    """When, where and how: a layer's step or range, its area, and the grid it's given on."""

    date: str | None = Field(None, description="One day (YYYY-MM-DD) for a daily layer; default the last observed day")
    time: str | None = Field(
        None, description="One hour (ISO, UTC unless a zone is given) for an hourly layer; default the last observed"
    )
    start: str | None = Field(None, description="First day (or hour) of a range, inclusive")
    end: str | None = Field(None, description="Last day (or hour) of a range, inclusive; default the last observed")
    stat: Literal["sum", "mean", "min", "max"] | None = Field(
        None, description="Reduce the range to one map; without it, each step is returned"
    )
    bbox: str | None = Field(None, description="south,west,north,east in degrees; default the whole service box")
    region: str | None = Field(
        None, description="A state (wisconsin, WI) or county (FIPS code, 55025): only its cells are returned"
    )
    stride: int = Field(1, ge=1, le=MAX_STRIDE, description="Every nth cell in each direction (native grid only)")
    grid: Literal["native", "latlon"] = Field(
        "native", description="native: NDFD's 2.5 km Lambert cells; latlon: a regular grid every `res` degrees"
    )
    res: float | None = Field(None, description=f"latlon: the step in degrees, at least {MIN_LATLON_RES}")
    method: Literal["nearest", "mean"] | None = Field(
        None,
        description="latlon: the cell under each point, or the mean of the cells within ±res/2 (default: mean "
        "from 0.05°, nearest below)",
    )
    cells: bool = Field(False, description="JSON and CSV: add each cell's j and i on the native grid")
    dd: str | None = Field(None, description="degree_days: the setting, method_base[_upper] (sine_50_86)")
    gaps: Literal["estimate", "missing"] = Field(
        "estimate", description="stat=sum and degree days: bridge gaps up to 7 days with a flagged estimate, or not"
    )
    output: str | None = Field(
        None, description="A model layer's output (`/layers` lists them); default its risk level, or a crop's stage"
    )
    planting: Literal["early", "mid", "late", "none"] | None = Field(
        None,
        description="A model layer with a crop: each place's typical planting date at this tier (default mid), or "
        "none for the model's default dates and no crop-stage gating",
    )


@router.get("/grids/{layer}", response=responses(TableResponse), summary="A layer over an area")
def grid(request: HttpRequest, layer: str, query: Query[GridQuery], output: Query[OutputQuery]) -> HttpResponse:
    """A layer (`/layers`) on one day or hour, each step of a range, or a range reduced by `stat`, over the service
    box, a `bbox` or a `region`. JSON and CSV are long form, a row per cell (and step): `date` or `time`, `kind`,
    `lat`, `lng` (the cell's center, or the lat/lng point), `j` and `i` with `cells=true`, the layer's value under
    its id, and with `stat` each cell's `estimated_days` and `missing_days`; up to 2 million values. NetCDF and
    GeoTIFF keep the native Lambert grid with its projection (or the lat/lng grid), a band per step."""
    started = time.perf_counter()
    found = LAYERS.get(layer)
    if found is None:
        raise ApiError("unknown_layer", f"no layer {layer!r}; GET /layers lists them", "layer", status=404)
    fmt = requested_format(request, FORMATS)
    warnings: list[str] = []
    now = clock.now()
    data_dir = settings.DATA_DIR
    observed = series.last_observed(data_dir, now)
    if observed is None:
        raise ApiError("no_data", "the archive has no data yet", None, status=503)
    first, last = _span(found, query, observed)
    stat = query.stat
    if stat is not None and stat not in found.stats:
        offered = ", ".join(found.stats) if found.stats else "none: each day is already a running total"
        raise ApiError("invalid", f"{found.id} can't be reduced by {stat}; stats: {offered}", "stat")
    model = _model_request(request, found, query, warnings) if found.source == "model" else None
    if model is None and (query.output is not None or query.planting is not None):
        param = "output" if query.output is not None else "planting"
        raise ApiError("invalid", f"{param} applies to model layers", param)
    setting = None
    if found.id == DEGREE_DAYS:
        settings_found = degree_day_settings(query.dd, output.units, warnings)
        if len(settings_found) > 1:
            raise ApiError("invalid", "one degree-day setting per map", "dd")
        setting = settings_found[0]
    elif query.dd is not None:
        raise ApiError("invalid", "dd applies only to the degree_days layer", "dd")

    cubes = _cubes(found, setting, stat, query.gaps, first, last)
    # Only what the layer reads: an open checks every variable it's given (~3 ms each)
    opened = [*_hourly_of(found), *([found.variable] if found.variable else [])]
    if found.id == DEGREE_DAYS:
        opened += ["air_temperature_min", "air_temperature_max"]
    if cubes:
        opened += [c for c in cubes if c] + ["temperature_estimated_days", "temperature_missing_days"]
    if model is not None:
        opened += [q.name for q in model.spec.inputs] + modelgrid.read_names(found.id)
    stores = series.Stores(opened)
    archive = _archive_window(data_dir, stores)
    window, mask, area = _area(query, archive)
    grid_spec = _grid_spec(query, window, mask)
    steps_out = 1 if stat is not None else _steps(found, first, last)
    cells_out = grid_spec["cells"]
    _check_size(fmt, steps_out, cells_out, grid_spec["full"])

    computed: dict[str, Any] = {
        "layer": found.id,
        **(
            {"time": _iso_hour(first)}
            if found.time_axis == "hour" and first == last
            else {"date": first.isoformat()}
            if first == last
            else {
                "start": _iso_hour(first) if isinstance(first, datetime) else first.isoformat(),
                "end": _iso_hour(last) if isinstance(last, datetime) else last.isoformat(),
            }
        ),
        "stat": stat,
        **(model.echo if model is not None else {}),
        "dd": setting.name if setting else None,
        "gaps": query.gaps,
        **area,
        **grid_spec["echo"],
        "format": fmt,
    }
    first_day = first.date() if isinstance(first, datetime) else first
    last_day = last.date() if isinstance(last, datetime) else last
    daily_names = [found.variable] if found.source == "daily" and found.variable else []
    if found.id == DEGREE_DAYS:
        daily_names = ["air_temperature_min", "air_temperature_max"]
    if model is not None and found.id in modelgrid.ON_REQUEST:
        daily_names = [q.name for q in model.spec.inputs]  # computed from the days themselves
    totals = [found.variable] if found.source == "cumulative" and found.variable else []
    totals += [c for c in (cubes or ()) if c]
    hourly_stamped = [found.variable] if found.source == "hourly" and found.variable else []
    ingredients: list[str] = []
    if model is not None:
        in_store = {v.name for v in modelmaps.variables()}
        names = modelgrid.read_names(found.id)
        ingredients = [n for n in names if n in in_store]
        totals += [n for n in names if n not in in_store]
    stamp = series.last_written(
        data_dir,
        first_day,
        last_day,
        totals=totals,
        now=now,
        daily=daily_names,
        hourly=hourly_stamped,
        ingredients=ingredients,
    )
    etag = etag_for(request, computed, stamp)
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged

    read_started = time.perf_counter()
    if model is not None:
        values, kinds, extra, sources, run, step_labels, from_cubes = _model_compute(
            found, model, first, last, window, stat, data_dir, now, stores, warnings
        )
    else:
        values, kinds, extra, sources, run, step_labels, from_cubes = _compute(
            found, first, last, window, stat, setting, query.gaps, cubes, data_dir, now, stores
        )
    compute_ms = (time.perf_counter() - read_started) * 1000
    values = np.where(mask[None], values, np.nan)
    extra = {name: np.where(mask, v, np.nan) for name, v in extra.items()}
    if query.stride > 1:
        values = values[:, :: query.stride, :: query.stride]
        extra = {name: v[:: query.stride, :: query.stride] for name, v in extra.items()}

    missing_steps = sum(k is None for k in kinds)
    if missing_steps:
        warnings.append(f"{missing_steps} of {len(kinds)} {found.time_axis}s have no data")
    if run.reason == "stale" and any(k is None for k in kinds):
        warnings.append("the forecast run is out of date, so the map ends with the archive")
    summary: dict[str, Any] = {
        "steps": len(kinds),
        "kinds": {kind or "missing": kinds.count(kind) for kind in dict.fromkeys(kinds)},
        "cells": cells_out,
        **({"stat": stat} if stat else {}),
        "corrections": list(series.in_box_corrections(kinds, run, _hourly_of(found))),
    }
    if cubes and from_cubes:
        summary["from_running_totals"] = [c for c in cubes if c]

    if model is not None:
        summary["model"] = {"id": found.id, "version": model.spec.version, "output": model.output.name}
        if model.planted is not None:
            summary["planting"] = _planting_summary(model, mask, warnings)
    unit, step = (model.output.unit, model.output.step) if model is not None else (found.unit, found.step)
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
        long_name = found.name + (f" ({setting.name})" if setting else "")
        if model is not None:
            long_name = f"{found.name}: {model.output.label}"
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
            return netcdf(file) if kind == "netcdf" else geotiff(file)

        result.render = render
    else:
        result.columns = _long_form(found, column, values, kinds, extra, step_labels, stat, window, mask, query, index)
    result.timings["read_and_shape"] = (time.perf_counter() - started) * 1000 - compute_ms
    return respond(request, result)


# --- Parsing -------------------------------------------------------------------------------------------------------


def _span(layer: Layer, q: GridQuery, observed: datetime) -> tuple[Any, Any]:
    if layer.time_axis == "hour":
        if q.date is not None:
            raise ApiError("invalid", f"{layer.id} is hourly: give time, or start and end", "date")
        if q.time is not None and (q.start or q.end):
            raise ApiError("conflict", "give either time, or start and end, not both", "time")
        if q.time is not None:
            hour = _parse_hour(q.time, "time")
            return hour, hour
        last = _parse_hour(q.end, "end") if q.end else observed
        first = _parse_hour(q.start, "start") if q.start else last
        if first > last:
            raise ApiError("out_of_order", f"start ({_iso_hour(first)}) is after end ({_iso_hour(last)})", "start")
        return first, last
    if q.time is not None:
        raise ApiError("invalid", f"{layer.id} is daily: give date, or start and end", "time")
    if q.date is not None and (q.start or q.end):
        raise ApiError("conflict", "give either date, or start and end, not both", "date")
    if q.date is not None:
        day = _parse_date(q.date, "date")
        return day, day
    last = _parse_date(q.end, "end") if q.end else series.last_closed_day(observed)
    if q.start is None:
        return (last, last) if q.end is None else (date(last.year, 1, 1), last)
    first = _parse_date(q.start, "start")
    if first > last:
        raise ApiError("out_of_order", f"start ({first}) is after end ({last})", "start")
    return first, last


def _parse_date(text: str, param: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ApiError("invalid", f"{param} ({text!r}) isn't a date (YYYY-MM-DD)", param) from None


def _parse_hour(text: str, param: str) -> datetime:
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ApiError("invalid", f"{param} ({text!r}) isn't an ISO time", param) from None
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if value.minute or value.second or value.microsecond:
        raise ApiError("invalid", f"{param} ({_iso_hour(value)}) isn't on the hour", param)
    return value


def _iso_hour(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def _steps(layer: Layer, first, last) -> int:
    if layer.time_axis == "hour":
        n = (last - first) // HOUR + 1
        if n > MAX_HOURS:
            raise ApiError("too_large", f"{n} hours; up to {MAX_HOURS} a request", "start")
        return n
    n = (last - first).days + 1
    if n > MAX_DAYS:
        raise ApiError("too_large", f"{n} days; up to {MAX_DAYS} a request", "start")
    return n


def _archive_window(data_dir, stores: series.Stores) -> Window:
    """The window the archive's stores hold (the service box as it was when they were made)."""
    for year in sorted(series.archive_years(data_dir), reverse=True):
        store = stores.get(data_dir, DAILY, year)
        if store is not None:
            return store.window
    raise ApiError("no_data", "the archive has no daily stores yet", None, status=503)


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
            raise ApiError("outside_box", f"the bbox has no cells in the service box ({settings.SERVICE_BOX})", "bbox")
    if q.region is not None:
        region = regions.find(q.region)
        if region is None:
            raise ApiError(
                "unknown_region",
                f"{q.region!r} isn't a state (wisconsin, WI) or a county's FIPS code (55025)",
                "region",
            )
        mask &= regions.mask(region, archive)
        echo["region"] = {"id": region.id, "name": region.name}
        if not mask.any():
            raise ApiError("outside_box", f"{region.name} has no cells in the service box", "region")
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
        raise ApiError("invalid", f"bbox ({text!r}) isn't south,west,north,east in degrees", "bbox") from None


def _grid_spec(q: GridQuery, window: Window, mask: np.ndarray) -> dict[str, Any]:
    """The output grid: how many cells each step has (rows in JSON and CSV, `cells`; the file's, `full`), and for
    a lat/lng grid its index."""
    if q.grid == "native":
        if q.res is not None or q.method is not None:
            raise ApiError("invalid", "res and method apply to grid=latlon", "res" if q.res is not None else "method")
        kept = mask[:: q.stride, :: q.stride]
        return {
            "cells": int(kept.sum()),
            "full": kept.size,
            "index": None,
            "echo": {"grid": "native", "stride": q.stride, "window": [window.j0, window.j1, window.i0, window.i1]},
        }
    if q.stride != 1:
        raise ApiError("invalid", "stride applies to the native grid; use res for a coarser lat/lng grid", "stride")
    if q.res is None:
        raise ApiError("missing", f"grid=latlon needs res (degrees, at least {MIN_LATLON_RES})", "res")
    if not MIN_LATLON_RES <= q.res <= 5:
        raise ApiError("out_of_range", f"res {q.res} isn't between {MIN_LATLON_RES} and 5 degrees", "res")
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
                f"{steps * cells:,} values ({steps} steps × {cells:,} cells); JSON and CSV take up to "
                f"{MAX_TEXT_VALUES:,}: ask for format=netcdf or geotiff, a stat, a smaller area, or a stride",
                "format",
            )
    elif steps * full > MAX_FILE_VALUES:
        raise ApiError(
            "too_large",
            f"{steps * full:,} values ({steps} steps × {full:,} cells); files take up to {MAX_FILE_VALUES:,}: "
            "a smaller area, a stride or fewer steps",
            "start",
        )


def _cubes(layer: Layer, setting, stat, gaps: str, first, last) -> tuple[str, str | None] | None:
    """The running totals a degree-day sum can be read from, where it can."""
    if layer.id != DEGREE_DAYS or setting is None or stat != "sum" or gaps != "estimate":
        return None
    if first.year != last.year:
        return None
    return cube_terms(setting.method, setting.base_f, setting.upper_f)


# --- Model layers --------------------------------------------------------------------------------------------------

# A user's own dates and settings apply at points, not on maps (D66)
_POINT_ONLY = ("biofix", "planting_date")


@dataclass(kw_only=True)
class _ModelRequest:
    spec: ModelSpec
    output: LayerOutput
    options: dict[str, str]
    tier: str | None  # the planting tier, or None
    crop: str | None  # the crop it's for (`agdata.planting`)
    echo: dict[str, Any]
    planted: np.ndarray | None = None  # each cell's planting date (ordinals), once computed
    window: Window | None = None


def _model_request(request: HttpRequest, layer: Layer, query: GridQuery, warnings: list[str]) -> _ModelRequest:
    """A model layer's output, options and planting tier from the request; a point's own settings are refused
    (D66)."""
    output = query.output
    spec = modelgrid.mapped()[layer.id].SPEC
    crop = modelgrid.tiered(spec.id)
    if query.planting is not None and crop is None:
        later = planting_crop(spec)
        message = f"{spec.id} has no crop to plant"
        if later is not None:
            message = f"{later[0]} isn't on maps yet, so {spec.id}'s map takes no planting tier"
        raise ApiError("not_applicable", message, "planting")
    tier = None if crop is None or query.planting == "none" else (query.planting or "mid")
    if tier is None and spec.id in modelmaps.TIER_MODELS:
        raise ApiError("invalid", f"{spec.id} is mapped per planting tier: early, mid or late", "planting")
    pointed = f"maps use each place's own settings (D66); for yours at a point, GET /api/v2/models/{spec.id}/run"
    for name in (*_POINT_ONLY, *modelgrid.PLACE_OPTIONS):
        if request.GET.get(name):
            raise ApiError("not_applicable", f"{name} doesn't apply to a map: {pointed}", name)
    chosen = layer.outputs[0] if output is None else next((o for o in layer.outputs if o.name == output), None)
    if chosen is None:
        names = ", ".join(o.name for o in layer.outputs)
        raise ApiError("invalid", f"{layer.id} has no output {output!r}; outputs: {names}", "output")
    options = {}
    for o in spec.options:
        if o.name in modelgrid.PLACE_OPTIONS:
            continue
        if request.GET.get(o.name) == "all":
            raise ApiError("invalid", f"one {o.name} per map; /models/{spec.id}/run runs them all at a point", o.name)
        options[o.name] = _option_values(o, request.GET.get(o.name), warnings)[0]
    if chosen.name == SUSCEPTIBILITY and tier is None:
        raise ApiError("invalid", "susceptibility needs a planting tier (early, mid or late)", "planting")
    echo = {"model": {"id": spec.id, "version": spec.version}, "output": chosen.name, "options": options}
    if crop is not None:
        echo["planting"] = tier or "none"
    return _ModelRequest(
        spec=spec, output=chosen, options=options, tier=tier, crop=crop[1] if crop else None, echo=echo
    )


def _planting_summary(model: _ModelRequest, mask: np.ndarray, warnings: list[str]) -> dict[str, Any]:
    """The tier's planting dates over the cells asked for, and how many have none (the model's defaults)."""
    assert model.planted is not None
    land = mask & (regions.cell_counties(model.window) > 0)  # open water is in no county, so has no crop
    dates = model.planted[land]
    known = dates[np.isfinite(dates)]
    without = int(dates.size - known.size)
    if not known.size:
        warnings.append(f"no typical {model.crop} planting dates here, so the model's default dates")
    elif without:
        then = "take the model's default dates"
        if model.spec.id in modelmaps.TIER_MODELS:
            then = "have no stages"
        elif model.spec.susceptible is not None:
            then = "aren't gated by the crop's stages"
        warnings.append(f"{without:,} cells have no typical {model.crop} planting date, so {then}")
    span = [date.fromordinal(int(v)).isoformat() for v in (known.min(), known.max())] if known.size else None
    return {"crop": model.crop, "tier": model.tier, "dates": span, "cells_without": without}


def _model_compute(layer, model: _ModelRequest, first, last, window, stat, data_dir, now, stores, warnings):
    """A model layer's output over days first..last, as `_compute` returns a layer's."""
    found = modelgrid.model_map(
        data_dir, layer.id, first, last, window, model.options, tier=model.tier, now=now, stores=stores
    )
    if model.tier is not None and model.crop is not None:
        model.planted = planting_map(model.crop, model.tier, window, season=first.year)
        model.window = window
    if found.stale:
        raise ApiError(
            "stale",
            f"{layer.id}'s ingredients are being rebuilt after an update; try again in a few minutes",
            None,
            status=503,
        )
    name = model.output.name
    values = found.level if name == "risk_level" else found.risk if name == "risk_value" else found.outputs[name]
    assert values is not None
    if found.in_region is not None and not found.in_region.any():
        warnings.append(f"{layer.id} is valid only in {', '.join(model.spec.region)}: no cells here")
    if found.in_season is not None and not any(found.in_season):
        first_md, last_md = model.spec.season or ("", "")
        warnings.append(f"out of season ({first_md} to {last_md})")
    started = [b is not None and d >= b for d, b in zip(found.dates, found.biofix, strict=True)]
    if model.spec.accumulations and not any(started):
        warnings.append(f"the season starts at the biofix, {found.biofix[-1]}: nothing accumulated yet")
    extra: dict[str, np.ndarray] = {}
    if stat is not None:
        value, _, missing = reduce(values, stat, None)
        values, extra = value[None], {"missing_days": missing}
    return values, found.kinds, extra, found.sources, found.forecast, found.dates, False


# --- Reading and computing -----------------------------------------------------------------------------------------


def _compute(layer, first, last, window, stat, setting, gaps, cubes, data_dir, now, stores):
    """(values (steps out, y, x) in the layer's stored unit, kinds per step read, extra per-cell counts, sources,
    the forecast run, the steps' labels, whether the running totals were read)."""
    extra: dict[str, np.ndarray] = {}
    if layer.source == "hourly":
        read = series.grid_hours(data_dir, layer.variable, first, last, window, now, stores)
    elif layer.source in ("daily", "cumulative"):
        layout = DAILY if layer.source == "daily" else CUMULATIVE
        read = series.grid_days(data_dir, layout, layer.variable, first, last, window, now, stores)
        _fresh(read, layer, layout, window, data_dir, stores)
    else:
        return _degree_days(first, last, window, stat, setting, gaps, cubes, data_dir, now, stores)
    values = read.values
    if stat is not None:
        value, estimated, missing = reduce(values, stat, layer.variable, gaps)
        values = value[None]
        extra = {"estimated_days": estimated, "missing_days": missing}
        if layer.time_axis == "hour":
            extra = {"missing_hours": missing}
    return values, read.kinds, extra, read.sources, read.forecast, read.steps, False


def _degree_days(first, last, window, stat, setting, gaps, cubes, data_dir, now, stores):
    lo = series.grid_days(data_dir, DAILY, "air_temperature_min", first, last, window, now, stores, read=not cubes)
    if cubes and all(k is not None for k in lo.kinds):
        cube, minus = cubes
        names = [n for n in (cube, minus) if n]
        total = np.zeros(window.shape)
        for name, sign in zip(names, (1, -1), strict=False):
            total += sign * _cube_change(data_dir, name, first, last, window, now, stores)
        if not np.isnan(total).any():
            estimated = _cube_change(data_dir, "temperature_estimated_days", first, last, window, now, stores)
            missing = _cube_change(data_dir, "temperature_missing_days", first, last, window, now, stores)
            extra = {"estimated_days": estimated, "missing_days": missing}
            return total[None], lo.kinds, extra, lo.sources, lo.forecast, lo.steps, True
    if cubes:  # a day without data in the range: the sum of the days there are, as the points add them
        lo = series.grid_days(data_dir, DAILY, "air_temperature_min", first, last, window, now, stores)
    hi = series.grid_days(data_dir, DAILY, "air_temperature_max", first, last, window, now, stores)
    _fresh(lo, LAYERS["air_temperature_min"], DAILY, window, data_dir, stores)
    _fresh(hi, LAYERS["air_temperature_max"], DAILY, window, data_dir, stores)
    dd, estimated, usable = degree_days(lo.values, hi.values, setting.method, setting.base_f, setting.upper_f, gaps)
    if stat is None:
        return dd, lo.kinds, {}, lo.sources, lo.forecast, lo.steps, False
    if stat == "sum":  # unusable days add nothing; a cell with none usable is missing
        value = np.where(usable.any(axis=0), np.where(usable, dd, 0.0).sum(axis=0, dtype=np.float64), np.nan)
    else:
        value, _, _ = reduce(dd, stat, None)
    extra = {"estimated_days": estimated.sum(axis=0), "missing_days": (~usable).sum(axis=0)}
    return value[None], lo.kinds, extra, lo.sources, lo.forecast, lo.steps, False


def _cube_change(data_dir, name, first: date, last: date, window, now, stores) -> np.ndarray:
    """A running total's change over first..last: its value on `last` less the day before `first` (zero on Jan 1)."""
    end = series.grid_days(data_dir, CUMULATIVE, name, last, last, window, now, stores).values[0]
    if first.month == 1 and first.day == 1:
        return end.astype(np.float64)
    before = first - timedelta(days=1)
    start = series.grid_days(data_dir, CUMULATIVE, name, before, before, window, now, stores).values[0]
    return end.astype(np.float64) - start


def _fresh(read: series.GridSteps, layer: Layer, layout, window: Window, data_dir, stores: series.Stores) -> None:
    """Days of a stale variable (D29) recomputed from the hours, in place; too many is a 503 until the rebuild."""
    stale = np.flatnonzero(read.stale)
    if not stale.size:
        return
    if layout is not DAILY or stale.size > MAX_STALE_DAYS:
        raise ApiError(
            "stale",
            f"{layer.id} is being rebuilt after an update ({stale.size} days here); try again in a few minutes, "
            f"or ask for up to {MAX_STALE_DAYS} days",
            None,
            status=503,
        )
    for k in stale.tolist():
        day: date = read.steps[k]
        path = data_dir if k < read.run_from else read.forecast.path
        assert path is not None and layer.variable is not None
        store = stores.get(path, DAILY, day.year)
        assert store is not None
        zones, index = cell_timezones(store)
        y0, x0 = store.window.local(window.j0, window.i0)
        local = index[y0 : y0 + window.shape[0], x0 : x0 + window.shape[1]]
        read.values[k] = days_from_hours(path, window, day, day, zones, local)[layer.variable][0]


# A running total's hourly variables: degree days from temperature; precipitation and ET0 from their own hours
_TOTALS_FROM = {"precipitation": ["precipitation"], "et0": ["et0"]}


def _hourly_of(layer: Layer) -> list[str]:
    """The hourly variables a layer is made from, for the corrections it lists."""
    if layer.source == "model":
        return series.hourly_needed([q.name for q in modelgrid.mapped()[layer.id].SPEC.inputs])
    if layer.variable is None or layer.id == DEGREE_DAYS or layer.variable.startswith("dd_"):
        return ["air_temperature"]
    if layer.source == "hourly":
        return [layer.variable]
    if layer.source == "cumulative":
        return _TOTALS_FROM.get(layer.variable, [])
    return series.hourly_needed([layer.variable])


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


def _long_form(layer, column, values, kinds, extra, steps, stat, window, mask, q, index) -> list[Column]:
    """A row per cell (or lat/lng point) and step, cells south to north then west to east, steps in order."""
    if index is None:
        kept = mask[:: q.stride, :: q.stride].ravel()
        jj, ii = np.mgrid[window.j0 : window.j1 : q.stride, window.i0 : window.i1 : q.stride]
        jj, ii = jj.ravel()[kept], ii.ravel()[kept]
        lat, lng = NDFD.latlon(jj, ii)
        flat = values.reshape(values.shape[0], -1)[:, kept]
        counts = {name: v.ravel()[kept] for name, v in extra.items()}
    else:
        inside = _points_inside(index, mask)
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
