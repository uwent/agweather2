"""Degree days from daily minimum and maximum temperature: single sine, simple average, and modified average.

Pure NumPy functions; they broadcast, so the same call works on a point's series or the whole grid. They take
temperatures and thresholds in one unit (°F for every legacy model, D18) and return degree days in that unit.
`upper=None` means no upper threshold. A missing min or max gives NaN, and so does a min above the max.

Single sine with a horizontal cutoff (Baskerville, G. L. and Emin, P. (1969), "Rapid estimation of heat
accumulation from maximum and minimum temperatures", Ecology 50(3), 514–517) fits a sine through the day's min
and max and integrates it above the base, capped at the upper threshold. Capping is linear:
min(max(T − base, 0), upper − base) = max(T − base, 0) − max(T − upper, 0) at every moment, so
DD(base, upper) = DD(base) − DD(upper) exactly, daily and summed (D26). The average methods aren't linear.

Ported from `../ag-weather` (`app/models/degree_days_calculator.rb`, the API's DD columns) and checked against
its outputs (tests/fixtures/degree_days_legacy.csv). Differences: the legacy default upper (150, in whatever
unit the call used) becomes no upper, and invalid input gives NaN rather than raising.
"""

import numpy as np


def degree_days_sine(min_temp, max_temp, base, upper=None):
    """Single-sine degree days with a horizontal cutoff at `upper`."""
    dd = _sine_above(min_temp, max_temp, base)
    if upper is not None:
        dd = dd - _sine_above(min_temp, max_temp, upper)
    return _valid(min_temp, max_temp, np.maximum(dd, 0.0))


def degree_days_average(min_temp, max_temp, base):
    """Simple average: (min + max) / 2 − base, at least 0."""
    lo, hi = _arrays(min_temp, max_temp)
    return _valid(lo, hi, np.maximum((lo + hi) / 2 - base, 0.0))


def degree_days_modified(min_temp, max_temp, base, upper=None):
    """Modified average: min raised to the base and both capped at `upper` before averaging (the corn GDD
    method with 50/86 °F)."""
    lo, hi = _arrays(min_temp, max_temp)
    cap = np.inf if upper is None else upper
    lo_c = np.minimum(np.maximum(lo, base), cap)
    hi_c = np.minimum(hi, cap)
    return _valid(lo, hi, np.maximum((lo_c + hi_c) / 2 - base, 0.0))


def _sine_above(min_temp, max_temp, threshold):
    """Area of the day's sine above `threshold`, in degree days (no upper cutoff)."""
    lo, hi = _arrays(min_temp, max_temp)
    mean = (lo + hi) / 2
    amplitude = (hi - lo) / 2
    with np.errstate(invalid="ignore", divide="ignore"):
        theta = np.arcsin(np.clip((threshold - mean) / amplitude, -1, 1))
        partial = ((mean - threshold) * (np.pi / 2 - theta) + amplitude * np.cos(theta)) / np.pi
    return np.where(hi <= threshold, 0.0, np.where(lo >= threshold, mean - threshold, partial))


def _arrays(min_temp, max_temp):
    return np.asarray(min_temp, dtype=float), np.asarray(max_temp, dtype=float)


def _valid(min_temp, max_temp, dd):
    lo, hi = _arrays(min_temp, max_temp)
    return np.where(np.isnan(lo) | np.isnan(hi) | (lo > hi), np.nan, dd)
