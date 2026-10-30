"""Estimates across gaps in a model's daily inputs (D45), by each variable's method.

The runner fills inputs before a model runs, and reports which days it filled, so a page can say "includes N
estimated days"; the inputs layer it shows keeps the raw values with their gaps. Only interior gaps are filled
(a value on each side): the days past the end of the data are the future, not a gap.

- `interpolate`: linear in time across gaps up to MAX_GAP_DAYS (temperature, humidity, wind, cloud, shortwave,
  ET0, soil and hour counts). Longer gaps stay missing.
- `zero`: no rain where there's no data (precipitation is never estimated), across gaps of any length.
"""

from collections.abc import Mapping
from typing import Literal

import numpy as np

GapFill = Literal["interpolate", "zero"]
MAX_GAP_DAYS = 7  # as the running totals' bridges (D25)


def fill_short_gaps(values: np.ndarray, max_gap: int) -> tuple[np.ndarray, np.ndarray]:
    """Linearly interpolates interior runs of NaN up to `max_gap` steps long, along axis 0.

    Gaps at the start or end, or longer than `max_gap`, stay NaN. Returns the filled copy and a mask of the
    filled values.
    """
    values = np.array(values, dtype=float)
    n = values.shape[0]
    valid = np.isfinite(values)
    steps = np.arange(n).reshape(-1, *([1] * (values.ndim - 1)))
    # Index of the last valid step at or before each step, and the first at or after it
    prev_idx = np.maximum.accumulate(np.where(valid, steps, -1), axis=0)
    next_idx = np.flip(np.minimum.accumulate(np.flip(np.where(valid, steps, n), axis=0), axis=0), axis=0)
    gap = next_idx - prev_idx - 1
    fill = ~valid & (prev_idx >= 0) & (next_idx < n) & (gap <= max_gap)
    if not fill.any():
        return values, fill
    prev_val = np.take_along_axis(values, np.clip(prev_idx, 0, n - 1), axis=0)
    next_val = np.take_along_axis(values, np.clip(next_idx, 0, n - 1), axis=0)
    weight = (steps - prev_idx) / np.where(next_idx > prev_idx, next_idx - prev_idx, 1)
    values[fill] = (prev_val + weight * (next_val - prev_val))[fill]
    return values, fill


def fill_zero(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Interior NaN → 0, along axis 0, whatever the gap's length. Returns the filled copy and its mask."""
    values = np.array(values, dtype=float)
    valid = np.isfinite(values)
    seen_before = np.logical_or.accumulate(valid, axis=0)
    seen_after = np.flip(np.logical_or.accumulate(np.flip(valid, axis=0), axis=0), axis=0)
    fill = ~valid & seen_before & seen_after
    values[fill] = 0.0
    return values, fill


def fill_inputs(
    daily: Mapping[str, np.ndarray], methods: Mapping[str, GapFill]
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Each input filled by its method (inputs without one are left as they are), and a mask per input of the
    days filled (time on axis 0)."""
    filled: dict[str, np.ndarray] = {}
    estimated: dict[str, np.ndarray] = {}
    for name, values in daily.items():
        method = methods.get(name)
        if method == "interpolate":
            filled[name], estimated[name] = fill_short_gaps(values, MAX_GAP_DAYS)
        elif method == "zero":
            filled[name], estimated[name] = fill_zero(values)
        else:
            filled[name] = np.asarray(values, dtype=float)
            estimated[name] = np.zeros(np.shape(values), dtype=bool)
    return filled, estimated
