"""Running totals and rolling windows of daily model outputs, counted from a start day (the biofix).

Days on axis 0. Days before `start` are NaN. A rolling window covers the last `days` days but not before
`start`, so it's partial at first (as the Crop Risk Tool's `frollapply(partial = TRUE)`). A missing day adds
nothing to a total or sum, and a mean is over the window's days that have values (NaN if none), so one gap
doesn't blank a season's risk.
"""

import numpy as np


def running_total(values: np.ndarray, start: int = 0) -> np.ndarray:
    total = np.cumsum(_from(values, start, fill=0.0), axis=0)
    return _before(total, start)


def rolling_sum(values: np.ndarray, days: int, start: int = 0) -> np.ndarray:
    return _before(_window(_from(values, start, fill=0.0), days), start)


def rolling_mean(values: np.ndarray, days: int, start: int = 0) -> np.ndarray:
    v = _from(values, start, fill=np.nan)
    sums = _window(np.nan_to_num(v), days)
    counts = _window(np.isfinite(v).astype(float), days)
    with np.errstate(invalid="ignore", divide="ignore"):
        return _before(np.where(counts > 0, sums / counts, np.nan), start)


def _from(values: np.ndarray, start: int, fill: float) -> np.ndarray:
    v = np.array(values, dtype=float)
    v[:start] = fill
    return v if np.isnan(fill) else np.nan_to_num(v, nan=fill)


def _window(values: np.ndarray, days: int) -> np.ndarray:
    total = np.cumsum(values, axis=0)
    shifted = np.concatenate([np.zeros((days, *values.shape[1:])), total[:-days]])[: values.shape[0]]
    return total - shifted


def _before(values: np.ndarray, start: int) -> np.ndarray:
    values[:start] = np.nan
    return values
