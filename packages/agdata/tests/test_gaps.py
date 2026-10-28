import numpy as np
import pytest

from agdata.gaps import clear_sky_shortwave_w_m2, estimate_et0_hourly_mm, estimate_shortwave_w_m2
from agmodels.weather import et0_hourly_series

LAT, LON = np.array([43.07]), np.array([-89.4])  # Madison
HOURS = np.arange("2025-07-01T01", "2025-07-04T01", dtype="datetime64[h]").astype("datetime64[s]")
PRESSURE = np.full((HOURS.size, 1), 98.5)
NOON_CDT = slice(41, 44)  # hours ending 17-19 UTC on July 2


def test_a_cloudy_afternoon_keeps_its_cloudiness():
    rso = clear_sky_shortwave_w_m2(HOURS, LAT, LON, PRESSURE)
    rs = 0.6 * rso
    rs[NOON_CDT] = np.nan
    estimate = estimate_shortwave_w_m2(HOURS, LAT, LON, rs, PRESSURE)
    np.testing.assert_allclose(estimate[NOON_CDT], 0.6 * rso[NOON_CDT], rtol=1e-6)
    assert rso[NOON_CDT].min() > 700  # midsummer midday


def test_a_missing_night_is_dark():
    rs = clear_sky_shortwave_w_m2(HOURS, LAT, LON, PRESSURE)
    night = slice(4, 8)  # hours ending 05-08 UTC: midnight to 3 am CDT
    rs[night] = np.nan
    np.testing.assert_array_equal(estimate_shortwave_w_m2(HOURS, LAT, LON, rs, PRESSURE)[night], 0)


def test_et0_with_missing_hours_is_close_to_the_truth():
    n = np.arange(HOURS.size)
    temperature = (22 + 7 * np.sin(2 * np.pi * (n - 15) / 24))[:, None]
    dew_point = np.full_like(temperature, 15.0)
    wind = np.full_like(temperature, 3.0)
    shortwave = 0.8 * clear_sky_shortwave_w_m2(HOURS, LAT, LON, PRESSURE)
    truth = et0_hourly_series(HOURS, LAT, LON, temperature, dew_point, wind, PRESSURE, shortwave)

    # An URMA hour and an HRRR hour missing: inputs and ET0 gone over the midday hours
    gaps = [a.copy() for a in (truth, temperature, dew_point, wind, PRESSURE, shortwave)]
    for a in gaps:
        a[NOON_CDT] = np.nan
    estimate = estimate_et0_hourly_mm(HOURS, LAT, LON, *gaps)
    assert np.isfinite(estimate).all()
    assert estimate[NOON_CDT].sum() == pytest.approx(truth[NOON_CDT].sum(), rel=0.05)
    np.testing.assert_array_equal(estimate[:40], truth[:40])  # hours with ET0 are kept


def test_et0_stays_missing_when_inputs_are_out_of_reach():
    temperature = np.full((HOURS.size, 1), 20.0)
    temperature[10:30] = np.nan  # 20 hours: longer than the input gaps it bridges
    et0 = np.full_like(temperature, np.nan)
    shortwave = clear_sky_shortwave_w_m2(HOURS, LAT, LON, PRESSURE)
    estimate = estimate_et0_hourly_mm(
        HOURS, LAT, LON, et0, temperature, temperature - 5, temperature * 0 + 2, PRESSURE, shortwave
    )
    assert np.isnan(estimate[10:30]).all()
