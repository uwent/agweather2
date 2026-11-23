"""Packed int16 values decoded to float32 in one parallel pass (Numba): `Variable.decode(dtype=np.float32)` for a
map's many days. The arithmetic is decode's, in float64 (the value times the scale, plus the offset), rounded to
float32 once; a season over the launch box is ~170 M values a variable, ~1.4 s on one core through NumPy.

And the other way, `encode_int16` for `Variable.encode` of many values (every write of a store): encode's arithmetic
term for term (float64, less the offset, over the scale, rounded half to even), in one pass rather than NumPy's
several full-size temporaries and boolean-indexed copies (240 hours over the launch window, 139 M values: 14 s)."""

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


@numba.njit(cache=True, parallel=True)
def _encode(values, scale: float, offset: float, fill: int, top: int, out) -> int:
    flat, flat_out = values.ravel(), out.ravel()
    bad = 0
    for k in numba.prange(flat.size):
        value = np.float64(flat[k])
        if not np.isfinite(value):
            flat_out[k] = fill
            continue
        code = np.rint((value - offset) / scale)
        if code <= fill or code > top:
            bad += 1
            flat_out[k] = fill
        else:
            flat_out[k] = np.int16(code)
    return bad


def encode_int16(values: np.ndarray, scale: float, offset: float) -> tuple[np.ndarray, int]:
    """`values` (float32 or float64) packed as `Variable.encode` packs them, and how many fell outside int16's range
    (written as FILL here; `encode` refuses them)."""
    if values.dtype not in (np.float32, np.float64):
        values = values.astype(np.float64)
    values = np.ascontiguousarray(values)
    out = np.empty(values.shape, dtype=np.int16)
    bad = _encode(values, float(scale), float(offset), int(FILL), int(np.iinfo(np.int16).max), out)
    return out, int(bad)


def warm() -> None:
    """Load (or compile) the kernel, so a server process's first map doesn't wait for it."""
    decode_float32(np.zeros((1, 1, 1), dtype=np.int16), 0.1, 0.0)
