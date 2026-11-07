"""Map titles, subtitles and captions as the public reads them (Ben, 2026-11-06; after v1's `image_title`).

v1 built "[statistic] [what] ([units]) for [dates]". Here a title goes from broad to specific with commas, the
when goes in the subtitle, and the caption says where the data come from and how many days or hours a map combines:

    Air temperature, daily maximum                    Precipitation, cumulative total
    Nov 5, 2026                                       Jan 1 – Nov 5, 2026
    Data sources: Air temperature (2 m) from          Data sources: Precipitation from URMA/RTMA hourly grids.
    URMA/RTMA hourly grids.                           309 days combined.

- **Title:** the layer's subject (`subject`), then its statistic: `daily maximum` for one day; over a range,
  `cumulative total` for a sum, `cumulative maximum` where the range's statistic is the day's own (the highest daily
  maximum), else `mean daily maximum`, `lowest daily maximum`. Degree days name their method and thresholds in the
  request's units ("Growing degree days, single sine 50–86 °F, cumulative total"); a model is "[model]: [result]".
- **Subtitle:** the region, the dates with three-letter months, an hour in Central time with UTC beside it, and for a
  model its planting tier and scenario options.
- **Caption:** the data sources by family (static: what each variable comes from, as `agdata.catalog` sources it),
  and the forecast where the map includes forecast days; then the days or hours combined, with the most estimated
  or missing at any location.

`layer_title` (the subject and its daily statistic, without dates) also names a layer in error messages.
"""

from datetime import date, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

import numpy as np

from agdata.layers import DEGREE_DAYS, Layer
from api.params import DegreeDaySetting

CENTRAL = ZoneInfo("America/Chicago")

# The base variables' public names, broad to specific; the longest matching prefix wins
_SUBJECTS = {
    "air_temperature": "Air temperature",
    "dew_point_depression": "Dew point depression",
    "dew_point": "Dew point",
    "relative_humidity": "Relative humidity",
    "wind_speed": "Wind speed",
    "wind_gust": "Wind gust",
    "wind_direction": "Wind direction",
    "surface_pressure": "Surface pressure",
    "cloud_cover": "Cloud cover",
    "precipitation": "Precipitation",
    "shortwave_radiation": "Solar radiation",
    "soil_temperature_4cm": "Soil temperature, 4 cm (1.6 in)",
    "soil_temperature_10cm": "Soil temperature, 10 cm (3.9 in)",
    "soil_temperature_30cm": "Soil temperature, 30 cm (11.8 in)",
    "snow_depth": "Snow depth",
    "et0": "Reference evapotranspiration (ET0)",
}
# Variables whose name doesn't follow `<base>_<statistic>`: (subject, the day's statistic)
_SPECIAL = {
    "hours_temperature_over_20c": ("Hours at or above 68 °F (20 °C)", "count"),
    "hours_temperature_over_30c": ("Hours at or above 86 °F (30 °C)", "count"),
    "hours_rh_under_70": ("Hours with relative humidity below 70%", "count"),
    "hours_rh_over_80": ("Hours with relative humidity of 80% or more", "count"),
    "hours_rh_over_90": ("Hours with relative humidity of 90% or more", "count"),
    "hours_rh_over_90_temperature_over_70f": (
        "Hours with relative humidity of 90% or more, at 70 °F (21 °C) or warmer",
        "count",
    ),
    "hours_rh_over_80_from_6pm": ("Hours with relative humidity of 80% or more, days from 6 p.m.", "count"),
    "hours_rh_over_90_from_6pm": ("Hours with relative humidity of 90% or more, days from 6 p.m.", "count"),
    "hours_rh_over_80_night": ("Night hours with relative humidity of 80% or more, 6 p.m. to 6 a.m.", "count"),
    "hours_rh_over_90_night": ("Night hours with relative humidity of 90% or more, 6 p.m. to 6 a.m.", "count"),
    "hours_rh_over_90_7pm_to_6am": ("Hours with relative humidity of 90% or more, 7 p.m. to 6 a.m.", "count"),
    "hours_soil_4cm_below_27f": ("Hours with soil below 27 °F, 4 cm (1.6 in)", "count"),
    "hours_soil_10cm_below_27f": ("Hours with soil below 27 °F, 10 cm (3.9 in)", "count"),
    "hours_soil_8in_below_27f": ("Hours with soil below 27 °F, 20 cm (8 in)", "count"),
    "temperature_mean_rh_over_80_from_6pm": (
        "Temperature in hours with relative humidity of 80% or more, days from 6 p.m.",
        "mean",
    ),
    "temperature_mean_rh_over_90_from_6pm": (
        "Temperature in hours with relative humidity of 90% or more, days from 6 p.m.",
        "mean",
    ),
    "air_temperature_min_overnight": ("Overnight air temperature (noon to noon)", "minimum"),
    "water_balance": ("Water balance (precipitation minus reference evapotranspiration)", "total"),
}
_DAILY = {"min": "minimum", "max": "maximum", "mean": "mean", "sum": "total"}
_RANGE = {"mean": "mean", "max": "highest", "min": "lowest"}  # a range's statistic of a different daily one
_STAT_WORDS = {"sum": "total", "max": "maximum", "min": "minimum", "mean": "mean"}
_CROPS = {"potato": "Potatoes", "soybean": "Soybeans"}
_METHODS = {"sine": "single sine", "modified": "modified", "average": "simple average"}

# Where each family's data come from (`agdata.catalog`'s sources), as the caption says it
_URMA = "URMA/RTMA hourly grids"
_FAMILY_SOURCES = (
    (
        "water_balance",
        f"Precipitation from {_URMA}; reference evapotranspiration (FAO-56) computed from air temperature, humidity "
        f"and wind from {_URMA} and solar radiation from HRRR",
    ),
    ("air_temperature", f"Air temperature (2 m) from {_URMA}"),
    ("temperature_mean", f"Air temperature and dew point (2 m) from {_URMA}"),
    ("hours_temperature", f"Air temperature (2 m) from {_URMA}"),
    ("dew_point", f"Air temperature and dew point (2 m) from {_URMA}"),
    ("relative_humidity", f"Relative humidity (2 m), computed from air temperature and dew point from {_URMA}"),
    ("hours_rh", f"Relative humidity (2 m), computed from air temperature and dew point from {_URMA}"),
    ("wind", f"Wind (10 m) from {_URMA}"),
    ("surface_pressure", f"Surface pressure from {_URMA}"),
    ("cloud_cover", f"Cloud cover from {_URMA}"),
    ("precipitation", f"Precipitation from {_URMA}"),
    ("shortwave_radiation", "Solar radiation from HRRR hourly grids, corrected to ground measurements"),
    ("soil_temperature", "Soil temperature from ERA5-Land, with ECMWF IFS for the latest days"),
    ("hours_soil", "Soil temperature from ERA5-Land, with ECMWF IFS for the latest days"),
    ("snow_depth", "Snow depth from ERA5-Land, with ECMWF IFS for the latest days"),
    (
        "et0",
        "Reference evapotranspiration (FAO-56) computed from air temperature, humidity and wind from URMA/RTMA "
        "and solar radiation from HRRR",
    ),
    ("dd_", f"Air temperature (2 m) from {_URMA}"),
    ("degree_days", f"Air temperature (2 m) from {_URMA}"),
)


def subject(layer: Layer) -> tuple[str, str | None]:
    """A weather layer's subject and the day's statistic (None for an hour, or a running total's `total`)."""
    if layer.id in _SPECIAL:
        return _SPECIAL[layer.id]
    name = layer.variable or layer.id
    base = max((k for k in _SUBJECTS if name.startswith(k)), key=len, default=None)
    found = _SUBJECTS[base] if base is not None else layer.name
    if layer.time_axis == "hour":
        return found, None
    if layer.source == "cumulative":
        return found, "total"
    return found, _DAILY.get(name.rsplit("_", 1)[-1])


def layer_title(layer: Layer) -> str:
    """A layer's name as a reader says it, without dates: "Air temperature, daily maximum"."""
    if layer.source == "model":
        return layer.name
    if layer.id == DEGREE_DAYS:
        return "Growing degree days"
    if layer.id.startswith("dd_"):
        return f"Growing degree days, {_dd_layer_setting(layer.id)}, cumulative total"
    what, statistic = subject(layer)
    if layer.time_axis == "hour":
        return f"{what}, hourly"
    if layer.source == "cumulative":
        return f"{what}, cumulative total"
    return f"{what}, daily {statistic}" if statistic else what


def title(a: Any, units: str) -> str:
    """The map's title for a `layermaps.LayerAsk` (`units`: the request's system, for degree-day thresholds)."""
    layer: Layer = a.layer
    ranged = a.first != a.last and a.stat is not None
    if a.model is not None:
        result = _lower_first(a.model.output.label)
        text = f"{a.model.spec.name}: {result}"
        return f"{text}, cumulative {_STAT_WORDS[str(a.stat)]}" if ranged else text
    if layer.id == DEGREE_DAYS:
        what = f"Growing degree days, {setting_text(a.setting, units)}"
        return f"{what}, {_statistic('total', a.stat if ranged else None)}"
    if layer.id.startswith("dd_"):
        return f"Growing degree days, {_dd_layer_setting(layer.id, units)}, cumulative total"
    what, daily = subject(layer)
    if layer.time_axis == "hour":
        return f"{what}, cumulative {_STAT_WORDS[str(a.stat)]}" if ranged else f"{what}, hourly"
    if layer.source == "cumulative":
        return f"{what}, cumulative total"
    return f"{what}, {_statistic(daily or 'value', a.stat if ranged else None)}"


def subtitle(a: Any, region: str | None = None) -> str:
    """Where and when, and a model's planting and options: "Wisconsin · Jan 1 – Nov 5, 2026"."""
    parts = [region] if region else []
    model = a.model
    if model is not None and model.season is not None and a.first == a.last:
        parts.append(f"{model.season.label} season, through {day_text(a.last)}")
    elif isinstance(a.first, datetime):
        parts.append(hour_text(a.first) if a.first == a.last else f"{hour_text(a.first)} to {hour_text(a.last)}")
    elif a.layer.source == "cumulative":
        parts.append(range_text(date(a.last.year, 1, 1), a.last))
    else:
        parts.append(day_text(a.first) if a.first == a.last else range_text(a.first, a.last))
    if model is not None:
        if model.tier is not None and model.crop is not None:
            crop = _CROPS.get(model.crop, model.crop.replace("-", " ").capitalize())
            parts.append(f"{crop} planted on typical {model.tier}-season dates")
        for option in model.spec.options:
            if option.name in model.options and option.choices:
                chosen = dict(option.choices).get(model.options[option.name])
                if chosen is not None and model.options[option.name] != option.default:
                    parts.append(f"{option.label}: {chosen}")
    return " · ".join(parts)


def caption(a: Any, computed: Any) -> list[str]:
    """The data sources, then the days or hours combined: one string a line (`mapimage.map_png` wraps them)."""
    lines = [f"Data sources: {_sources(a)}{_forecast(a, computed)}."]
    combined = _combined(a, computed)
    if combined:
        lines.append(combined)
    return lines


def setting_text(setting: DegreeDaySetting | None, units: str) -> str:
    """A degree-day setting in the request's units: "single sine 50–86 °F", "modified, base 40 °F"."""
    if setting is None:
        return "any setting"
    method = _METHODS[setting.method]
    base = _threshold(setting.base_f, units)
    if setting.upper_f is None:
        return f"{method}, base {base}"
    return f"{method} {base.split(' ')[0]}–{_threshold(setting.upper_f, units)}"


def day_text(day: date) -> str:
    """A day with a three-letter month: "Nov 5, 2026"."""
    return f"{day:%b} {day.day}, {day.year}"


def range_text(first: date, last: date) -> str:
    """ "Jan 1 – Nov 5, 2026", or with both years when they differ."""
    if first.year == last.year:
        return f"{first:%b} {first.day} – {day_text(last)}"
    return f"{day_text(first)} – {day_text(last)}"


def hour_text(when: datetime) -> str:
    """An hour as Central time with UTC beside it: "Nov 6, 2026, 7 a.m. CST (13:00 UTC)"."""
    local = when.astimezone(CENTRAL)
    clock = "noon" if local.hour == 12 else "midnight" if local.hour == 0 else _clock(local.hour)
    return f"{day_text(local.date())}, {clock} {local.tzname()} ({when.astimezone(ZoneInfo('UTC')):%H:%M} UTC)"


# --- Helpers ------------------------------------------------------------------------------------------------------


def _statistic(daily: str, ranged: str | None) -> str:
    if ranged is None:
        return f"daily {daily}"
    if ranged == "sum":
        return "cumulative count" if daily == "count" else "cumulative total"
    if _DAILY.get(ranged) == daily:
        return f"cumulative {daily}"
    return f"{_RANGE.get(ranged, ranged)} daily {daily}"


def _dd_layer_setting(layer_id: str, units: str = "us") -> str:
    """A running-total layer's setting from its id: dd_sine_50 → "single sine, base 50 °F"."""
    parts = layer_id.removeprefix("dd_").split("_")
    numbers = [float(p.replace("p", ".")) for p in parts[1:]]
    setting = DegreeDaySetting(
        name=layer_id, method=cast(Any, parts[0]), base_f=numbers[0], upper_f=numbers[1] if len(numbers) > 1 else None
    )
    return setting_text(setting, units)


def _threshold(value_f: float, units: str) -> str:
    value, unit = (value_f, "°F") if units == "us" else ((value_f - 32) * 5 / 9, "°C")
    return f"{value:.1f}".removesuffix(".0") + f" {unit}"


def _clock(hour: int) -> str:
    return f"{hour % 12 or 12} {'a.m.' if hour < 12 else 'p.m.'}"


def _lower_first(text: str) -> str:
    """ "Risk level" → "risk level"; "P-days…" and "GDD…" keep their capitals."""
    return text[0].lower() + text[1:] if len(text) > 1 and text[1].islower() else text


def _sources(a: Any) -> str:
    if a.model is not None:
        names = {i.name for i in a.model.spec.inputs}
        found = [f"Weather from {_URMA}"]
        if any(n.startswith("shortwave") or n.startswith("et0") for n in names):
            found.append("solar radiation from HRRR")
        if any("soil" in n for n in names):
            found.append("soil temperature from ERA5-Land and ECMWF IFS")
        return ", ".join(found)
    name = a.layer.variable or a.layer.id
    return next((text for prefix, text in _FAMILY_SOURCES if name.startswith(prefix)), "AgWeather's archive")


def _forecast(a: Any, computed: Any) -> str:
    kinds = list(computed.kinds)
    ahead = [step for step, kind in zip(computed.steps, kinds, strict=False) if kind in ("partial", "forecast")]
    if not ahead:
        return ""
    soil = (a.layer.variable or a.layer.id).startswith(("soil", "snow", "hours_soil"))
    source = "the ECMWF IFS forecast" if soil else "the National Blend of Models (NBM) forecast"
    first = ahead[0]
    when = hour_text(first) if isinstance(first, datetime) else day_text(first)
    return f"; {source} from {when}"


def _combined(a: Any, computed: Any) -> str:
    """ "309 days combined." with the most estimated or missing at any location, for a range or a running total."""
    if a.layer.source == "cumulative":
        days = (a.last - date(a.last.year, 1, 1)).days + 1
        return f"{_counted(days, 'day')} combined, from January 1."
    if a.first == a.last or a.stat is None:
        return ""
    hourly = isinstance(a.first, datetime)
    n = (a.last - a.first) // timedelta(hours=1) + 1 if hourly else (a.last - a.first).days + 1
    unit = "hour" if hourly else "day"
    text = f"{_counted(n, unit)} combined"
    notes = []
    mapped = np.isfinite(computed.values[0])  # cells with a value: open water and cells outside a model don't count
    for key, word in (("estimated_days", "estimated"), ("missing_days", "missing"), ("missing_hours", "missing")):
        values = computed.extra.get(key)
        if values is None:
            continue
        counts = np.asarray(values, dtype=float)[mapped]
        most = int(np.nanmax(counts)) if np.isfinite(counts).any() else 0
        if most:
            notes.append(f"up to {_counted(most, unit)} {word} at some locations")
    return text + (f"; {', '.join(notes)}." if notes else ".")


def _counted(n: int, noun: str) -> str:
    return f"{n:,} {noun}" if n == 1 else f"{n:,} {noun}s"
