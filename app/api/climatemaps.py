"""Climate on maps (D86; PLAN.md Phase 6 E4): `climate=` on a layer, the freeze layers and elevation.

A layer that lists `climate` (`agdata.layers`) takes `climate=normal`, `departure` or `percentile` with `period=`:

- **normal**: the stored normal maps (`agdata.normals`, D85) for the map as asked, with no weather read. That holds
  where the map is linear in what's stored: one day of a daily variable (its pooled mean), a range's mean (the mean
  of its days' means) or a sum of one that adds up (precipitation's and ET0's from their normal running totals,
  each year's own total; sunlight's from its days' means), a running total on a day, and degree days whose setting
  the stored cubes make (a single sine pair is the difference of its thresholds', any start a subtraction).
  A minimum or maximum over days, a count, a first or last day, an hourly map and a model's aren't, and are refused
  (the points, `/climate/*`, compute them from the years).
- **departure**: the map as asked less its normal, in a difference's unit (°F of difference, not °F).
- **percentile**: where the map sits among the period's years, from the stored deciles (`normals.percentile_among`):
  only running totals from January 1 of modified 50/86 and sine 41/86 degree days and precipitation, not in `last5`.

`freeze_chance` (a day of the year, `threshold=32`, `28` or `24` °F), `freeze_dates` (no time; `output=` the date or
season length) and `elevation` (no time; `output=mean`, `min`, `max` or `spread`, from `agdata.terrain`) are maps of
the stored statistics alone.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from django.conf import settings

from agdata import normals, palettes, series, terrain
from agdata.catalog import dd_name
from agdata.grid import Window
from agdata.layers import DEGREE_DAYS, ELEVATION_OUTPUTS, FREEZE_DATE_OUTPUTS, NORMAL_DECILES, Layer, LayerOutput
from api.errors import ApiError
from api.events import EPOCH
from api.maptitles import layer_title

KINDS = ("normal", "departure", "percentile")
FREEZE_F = (32, 28, 24)  # the thresholds the normal maps hold (`normals.FREEZE_F`)
FREEZE_C = {32: 0.0, 28: -2.2, 24: -4.4}  # as a request in metric gives them (`/freeze`'s defaults)
PERIOD_WORDS = {"last30": "30-year", "last10": "10-year", "last5": "5-year"}
SUMMED_FROM_RUNNING = {"precipitation_sum": "precipitation", "et0_sum": "et0"}
DIFFERENCE_UNITS = {"degC": "delta_degC", "degF": "delta_degF"}


@dataclass(frozen=True, kw_only=True)
class ClimateAsk:
    """What a map asks of the climate: `kind` (`climate=`, None for the freeze and elevation layers), the period,
    a freeze threshold (°F), an output of those layers, and the stored running totals a degree-day setting is made
    of (`cubes`: a name, and one to subtract)."""

    kind: str | None
    period: str
    years: tuple[int, int] | None  # the store's first and last year
    threshold_f: int | None = None
    output: LayerOutput | None = None
    cubes: tuple[str, str | None] | None = None


def built(period: str) -> dict[str, Any]:
    found = normals.info(settings.DATA_DIR, period)
    if found is None:
        raise ApiError(
            "no_data",
            f"The {PERIOD_WORDS[period]} normal maps aren't ready yet. Please try again later, or ask for "
            "the normals at a location with /climate/normals.",
            "period",
            status=503,
        )
    return found


def _years(info: dict[str, Any]) -> tuple[int, int] | None:
    years = info.get("years") or []
    return (min(years), max(years)) if years else None


def threshold_f(value: float | None, units: str) -> int:
    """A freeze threshold as asked (default 32 °F) as one the maps hold, or an ApiError."""
    if value is None:
        return 32
    for f in FREEZE_F:
        if (units == "metric" and abs(value - FREEZE_C[f]) < 0.05) or (units != "metric" and abs(value - f) < 0.05):
            return f
    held = ", ".join(f"{FREEZE_C[f]:g}" if units == "metric" else str(f) for f in FREEZE_F)
    unit = "°C" if units == "metric" else "°F"
    raise ApiError(
        "invalid",
        f"Freeze maps are kept for {held} {unit}, not {value:g} {unit}. Choose one of those, or ask for any "
        "threshold at a location with /climate/frost.",
        "threshold",
    )


def _output(layer: Layer, name: str | None) -> LayerOutput:
    if name is None:
        return layer.outputs[0]
    found = next((o for o in layer.outputs if o.name == name), None)
    if found is None:
        names = ", ".join(o.name for o in layer.outputs)
        raise ApiError(
            "invalid", f"{layer_title(layer)} has no output named {name!r}. Choose one of {names}.", "output"
        )
    return found


def ask_layer(layer: Layer, q: Any, units: str) -> ClimateAsk:
    """The freeze and elevation layers' settings, checked."""
    for param in ("stat", "count", "first", "last", "since", "dd", "biofix", "season", "roll", "start", "end"):
        if getattr(q, param, None) is not None:
            raise ApiError(
                "not_applicable",
                f"{layer_title(layer)} is one map of stored statistics, so it takes no {param}. Leave it out.",
                param,
            )
    if getattr(q, "climate", None) is not None:
        raise ApiError(
            "not_applicable",
            f"{layer_title(layer)} is already a climate statistic, so it takes no climate. Leave it out.",
            "climate",
        )
    if layer.time_axis == "none" and (q.date is not None or q.time is not None):
        param = "date" if q.date is not None else "time"
        raise ApiError("not_applicable", f"{layer_title(layer)} doesn't change by date, so it takes no {param}.", param)
    if q.time is not None:
        raise ApiError(
            "invalid", f"{layer_title(layer)} is by day of the year. Give a date rather than a time.", "time"
        )
    if layer.source == "terrain":
        if q.threshold is not None:
            raise ApiError("not_applicable", "threshold applies only to the freeze maps. Leave it out.", "threshold")
        if terrain.load(settings.DATA_DIR) is None:
            raise ApiError("no_data", "The elevation map isn't ready yet. Please try again later.", None, status=503)
        return ClimateAsk(kind=None, period=q.period, years=None, output=_output(layer, q.output))
    if q.output is not None and not layer.outputs:
        raise ApiError("not_applicable", f"{layer_title(layer)} has no outputs. Leave out output.", "output")
    info = built(q.period)
    return ClimateAsk(
        kind=None,
        period=q.period,
        years=_years(info),
        threshold_f=threshold_f(q.threshold, units),
        output=_output(layer, q.output) if layer.outputs else None,
    )


def check(
    layer: Layer,
    q: Any,
    *,
    first: Any,
    last: Any,
    stat: str | None,
    setting: Any,
    roll: Any,
    counted: bool,
    model: Any,
) -> ClimateAsk | None:
    """`climate=` on a weather layer, checked against what the normal maps can give (module docstring); None
    without it, refusing `period` and `threshold` alone."""
    kind = q.climate
    if kind is None:
        if q.period != "last30":
            raise ApiError(
                "not_applicable",
                "period chooses the years of a climate map, so it applies only with climate=normal, departure or "
                "percentile. Add climate, or leave out period.",
                "period",
            )
        if q.threshold is not None:
            raise ApiError("not_applicable", "threshold applies only to the freeze maps. Leave it out.", "threshold")
        return None
    title = layer_title(layer)
    if q.threshold is not None:
        raise ApiError("not_applicable", "threshold applies only to the freeze maps. Leave it out.", "threshold")
    if kind not in layer.climate:
        offered = (
            f"It takes climate={' or '.join(layer.climate)}."
            if layer.climate
            else "Normals are kept for the daily weather variables, their running totals and degree days."
        )
        raise ApiError("not_applicable", f"We don't keep the {kind} maps of {title}. {offered}", "climate")
    if model is not None or counted:
        raise ApiError(
            "not_applicable",
            "A climate map combines days by their sum or mean. Leave out count, first, last and since, or ask for "
            "them at a location with /climate/normals.",
            "climate",
        )
    if first != last and stat is None:
        raise ApiError(
            "invalid",
            "A climate map shows one map. Give one date, or a range of days with stat=sum or stat=mean.",
            "climate",
        )
    if stat in ("min", "max"):
        raise ApiError(
            "not_applicable",
            f"The normal of a range's {'lowest' if stat == 'min' else 'highest'} value isn't kept as a map. Use "
            "stat=mean or sum, or ask at a location with /climate/normals, which works it out from each year.",
            "stat",
        )
    info = built(q.period)
    held = {name.split("/")[0] for name in _stored(info)}
    cubes = None
    if layer.source == "daily":
        assert layer.variable is not None
        if layer.variable not in held:
            raise ApiError(
                "not_applicable",
                f"The {PERIOD_WORDS[q.period]} normals have no {title}: the records before 2016 have each day's "
                "minimum and maximum only. Ask for period=last10 or last5.",
                "period",
            )
    elif layer.id == DEGREE_DAYS:
        cubes = _setting_cubes(setting)
        if cubes is None or any(c is not None and c not in held for c in cubes):
            raise ApiError(
                "not_applicable",
                f"Normal maps are kept for the degree-day settings we keep running totals of, not {setting.name}. "
                "Ask for its normals at a location with /climate/normals?dd=" + setting.name + ".",
                "dd",
            )
    if kind == "percentile":
        decile = _decile_name(layer, setting)
        if decile is None or q.period == "last5":
            raise ApiError(
                "not_applicable",
                "Percentile maps are kept for running totals from January 1 of precipitation and modified 50/86 "
                "and single sine 41/86 degree days, over the 30 or 10 years. Ask for climate=departure, or for the "
                "percentile at a location with /climate/compare.",
                "climate",
            )
        start = first if isinstance(first, date) else None
        if layer.id == DEGREE_DAYS and (stat != "sum" or start is None or (start.month, start.day) != (1, 1)):
            raise ApiError(
                "invalid",
                "A percentile map ranks the running total from January 1. Give start as January 1 with stat=sum.",
                "start",
            )
    del roll  # a window is a range with its statistic by now (`layermaps._roll_range`)
    return ClimateAsk(kind=kind, period=q.period, years=_years(info), cubes=cubes)


def _stored(info: dict[str, Any]) -> list[str]:
    return [s.name for s in normals.stats(str(info.get("period")))]


def _setting_cubes(setting: Any) -> tuple[str, str | None] | None:
    """The stored running totals a setting is made of: its own, or a single sine pair's two thresholds."""
    if setting is None:
        return None
    if setting.method == "sine" and setting.upper_f is not None:
        return (dd_name("sine", setting.base_f), dd_name("sine", setting.upper_f))
    return (dd_name(setting.method, setting.base_f, setting.upper_f), None)


def _decile_name(layer: Layer, setting: Any) -> str | None:
    """The stored deciles a map's percentile is placed among (`normals.DECILE_NAMES`), or None."""
    if layer.source == "cumulative" and layer.variable in NORMAL_DECILES:
        return layer.variable
    if layer.id == DEGREE_DAYS and setting is not None and f"dd_{setting.name}" in NORMAL_DECILES:
        return f"dd_{setting.name}"
    return None


# --- Units, colors and words ---------------------------------------------------------------------------------------


def unit(c: ClimateAsk, layer_unit: str) -> str:
    if c.output is not None:
        return c.output.unit
    if c.kind == "percentile":
        return "percent"
    if c.kind == "departure":
        return DIFFERENCE_UNITS.get(layer_unit, layer_unit)
    return layer_unit


def use(c: ClimateAsk, layer_use: str) -> str:
    if c.output is not None:
        return c.output.use
    return palettes.climate_use(layer_use, c.kind or "normal")


def words(c: ClimateAsk) -> str:
    """What a climate map is, for its title: "30-year normal", "departure from the 30-year normal"."""
    period = PERIOD_WORDS[c.period]
    if c.kind == "departure":
        return f"departure from the {period} normal"
    if c.kind == "percentile":
        return f"percentile among the {period} period's years"
    return f"{period} normal"


def years_text(c: ClimateAsk) -> str:
    return f"{c.years[0]}–{c.years[1]}" if c.years else ""


# --- Maps ------------------------------------------------------------------------------------------------------


def stamp(c: ClimateAsk) -> str | None:
    if c.output is not None and c.threshold_f is None:  # elevation
        t = terrain.load(settings.DATA_DIR)
        return None if t is None else f"terrain:{t.stamp}"
    return normals.stamp(settings.DATA_DIR, c.period)


def normal(layer: Layer, c: ClimateAsk, first: date, last: date, stat: str | None, window: Window) -> np.ndarray:
    """The normal of the map as asked (one map, in the layer's stored unit)."""
    data_dir, period = settings.DATA_DIR, c.period
    days = (last - first).days + 1
    if layer.source == "cumulative":
        assert layer.variable is not None
        return normals.read_within(data_dir, period, f"{layer.variable}/mean", last, window)
    if layer.id == DEGREE_DAYS:
        assert c.cubes is not None
        cube, minus = c.cubes
        total = normals.running_change(data_dir, period, cube, first, last, window)
        if minus is not None:
            total = total - normals.running_change(data_dir, period, minus, first, last, window)
        return total / days if stat == "mean" else total
    assert layer.variable is not None
    if stat == "sum" and layer.variable in SUMMED_FROM_RUNNING:
        return normals.running_change(data_dir, period, SUMMED_FROM_RUNNING[layer.variable], first, last, window)
    total = np.zeros(window.shape)
    day = first
    while day <= last:
        total = total + normals.read_within(data_dir, period, f"{layer.variable}/mean", day, window)
        day = date.fromordinal(day.toordinal() + 1)
    return total if stat == "sum" else total / days


def percentile(layer: Layer, c: ClimateAsk, value: np.ndarray, last: date, window: Window, setting: Any) -> np.ndarray:
    name = _decile_name(layer, setting)
    assert name is not None
    deciles = [
        normals.read_within(settings.DATA_DIR, c.period, f"{name}/p{p:g}", last, window) for p in normals.DECILES
    ]
    return normals.percentile_among(value, deciles)


def stored_layer(layer: Layer, c: ClimateAsk, day: date, window: Window) -> np.ndarray:
    """A freeze or elevation map (one map), in its output's unit: a freeze date as days since 1970 in `day`'s
    year (the date unit of D78's maps)."""
    if layer.source == "terrain":
        t = terrain.load(settings.DATA_DIR)
        assert t is not None and c.output is not None
        field = next(stored for name, _, stored in ELEVATION_OUTPUTS if name == c.output.name)
        return t.crop(field, window).astype(np.float64)
    prefix = f"freeze_{c.threshold_f}"
    if c.output is None:  # freeze_chance
        return normals.read_within(settings.DATA_DIR, c.period, f"{prefix}/chance", day, window)
    stored = next(s for name, _, s in FREEZE_DATE_OUTPUTS if name == c.output.name)
    values = normals.read_within(settings.DATA_DIR, c.period, f"{prefix}/{stored}", None, window)
    if c.output.unit != "date":
        return values
    return slot_dates(values, day.year)


def slot_dates(slots: np.ndarray, year: int) -> np.ndarray:
    """Calendar slots (`climatology.slot`) as days since 1970 in `year`: in a year without February 29, a slot after
    it is a day earlier, and February 29 itself is March 1."""
    leap = date(year, 3, 1).toordinal() - date(year, 2, 1).toordinal() == 29
    base = float((date(year, 1, 1) - EPOCH).days)
    shift = 0.0 if leap else 1.0
    return np.where(np.isfinite(slots), base + slots - np.where(slots > 59, shift, 0.0), np.nan)


def sources(c: ClimateAsk) -> list[str]:
    if c.output is not None and c.threshold_f is None:
        return ["nhdplus"]
    info = normals.info(settings.DATA_DIR, c.period) or {}
    years, archive = info.get("years") or [], set(info.get("archive_years") or [])
    found = ["agweather"] if any(y in archive for y in years) else []
    return found + (["gridmet"] if any(y not in archive for y in years) else [])


def no_forecast() -> series.Forecast:
    return series.Forecast(path=None, reason="none")


def year_span(year: int) -> tuple[float, float]:
    """A freeze-date map's domain bounds: the year's first and last day, as days since 1970."""
    return float((date(year, 1, 1) - EPOCH).days), float((date(year, 12, 31) - EPOCH).days)
