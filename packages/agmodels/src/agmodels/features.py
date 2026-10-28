"""Daily features: what the models read beyond daily min, mean and max, computed from hours (PLAN.md Phase 3 B).

Hourly-native, following the Crop Risk Tool's `build_daily` (its fits used these windows):

- the calendar day (local);
- night: the hours 20:00–06:59 local by the clock (the tar spot coefficients were fitted on it);
- the day from 8 pm: 20:00 the evening before through 19:59 (so an overnight wet period isn't split at
  midnight). Features over it end in `_from_8pm`.

The reducers take one window's hours on axis 0 (a point (hours,) or the grid (hours, y, x)). A count with any
hour missing is missing (D25), and so is a mean over hours none of which qualify (there's nothing to average).
`daily_features` groups a point's hourly series into those windows; the grid rollup (`agdata.daily`) groups by
each cell's zone and calls the same reducers. Humidity thresholds use RH from temperature and dew point.
"""

import warnings
from collections.abc import Mapping

import numpy as np

NIGHT_FIRST_HOUR, NIGHT_LAST_HOUR = 20, 6  # local clock hours, inclusive
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


def hours_humid_and_warm(temperature_c, rh_percent, rh_from: float, temperature_from_c: float) -> np.ndarray:
    """Hours with RH at or above `rh_from` and temperature at or above `temperature_from_c` together."""
    t, rh = np.asarray(temperature_c, dtype=float), np.asarray(rh_percent, dtype=float)
    missing = np.isnan(t).any(axis=0) | np.isnan(rh).any(axis=0)
    return np.where(missing, np.nan, ((rh >= rh_from) & (t >= temperature_from_c)).sum(axis=0))


def is_night(local_hour: np.ndarray) -> np.ndarray:
    hour = np.asarray(local_hour)
    return (hour >= NIGHT_FIRST_HOUR) | (hour <= NIGHT_LAST_HOUR)


def calendar_features(
    temperature_c: np.ndarray, rh_percent: np.ndarray, dew_point_c: np.ndarray | None = None
) -> dict[str, np.ndarray]:
    """Features over a calendar day's hours (with the dew point, its depression's daily statistics too)."""
    extra = {} if dew_point_c is None else daily_statistics("dew_point_depression", temperature_c - dew_point_c)
    return extra | {
        "hours_temperature_over_20c": hours_at_or_above(temperature_c, 20),
        "hours_temperature_over_30c": hours_at_or_above(temperature_c, 30),
        "hours_rh_under_70": hours_below(rh_percent, 70),
        "hours_rh_over_80": hours_at_or_above(rh_percent, 80),
        "hours_rh_over_90": hours_at_or_above(rh_percent, 90),
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


def from_8pm_features(temperature_c: np.ndarray, rh_percent: np.ndarray, night: np.ndarray) -> dict[str, np.ndarray]:
    """Features over a day from 8 pm (20:00 the evening before through 19:59); `night` marks its night hours
    (bool, broadcast against the hours axis)."""
    rh = np.asarray(rh_percent, dtype=float)
    night = np.asarray(night, dtype=bool).reshape(-1, *([1] * (rh.ndim - 1)))
    out = {}
    for threshold in (80, 90):
        wet = np.where(np.isnan(rh), np.nan, rh >= threshold)
        out[f"hours_rh_over_{threshold}_from_8pm"] = hours_at_or_above(rh, threshold)
        out[f"hours_rh_over_{threshold}_night"] = np.where(
            np.isnan(rh).any(axis=0), np.nan, ((rh >= threshold) & night).sum(axis=0)
        )
        out[f"temperature_mean_rh_over_{threshold}_from_8pm"] = mean_where(temperature_c, wet)
    return out


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
    """A point's hourly series (local datetime64 instants, consecutive) → (dates, features per date).

    v2's calendar day is the hours ending 01:00–24:00 (`midnight_ends_day`), as in the stores: the reading at
    midnight closes the day, and an hour's precip, stamped at its end, falls in the day it fell. The Crop Risk
    Tool counts the instants 00:00–23:00 (pass False to match it), which puts each day's precip an hour early.
    """
    t = np.asarray(local_time, dtype="datetime64[h]")
    dates = (t - np.timedelta64(1 if midnight_ends_day else 0, "h")).astype("datetime64[D]")
    from_8pm = (t + np.timedelta64(4, "h")).astype("datetime64[D]")
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
        evening = from_8pm == day
        features |= from_8pm_features(temperature_c[evening], rh_percent[evening], is_night(hour[evening]))
        for name, value in features.items():
            out.setdefault(name, []).append(value)
    daily = {name: np.array(values, dtype=float) for name, values in out.items()}
    return days, daily | across_days(daily)


def daily_statistics(name: str, hours: np.ndarray) -> dict[str, np.ndarray]:
    """`{name}_min`, `_mean`, `_max` over a day's hours, NaN with fewer than MIN_HOURS of them (D25)."""
    hours = np.asarray(hours, dtype=float)
    enough = np.isfinite(hours).sum(axis=0) >= MIN_HOURS
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells
        stats = {"min": np.nanmin(hours, axis=0), "mean": np.nanmean(hours, axis=0), "max": np.nanmax(hours, axis=0)}
    return {f"{name}_{stat}": np.where(enough, value, np.nan) for stat, value in stats.items()}


def _sum_all(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.where(np.isnan(values).any(axis=0), np.nan, np.nansum(values, axis=0))
