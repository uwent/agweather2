"""Packed int16 values decoded to float32 in one parallel pass (Numba): `Variable.decode(dtype=np.float32)` for a
map's many days. The arithmetic is decode's, in float64 (the value times the scale, plus the offset), rounded to
float32 once; a season over the launch box is ~170 M values a variable, ~1.4 s on one core through NumPy."""

import numba
import numpy as np

from agdata.catalog import FILL


@numba.njit(cache=True, parallel=True)
def _decode(packed, scale: float, offset: float, fill: int, out) -> None:
    flat, flat_out = packed.ravel(), out.ravel()
    for k in numba.prange(flat.size):
        code = flat[k]
        if code == fill:
            flat_out[k] = np.nan
        else:
            value = np.float64(code)
            value *= scale
            value += offset
            flat_out[k] = value


def decode_float32(packed: np.ndarray, scale: float, offset: float) -> np.ndarray:
    packed = np.ascontiguousarray(packed, dtype=np.int16)
    out = np.empty(packed.shape, dtype=np.float32)
    _decode(packed, float(scale), float(offset), int(FILL), out)
    return out


def warm() -> None:
    """Load (or compile) the kernel, so a server process's first map doesn't wait for it."""
    decode_float32(np.zeros((1, 1, 1), dtype=np.int16), 0.1, 0.0)
