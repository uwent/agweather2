"""Estimates across gaps, for running totals only (D25). Stored hours and days stay raw.

Hourly ET0 where an hour is missing: shortwave from the clear-sky curve scaled by the cloudiness (Rs/Rso) of the
nearest usable daytime hours, interpolated in time, and temperature, dew point, wind and pressure interpolated
across short gaps; then the FAO-56 hourly chain on the filled inputs. Following the clear-sky curve keeps the
day's shape and season (a fitted sine doesn't), and the neighbouring cloudiness carries over how cloudy it was.
"""

import numpy as np

from agdata.qc import fill_short_gaps
from agmodels.weather import (
    CLOUDINESS_MIN_ELEVATION_DEG,
    elevation_from_pressure_m,
    et0_hourly_series,
    extraterrestrial_radiation_hourly,
    solar_elevation_deg,
)

MAX_INPUT_GAP_HOURS = 6  # temperature, dew point, wind and pressure
MAX_CLOUDINESS_GAP_HOURS = 30  # Rs/Rso, which is only measurable in daytime, so it spans a night and a day


def clear_sky_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, pressure_kpa) -> np.ndarray:
    """Rso as a mean flux over the hour ending at each time, W/m² (FAO-56 eq. 37), time on axis 0."""
    extra = (1,) * np.ndim(latitude_deg)
    times = np.asarray(hour_end, dtype="datetime64[s]").reshape(-1, *extra)
    ra = extraterrestrial_radiation_hourly(times, latitude_deg, longitude_deg)
    return (0.75 + 2e-5 * elevation_from_pressure_m(pressure_kpa)) * ra / 0.0036


def estimate_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, shortwave_w_m2, pressure_kpa) -> np.ndarray:
    """Shortwave with missing hours estimated as Rso × the interpolated Rs/Rso (NaN where none is in reach)."""
    rs = np.asarray(shortwave_w_m2, dtype=float)
    rso = clear_sky_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, pressure_kpa)
    extra = (1,) * np.ndim(latitude_deg)
    mid = np.asarray(hour_end, dtype="datetime64[s]").reshape(-1, *extra) - np.timedelta64(1800, "s")
    usable = (solar_elevation_deg(mid, latitude_deg, longitude_deg) > CLOUDINESS_MIN_ELEVATION_DEG) & np.isfinite(rs)
    ratio = np.where(usable & (rso > 0), np.clip(rs / np.where(rso > 0, rso, 1), 0, 1.2), np.nan)
    ratio, _ = fill_short_gaps(ratio, MAX_CLOUDINESS_GAP_HOURS)
    estimate = np.where(rso > 0, ratio * rso, 0.0)
    return np.where(np.isfinite(rs), rs, estimate)


def estimate_et0_hourly_mm(
    hour_end,
    latitude_deg,
    longitude_deg,
    et0_mm,
    temperature_c,
    dew_point_c,
    wind_speed_m_s,
    pressure_kpa,
    shortwave_w_m2,
) -> np.ndarray:
    """Hourly ET0 with missing hours estimated (NaN where an input can't be); hours with ET0 are kept."""
    filled = [
        fill_short_gaps(np.asarray(v, dtype=float), MAX_INPUT_GAP_HOURS)[0]
        for v in (temperature_c, dew_point_c, wind_speed_m_s, pressure_kpa)
    ]
    temperature, dew_point, wind, pressure = filled
    shortwave = estimate_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, shortwave_w_m2, pressure)
    with np.errstate(invalid="ignore"):
        estimate = et0_hourly_series(
            hour_end, latitude_deg, longitude_deg, temperature, dew_point, wind, pressure, shortwave
        )
    et0 = np.asarray(et0_mm, dtype=float)
    return np.where(np.isfinite(et0), et0, estimate)
