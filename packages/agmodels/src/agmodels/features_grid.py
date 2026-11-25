"""Daily features' costliest parts over the grid in compiled passes (Numba), for the grid's rollup (`agdata.daily`).

- `scab_features_grid`: apple scab's features (`features.scab_features`, with `apple_scab.infection_periods`) for
  every day of a rollup pass at once. The NumPy version runs a day's 120-hour window as whole-array steps (an hour's
  step is a dozen full-size temporaries), so a block's month took ~17 s of its ~52 s rollup; this takes ~2 s on one
  core. Each day's window is its own run, as there: a wet period isn't carried from one window to the next (D96).
- `cci_grid`: the Cattle Comfort Index of every hour (`livestock.cci`), ~7 s of a block's month in NumPy, ~1 s here:
  the time is in its seven calls to exp, log and sqrt, five of which depend on the wind alone, and the archive's wind
  comes in steps of 0.1 m/s, so a thread keeps the wind term by value.

The NumPy functions stay the reference, and what points use; these repeat them term for term in float64, and give the
same bits (tests hold them to it; the whole rollup of a launch-box block-month was compared variable by variable)."""

import math

import numba
import numpy as np

from agmodels import features, livestock
from agmodels.models import apple_scab

NAMES = (
    "scab_infection",
    "scab_wet_hours",
    "scab_wet_temperature",
    "scab_period_truncated",
    "precipitation_7am_to_7pm",
    "precipitation_8pm_to_6am",
    "temperature_mean_rain_7am_to_7pm",
)

_TABLE = np.ascontiguousarray(apple_scab._HOURS_NEEDED, dtype=np.float64)


@numba.njit(cache=True, inline="always")
def _hours_needed(mean_f: float, table) -> float:
    t = math.floor(mean_f + 0.5)
    if math.isfinite(t) and t >= 0 and t < table.shape[0]:
        return table[int(t)]
    return np.inf


CHUNK = 256  # neighbouring cells a thread runs together, so each hour's reads are contiguous


@numba.njit(cache=True, parallel=True)
def _kernel(t, rh, rain, starts, day, night, window, rain_mm, wet_rh, join, table, out) -> None:
    cells = t.shape[1]
    days = starts.shape[0]
    day_start = window - 24
    for chunk in numba.prange((cells + CHUNK - 1) // CHUNK):
        a = chunk * CHUNK
        m = min(a + CHUNK, cells) - a
        # each cell's state through a day's window: apple_scab.infection_periods and scab_features, term for term
        missing = np.empty(m, dtype=np.bool_)
        in_period = np.empty(m, dtype=np.bool_)
        last_wet = np.empty(m, dtype=np.int64)
        hours = np.empty(m, dtype=np.float64)
        t_sum = np.empty(m, dtype=np.float64)
        start = np.empty(m, dtype=np.int64)
        reached = np.empty(m, dtype=np.bool_)
        infection = np.empty(m, dtype=np.bool_)
        day_rain = np.empty(m, dtype=np.float64)
        day_missing = np.empty(m, dtype=np.bool_)
        night_rain = np.empty(m, dtype=np.float64)
        night_missing = np.empty(m, dtype=np.bool_)
        rainy_sum = np.empty(m, dtype=np.float64)
        rainy_count = np.empty(m, dtype=np.int64)
        rainy_missing = np.empty(m, dtype=np.bool_)
        for d in range(days):
            s = starts[d]
            missing[:] = False
            in_period[:] = False
            last_wet[:] = -10_000
            hours[:] = 0.0
            t_sum[:] = 0.0
            start[:] = 0
            reached[:] = False
            infection[:] = False
            day_rain[:] = 0.0
            day_missing[:] = False
            night_rain[:] = 0.0
            night_missing[:] = False
            rainy_sum[:] = 0.0
            rainy_count[:] = 0
            rainy_missing[:] = False
            for k in range(window):
                in_day = day[d, k]
                in_night = night[d, k]
                for j in range(m):
                    c = a + j
                    tk = np.float64(t[s + k, c])
                    rk = np.float64(rain[s + k, c])
                    hk = np.float64(rh[s + k, c])
                    if math.isnan(tk) or math.isnan(rk) or math.isnan(hk):
                        missing[j] = True
                    raining = rk >= rain_mm
                    wet = raining or hk >= wet_rh
                    begins = (not in_period[j]) and raining
                    if begins and k - last_wet[j] >= join:
                        hours[j] = 0.0
                        t_sum[j] = 0.0
                        start[j] = k
                        reached[j] = False
                    period = in_period[j] or begins
                    counted = period and wet
                    in_period[j] = period and wet
                    if counted:
                        hours[j] = hours[j] + 1.0
                        t_sum[j] = t_sum[j] + (tk * 1.8 + 32)
                        last_wet[j] = k
                        enough = hours[j] >= _hours_needed(t_sum[j] / hours[j], table)
                        if enough and not reached[j] and k >= day_start:
                            infection[j] = True
                        reached[j] = reached[j] or enough
                    if in_day:
                        if math.isnan(rk):
                            day_missing[j] = True
                            rainy_missing[j] = True
                        else:
                            day_rain[j] = day_rain[j] + rk
                        if math.isnan(tk):
                            rainy_missing[j] = True
                        elif rk >= rain_mm:
                            rainy_sum[j] = rainy_sum[j] + tk
                            rainy_count[j] += 1
                    if in_night:
                        if math.isnan(rk):
                            night_missing[j] = True
                        else:
                            night_rain[j] = night_rain[j] + rk
            for j in range(m):
                c = a + j
                touched = last_wet[j] >= day_start
                if missing[j]:
                    out[0, d, c] = np.nan
                    out[1, d, c] = np.nan
                    out[2, d, c] = np.nan
                    out[3, d, c] = np.nan
                else:
                    out[0, d, c] = 1.0 if infection[j] else 0.0
                    out[1, d, c] = hours[j] if touched else 0.0
                    out[2, d, c] = ((t_sum[j] / (hours[j] if hours[j] > 0 else 1.0)) - 32) / 1.8 if touched else np.nan
                    out[3, d, c] = 1.0 if (touched and start[j] < join) else 0.0
                out[4, d, c] = np.nan if day_missing[j] else day_rain[j]
                out[5, d, c] = np.nan if night_missing[j] else night_rain[j]
                n_rainy = rainy_count[j]
                out[6, d, c] = np.nan if (rainy_missing[j] or n_rainy == 0) else rainy_sum[j] / n_rainy


def scab_features_grid(
    temperature_c: np.ndarray,
    rh_percent: np.ndarray,
    precipitation_mm: np.ndarray,
    starts: np.ndarray,
    local_hours: list[np.ndarray],
    dtype: type = np.float32,
) -> dict[str, np.ndarray]:
    """Apple scab's daily features (`features.scab_features`) for many days at once: the hours (hours, y, x), each
    day's window the WINDOW_HOURS hours from `starts[d]`, whose readings' clock hours are `local_hours[d]`. Each
    feature (days, y, x) as `dtype` (float32 for the grid's stores; float64 for a point's, as `scab_features` gives),
    equal to `scab_features` on each day's window cast to it."""
    window = features.SCAB_HOURS
    shape = temperature_c.shape
    n = shape[0]
    cells = int(np.prod(shape[1:], dtype=np.int64))
    t = np.ascontiguousarray(temperature_c).reshape(n, cells)
    rh = np.ascontiguousarray(rh_percent).reshape(n, cells)
    rain = np.ascontiguousarray(precipitation_mm).reshape(n, cells)
    if rh.shape != t.shape or rain.shape != t.shape:
        raise ValueError(
            f"the hours differ in shape: {temperature_c.shape}, {rh_percent.shape}, {precipitation_mm.shape}"
        )
    begins = np.asarray(starts, dtype=np.int64)
    if len(local_hours) != begins.size or any(np.asarray(h).shape != (window,) for h in local_hours):
        raise ValueError(f"each day needs its window's {window} clock hours")
    if begins.size and (begins.min() < 0 or begins.max() + window > n):
        raise ValueError("a day's window reaches outside the hours")
    masks = [features.scab_rain_hours(h) for h in local_hours]
    day = np.array([m[0] for m in masks], dtype=np.bool_).reshape(begins.size, window)
    night = np.array([m[1] for m in masks], dtype=np.bool_).reshape(begins.size, window)
    out = np.empty((len(NAMES), begins.size, cells), dtype=dtype)
    if begins.size and cells:
        _kernel(
            t,
            rh,
            rain,
            begins,
            day,
            night,
            window,
            apple_scab.RAIN_MM,
            apple_scab.WET_RH,
            apple_scab.JOIN_HOURS,
            _TABLE,
            out,
        )
    return {name: out[k].reshape(begins.size, *shape[1:]) for k, name in enumerate(NAMES)}


_LOG_10M = float(np.log(67.8 * 10 - 5.42))  # weather.wind_speed_2m's divisor


SLOTS = 8192  # the wind term's memo, per thread: stored wind comes in steps of 0.1 m/s, so ~750 values at most


@numba.njit(cache=True, inline="always")
def _wind_term(w: float, ln_0_3: float) -> float:
    ws = max(w * 4.87 / _LOG_10M, 0.0)
    ws2 = ws * ws
    factor = math.exp(-0.45 * math.log(2.26 * ws + 0.23))
    exponent = factor * (2.9 + 1.14e-6 * ws2 * math.sqrt(ws) + 2 * math.log(2.26 * ws + 0.33) / ln_0_3)
    return -6.56 * math.exp(-exponent) - 0.00566 * ws2 + 3.33


@numba.njit(cache=True, parallel=True)
def _cci_kernel(t_c, rh, ws10, rad_w, ln_0_3, out) -> None:
    n = t_c.size
    for chunk in numba.prange((n + CHUNK * 64 - 1) // (CHUNK * 64)):
        # The wind term (five of the index's seven calls to exp, log and sqrt) depends on the wind alone, so it's
        # kept by value: a slot holds the last wind seen there and its term, the same bits as computing it again.
        keys = np.full(SLOTS, np.nan)
        terms = np.empty(SLOTS)
        for k in range(chunk * CHUNK * 64, min((chunk + 1) * CHUNK * 64, n)):
            t = np.float64(t_c[k])
            h = np.float64(rh[k])
            w = np.float64(ws10[k])
            r = np.float64(rad_w[k])
            if math.isnan(t) or math.isnan(h) or math.isnan(w) or math.isnan(r):
                out[k] = np.nan
                continue
            if abs(w) < 1e6:
                slot = int(w * 64.0) & (SLOTS - 1)
                if keys[slot] == w:
                    wind = terms[slot]
                else:
                    wind = _wind_term(w, ln_0_3)
                    keys[slot] = w
                    terms[slot] = wind
            else:
                wind = _wind_term(w, ln_0_3)
            rad = max(r, 0.0)
            t2 = t * t
            humidity = math.exp(0.00182 * h + 1.8e-5 * t * h) * (0.000054 * t2 + 0.00192 * t - 0.0246) * (h - 30)
            radiation = 0.0076 * rad - 0.00002 * rad * t + 0.00005 * t2 * math.sqrt(rad) + 0.1 * t - 2
            out[k] = t + humidity + wind + radiation


def cci_grid(temperature_c, rh_percent, wind_speed_10m_m_s, shortwave_w_m2) -> np.ndarray:
    """`livestock.cci` (°C, float64) of arrays of one shape, in one pass; NaN where any input is missing."""
    arrays = [np.ascontiguousarray(a) for a in (temperature_c, rh_percent, wind_speed_10m_m_s, shortwave_w_m2)]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays):
        raise ValueError(f"the inputs differ in shape: {[a.shape for a in arrays]}")
    out = np.empty(shape, dtype=np.float64)
    if out.size:
        t, rh, wind, sun = (a.reshape(-1) for a in arrays)
        _cci_kernel(t, rh, wind, sun, livestock.LN_0_3, out.reshape(-1))
    return out


def warm() -> None:
    """Load (or compile) the kernels for the inputs a point's rollup (float64) and the grid's (float32) give them, so a
    server process's first point request doesn't wait ~0.5–0.8 s for them (`api.layermaps.warm_kernels`)."""
    window = features.SCAB_HOURS
    for dtype in (np.float32, np.float64):
        hours = np.zeros((window, 1, 1), dtype=dtype)
        scab_features_grid(
            temperature_c=hours,
            rh_percent=hours,
            precipitation_mm=hours,
            starts=np.zeros(1, dtype=np.int64),
            local_hours=[np.arange(window) % 24],
            dtype=dtype,
        )
        cci_grid(hours, hours, hours, hours)
