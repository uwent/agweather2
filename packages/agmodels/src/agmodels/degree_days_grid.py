"""Degree days over the grid in one parallel pass (Numba), for a custom degree-day map (§3: a season over the box
in < 2 s; docs/architecture.md §5's "arbitrary ones run on the fly with Numba").

The same three methods as `agmodels.degree_days`, which stays the reference (and what points use): the formulas are
the same, term for term, in float64, from float32 daily min and max in °C to float32 degree days in °F·d. The NumPy
versions make several full-size temporaries per call (a season over the launch box is ~170 M cell-days); this makes
none and uses every core. Missing or crossed temperatures (min above max) give NaN, as there."""

import math

import numba
import numpy as np

METHOD_CODES = {"sine": 0, "average": 1, "modified": 2}


@numba.njit(cache=True, inline="always")
def _sine_above(lo: float, hi: float, threshold: float) -> float:
    mean = (lo + hi) / 2
    if hi <= threshold:
        return 0.0
    if lo < threshold:  # crosses: the sine's area above the threshold
        amplitude = (hi - lo) / 2
        x = (threshold - mean) / amplitude
        theta = math.asin(min(max(x, -1.0), 1.0))
        return ((mean - threshold) * (math.pi / 2 - theta) + amplitude * math.cos(theta)) / math.pi
    return mean - threshold


@numba.njit(cache=True, inline="always")
def _one(lo_c: float, hi_c: float, method: int, base_f: float, upper_f: float, has_upper: bool) -> float:
    """A cell-day's degree days (°F·d, float64), NaN where either is missing or the min is above the max."""
    lo = np.float64(lo_c) * 1.8 + 32
    hi = np.float64(hi_c) * 1.8 + 32
    if math.isnan(lo) or math.isnan(hi) or lo > hi:
        return np.nan
    cap = upper_f if has_upper else np.inf
    if method == 0:
        dd = _sine_above(lo, hi, base_f)
        if has_upper:
            dd = dd - _sine_above(lo, hi, upper_f)
    elif method == 1:
        dd = (min(lo, cap) + min(hi, cap)) / 2 - base_f
    else:
        dd = (min(max(lo, base_f), cap) + min(hi, cap)) / 2 - base_f
    return max(dd, 0.0)


@numba.njit(cache=True, parallel=True)
def _kernel(lo_c, hi_c, method: int, base_f: float, upper_f: float, has_upper: bool, out) -> None:
    flat_lo, flat_hi, flat_out = lo_c.ravel(), hi_c.ravel(), out.ravel()
    for k in numba.prange(flat_lo.size):
        flat_out[k] = _one(flat_lo[k], flat_hi[k], method, base_f, upper_f, has_upper)


CHUNK = 4096  # cells a thread sums at a time, day by day (a day's run of them is contiguous)


@numba.njit(cache=True, parallel=True)
def _sum_kernel(lo_c, hi_c, method: int, base_f: float, upper_f: float, has_upper: bool, total, usable) -> None:
    days, cells = lo_c.shape
    for c in numba.prange((cells + CHUNK - 1) // CHUNK):
        a = c * CHUNK
        b = min(a + CHUNK, cells)
        for d in range(days):
            for k in range(a, b):
                if math.isnan(lo_c[d, k]) or math.isnan(hi_c[d, k]):
                    continue
                # each day as `degree_days_c` gives it, summed in order (a min above the max adds NaN, as there)
                total[k] += np.float64(np.float32(_one(lo_c[d, k], hi_c[d, k], method, base_f, upper_f, has_upper)))
                usable[k] += 1


def degree_days_c(
    min_c: np.ndarray, max_c: np.ndarray, method: str, base_f: float, upper_f: float | None
) -> np.ndarray:
    """Each cell-day's degree days (°F·d, float32) by `method` from daily min and max in °C (any shape, the same
    for both); NaN where either is missing or the min is above the max."""
    lo = np.ascontiguousarray(min_c, dtype=np.float32)
    hi = np.ascontiguousarray(max_c, dtype=np.float32)
    if lo.shape != hi.shape:
        raise ValueError(f"min and max differ in shape: {lo.shape} and {hi.shape}")
    out = np.empty(lo.shape, dtype=np.float32)
    _kernel(lo, hi, METHOD_CODES[method], float(base_f), float(upper_f or 0.0), upper_f is not None, out)
    return out


def degree_days_sum_c(
    min_c: np.ndarray, max_c: np.ndarray, method: str, base_f: float, upper_f: float | None
) -> tuple[np.ndarray, np.ndarray]:
    """The sum over days (axis 0) of each cell's degree days (°F·d, float64) and its count of usable days (both
    temperatures known), each (y, x), from daily min and max in °C: what `degree_days_c` then a sum over the usable
    days gives, to the bit (NaN where a usable day's min is above its max),
    without the (days, y, x) degree days or a float64 copy of them (over the launch box a season is ~600 MB of
    them and 1.2 GB of copy). The sum is 0 where no day is usable."""
    lo = np.ascontiguousarray(min_c, dtype=np.float32)
    hi = np.ascontiguousarray(max_c, dtype=np.float32)
    if lo.shape != hi.shape:
        raise ValueError(f"min and max differ in shape: {lo.shape} and {hi.shape}")
    n = lo.shape[0]
    total = np.zeros(lo[0].size if n else 0, dtype=np.float64)
    usable = np.zeros(total.size, dtype=np.int32)
    if n:
        _sum_kernel(
            lo.reshape(n, -1),
            hi.reshape(n, -1),
            METHOD_CODES[method],
            float(base_f),
            float(upper_f or 0.0),
            upper_f is not None,
            total,
            usable,
        )
    return total.reshape(lo.shape[1:]), usable.reshape(lo.shape[1:])


def warm() -> None:
    """Load (or compile) the kernel for float32 input, so a server process's first map doesn't wait ~0.5 s for it."""
    cell = np.zeros((1, 1, 1), dtype=np.float32)
    for method in METHOD_CODES:
        degree_days_c(cell, cell, method, 50.0, 86.0)
        degree_days_c(cell, cell, method, 50.0, None)
        degree_days_sum_c(cell, cell, method, 50.0, 86.0)
        degree_days_sum_c(cell, cell, method, 50.0, None)
