"""Map titles, subtitles and captions as the public reads them (Ben, 2026-11-06; after v1's `image_title`).

v1 built "[statistic] [what] ([units]) for [dates]". Here a title goes from broad to specific with commas, the
when (with how many days or hours a map combines) goes in the subtitle, and the caption says where the data come
from and how many days were estimated or missing (Ben, 2026-11-07):

    Air temperature, daily maximum                    Precipitation, cumulative total
    Nov 5, 2026                                       Jan 1 – Nov 5, 2026 (309 days)
    Data sources: Air temperature (2 m) from          Data sources: Precipitation from URMA/RTMA hourly grids.
    URMA/RTMA hourly grids.                           At some locations, up to 2 days were missing.

- **Title:** the layer's subject (`subject`), then its statistic (a count adds what it counts, "days at or above
  86 °F"): `daily maximum` for one day; over a range,
  `cumulative total` for a sum, `cumulative maximum` where the range's statistic is the day's own (the highest daily
  maximum), else `mean daily maximum`, `lowest daily maximum`. Degree days name their method and thresholds in the
  request's units ("Growing degree days, single sine 50–86 °F, cumulative total"); a model is "[model]: [result]".
- **Subtitle:** the region, the dates with three-letter months and, for a range combined or a running total, how many
  days or hours it combines; an hour in Central time with UTC beside it; for a model its planting tier and scenario
  options.
- **Caption:** the data sources by family (static: what each variable comes from, as `agdata.catalog` sources it),
  and the forecast where the map includes forecast days; then the most days or hours estimated or missing at any
  location, where there are any.

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
    "water_balance": "Water balance (precipitation minus reference evapotranspiration)",
    "thi": "Temperature humidity index",
    "cci": "Cattle comfort index",
    "chill_portions": "Chill portions (Dynamic model)",
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
    "chill_hours": ("Chill hours (32 to 45 °F, 0 to 7.2 °C)", "count"),
    "utah_chill_units": ("Utah chill units", "total"),
    "hours_thi_over_68": ("Hours with a temperature humidity index of 68 or more", "count"),
    "hours_thi_over_72": ("Hours with a temperature humidity index of 72 or more", "count"),
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
    ("chill", f"Hourly air temperature (2 m) from {_URMA}"),
    ("utah_chill", f"Hourly air temperature (2 m) from {_URMA}"),
    ("thi", f"Air temperature and relative humidity (2 m) from {_URMA}"),
    ("hours_thi", f"Air temperature and relative humidity (2 m) from {_URMA}"),
    (
        "cci",
        f"Air temperature, relative humidity and wind from {_URMA}, and solar radiation from HRRR",
    ),
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
    """The map's title for a `layermaps.LayerAsk` (`units`: the request's system, for degree-day thresholds); a count
    is the one-day title and what it counts: "Air temperature, daily maximum, days at or above 86 °F". A window
    (`roll=`) names its length: "Precipitation, 7-day total", "Air temperature, 14-day mean daily maximum"."""
    climate = getattr(a, "climate", None)
    if climate is not None and a.layer.source in ("normals", "terrain"):
        return _stored_title(a, units)
    text = _rolled(_title(a, units), a)
    count = getattr(a, "count", None)
    if climate is not None:
        from api import climatemaps

        counted = "" if count is None else f", {count.words(a.count_shown)}"
        return f"{text}{counted}, {climatemaps.words(climate)}"
    event = getattr(a, "event", None)
    if event is not None:
        return f"{text}, {event.words(a.count_shown)}"
    return text if count is None else f"{text}, {count.words(a.count_shown)}"


def _title(a: Any, units: str) -> str:
    layer: Layer = a.layer
    ranged = a.first != a.last and a.stat not in (None, "count", "first", "last", "since")
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


def _stored_title(a: Any, units: str) -> str:
    """A freeze or elevation map's title: "Chance of a freeze (32 °F), 30-year normal"."""
    c = a.climate
    if a.layer.source == "terrain":
        return f"Elevation, {c.output.label[0].lower()}{c.output.label[1:]}" if c.output.name != "mean" else "Elevation"
    from api import climatemaps

    threshold = _threshold(float(c.threshold_f), units)
    period = climatemaps.PERIOD_WORDS[c.period]
    if c.output is None:
        return f"Chance of a freeze ({threshold}), {period} normal"
    return f"{c.output.label} ({threshold}), {period} normal"


def _rolled(text: str, a: Any) -> str:
    roll = getattr(a, "roll", None)
    if roll is None or a.stat not in _STAT_WORDS:
        return text
    if ", cumulative " in text:
        return text.replace(", cumulative ", f", {roll.days}-day ", 1)
    head, _, tail = text.rpartition(", ")
    return f"{head}, {roll.days}-day {tail}" if head else f"{text}, {roll.days}-day {_STAT_WORDS[str(a.stat)]}"


def subtitle(a: Any, region: str | None = None) -> str:
    """Where and when, and a model's planting and options: "Wisconsin · Jan 1 – Nov 5, 2026"."""
    parts = [region] if region else []
    model = a.model
    climate = getattr(a, "climate", None)
    if climate is not None and a.layer.source in ("normals", "terrain"):
        if a.layer.time_axis == "day_of_year":
            parts.append(f"{a.first:%B} {a.first.day}")
        if climate.years is not None:
            parts.append(f"Years {climate.years[0]}–{climate.years[1]}")
        return " · ".join(parts)
    if model is not None and model.season is not None and a.first == a.last:
        parts.append(f"{model.season.label} season, through {day_text(a.last)}")
    elif isinstance(a.first, datetime):
        parts.append(
            hour_text(a.first) if a.first == a.last else f"{hour_text(a.first)} to {hour_text(a.last)}{_span(a)}"
        )
    elif a.layer.source == "cumulative":
        parts.append(f"{range_text(date(a.last.year, 1, 1), a.last)}{_span(a)}")
    elif getattr(a, "roll", None) is not None:
        where = "ending" if a.roll.align == "trailing" else "centered on"
        parts.append(f"{a.roll.days} days {where} {day_text(a.roll_day)} ({range_text(a.first, a.last)})")
    else:
        parts.append(day_text(a.first) if a.first == a.last else f"{range_text(a.first, a.last)}{_span(a)}")
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
    """The data sources, then the days or hours estimated or missing: one string a line (`mapimage.map_png` wraps
    them)."""
    lines = [f"Data sources: {_sources(a)}{_forecast(a, computed)}{_climate_sources(a)}."]
    gaps = _gaps(a, computed)
    if gaps:
        lines.append(gaps)
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
    c = getattr(a, "climate", None)
    if c is not None and a.layer.source == "terrain":
        return "Elevation from the USGS National Elevation Dataset in NHDPlus V2"
    if c is not None and a.layer.source == "normals":
        return "Daily minimum air temperature from "
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


def _climate_sources(a: Any) -> str:
    """A climate map's years and their sources, after the weather's (or alone, for stored statistics)."""
    c = getattr(a, "climate", None)
    if c is None or a.layer.source == "terrain" or c.years is None:
        return ""
    first, last = c.years
    since = max(first, 2016)
    parts = [f"AgWeather's archive ({since}–{last})"] if last >= 2016 else []
    if first < 2016:
        parts.append(f"gridMET ({first}–2015), adjusted to the archive")
    text = " and ".join(parts)
    return f"; normals from {text}" if a.layer.source != "normals" else text


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


def _span(a: Any) -> str:
    """ " (309 days)" for a running total or a range combined into one map; "" for a single day or each step."""
    if a.layer.source == "cumulative":
        return f" ({_counted((a.last - date(a.last.year, 1, 1)).days + 1, 'day')})"
    if a.first == a.last or a.stat is None:
        return ""
    if isinstance(a.first, datetime):
        return f" ({_counted((a.last - a.first) // timedelta(hours=1) + 1, 'hour')})"
    return f" ({_counted((a.last - a.first).days + 1, 'day')})"


def _gaps(a: Any, computed: Any) -> str:
    """ "At some locations, up to 3 days were estimated and up to 1 day was missing." for a range combined, from
    the most at any location with a value; "" where there were none."""
    if a.first == a.last or a.stat is None:
        return ""
    unit = "hour" if isinstance(a.first, datetime) else "day"
    notes = []
    mapped = np.isfinite(computed.values[0])  # cells with a value: open water and cells outside a model don't count
    for key, word in (("estimated_days", "estimated"), ("missing_days", "missing"), ("missing_hours", "missing")):
        values = computed.extra.get(key)
        if values is None:
            continue
        counts = np.asarray(values, dtype=float)[mapped]
        most = int(np.nanmax(counts)) if np.isfinite(counts).any() else 0
        if most:
            notes.append(f"up to {_counted(most, unit)} {'was' if most == 1 else 'were'} {word}")
    return f"At some locations, {' and '.join(notes)}." if notes else ""


def _counted(n: int, noun: str) -> str:
    return f"{n:,} {noun}" if n == 1 else f"{n:,} {noun}s"
