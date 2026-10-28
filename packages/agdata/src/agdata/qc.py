"""Quality control for hourly blocks (time on axis 0): range checks, spikes, and filling short gaps.

Values that fail a check become NaN (missing), never 0. Filling is limited to short interior gaps in
continuous variables, and the caller records which steps were filled (the store's per-step source).
"""

from dataclasses import dataclass

import numpy as np

from agdata.catalog import Variable

MAX_FILL_HOURS = 3


@dataclass
class QcResult:
    values: np.ndarray
    out_of_range: int
    spikes: int
    filled: np.ndarray  # bool, same shape: values interpolated by fill_short_gaps


def check_range(variable: Variable, values: np.ndarray) -> tuple[np.ndarray, int]:
    """Values outside the variable's plausible range → NaN; returns the cleaned copy and how many failed."""
    values = np.array(values, dtype=float)
    bad = np.isfinite(values) & ((values < variable.valid_min) | (values > variable.valid_max))
    values[bad] = np.nan
    return values, int(bad.sum())


def remove_spikes(values: np.ndarray, threshold: float) -> tuple[np.ndarray, int]:
    """A value more than `threshold` above (or below) both its neighbors in time → NaN."""
    values = np.array(values, dtype=float)
    if values.shape[0] < 3:
        return values, 0
    middle, before, after = values[1:-1], values[:-2], values[2:]
    up = (middle - before > threshold) & (middle - after > threshold)
    down = (before - middle > threshold) & (after - middle > threshold)
    spike = np.zeros(values.shape, dtype=bool)
    spike[1:-1] = up | down
    values[spike] = np.nan
    return values, int(spike.sum())


def fill_short_gaps(values: np.ndarray, max_gap: int = MAX_FILL_HOURS) -> tuple[np.ndarray, np.ndarray]:
    """Linearly interpolates interior runs of NaN up to `max_gap` steps long, along axis 0.

    Gaps at the start or end of the block, or longer than `max_gap`, stay NaN. Returns the filled copy and a
    mask of the filled values.
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


def run_qc(variable: Variable, values: np.ndarray) -> QcResult:
    """Range check, spike check (where the variable has a threshold), then short-gap filling (where fillable)."""
    cleaned, out_of_range = check_range(variable, values)
    spikes = 0
    if variable.spike_c is not None:
        cleaned, spikes = remove_spikes(cleaned, variable.spike_c)
    if variable.fillable:
        cleaned, filled = fill_short_gaps(cleaned)
    else:
        filled = np.zeros(cleaned.shape, dtype=bool)
    return QcResult(cleaned, out_of_range, spikes, filled)
