"""Test helpers shared by agmodels' tests (pytest's importlib mode keeps test files from importing each other):
a plausible Wisconsin daily series for every input any model reads, from September 2024 to February 2026."""

from datetime import date, timedelta

import numpy as np

FIRST = date(2024, 9, 1)
DAYS = 520  # to early February 2026
DATES = [FIRST + timedelta(days=k) for k in range(DAYS)]
LATITUDE = 43.1


def year_of_weather() -> dict[str, np.ndarray]:
    """A plausible Wisconsin daily series for every input any model reads."""
    rng = np.random.default_rng(3)
    doy = np.array([d.timetuple().tm_yday for d in DATES], dtype=float)
    season = -np.cos(2 * np.pi * (doy - 15) / 365)  # −1 mid-January, +1 mid-July
    mean = 8 + 16 * season + rng.normal(0, 2.5, DAYS)
    rh_mean = 72 + 8 * rng.standard_normal(DAYS)
    hours_humid = np.clip(np.round(6 + 4 * season + 3 * rng.standard_normal(DAYS)), 0, 24)
    soil = 8 + 12 * season
    return {
        "air_temperature_mean": mean,
        "air_temperature_min": mean - 6,
        "air_temperature_max": mean + 6,
        "dew_point_min": mean - 9,
        "dew_point_depression_max": np.full(DAYS, 9.0),
        "dew_point_depression_mean": np.full(DAYS, 4.0),
        "relative_humidity_mean": np.clip(rh_mean, 30, 100),
        "relative_humidity_max": np.clip(rh_mean + 20, 30, 100),
        "precipitation_sum": np.where(rng.random(DAYS) < 0.3, rng.exponential(6, DAYS), 0.0),
        "wind_speed_max": np.full(DAYS, 6.0),
        "hours_rh_over_80": hours_humid + 3,
        "hours_rh_over_90": hours_humid,
        "hours_rh_over_90_from_8pm": hours_humid,
        "hours_rh_over_90_night": np.minimum(hours_humid, 10),
        "hours_rh_over_90_temperature_over_70f": np.where(mean > 21, hours_humid / 2, 0),
        "hours_rh_under_70": 24 - hours_humid - 3,
        "hours_temperature_over_30c": np.where(mean + 6 > 30, 3.0, 0.0),
        "temperature_mean_rh_over_90_from_8pm": mean - 2,
        "hours_soil_4cm_below_27f": np.where(soil - 4 < -3, 12.0, 0.0),
        "hours_soil_10cm_below_27f": np.where(soil - 2 < -3, 8.0, 0.0),
        "hours_soil_8in_below_27f": np.where(soil < -3, 4.0, 0.0),
        "soil_temperature_4cm_min": soil - 4,
        "soil_temperature_10cm_min": soil - 2,
        "soil_temperature_30cm_min": soil,
    }


WEATHER = year_of_weather()
