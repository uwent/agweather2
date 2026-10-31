"""Filling a forecast's hours between its output steps (Phase 4 A), time on axis 0.

NBM gives most fields hourly for two days, then every 3 and 6 hours; models read hours. These fill the hours
between steps, never past the last one or across a gap longer than a 6-hour step, and report which hours they
filled. Temperature and dew point follow a monotone cubic (PCHIP: no overshoot past the steps, so no invented
extremes); wind, gust and cloud are linear; direction goes through unit vectors; shortwave follows the clear-sky
curve scaled by each solar day's clearness.
"""

import warnings

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


WINDOW_HOURS = 12  # NBM's TMAX covers the 12 hours ending at its step


def reach_window_max(values: np.ndarray, window_max: np.ndarray, hours: int = WINDOW_HOURS) -> np.ndarray:
    """Hourly temperatures (time on axis 0) with each window's warm part raised or lowered so its max meets the
    window max given at the window's last step (NaN elsewhere): a bump over the straight line between the
    window's first and last hours, scaled by how far each hour stands above that line, so nothing moves at the
    window's edges and the day keeps its shape. Windows without a target, or flat ones, are left as they are."""
    out = np.array(values, dtype=float)
    targets = np.asarray(window_max, dtype=float)
    present = np.isfinite(targets).reshape(targets.shape[0], -1).any(axis=1)
    for end in np.flatnonzero(present):
        if end < hours - 1:
            continue
        window = slice(end - hours + 1, end + 1)
        seg = out[window]
        line = seg[0] + (seg[-1] - seg[0]) * (np.arange(hours) / (hours - 1)).reshape(-1, *([1] * (seg.ndim - 1)))
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells
            rise = seg - line
            warmest = np.nanmax(seg, axis=0)
            delta = targets[end] - warmest
            # Scaled to the warmest hour's own rise, so it moves by the whole difference and no hour passes it
            at_warmest = np.take_along_axis(rise, np.nanargmax(np.nan_to_num(seg, nan=-np.inf), axis=0)[None], 0)[0]
            reference = np.where(at_warmest > 0.3, at_warmest, np.nanmax(rise, axis=0))
            shape = np.where(reference > 0.3, np.clip(rise / np.where(reference > 0.3, reference, 1), 0, 1), 0.0)
            moved = seg + np.nan_to_num(shape) * np.nan_to_num(delta)
            # Lowering: no moved hour stays above it (the window's ends don't move, even if they're above it)
            moved = np.where((delta < 0) & (shape > 0), np.fmin(moved, targets[end]), moved)
        out[window] = np.where(np.isfinite(delta), moved, seg)
    return out


def reach_window_min(values: np.ndarray, window_min: np.ndarray, hours: int = WINDOW_HOURS) -> np.ndarray:
    """`reach_window_max` for a window's cold part: each window's coldest hours moved so its min meets the target
    given at the window's last step, the window's edges left where they are."""
    return -reach_window_max(-np.asarray(values, dtype=float), -np.asarray(window_min, dtype=float), hours)
