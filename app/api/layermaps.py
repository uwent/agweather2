"""A layer's map as a request asks for it (`agdata.layers`): what `/grids`, `/tiles` and `/maps` share.

`ask` checks a request's time, statistic, degree-day setting and model settings against the layer and opens its
stores; `stamp` is the data stamp for its ETag (the stores' write times, the forecast run); `compute` reads or
computes its values over a window, in the layer's stored unit (a model output's for a model layer).

A range with `stat` becomes one map, reduced by `agdata.grids` with the points' gap rules (D45, D56), and each
cell's estimated and missing days beside it. Degree days for any setting are computed from each day's minimum and
maximum; a setting the archive keeps as a running total (`agdata.cumulative`) is read from it for `stat=sum`
when every day in the range has data, which is the same sum (to its stored 0.5 °F·d) in a fraction of the time.

A model's layer (its id is the model's) is finished per cell from its stored ingredients (`agdata.modelgrid`): one
output (`output=`, default the risk level or a crop's stage) with the model's scenario options. Maps take each
place's own settings (D66), so a biofix, planting date or maturity is refused, pointing to the point endpoints. A
seasonal product (D68) takes `season=`.

A daily variable that a newer version of its code hasn't rebuilt yet (D29: between a deploy and `rebuild --stale`)
is computed from the hours for up to MAX_STALE_DAYS days; a longer range is a 503 until the rebuild is done.
"""

import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

import numpy as np
from django.http import HttpRequest
from ninja import Field, Schema

from agdata import modelgrid, modelmaps, regions, seasonal, series
from agdata.daily import cell_timezones, days_from_hours
from agdata.grid import Window
from agdata.grids import cube_terms, degree_days, reduce
from agdata.layers import DEGREE_DAYS, LAYERS, SUSCEPTIBILITY, Layer, LayerOutput
from agdata.planting import planting_crop, planting_map
from agdata.store import CUMULATIVE, DAILY
from agmodels import seasons
from agmodels.seasons import Season
from agmodels.spec import ModelSpec
from api.errors import ApiError
from api.params import degree_day_settings
from api.runs import _option_values

MAX_STALE_DAYS = 7
HOUR = timedelta(hours=1)


class LayerQuery(Schema):
    """When and how: a layer's step or range, its statistic, and its settings."""

    date: str | None = Field(None, description="One day (YYYY-MM-DD) for a daily layer; default the last observed day")
    time: str | None = Field(
        None, description="One hour (ISO, UTC unless a zone is given) for an hourly layer; default the last observed"
    )
    start: str | None = Field(None, description="First day (or hour) of a range, inclusive")
    end: str | None = Field(None, description="Last day (or hour) of a range, inclusive; default the last observed")
    stat: Literal["sum", "mean", "min", "max"] | None = Field(
        None, description="Reduce the range to one map; without it, each step is returned"
    )
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
    season: str | None = Field(
        None,
        description="A seasonal product (`/layers` lists its seasons): the season, as 2025-26; default the current "
        "one. Its map is the count through the season's last day, or the last observed day before it",
    )


@dataclass(kw_only=True)
class LayerAsk:
    """A layer's map as asked for, checked: its steps, statistic and settings, and the stores it reads."""

    layer: Layer
    first: Any  # a date, or a datetime for an hourly layer
    last: Any
    stat: str | None
    gaps: str
    setting: Any  # degree days: the setting (`api.params.degree_day_settings`)
    cubes: tuple[str, str | None] | None  # degree days: the running totals a sum can be read from
    model: "ModelRequest | None"
    stores: series.Stores
    observed: datetime  # the archive's last observed hour
    warnings: list[str] = field(default_factory=list)

    @property
    def unit(self) -> str:
        return self.model.output.unit if self.model is not None else self.layer.unit

    @property
    def step(self) -> float:
        return self.model.output.step if self.model is not None else self.layer.step

    @property
    def label(self) -> str:
        """The map's title: the layer's name, with its setting or model output."""
        if self.model is not None:
            return f"{self.layer.name}: {self.model.output.label}"
        return self.layer.name + (f" ({self.setting.name})" if self.setting else "")

    def echo(self) -> dict[str, Any]:
        """The request as resolved, for `meta.request` and the ETag."""
        first, last = self.first, self.last
        if first == last:
            when = {"time": iso_hour(first)} if self.layer.time_axis == "hour" else {"date": first.isoformat()}
        else:
            when = {
                "start": iso_hour(first) if isinstance(first, datetime) else first.isoformat(),
                "end": iso_hour(last) if isinstance(last, datetime) else last.isoformat(),
            }
        model = self.model
        return {
            "layer": self.layer.id,
            **when,
            "stat": self.stat,
            **(model.echo if model is not None else {}),
            **({"season": model.season.name} if model is not None and model.season is not None else {}),
            "dd": self.setting.name if self.setting else None,
            "gaps": self.gaps,
        }


def ask(request: HttpRequest, layer_id: str, q: LayerQuery, units: str, now: datetime) -> LayerAsk:
    """A request for a layer's map, checked; ApiError where it doesn't apply."""
    found = LAYERS.get(layer_id)
    if found is None:
        raise ApiError("unknown_layer", f"no layer {layer_id!r}; GET /layers lists them", "layer", status=404)
    warnings: list[str] = []
    data_dir = _data_dir()
    observed = series.last_observed(data_dir, now)
    if observed is None:
        raise ApiError("no_data", "the archive has no data yet", None, status=503)
    first, last = span(found, q, observed)
    stat = q.stat
    if stat is not None and stat not in found.stats:
        offered = ", ".join(found.stats) if found.stats else "none: each day is already a running total"
        raise ApiError("invalid", f"{found.id} can't be reduced by {stat}; stats: {offered}", "stat")
    model = model_request(request, found, q, warnings) if found.source == "model" else None
    if model is None and (q.output is not None or q.planting is not None):
        param = "output" if q.output is not None else "planting"
        raise ApiError("invalid", f"{param} applies to model layers", param)
    if model is not None and model.spec.seasonal is not None:
        first, last = season_span(model, q, first, last, series.last_closed_day(observed), now.date(), warnings)
        if model.projected and (first != last or stat is not None):
            raise ApiError("invalid", f"{model.output.name} is one day's projection: give a date or season", "output")
        if model.projected and model.season is None:
            raise ApiError("invalid", f"{model.output.name} projects a season: {first} is between seasons", "output")
    elif q.season is not None:
        raise ApiError("not_applicable", f"{found.id} isn't a seasonal product", "season")
    setting = None
    if found.id == DEGREE_DAYS:
        settings_found = degree_day_settings(q.dd, units, warnings)
        if len(settings_found) > 1:
            raise ApiError("invalid", "one degree-day setting per map", "dd")
        setting = settings_found[0]
    elif q.dd is not None:
        raise ApiError("invalid", "dd applies only to the degree_days layer", "dd")
    cubes = _cubes(found, setting, stat, q.gaps, first, last)
    # Only what the layer reads: an open checks every variable it's given (~3 ms each)
    opened = [*hourly_of(found), *([found.variable] if found.variable else [])]
    if found.id == DEGREE_DAYS:
        opened += ["air_temperature_min", "air_temperature_max"]
    if cubes:
        opened += [c for c in cubes if c] + ["temperature_estimated_days", "temperature_missing_days"]
    if model is not None:
        opened += [q.name for q in model.spec.inputs] + modelgrid.read_names(found.id)
    return LayerAsk(
        layer=found,
        first=first,
        last=last,
        stat=stat,
        gaps=q.gaps,
        setting=setting,
        cubes=cubes,
        model=model,
        stores=series.Stores(opened),
        observed=observed,
        warnings=warnings,
    )


def stamp(a: LayerAsk, now: datetime) -> Any:
    """The data stamp of what the map reads (`series.last_written`), for its ETag."""
    found, model = a.layer, a.model
    first_day = a.first.date() if isinstance(a.first, datetime) else a.first
    last_day = a.last.date() if isinstance(a.last, datetime) else a.last
    daily_names = [found.variable] if found.source == "daily" and found.variable else []
    if found.id == DEGREE_DAYS:
        daily_names = ["air_temperature_min", "air_temperature_max"]
    if model is not None and found.id in modelgrid.ON_REQUEST:
        daily_names = [q.name for q in model.spec.inputs]  # computed from the days themselves
    totals = [found.variable] if found.source == "cumulative" and found.variable else []
    totals += [c for c in (a.cubes or ()) if c]
    hourly_stamped = [found.variable] if found.source == "hourly" and found.variable else []
    ingredients: list[str] = []
    if model is not None:
        in_store = {v.name for v in modelmaps.variables()}
        names = modelgrid.read_names(found.id)
        ingredients = [n for n in names if n in in_store]
        totals += [n for n in names if n not in in_store]
    stamp_from = first_day
    if model is not None and model.season is not None:
        # A season's count reads back to its start, and a projection the earlier seasons
        years = series.archive_years(_data_dir()) if model.projected else []
        stamp_from = min([model.season.first, *(date(y, 1, 1) for y in years)])
    return series.last_written(
        _data_dir(),
        stamp_from,
        last_day,
        totals=totals,
        now=now,
        daily=daily_names,
        hourly=hourly_stamped,
        ingredients=ingredients,
    )


@dataclass(kw_only=True)
class Computed:
    """A layer's map: values (steps out, y, x) in its stored unit, and how they came to be."""

    values: np.ndarray
    kinds: list[str | None]  # per step read
    extra: dict[str, np.ndarray]  # per-cell counts beside a reduced range (estimated and missing days)
    sources: tuple[str, ...] | list[str]
    run: series.Forecast
    steps: list  # the steps' labels (days or hours)
    from_cubes: bool  # degree days read from the running totals
    ms: float  # time to compute


def compute(a: LayerAsk, window: Window, now: datetime) -> Computed:
    """The layer's map over `window`."""
    started = time.perf_counter()
    data_dir = _data_dir()
    if a.model is not None:
        found = _model_compute(a.layer, a.model, a.first, a.last, window, a.stat, data_dir, now, a.stores, a.warnings)
    else:
        found = _compute(a.layer, a.first, a.last, window, a.stat, a.setting, a.gaps, a.cubes, data_dir, now, a.stores)
    values, kinds, extra, sources, run, steps, from_cubes = found
    return Computed(
        values=values,
        kinds=kinds,
        extra=extra,
        sources=sources,
        run=run,
        steps=steps,
        from_cubes=from_cubes,
        ms=(time.perf_counter() - started) * 1000,
    )


def _data_dir():
    from django.conf import settings

    return settings.DATA_DIR


# --- Parsing -------------------------------------------------------------------------------------------------------


def span(layer: Layer, q: LayerQuery, observed: datetime) -> tuple[Any, Any]:
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
            raise ApiError("out_of_order", f"start ({iso_hour(first)}) is after end ({iso_hour(last)})", "start")
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
        raise ApiError("invalid", f"{param} ({iso_hour(value)}) isn't on the hour", param)
    return value


def iso_hour(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def archive_window(data_dir, stores: series.Stores) -> Window:
    """The window the archive's stores hold (the service box as it was when they were made)."""
    for year in sorted(series.archive_years(data_dir), reverse=True):
        store = stores.get(data_dir, DAILY, year)
        if store is not None:
            return store.window
    raise ApiError("no_data", "the archive has no daily stores yet", None, status=503)


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
class ModelRequest:
    spec: ModelSpec
    output: LayerOutput
    options: dict[str, str]
    tier: str | None  # the planting tier, or None
    crop: str | None  # the crop it's for (`agdata.planting`)
    echo: dict[str, Any]
    planted: np.ndarray | None = None  # each cell's planting date (ordinals), once computed
    window: Window | None = None
    season: Season | None = None  # a seasonal product's season the map is in
    projection: seasonal.Projection | None = None  # once computed

    @property
    def projected(self) -> bool:
        return self.output.name.startswith((seasonal.PROJECTED, seasonal.CHANCE))


def model_request(request: HttpRequest, layer: Layer, query: LayerQuery, warnings: list[str]) -> ModelRequest:
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
    return ModelRequest(spec=spec, output=chosen, options=options, tier=tier, crop=crop[1] if crop else None, echo=echo)


def planting_summary(model: ModelRequest, mask: np.ndarray, warnings: list[str]) -> dict[str, Any]:
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


def _model_compute(layer, model: ModelRequest, first, last, window, stat, data_dir, now, stores, warnings):
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
    extra: dict[str, np.ndarray] = {}
    if model.projected:
        years = series.archive_years(data_dir)
        model.projection = seasonal.project(data_dir, layer.id, first, window, found, years, stores=stores, now=now)
        values = (model.projection.medians | model.projection.chances)[name][None]
        extra["projection_seasons"] = model.projection.counted.astype(float)
    else:
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
    if stat is not None:
        value, _, missing = reduce(values, stat, None)
        values, extra = value[None], {"missing_days": missing}
    return values, found.kinds, extra, found.sources, found.forecast, found.dates, False


def season_span(
    model: ModelRequest, query: LayerQuery, first: Any, last: Any, observed_day: date, today: date, warnings
) -> tuple[Any, Any]:
    """A seasonal product's days (D68): `season=` is its last day counted; no date its current season's; a date or
    range as asked, observed days only (Q16), the partial season with a warning before it's shown."""
    spec = model.spec
    if query.season is not None:
        if query.date or query.start or query.end:
            raise ApiError("conflict", "give either season, or a date or range, not both", "season")
        try:
            model.season = seasons.season_named(spec, query.season)
        except ValueError as error:
            raise ApiError("invalid", str(error), "season") from None
        day = seasonal.through(model.season, observed_day)
        if day is None:
            raise ApiError("not_yet", f"the {model.season.label} season hasn't started", "season", status=404)
        return day, day
    if not (query.date or query.start or query.end):
        model.season = seasons.current_season(spec, today)
        day = seasonal.through(model.season, observed_day)
        assert day is not None  # a season appears after it starts
        return day, day
    if last > observed_day:
        raise ApiError(
            "not_observed",
            f"{spec.id} counts observed days only; the last is {observed_day}",
            "date" if query.date else "end",
        )
    model.season = seasons.season_of(spec, last)
    if model.season is None:
        settled = seasons.current_season(spec, last)
        warnings.append(f"{last} is between seasons; season={settled.name} gives the last one's count")
    elif last < model.season.appears:
        warnings.append(
            f"the {model.season.label} season is open: its count so far, shown from {model.season.appears} on"
        )
    return first, last


def season_name(spec: ModelSpec, year: int) -> str:
    return seasons.season_starting(spec, year).name


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


def hourly_of(layer: Layer) -> list[str]:
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


# --- Computed maps, kept -------------------------------------------------------------------------------------------

# Maps computed for tiles and images, by what was asked and the data stamp: a screen of tiles is one map read
# 12–20 times, so it's computed once. A Wisconsin map is ~0.5 MB; the launch box's a few MB.
MAP_CACHE_SIZE = 24
_maps: "OrderedDict[str, Computed]" = OrderedDict()
_maps_lock = threading.Lock()


def cached(a: LayerAsk, window: Window, now: datetime, data_stamp: Any) -> Computed:
    """`compute` over `window`, kept for the next request asking the same of the same data."""
    key = json.dumps([a.echo(), data_stamp, [window.j0, window.j1, window.i0, window.i1]], default=str)
    with _maps_lock:
        found = _maps.get(key)
        if found is not None:
            _maps.move_to_end(key)
            return found
    found = compute(a, window, now)
    with _maps_lock:
        _maps[key] = found
        while len(_maps) > MAP_CACHE_SIZE:
            _maps.popitem(last=False)
    return found
