import numpy as np
import pytest

from agmodels import weather as w

# FAO-56 Example 19: N'Diaye, Senegal (16°13'N, 16°15'W, 8 m), 1 October. The example's clock uses a 15°W
# standard meridian (Lz = 15), so its clock time is UTC - 1 h: its 14-15 h is the hour ending 16:00 UTC
LAT, LON, Z = 16 + 13 / 60, -(16 + 15 / 60), 8
DAY_END = np.datetime64("2026-10-01T16:00")  # the example's 14-15 h
NIGHT_END = np.datetime64("2026-10-01T04:00")  # the example's 02-03 h
PRESSURE = 101.3 * ((293 - 0.0065 * Z) / 293) ** 5.26  # eq. 7: 101.2 kPa


def test_humidity_terms_match_example_19():
    assert w.saturation_vapor_pressure_kpa(38) == pytest.approx(6.625, abs=0.001)
    assert w.svp_slope_kpa_per_c(38) == pytest.approx(0.358, abs=0.001)
    assert w.psychrometric_constant_kpa_per_c(PRESSURE) == pytest.approx(0.0673, abs=0.0001)
    assert w.saturation_vapor_pressure_kpa(28) == pytest.approx(3.780, abs=0.001)


def test_relative_humidity_from_dew_point():
    assert w.relative_humidity_percent(20, 20) == pytest.approx(100)
    assert w.relative_humidity_percent(20, 25) == pytest.approx(100)  # supersaturated → 100
    assert w.relative_humidity_percent(30, 10) == pytest.approx(28.9, abs=0.1)
    np.testing.assert_allclose(w.relative_humidity_percent(np.array([20.0, np.nan]), 10), [52.5, np.nan], atol=0.1)


def test_extraterrestrial_radiation_matches_example_19():
    assert w.extraterrestrial_radiation_hourly(DAY_END, LAT, LON) == pytest.approx(3.543, abs=0.01)
    assert w.extraterrestrial_radiation_hourly(NIGHT_END, LAT, LON) == 0


def test_day_hour_matches_example_19():
    ea = 0.52 * w.saturation_vapor_pressure_kpa(38)  # RH 52 %
    assert ea == pytest.approx(3.445, abs=0.001)
    ra = w.extraterrestrial_radiation_hourly(DAY_END, LAT, LON)
    rso = (0.75 + 2e-5 * Z) * ra
    assert rso == pytest.approx(2.658, abs=0.01)
    rn = w.net_radiation_hourly_mj(2.450, 2.450 / rso, 38, ea)
    assert rn == pytest.approx(1.749, abs=0.005)
    et0 = w.et0_hourly_mm(38, ea, 3.3, rn, 0.1 * rn, PRESSURE)
    assert et0 == pytest.approx(0.63, abs=0.005)


def test_night_hour_matches_example_19():
    ea = 0.90 * w.saturation_vapor_pressure_kpa(28)  # RH 90 %
    rn = w.net_radiation_hourly_mj(0.0, 0.8, 28, ea)
    assert rn == pytest.approx(-0.100, abs=0.002)
    assert w.et0_hourly_mm(28, ea, 1.9, rn, 0.5 * rn, PRESSURE) == pytest.approx(0.0, abs=0.005)


def test_wind_and_elevation_conversions():
    assert w.wind_speed_2m(1.0) == pytest.approx(0.748, abs=0.001)
    assert w.elevation_from_pressure_m(PRESSURE) == pytest.approx(Z, abs=0.5)


def test_cloudiness_ratio_carries_the_last_daytime_value_overnight():
    rs = np.array([0.0, 2.0, 1.0, 0.0, 0.0])
    rso = np.array([0.0, 2.5, 2.0, 0.1, 0.0])
    elevation = np.array([-10, 40, 30, 5, -20])
    np.testing.assert_allclose(w.cloudiness_ratio(rs, rso, elevation), [0.8, 0.8, 0.5, 0.5, 0.5])


def test_solar_elevation_at_noon_and_midnight():
    # Madison near the June solstice: about 90 - 43.07 + 23.4 = 70° at solar noon, below the horizon at midnight
    noon = w.solar_elevation_deg(np.datetime64("2026-06-21T18:00"), 43.07, -89.40)  # about 12:00 solar time
    assert noon == pytest.approx(70.3, abs=1.0)
    assert w.solar_elevation_deg(np.datetime64("2026-06-21T06:00"), 43.07, -89.40) < -20


def test_series_over_a_grid_broadcasts_and_sums_to_a_sensible_day():
    # A clear July day in Madison on a 2 x 3 grid of identical cells: daily ET0 near 5-7 mm
    hours = np.arange(
        np.datetime64("2026-07-15T06:00"), np.datetime64("2026-07-16T06:00"), np.timedelta64(1, "h")
    ) + np.timedelta64(1, "h")
    local = (np.arange(24) + 1 + 6 - 5) % 24  # CDT hour ending
    temp = 22 + 8 * np.sin((local - 9) / 24 * 2 * np.pi)
    elevation = w.solar_elevation_deg(hours - np.timedelta64(30, "m"), 43.07, -89.40)
    shortwave = np.clip(1000 * np.sin(np.radians(np.maximum(elevation, 0))), 0, None) * 0.8
    grid = (2, 3)
    expand = lambda a: np.broadcast_to(np.asarray(a, dtype=float)[:, None, None], (24, *grid))  # noqa: E731
    lat, lon = np.full(grid, 43.07), np.full(grid, -89.40)
    et0 = w.et0_hourly_series(
        hours,
        lat,
        lon,
        expand(temp),
        expand(temp - 8),
        expand(np.full(24, 3.0)),
        expand(np.full(24, 98.0)),
        expand(shortwave),
    )
    assert et0.shape == (24, *grid)
    daily = et0.sum(axis=0)
    assert np.allclose(daily, daily[0, 0])
    assert 4.5 < daily[0, 0] < 7.5
    # Peaks in the early afternoon: index k is the hour ending 07+k UTC, so 11-14 is 13:00-16:00 CDT
    assert et0[:, 0, 0].argmax() in range(11, 15)


def test_missing_inputs_give_missing_et0():
    out = w.et0_hourly_mm(np.nan, 1.0, 2.0, 0.5, 0.05, 98.0)
    assert np.isnan(out)
