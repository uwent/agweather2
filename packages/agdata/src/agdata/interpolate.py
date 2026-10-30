"""Filling a forecast's hours between its output steps (Phase 4 A), time on axis 0.

NBM gives most fields hourly for two days, then every 3 and 6 hours; models read hours. These fill the hours
between steps, never past the last one or across a gap longer than a 6-hour step, and report which hours they
filled. Temperature and dew point follow a monotone cubic (PCHIP: no overshoot past the steps, so no invented
extremes); wind, gust and cloud are linear; direction goes through unit vectors; shortwave follows the clear-sky
curve scaled by each solar day's clearness.
"""

import numpy as np

from agdata.gaps import clear_sky_shortwave_w_m2
from agdata.qc import fill_short_gaps

MAX_STEP_GAP_HOURS = 5  # the hours between two 6-hourly steps
MIN_SAMPLES_PER_DAY = 4  # DSWRF samples in a solar day (a 6-hourly day has 4)


def steps_with_data(values: np.ndarray) -> np.ndarray:
    """Indices along axis 0 where any cell has a value (a forecast's steps are the same for every cell)."""
    finite = np.isfinite(values)
    return np.flatnonzero(finite.reshape(finite.shape[0], -1).any(axis=1))


def pchip(values: np.ndarray, max_gap: int = MAX_STEP_GAP_HOURS) -> tuple[np.ndarray, np.ndarray]:
    """Monotone cubic interpolation (Fritsch and Carlson 1980, with Fritsch and Butland's derivatives, as SciPy's
    PchipInterpolator) across interior gaps of up to `max_gap` steps. Returns the filled copy and a mask of the
    filled values."""
    values = np.array(values, dtype=float)
    known = steps_with_data(values)
    filled = np.zeros(values.shape, dtype=bool)
    if len(known) < 2:
        return values, filled
    x = known.astype(float)
    y = values[known]
    extra = (1,) * (values.ndim - 1)
    h = np.diff(x).reshape(-1, *extra)
    delta = np.diff(y, axis=0) / h
    slope = np.zeros_like(y)
    if len(known) > 2:
        h0, h1 = h[:-1], h[1:]
        w1, w2 = 2 * h1 + h0, h1 + 2 * h0
        d0, d1 = delta[:-1], delta[1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            harmonic = (w1 + w2) / (w1 / d0 + w2 / d1)
        slope[1:-1] = np.where(d0 * d1 > 0, harmonic, 0.0)
    slope[0], slope[-1] = delta[0], delta[-1]
    for k in range(len(known) - 1):
        a, b = known[k], known[k + 1]
        if b - a < 2 or b - a - 1 > max_gap:
            continue
        span = float(b - a)
        t = (np.arange(a + 1, b) - a).reshape(-1, *extra) / span
        h00, h10 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t
        h01, h11 = -2 * t**3 + 3 * t**2, t**3 - t**2
        inside = h00 * y[k] + h10 * span * slope[k] + h01 * y[k + 1] + h11 * span * slope[k + 1]
        gap = values[a + 1 : b]
        fill = np.isnan(gap) & np.isfinite(inside)
        values[a + 1 : b] = np.where(fill, inside, gap)
        filled[a + 1 : b] = fill
    return values, filled


def linear(values: np.ndarray, max_gap: int = MAX_STEP_GAP_HOURS) -> tuple[np.ndarray, np.ndarray]:
    """Linear interpolation across interior gaps of up to `max_gap` steps."""
    return fill_short_gaps(values, max_gap)


def direction_deg(values: np.ndarray, max_gap: int = MAX_STEP_GAP_HOURS) -> tuple[np.ndarray, np.ndarray]:
    """Wind direction (degrees) through its unit vector, so 350° and 10° meet at 0°, not 180°."""
    radians = np.deg2rad(np.asarray(values, dtype=float))
    east, filled = fill_short_gaps(np.sin(radians), max_gap)
    north, _ = fill_short_gaps(np.cos(radians), max_gap)
    with np.errstate(invalid="ignore"):
        degrees = np.rad2deg(np.arctan2(east, north)) % 360
    return np.where(np.isfinite(east) & np.isfinite(north), degrees, np.nan), filled


def shortwave_hourly_w_m2(
    valid_times, samples_w_m2: np.ndarray, latitude_deg, longitude_deg, pressure_kpa
) -> tuple[np.ndarray, np.ndarray]:
    """Hourly mean shortwave from NBM's DSWRF, through each solar day's clearness (time on axis 0).

    NBM's DSWRF isn't a value for the hour: against HRRR's hourly means it fits means over the 1 to 6 hours
    before the valid time, the window changing with lead and time of day (it blends models that average over
    different periods). Days are robust to that: solar midnight is dark, so each solar day's mean of the samples,
    over the clear-sky mean at the same times, is its clearness; each hour gets it times its clear-sky mean. On
    six 2026 runs over Wisconsin this was closer to HRRR's daily totals than reading the samples as 3-hour means
    (lead day 0: MAE 2.2 against 2.4 MJ/m²; bias over 11 days −1.2 against −2.5 MJ/m²). A day needs
    `MIN_SAMPLES_PER_DAY` samples; otherwise its daylight hours are missing. Returns the hourly means and a mask
    of the estimated hours (every hour: none is a measured hourly value).
    """
    times = np.asarray(valid_times, dtype="datetime64[s]")
    samples = np.asarray(samples_w_m2, dtype=float)
    rso = clear_sky_shortwave_w_m2(times, latitude_deg, longitude_deg, pressure_kpa)
    day = solar_day(times, longitude_deg)
    clearness = np.full(samples.shape, np.nan)
    have = np.isfinite(samples)
    for d in np.unique(day):
        in_day = day == d
        sampled = in_day & have
        count = sampled.sum(axis=0)
        flux = np.where(sampled, samples, 0.0).sum(axis=0)
        clear = np.where(sampled, rso, 0.0).sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where((count >= MIN_SAMPLES_PER_DAY) & (clear > 0), np.clip(flux / clear, 0, 1.2), np.nan)
        clearness = np.where(in_day, ratio, clearness)
    hourly = np.where(rso > 0, clearness * rso, 0.0)
    return hourly, np.isfinite(hourly)


def solar_day(hour_end, longitude_deg) -> np.ndarray:
    """Each hour's solar day (days since 1970-01-01, from solar midnight by longitude), time on axis 0."""
    times = np.asarray(hour_end, dtype="datetime64[s]")
    extra = (1,) * np.ndim(longitude_deg)
    hours = (times.astype("int64") / 3600.0).reshape(-1, *extra)
    # An hour belongs to the day its middle falls in
    return np.floor((hours - 0.5 + np.asarray(longitude_deg) / 15) / 24).astype(int)
