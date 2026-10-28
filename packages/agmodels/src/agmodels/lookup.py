"""Helpers for the lookup tables disease models are written as."""

import numpy as np


def steps_over(values, *thresholds: float) -> np.ndarray:
    """How many thresholds each value exceeds (strictly), as numbers: NumPy adds boolean arrays as OR."""
    v = np.asarray(values, dtype=float)
    return sum(((v > t).astype(float) for t in thresholds), np.zeros_like(v))


def level_reached(values, *thresholds: float) -> np.ndarray:
    """How many thresholds each value has reached (>=), NaN where the value is: a risk level from a total."""
    v = np.asarray(values, dtype=float)
    reached = sum(((v >= t).astype(float) for t in thresholds), np.zeros_like(v))
    return np.where(np.isnan(v), np.nan, reached)
