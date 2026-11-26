"""The standard normal distribution's CDF, elementwise (NaN where the argument isn't finite).

NumPy has no `erf`, so the reference is `math.erf` value by value (`normal_cdf_reference`), which a point uses. Over the
grid that's ~1 µs a value: apple scab's ascospore maturity, a season of a 256-cell block, took ~10 s in it. Many
values go through a Numba kernel instead (`PARALLEL_SIZE`), the same arithmetic term for term (`math.erf` is the C
library's in both), with a parity test against the reference."""

import math

import numba
import numpy as np

PARALLEL_SIZE = 4096  # values: fewer go through the reference, so a point never loads Numba


def _cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2))) if math.isfinite(z) else math.nan


normal_cdf_reference = np.vectorize(_cdf, otypes=[float])


@numba.vectorize(["float64(float64)"], cache=True)
def _cdf_kernel(z):
    if not math.isfinite(z):
        return math.nan
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def normal_cdf(z) -> np.ndarray:
    """Φ(z), as float64; NaN where z is NaN or infinite."""
    z = np.asarray(z, dtype=float)
    if z.size >= PARALLEL_SIZE:
        with np.errstate(invalid="ignore"):  # NaN where z isn't finite, as the reference gives
            return np.asarray(_cdf_kernel(z))
    return normal_cdf_reference(z)
