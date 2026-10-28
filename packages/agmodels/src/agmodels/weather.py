"""Weather physics: humidity, sun geometry and FAO-56 hourly grass reference evapotranspiration.

Pure NumPy functions; they broadcast, so the same call works on a point's series or the whole grid. Units are
in the names where they aren't SI-obvious. Equation numbers are from FAO Irrigation and Drainage Paper 56:
Allen, R. G., Pereira, L. S., Raes, D. and Smith, M. (1998), "Crop evapotranspiration: guidelines for
computing crop water requirements", https://www.fao.org/4/x0490e/x0490e00.htm. Time arrays are UTC
`datetime64`; an hourly value at time t covers the hour ending at t.
"""

import numpy as np

SOLAR_CONSTANT = 0.0820  # MJ m-2 min-1
STEFAN_BOLTZMANN_HOURLY = 2.043e-10  # MJ K-4 m-2 h-1 (FAO-56 eq. 39 for hourly steps)
ALBEDO_GRASS = 0.23
# ASCE-EWRI (2005): below this sun elevation Rs/Rso is unreliable, so the last value above it carries on
CLOUDINESS_MIN_ELEVATION_DEG = 17.2
DEFAULT_RS_RSO = 0.8  # before any daytime value to carry (FAO-56 Example 19's night assumption)


# Humidity


def saturation_vapor_pressure_kpa(temperature_c):
    """e°(T), FAO-56 eq. 11 (the Tetens/Magnus form over water)."""
    t = np.asarray(temperature_c, dtype=float)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def vapor_pressure_kpa(dew_point_c):
    """Actual vapor pressure from dew point, FAO-56 eq. 14."""
    return saturation_vapor_pressure_kpa(dew_point_c)


def relative_humidity_percent(temperature_c, dew_point_c):
    """RH from temperature and dew point, 0–100 (a dew point above the temperature counts as saturated)."""
    rh = 100 * vapor_pressure_kpa(dew_point_c) / saturation_vapor_pressure_kpa(temperature_c)
    return np.clip(rh, 0, 100)


def svp_slope_kpa_per_c(temperature_c):
    """Δ, the slope of the saturation vapor pressure curve, FAO-56 eq. 13."""
    t = np.asarray(temperature_c, dtype=float)
    return 4098 * saturation_vapor_pressure_kpa(t) / (t + 237.3) ** 2


def psychrometric_constant_kpa_per_c(pressure_kpa):
    """γ, FAO-56 eq. 8."""
    return 0.000665 * np.asarray(pressure_kpa, dtype=float)


def elevation_from_pressure_m(pressure_kpa):
    """Elevation from surface pressure, inverting FAO-56 eq. 7 (for Rso where no elevation grid is at hand)."""
    p = np.asarray(pressure_kpa, dtype=float)
    return (293 - 293 * (p / 101.3) ** (1 / 5.26)) / 0.0065


def wind_speed_2m(wind_speed_10m):
    """Wind at 2 m from wind at 10 m over short grass, FAO-56 eq. 47."""
    return np.asarray(wind_speed_10m, dtype=float) * 4.87 / np.log(67.8 * 10 - 5.42)


# Sun


def _day_of_year(times) -> np.ndarray:
    days = np.asarray(times, dtype="datetime64[D]")
    return (days - days.astype("datetime64[Y]")).astype(int) + 1


def _hours_utc(times) -> np.ndarray:
    t = np.asarray(times, dtype="datetime64[s]")
    return (t - t.astype("datetime64[D]")).astype(float) / 3600


def _solar_terms(times, longitude_deg):
    """Declination (eq. 24), inverse relative Earth-Sun distance (eq. 23) and solar hour angle (eq. 31)."""
    j = _day_of_year(times)
    declination = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    b = 2 * np.pi * (j - 81) / 364
    seasonal_correction_h = 0.1645 * np.sin(2 * b) - 0.1255 * np.cos(b) - 0.025 * np.sin(b)  # eq. 32-33
    # UTC clock time plus the longitude's offset is local solar time (Lz = 0 in eq. 31, east positive)
    solar_time_h = _hours_utc(times) + np.asarray(longitude_deg, dtype=float) / 15 + seasonal_correction_h
    hour_angle = np.pi / 12 * (solar_time_h - 12)
    return declination, dr, hour_angle


def solar_elevation_deg(times, latitude_deg, longitude_deg):
    """The sun's elevation above the horizon at each time (instantaneous)."""
    times = np.asarray(times, dtype="datetime64[s]")
    declination, _, hour_angle = _solar_terms(times, longitude_deg)
    lat = np.radians(latitude_deg)
    sin_elevation = np.sin(lat) * np.sin(declination) + np.cos(lat) * np.cos(declination) * np.cos(hour_angle)
    return np.degrees(np.arcsin(np.clip(sin_elevation, -1, 1)))


def extraterrestrial_radiation_hourly(hour_end, latitude_deg, longitude_deg):
    """Ra over the hour ending at each time, MJ m-2 h-1, FAO-56 eq. 28 (0 when the sun is down)."""
    mid = np.asarray(hour_end, dtype="datetime64[s]") - np.timedelta64(1800, "s")
    declination, dr, omega = _solar_terms(mid, longitude_deg)
    lat = np.radians(latitude_deg)
    sunset = np.arccos(np.clip(-np.tan(lat) * np.tan(declination), -1, 1))  # eq. 25
    omega1 = np.clip(omega - np.pi / 24, -sunset, sunset)  # eq. 29-30, limited to the daylight hours
    omega2 = np.clip(omega + np.pi / 24, -sunset, sunset)
    ra = (
        12
        * 60
        / np.pi
        * SOLAR_CONSTANT
        * dr
        * (
            (omega2 - omega1) * np.sin(lat) * np.sin(declination)
            + np.cos(lat) * np.cos(declination) * (np.sin(omega2) - np.sin(omega1))
        )
    )
    return np.maximum(ra, 0)


# Reference evapotranspiration


def cloudiness_ratio(rs, rso, sun_elevation_deg, axis: int = 0):
    """Rs/Rso for net longwave (0.25–1), carried forward along the time axis while the sun is too low to measure it.

    Hours before the first usable daytime value take DEFAULT_RS_RSO.
    """
    rs, rso = np.asarray(rs, dtype=float), np.asarray(rso, dtype=float)
    usable = (np.asarray(sun_elevation_deg) > CLOUDINESS_MIN_ELEVATION_DEG) & (rso > 0) & np.isfinite(rs)
    ratio = np.where(usable, np.clip(rs / np.where(rso > 0, rso, 1), 0.25, 1.0), np.nan)
    ratio = np.moveaxis(np.broadcast_to(ratio, np.broadcast_shapes(ratio.shape, usable.shape)).copy(), axis, 0)
    last = np.full(ratio.shape[1:], DEFAULT_RS_RSO)
    for k in range(ratio.shape[0]):
        last = np.where(np.isnan(ratio[k]), last, ratio[k])
        ratio[k] = last
    return np.moveaxis(ratio, 0, axis)


def et0_hourly_mm(
    temperature_c,
    vapor_pressure_kpa_,
    wind_speed_2m_m_s,
    net_radiation_mj,
    soil_heat_flux_mj,
    pressure_kpa,
):
    """FAO-56 Penman-Monteith grass reference ET0 for one hour, mm (eq. 53). Negative results (dew) become 0."""
    t = np.asarray(temperature_c, dtype=float)
    delta = svp_slope_kpa_per_c(t)
    gamma = psychrometric_constant_kpa_per_c(pressure_kpa)
    u2 = np.asarray(wind_speed_2m_m_s, dtype=float)
    deficit = saturation_vapor_pressure_kpa(t) - np.asarray(vapor_pressure_kpa_, dtype=float)
    numerator = (
        0.408 * delta * (np.asarray(net_radiation_mj) - soil_heat_flux_mj) + gamma * 37 / (t + 273) * u2 * deficit
    )
    return np.maximum(numerator / (delta + gamma * (1 + 0.34 * u2)), 0)


def net_radiation_hourly_mj(rs_mj, rs_rso, temperature_c, vapor_pressure_kpa_):
    """Rn = Rns − Rnl over an hour, MJ m-2 h-1 (eq. 38-40, hourly σ)."""
    t_k = np.asarray(temperature_c, dtype=float) + 273.16
    rns = (1 - ALBEDO_GRASS) * np.asarray(rs_mj, dtype=float)
    rnl = (
        STEFAN_BOLTZMANN_HOURLY
        * t_k**4
        * (0.34 - 0.14 * np.sqrt(np.asarray(vapor_pressure_kpa_, dtype=float)))
        * (1.35 * np.asarray(rs_rso) - 0.35)
    )
    return rns - rnl


def et0_hourly_series(
    hour_end,
    latitude_deg,
    longitude_deg,
    temperature_c,
    dew_point_c,
    wind_speed_10m_m_s,
    pressure_kpa,
    shortwave_w_m2,
):
    """Hourly ET0 (mm) for series with time on axis 0: the whole FAO-56 hourly chain from stored variables.

    `hour_end` is 1-D (time); latitude and longitude broadcast against the remaining axes (a point, or y and x).
    Shortwave is the hour's mean flux (W/m²). Night soil heat flux is 0.5 Rn, day 0.1 Rn (eq. 45-46).
    """
    hour_end = np.asarray(hour_end, dtype="datetime64[s]")
    extra = (1,) * np.ndim(latitude_deg)
    times = hour_end.reshape(-1, *extra)
    rs = np.asarray(shortwave_w_m2, dtype=float) * 0.0036  # W/m² over an hour → MJ/m²
    ra = extraterrestrial_radiation_hourly(times, latitude_deg, longitude_deg)
    rso = (0.75 + 2e-5 * elevation_from_pressure_m(pressure_kpa)) * ra  # eq. 37
    mid = times - np.timedelta64(1800, "s")
    elevation = solar_elevation_deg(mid, latitude_deg, longitude_deg)
    ea = vapor_pressure_kpa(dew_point_c)
    rn = net_radiation_hourly_mj(rs, cloudiness_ratio(rs, rso, elevation), temperature_c, ea)
    g = np.where(ra > 0, 0.1, 0.5) * rn
    return et0_hourly_mm(temperature_c, ea, wind_speed_2m(wind_speed_10m_m_s), rn, g, pressure_kpa)
