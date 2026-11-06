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
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

import numpy as np
from django.http import HttpRequest
from ninja import Schema

from agdata import modelgrid, modelmaps, palettes, regions, seasonal, series
from agdata import units as agunits
from agdata.daily import cell_timezones, days_from_hours
from agdata.grid import Window
from agdata.grids import cube_terms, degree_days, reduce
from agdata.layers import DEGREE_DAYS, LAYERS, SUSCEPTIBILITY, Layer, LayerOutput
from agdata.planting import planting_crop, planting_map
from agdata.store import CUMULATIVE, DAILY
from agmodels import seasons
from agmodels.seasons import Season
from agmodels.spec import ModelSpec
from api.errors import ApiError, day_text, hour_text
from api.maptitles import layer_title
from api.params import degree_day_settings, parse_hour, resolve_biofix
from api.runs import option_values

NO_DATA = "The archive has no weather data yet. Please try again later."
MAX_STALE_DAYS = 7
MAX_DAYS = 366  # a map's range of days, returned or reduced by `stat`
MAX_HOURS = 31 * 24
HOUR = timedelta(hours=1)


class LayerQuery(Schema):
    """When and how: a layer's step or range, its statistic, and its settings."""

    date: str | None = None
    time: str | None = None
    start: str | None = None
    end: str | None = None
    stat: Literal["sum", "mean", "min", "max"] | None = None
    dd: str | None = None
    gaps: Literal["estimate", "missing"] = "estimate"
    output: str | None = None
    planting: Literal["early", "mid", "late", "none"] | None = None
    season: str | None = None
    biofix: str | None = None  # degree days only: the start of a sum (a date, or MM-DD)


@dataclass(frozen=True, kw_only=True)
class ScaleAsked:
    """`scale=` as a request gives it: `default`, `auto`, or a range whose ends (None: from the data) are in the
    stored unit."""

    mode: Literal["default", "auto", "range"]
    low: float | None = None
    high: float | None = None
    text: str = ""  # as sent, for the ETag


def parse_scale(text: str | None, stored: str, shown: str) -> ScaleAsked | None:
    """`scale=default`, `auto`, `low,high`, `low,` or `,high` (in `shown`, the request's unit for the map) → the
    stored unit; None when not given."""
    if text is None or not text.strip():
        return None
    given = text.strip().lower()
    if given in ("default", "auto"):
        return ScaleAsked(mode=given, text=given)  # type: ignore[arg-type]
    parts = given.split(",")
    hint = (
        "Give scale=default, scale=auto, or the colors' range as low,high, such as scale=40,90 (one end may be blank)."
    )
    if len(parts) != 2:
        raise ApiError("invalid", f"We can't read scale={text}. {hint}", "scale")
    try:
        ends = [None if not part.strip() else float(part) for part in parts]
    except ValueError:
        raise ApiError("invalid", f"We can't read scale={text}. {hint}", "scale") from None
    if ends[0] is None and ends[1] is None:
        raise ApiError("invalid", f"scale needs at least one end. {hint}", "scale")
    if ends[0] is not None and ends[1] is not None and ends[0] >= ends[1]:
        raise ApiError(
            "out_of_order", f"The scale's low end ({parts[0]}) must be below its high end ({parts[1]}).", "scale"
        )
    low, high = (None if e is None else float(agunits.convert(np.float64(e), shown, stored)) for e in ends)
    return ScaleAsked(mode="range", low=low, high=high, text=given)


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
    units: str = "us"  # the request's system, for a title's degree-day thresholds
    scale_asked: "ScaleAsked | None" = None  # `scale=`, in the stored unit (`parse_scale`)
    palette_asked: "palettes.Palette | None" = None  # `palette=` (`_palette_asked`)

    @property
    def unit(self) -> str:
        return self.model.output.unit if self.model is not None else self.layer.unit

    @property
    def step(self) -> float:
        return self.model.output.step if self.model is not None else self.layer.step

    @property
    def scale(self) -> palettes.Scale:
        """The map's palette (`palette=` if asked, else its use's) and its fixed domain (None: from the map's values,
        `auto_domain`)."""
        if self.model is not None:
            found = palettes.scale_for(self.model.output.use, "day", running=True)
        else:
            running = self.layer.source == "cumulative" or self.stat is not None
            found = palettes.scale_for(self.layer.use, self.layer.time_axis, running)
        return found if self.palette_asked is None else replace(found, palette=self.palette_asked)

    @property
    def categories(self) -> list[str] | None:
        """A categorical map's level names, in order."""
        if self.model is None:
            return None
        name = self.model.output.name
        if name in ("risk_level", f"{seasonal.PROJECTED}risk_level") and self.model.spec.risk is not None:
            return list(self.model.spec.risk.levels)
        if name == SUSCEPTIBILITY:
            return ["Not susceptible", "Near susceptible stages", "Susceptible"]
        return None

    def domain(self, values: np.ndarray) -> tuple[float, float]:
        """What the palette's ends stand for, in the stored unit, from `values` (the whole map's, so every tile of it
        colors alike) where the request or the map's use leaves it open: `scale=` as asked (`auto` from the data, an
        end left blank from the data), else the use's default domain, else the data's."""
        found = self.scale
        asked = self.scale_asked
        if found.palette.kind == "categorical" or ((asked is None or asked.mode == "default") and found.domain):
            return found.domain  # type: ignore[return-value]
        auto = palettes.auto_domain(values, centered=found.centered)
        if asked is None or asked.mode != "range":
            return auto
        lo = asked.low if asked.low is not None else auto[0]
        hi = asked.high if asked.high is not None else auto[1]
        if lo >= hi:  # an end from the data on the wrong side of the one given: keep the data's span
            span = auto[1] - auto[0] or 1.0
            lo, hi = (lo, lo + span) if asked.low is not None else (hi - span, hi)
        return (lo, hi)

    @property
    def label(self) -> str:
        """The map's title as the public reads it (`api.maptitles`): "Air temperature, daily maximum"."""
        from api import maptitles

        return maptitles.title(self, self.units)

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
            **({"scale": self.scale_asked.text} if self.scale_asked is not None else {}),
            **({"palette": self.palette_asked.id} if self.palette_asked is not None else {}),
        }


def ask(request: HttpRequest, layer_id: str, q: LayerQuery, units: str, now: datetime) -> LayerAsk:
    """A request for a layer's map, checked; ApiError where it doesn't apply."""
    found = LAYERS.get(layer_id)
    if found is None:
        raise ApiError(
            "unknown_layer",
            f"We don't have a map layer named {layer_id!r}. GET /api/v2/layers lists every layer.",
            "layer",
            status=404,
        )
    warnings: list[str] = []
    data_dir = _data_dir()
    observed = series.last_observed(data_dir, now)
    if observed is None:
        raise ApiError("no_data", NO_DATA, None, status=503)
    first, last = span(found, q, observed)
    stat = q.stat or ("sum" if q.biofix is not None else None)  # a biofix starts a total
    if stat is not None and stat not in found.stats:
        offered = (
            f"stat={' or '.join(found.stats)}"
            if found.stats
            else "no stat, because each day is already a running total; give one date"
        )
        raise ApiError(
            "invalid", f"{layer_title(found)} can't be combined over days by stat={stat}. It takes {offered}.", "stat"
        )
    model = model_request(request, found, q, warnings) if found.source == "model" else None
    if model is None and (q.output is not None or q.planting is not None):
        param = "output" if q.output is not None else "planting"
        raise ApiError(
            "invalid",
            f"{param} applies only to a model's map, and {layer_title(found)} isn't one. Leave out {param}.",
            param,
        )
    if model is not None and model.spec.seasonal is not None:
        first, last = season_span(model, q, first, last, series.last_closed_day(observed), now.date(), warnings)
        if model.projected and (first != last or stat is not None):
            raise ApiError(
                "invalid",
                f"{model.output.label} is a projection for one day. Give a date or a season, without stat.",
                "output",
            )
        if model.projected and model.season is None:
            raise ApiError(
                "invalid",
                f"{model.output.label} projects a season, and {day_text(first)} is between seasons. "
                "Give a date within one.",
                "output",
            )
    elif q.season is not None:
        raise ApiError(
            "not_applicable",
            f"{layer_title(found)} isn't counted by season, so it takes no season. Give a date instead.",
            "season",
        )
    setting = None
    if found.id == DEGREE_DAYS:
        settings_found = degree_day_settings(q.dd, units, warnings)
        if len(settings_found) > 1:
            raise ApiError(
                "invalid",
                "A map shows one degree-day setting. Give a single dd value, or one request per setting.",
                "dd",
            )
        setting = settings_found[0]
    elif q.dd is not None:
        raise ApiError(
            "invalid", "dd applies only to the degree_days layer. Leave it out, or ask for /grids/degree_days.", "dd"
        )
    cubes = _cubes(found, setting, stat, q.gaps, first, last)
    # Only what the layer reads: an open checks every variable it's given (~3 ms each)
    opened = [*hourly_of(found), *([found.variable] if found.variable else [])]
    if found.id == DEGREE_DAYS:
        opened += ["air_temperature_min", "air_temperature_max"]
    if cubes:
        opened += [c for c in cubes if c] + ["temperature_estimated_days", "temperature_missing_days"]
    if model is not None:
        opened += [q.name for q in model.spec.inputs] + modelgrid.read_names(found.id)
    a = LayerAsk(
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
        units=units,
    )
    a.scale_asked = _scale_asked(request, a)
    a.palette_asked = _palette_asked(request, a)
    return a


def _palette_asked(request: HttpRequest, a: "LayerAsk") -> palettes.Palette | None:
    """`palette=` (only the endpoints that color a map declare it): any of `/palettes`, reversed with `_r`. A map
    with a color per level takes a categorical palette with as many levels; any other map, any other palette."""
    text = (request.GET.get("palette") or "").strip()
    if not text:
        return None
    try:
        chosen = palettes.palette(text)
    except KeyError:
        raise ApiError(
            "unknown_palette",
            f"We don't have a palette named {text!r}. GET /api/v2/palettes lists them; add _r to any name to "
            "reverse it.",
            "palette",
        ) from None
    default = a.scale.palette
    if default.kind == "categorical":
        if chosen.kind != "categorical" or len(chosen.colors) != len(default.colors):
            raise ApiError(
                "not_applicable",
                f"{a.label} has a color for each of its {len(default.colors)} levels, so it needs a categorical "
                f"palette with {len(default.colors)} colors, such as {default.id}.",
                "palette",
            )
    elif chosen.kind == "categorical":
        raise ApiError(
            "not_applicable",
            f"{text} has a color for each level of a category, and {a.label} is a range of values. Choose a "
            "sequential, diverging or cyclic palette from GET /api/v2/palettes.",
            "palette",
        )
    return chosen


def _scale_asked(request: HttpRequest, a: "LayerAsk") -> ScaleAsked | None:
    """`scale=` (only the endpoints that color a map declare it), in the stored unit."""
    text = request.GET.get("scale")
    if not text:
        return None
    if a.scale.palette.kind == "categorical":
        raise ApiError(
            "not_applicable",
            f"{a.label} has a color for each level, so it takes no scale. Leave out scale.",
            "scale",
        )
    from api.envelope import Column, output_units, shown_unit

    variable = a.layer.variable or a.layer.id if a.model is None else a.model.output.name
    column = Column(name=a.layer.id, values=[], unit=a.unit, step=a.step, variable=variable)
    system, overrides = output_units(request)
    return parse_scale(text, a.unit, shown_unit(column, system, overrides))


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
    """The layer's first and last step as asked (defaults: the latest), at most MAX_DAYS or MAX_HOURS apart, whether
    each step is returned or the range is reduced by `stat`: a reduced range reads every step too."""
    first, last = _span(layer, q, observed)
    if layer.time_axis == "hour":
        n, limit, unit = (last - first) // HOUR + 1, MAX_HOURS, "hours"
    else:
        n, limit, unit = (last - first).days + 1, MAX_DAYS, "days"
    if n > limit:
        raise ApiError(
            "too_large", f"The range is {n} {unit} long; a map covers up to {limit}. Choose a shorter range.", "start"
        )
    return first, last


def _span(layer: Layer, q: LayerQuery, observed: datetime) -> tuple[Any, Any]:
    if layer.time_axis == "hour":
        if q.date is not None:
            raise ApiError(
                "invalid",
                f"{layer_title(layer)} is hourly, so it takes a time rather than a date. Give time, or start and "
                "end times.",
                "date",
            )
        if q.time is not None and (q.start or q.end):
            raise ApiError(
                "conflict", "Give either time for one hour, or start and end for a range, but not both.", "time"
            )
        if q.time is not None:
            hour = parse_hour(q.time, "time")
            return hour, hour
        last = parse_hour(q.end, "end") if q.end else observed
        if q.stat is not None and q.start is None:
            raise ApiError(
                "missing",
                f"{layer_title(layer)} is hourly, so stat needs a start time for the hours it combines, such as "
                "start=2025-07-08T00:00Z.",
                "start",
            )
        first = parse_hour(q.start, "start") if q.start else last
        if first > last:
            raise ApiError(
                "out_of_order",
                f"The start time ({hour_text(first)}) is after the end time ({hour_text(last)}). "
                "Choose a start on or before "
                "the end.",
                "start",
            )
        return first, last
    if q.time is not None:
        raise ApiError(
            "invalid",
            f"{layer_title(layer)} is daily, so it takes a date rather than a time. Give date, or start and end dates.",
            "time",
        )
    if q.date is not None and (q.start or q.end or q.biofix):
        raise ApiError(
            "conflict",
            "Give either date for one day, or a range of days (start or biofix, and end), but not both.",
            "date",
        )
    if q.date is not None:
        day = parse_date(q.date, "date")
        return day, day
    last = parse_date(q.end, "end") if q.end else series.last_closed_day(observed)
    if q.biofix is not None:
        if layer.id != DEGREE_DAYS:
            raise ApiError(
                "not_applicable",
                f"biofix starts a degree-day total, and {layer_title(layer)} isn't one. Give start for the first day.",
                "biofix",
            )
        if q.start is not None:
            raise ApiError("conflict", "Give either biofix or start for the first day, but not both.", "biofix")
        first = resolve_biofix(q.biofix, last)
        assert first is not None
        if first > last:
            raise ApiError(
                "out_of_order",
                f"The biofix ({day_text(first)}) is after the end date ({day_text(last)}). Choose an end on or after "
                "it.",
                "biofix",
            )
        return first, last
    if q.start is None:
        # A range to combine (stat) or one with only its end: the season to date, as at points
        return (last, last) if q.end is None and q.stat is None else (date(last.year, 1, 1), last)
    first = parse_date(q.start, "start")
    if first > last:
        raise ApiError(
            "out_of_order",
            f"The start date ({day_text(first)}) is after the end date ({day_text(last)}). Choose a start date on or "
            "before the end date.",
            "start",
        )
    return first, last


def parse_date(text: str, param: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ApiError(
            "invalid", f"The {param} date ({text}) isn't a date. Give dates as YYYY-MM-DD, such as 2025-07-08.", param
        ) from None


def iso_hour(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def archive_window(data_dir, stores: series.Stores) -> Window:
    """The window the archive's stores hold (the service box as it was when they were made)."""
    for year in sorted(series.archive_years(data_dir), reverse=True):
        store = stores.get(data_dir, DAILY, year)
        if store is not None:
            return store.window
    raise ApiError("no_data", NO_DATA, None, status=503)


def _cubes(layer: Layer, setting, stat, gaps: str, first, last) -> tuple[str, str | None] | None:
    """The running totals a degree-day sum can be read from, where it can."""
    if layer.id != DEGREE_DAYS or setting is None or stat != "sum" or gaps != "estimate":
        return None
    if first.year != last.year:
        return None
    return cube_terms(setting.method, setting.base_f, setting.upper_f)


# --- Model layers --------------------------------------------------------------------------------------------------

# A user's own dates and settings apply at points, not on maps (D66)
POINT_ONLY = ("biofix", "planting_date")


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
        message = f"The {spec.name} model has no crop, so its map takes no planting. Leave out planting."
        if later is not None:
            message = (
                f"The crop stages {spec.name} uses aren't mapped yet, so its map takes no planting. Leave out planting."
            )
        raise ApiError("not_applicable", message, "planting")
    tier = None if crop is None or query.planting == "none" else (query.planting or "mid")
    if tier is None and spec.id in modelmaps.TIER_MODELS and not spec.ingredients:  # soybean, spring wheat
        raise ApiError(
            "invalid",
            f"{spec.name} is mapped for typical planting dates. Give planting=early, mid or late.",
            "planting",
        )
    pointed = (
        f"A map uses each location's typical settings. To run {spec.name} with your own at a location, use "
        f"GET /api/v2/models/{spec.id}/run."
    )
    for name in (*POINT_ONLY, *modelgrid.PLACE_OPTIONS):
        if request.GET.get(name):
            raise ApiError("not_applicable", f"{name} doesn't apply to a map. {pointed}", name)
    chosen = layer.outputs[0] if output is None else next((o for o in layer.outputs if o.name == output), None)
    if chosen is None:
        names = ", ".join(o.name for o in layer.outputs)
        raise ApiError(
            "invalid", f"{layer_title(layer)} has no output named {output!r}. Choose one of: {names}.", "output"
        )
    options = {}
    for o in spec.options:
        if o.name in modelgrid.PLACE_OPTIONS:
            continue
        if request.GET.get(o.name) == "all":
            raise ApiError(
                "invalid",
                f"A map shows one {o.name}. Give one value, or use GET /api/v2/models/{spec.id}/run "
                "to run every choice at "
                "a location.",
                o.name,
            )
        options[o.name] = option_values(o, request.GET.get(o.name), warnings)[0]
    if chosen.name == SUSCEPTIBILITY and tier is None:
        raise ApiError(
            "invalid",
            "Susceptibility comes from the crop's stages, so it needs a planting date. Give "
            "planting=early, mid or late.",
            "planting",
        )
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
        warnings.append(
            f"We have no typical {model.crop} planting dates in this area, so the map uses the model's default dates."
        )
    elif without:
        then = "take the model's default dates"
        if model.spec.id in modelmaps.TIER_MODELS:
            then = "have no stages"
        elif model.spec.susceptible is not None:
            then = "aren't gated by the crop's stages"
        warnings.append(f"Some grid cells ({without:,}) have no typical {model.crop} planting date, so they {then}.")
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
            f"We're updating the data behind the {layer_title(layer)} map. Please try again in a few minutes.",
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
    # Land only: a crop's disease or pest over open water (the Great Lakes and their shore cells) means nothing
    values = np.where(regions.land(data_dir, window), values, np.nan)
    if found.in_region is not None and not found.in_region.any():
        warnings.append(
            f"{layer_title(layer)} was developed for {', '.join(model.spec.region)}, and none of this area "
            "is in those states, so "
            "the map is empty."
        )
    if found.in_season is not None and not any(found.in_season):
        first_md, last_md = model.spec.season or ("", "")
        warnings.append(
            f"These dates are outside the model's season ({_month_day(first_md)} to {_month_day(last_md)})."
        )
    started = [b is not None and d >= b for d, b in zip(found.dates, found.biofix, strict=True)]
    if model.spec.accumulations and not any(started):
        warnings.append(
            f"The season starts at the biofix, {_day_or(found.biofix[-1])}, so nothing has accumulated yet."
        )
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
            raise ApiError("conflict", "Give either a season, or a date or range of dates, but not both.", "season")
        try:
            model.season = seasons.season_named(spec, query.season)
        except ValueError as error:
            raise ApiError("invalid", str(error), "season") from None
        day = seasonal.through(model.season, observed_day)
        if day is None:
            raise ApiError(
                "not_yet",
                f"The {model.season.label} season hasn't started yet. Choose an earlier season.",
                "season",
                status=404,
            )
        return day, day
    if not (query.date or query.start or query.end):
        model.season = seasons.current_season(spec, today)
        day = seasonal.through(model.season, observed_day)
        assert day is not None  # a season appears after it starts
        return day, day
    if last > observed_day:
        raise ApiError(
            "not_observed",
            f"{spec.name} counts observed days only, and the last observed day is {day_text(observed_day)}. Choose a "
            "date on or before it.",
            "date" if query.date else "end",
        )
    model.season = seasons.season_of(spec, last)
    if model.season is None:
        settled = seasons.current_season(spec, last)
        warnings.append(f"{day_text(last)} is between seasons. season={settled.name} gives the last season's count.")
    elif last < model.season.appears:
        warnings.append(
            f"The {model.season.label} season isn't over: this is its count so far, which we show from "
            f"{day_text(model.season.appears)} on."
        )
    return first, last


def _month_day(text: str) -> str:
    """ "08-15" → "August 15"."""
    month, day = (int(p) for p in text.split("-"))
    return f"{date(2001, month, day):%B} {day}"


def _day_or(day: date | None) -> str:
    return "not set" if day is None else day_text(day)


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
            f"We're updating {layer_title(layer)} after a change to how it's computed. Please try again in a few "
            "minutes, or "
            f"ask for up to {MAX_STALE_DAYS} days.",
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


# How long a client or shared cache may keep an image of a layer: the hourly ingest rewrites the last week (URMA
# replacing RTMA) and ERA5-Land replaces soil ~5 days late, so recent times and `latest` stay short; older ones are
# settled but for a rebuild after a deploy, so a day
RECENT_DAYS = 10
RECENT_SECONDS = 300
SETTLED_SECONDS = 86_400


def cache_control(a: LayerAsk, now: datetime, latest: bool) -> str:
    """`Cache-Control` for a tile, legend or map image of `a` (`latest`: asked without a time, so it moves on)."""
    last = a.last.date() if isinstance(a.last, datetime) else a.last
    settled = not latest and last < now.date() - timedelta(days=RECENT_DAYS)
    age = SETTLED_SECONDS if settled else RECENT_SECONDS
    return f"public, max-age={age}, stale-while-revalidate={age}"
