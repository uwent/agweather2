"""Daily features: what the models read beyond daily min, mean and max, computed from hours (PLAN.md Phase 3 B).

Hourly-native, after the Crop Risk Tool's `build_daily`, with v2's windows (D74). An hourly value is stamped at the
end of its hour (precipitation is what fell in that hour; temperature and humidity are the reading at that time), and
a window from A to B holds the readings stamped after A through B, so a window's precipitation is exactly what fell
between A and B. Clock hours are the day basis's: CST all year on the grid, a point's own zone with `day_basis=local`.

- the calendar day: midnight to midnight (readings 01:00–24:00);
- the day from 6 pm (`_from_6pm`): 6 pm the evening before to 6 pm (readings 19:00–18:00), so an overnight wet
  period isn't split at midnight; the disease-severity models read it (the Crop Risk Tool's was from 8 pm);
- night (`_night`): 6 pm to 6 am (readings 19:00–06:00, 12 hours), within the day from 6 pm;
- tar spot's night (`_7pm_to_6am`): 7 pm to 6 am (readings 20:00–06:00, 11 hours), the window Webster et al.'s
  coefficients were fitted on as the Crop Risk Tool counts it;
- overnight (`_overnight`): noon the day before to noon (readings 13:00–12:00), for the night's minimum, which on a
  winter morning can come after 7 am.

The reducers take one window's hours on axis 0 (a point (hours,) or the grid (hours, y, x)). A count with any hour
missing is missing (D25), and so is a mean over hours none of which qualify (there's nothing to average).
`daily_features` groups a point's hourly series into those windows; the grid rollup (`agdata.daily`) and a point's
rollup (`agdata.point`) cut the windows with `agdata.timezones` and call the same reducers. Humidity thresholds use RH
from temperature and dew point.
"""

import warnings
from collections.abc import Mapping

import numpy as np

# Windows within a day, by the clock hour each ends at (readings stamped after the hour the day before, through it)
EVENING_HOUR = 18  # the day from 6 pm
OVERNIGHT_HOUR = 12  # noon to noon
NIGHT = (18, 6)  # night: readings after 18:00 through 06:00
TAR_SPOT_NIGHT = (19, 6)  # tar spot's: after 19:00 through 06:00
MIN_HOURS = 20  # a day's min, mean or max needs this many of its hours (D25); counts and sums need them all


def hours_at_or_above(values: np.ndarray, threshold: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.where(np.isnan(values).any(axis=0), np.nan, (values >= threshold).sum(axis=0))


def hours_below(values: np.ndarray, threshold: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.where(np.isnan(values).any(axis=0), np.nan, (values < threshold).sum(axis=0))


def mean_where(values: np.ndarray, condition: np.ndarray) -> np.ndarray:
    """Mean of `values` over the hours where `condition` holds; NaN if any hour is missing or none qualify."""
    values = np.asarray(values, dtype=float)
    missing = np.isnan(values).any(axis=0) | np.isnan(condition).any(axis=0)
    mask = np.nan_to_num(condition) > 0
    count = mask.sum(axis=0)
    with np.errstate(invalid="ignore"):
        mean = np.where(mask, np.nan_to_num(values), 0).sum(axis=0) / count
    return np.where(missing | (count == 0), np.nan, mean)


# Pecan scab hours (Oklahoma Mesonet's Pecan Scab Advisor): RH at or above 90% and temperature at or above 70 °F
SCAB_C = (70 - 32) / 1.8

# The disease models' RH ≥ 90% comes from in-field stations (Wallin, TOMCAST, Windels, BOTCAST, Webster's fits).
# Gridded RH reads a little low where it matters: against 80 Wisconet stations (2025–2026, May–September), the
# archive's RH ≥ 88% counts as many hours as the stations' RH ≥ 90%, and as their leaf-wet hours (D50;
# docs/validation-humidity.md). So the "RH ≥ 90%" features are counted at 88% on our hourly data, and keep their
# names: they mean what a station would have counted at 90%. Pecan scab's threshold is the Oklahoma Mesonet's,
# not checked against its stations, so it stays at 90%.
STATION_RH_90_AS_GRIDDED = 88.0


def hours_humid_and_warm(temperature_c, rh_percent, rh_from: float, temperature_from_c: float) -> np.ndarray:
    """Hours with RH at or above `rh_from` and temperature at or above `temperature_from_c` together."""
    t, rh = np.asarray(temperature_c, dtype=float), np.asarray(rh_percent, dtype=float)
    missing = np.isnan(t).any(axis=0) | np.isnan(rh).any(axis=0)
    return np.where(missing, np.nan, ((rh >= rh_from) & (t >= temperature_from_c)).sum(axis=0))


def in_hours(local_hour: np.ndarray, after: int, through: int) -> np.ndarray:
    """Readings stamped after clock hour `after` through `through`, across midnight (`(18, 6)`: 19:00–06:00)."""
    hour = np.asarray(local_hour)
    return (hour > after) | (hour <= through)


def calendar_features(
    temperature_c: np.ndarray,
    rh_percent: np.ndarray,
    dew_point_c: np.ndarray | None = None,
    rh_90_at: float | None = None,
) -> dict[str, np.ndarray]:
    """Features over a calendar day's hours (with the dew point, its depression's daily statistics too). `rh_90_at`
    is the RH the "≥ 90%" hours are counted at: `STATION_RH_90_AS_GRIDDED` on gridded RH (the default), 90 on a
    station's own (a POSTed run, D58)."""
    rh_90 = STATION_RH_90_AS_GRIDDED if rh_90_at is None else rh_90_at
    extra = {} if dew_point_c is None else daily_statistics("dew_point_depression", temperature_c - dew_point_c)
    return extra | {
        "hours_temperature_over_20c": hours_at_or_above(temperature_c, 20),
        "hours_temperature_over_30c": hours_at_or_above(temperature_c, 30),
        "hours_rh_under_70": hours_below(rh_percent, 70),
        "hours_rh_over_80": hours_at_or_above(rh_percent, 80),
        "hours_rh_over_90": hours_at_or_above(rh_percent, rh_90),
        "hours_rh_over_90_temperature_over_70f": hours_humid_and_warm(temperature_c, rh_percent, 90, SCAB_C),
    }


# Potato tubers die after enough hours below 27 °F (the potato volunteer model, Kirk and Wharton, MSU)
KILLING_SOIL_C = (27 - 32) / 1.8


EIGHT_INCHES_CM = 20.32


def soil_between(depth_cm: float, upper_cm: float, upper_c, lower_cm: float, lower_c) -> np.ndarray:
    """Soil temperature at `depth_cm`, linear between two stored levels (HRRR stores 4, 10 and 30 cm)."""
    weight = (depth_cm - upper_cm) / (lower_cm - upper_cm)
    return (1 - weight) * np.asarray(upper_c, dtype=float) + weight * np.asarray(lower_c, dtype=float)


def soil_features(soil_4cm_c: np.ndarray, soil_10cm_c: np.ndarray, soil_30cm_c: np.ndarray) -> dict[str, np.ndarray]:
    """Hours of a calendar day with soil below 27 °F at 2, 4 and 8 in: HRRR's 4 and 10 cm levels (D9), and 8 in
    (20.3 cm) interpolated between 10 and 30 cm."""
    eight_inches = soil_between(EIGHT_INCHES_CM, 10, soil_10cm_c, 30, soil_30cm_c)
    return {
        "hours_soil_4cm_below_27f": hours_below(soil_4cm_c, KILLING_SOIL_C),
        "hours_soil_10cm_below_27f": hours_below(soil_10cm_c, KILLING_SOIL_C),
        "hours_soil_8in_below_27f": hours_below(eight_inches, KILLING_SOIL_C),
    }


def evening_features(
    temperature_c: np.ndarray, rh_percent: np.ndarray, local_hour: np.ndarray, rh_90_at: float | None = None
) -> dict[str, np.ndarray]:
    """Features over a day from 6 pm (readings 19:00 the evening before through 18:00), with its night's and tar
    spot's night's hours; `local_hour` is each reading's clock hour. `rh_90_at` as in `calendar_features`."""
    rh = np.asarray(rh_percent, dtype=float)
    shape = (-1, *([1] * (rh.ndim - 1)))
    night = in_hours(local_hour, *NIGHT).reshape(shape)
    tar_spot_night = in_hours(local_hour, *TAR_SPOT_NIGHT).reshape(shape)
    missing = np.isnan(rh).any(axis=0)
    rh_90 = STATION_RH_90_AS_GRIDDED if rh_90_at is None else rh_90_at
    out = {}
    for threshold, counted_at in ((80, 80.0), (90, rh_90)):
        wet = np.where(np.isnan(rh), np.nan, rh >= counted_at)
        out[f"hours_rh_over_{threshold}_from_6pm"] = hours_at_or_above(rh, counted_at)
        out[f"hours_rh_over_{threshold}_night"] = np.where(missing, np.nan, ((rh >= counted_at) & night).sum(axis=0))
        out[f"temperature_mean_rh_over_{threshold}_from_6pm"] = mean_where(temperature_c, wet)
    out["hours_rh_over_90_7pm_to_6am"] = np.where(missing, np.nan, ((rh >= rh_90) & tar_spot_night).sum(axis=0))
    return out


def overnight_features(temperature_c: np.ndarray) -> dict[str, np.ndarray]:
    """The overnight minimum, over noon the day before to noon (readings 13:00–12:00); missing with fewer than
    MIN_HOURS of them (D25)."""
    return {"air_temperature_min_overnight": daily_statistics("air_temperature", temperature_c)["air_temperature_min"]}


def across_days(daily: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Features that look across days, from the daily ones (days on axis 0)."""
    hot = np.asarray(daily["hours_temperature_over_30c"], dtype=float)
    hot_day = np.where(np.isnan(hot), np.nan, hot >= 4)
    hot_past_5 = np.full(hot.shape, np.nan)
    for n in range(hot.shape[0]):
        window = hot_day[max(0, n - 4) : n + 1]
        # Any hot day makes it hot; otherwise a missing day leaves it unknown (as R's any() with NA)
        hot_past_5[n] = np.where((window == 1).any(axis=0), 1, np.where(np.isnan(window).any(axis=0), np.nan, 0))
    under_70 = np.asarray(daily["hours_rh_under_70"], dtype=float)
    precip = np.asarray(daily["precipitation_sum"], dtype=float)
    dry = np.where(np.isnan(under_70) | np.isnan(precip), np.nan, (under_70 >= 6) & (precip < 1))
    return {"hot_past_5_days": hot_past_5, "dry": dry}


def daily_features(
    local_time: np.ndarray,
    temperature_c: np.ndarray,
    rh_percent: np.ndarray,
    precipitation_mm: np.ndarray,
    midnight_ends_day: bool = True,
    dew_point_c: np.ndarray | None = None,
    soil_4cm_c: np.ndarray | None = None,
    soil_10cm_c: np.ndarray | None = None,
    soil_30cm_c: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """A point's hourly series (local datetime64 instants, consecutive, whole days) → (dates, features per date).
    A partial first or last day counts only the hours it's given (the grid's rollup reads every day's full window,
    so its partial days are missing instead).

    v2's calendar day is the hours ending 01:00–24:00 (`midnight_ends_day`), as in the stores: the reading at
    midnight closes the day, and an hour's precip, stamped at its end, falls in the day it fell. The Crop Risk
    Tool counts the instants 00:00–23:00 (pass False to match it), which puts each day's precip an hour early.
    The day from 6 pm and the overnight window follow the module's rule whatever `midnight_ends_day` is.
    """
    t = np.asarray(local_time, dtype="datetime64[h]")
    dates = (t - np.timedelta64(1 if midnight_ends_day else 0, "h")).astype("datetime64[D]")
    from_6pm = (t + np.timedelta64(23 - EVENING_HOUR, "h")).astype("datetime64[D]")
    overnight = (t + np.timedelta64(23 - OVERNIGHT_HOUR, "h")).astype("datetime64[D]")
    hour = (t - t.astype("datetime64[D]")).astype(int)
    days = np.unique(dates)
    out: dict[str, list] = {}
    for day in days:
        today = dates == day
        dew_point = None if dew_point_c is None else dew_point_c[today]
        features = calendar_features(temperature_c[today], rh_percent[today], dew_point)
        features["precipitation_sum"] = _sum_all(precipitation_mm[today])
        features |= daily_statistics("air_temperature", temperature_c[today])
        if soil_4cm_c is not None and soil_10cm_c is not None and soil_30cm_c is not None:
            features |= soil_features(soil_4cm_c[today], soil_10cm_c[today], soil_30cm_c[today])
        evening = from_6pm == day
        features |= evening_features(temperature_c[evening], rh_percent[evening], hour[evening])
        features |= overnight_features(temperature_c[overnight == day])
        for name, value in features.items():
            out.setdefault(name, []).append(value)
    daily = {name: np.array(values, dtype=float) for name, values in out.items()}
    return days, daily | across_days(daily)


def daily_statistics(name: str, hours: np.ndarray) -> dict[str, np.ndarray]:
    """`{name}_min`, `_mean`, `_max` over a day's hours, NaN with fewer than MIN_HOURS of them (D25)."""
    hours = np.asarray(hours, dtype=float)
    if hours.shape[0] == 0:  # a window the series doesn't reach (a point's first or last day)
        return {f"{name}_{stat}": np.full(hours.shape[1:], np.nan) for stat in ("min", "mean", "max")}
    enough = np.isfinite(hours).sum(axis=0) >= MIN_HOURS
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells
        stats = {"min": np.nanmin(hours, axis=0), "mean": np.nanmean(hours, axis=0), "max": np.nanmax(hours, axis=0)}
    return {f"{name}_{stat}": np.where(enough, value, np.nan) for stat, value in stats.items()}


def _sum_all(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.where(np.isnan(values).any(axis=0), np.nan, np.nansum(values, axis=0))
