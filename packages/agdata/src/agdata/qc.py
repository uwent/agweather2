"""Quality control for hourly blocks (time on axis 0): range checks, spikes, and filling short gaps.

Values that fail a check become NaN (missing), never 0. Filling is limited to short interior gaps in
continuous variables, and the caller records which steps were filled (the store's per-step source).
"""

from dataclasses import dataclass

import numpy as np

from agdata.catalog import Variable
from agmodels import gaps

MAX_FILL_HOURS = 3


@dataclass(kw_only=True)
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
    """Linearly interpolates interior runs of NaN up to `max_gap` steps long, along axis 0 (`agmodels.gaps`, which
    the models' inputs share). Returns the filled copy and a mask of the filled values."""
    return gaps.fill_short_gaps(values, max_gap)


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
    return QcResult(values=cleaned, out_of_range=out_of_range, spikes=spikes, filled=filled)
