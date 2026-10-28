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

from collections.abc import Mapping

import numpy as np

NIGHT_FIRST_HOUR, NIGHT_LAST_HOUR = 20, 6  # local clock hours, inclusive


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


def is_night(local_hour: np.ndarray) -> np.ndarray:
    hour = np.asarray(local_hour)
    return (hour >= NIGHT_FIRST_HOUR) | (hour <= NIGHT_LAST_HOUR)


def calendar_features(temperature_c: np.ndarray, rh_percent: np.ndarray) -> dict[str, np.ndarray]:
    """Features over a calendar day's hours."""
    return {
        "hours_temperature_over_20c": hours_at_or_above(temperature_c, 20),
        "hours_temperature_over_30c": hours_at_or_above(temperature_c, 30),
        "hours_rh_under_70": hours_below(rh_percent, 70),
        "hours_rh_over_80": hours_at_or_above(rh_percent, 80),
        "hours_rh_over_90": hours_at_or_above(rh_percent, 90),
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
    precip = np.asarray(daily["precipitation_mm"], dtype=float)
    dry = np.where(np.isnan(under_70) | np.isnan(precip), np.nan, (under_70 >= 6) & (precip < 1))
    return {"hot_past_5_days": hot_past_5, "dry": dry}


def daily_features(
    local_time: np.ndarray, temperature_c: np.ndarray, rh_percent: np.ndarray, precipitation_mm: np.ndarray
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """A point's hourly series (local datetime64 instants, consecutive) → (dates, features per date).

    An instant at local midnight belongs to the day it starts, as in the Crop Risk Tool's Open-Meteo frames; pass
    instants an hour earlier for hour-ending data that should count midnight with the day before.
    """
    t = np.asarray(local_time, dtype="datetime64[h]")
    dates = t.astype("datetime64[D]")
    from_8pm = (t + np.timedelta64(4, "h")).astype("datetime64[D]")
    hour = (t - dates).astype(int)
    days = np.unique(dates)
    out: dict[str, list] = {}
    for day in days:
        today = dates == day
        features = calendar_features(temperature_c[today], rh_percent[today])
        features["precipitation_mm"] = _sum_all(precipitation_mm[today])
        evening = from_8pm == day
        features |= from_8pm_features(temperature_c[evening], rh_percent[evening], is_night(hour[evening]))
        for name, value in features.items():
            out.setdefault(name, []).append(value)
    daily = {name: np.array(values, dtype=float) for name, values in out.items()}
    return days, daily | across_days(daily)


def _sum_all(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.where(np.isnan(values).any(axis=0), np.nan, np.nansum(values, axis=0))
