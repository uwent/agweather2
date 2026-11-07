"""Reducing a run of map steps, and degree days over the grid (`/grids/{layer}`; PLAN.md Phase 5 E).

The rules are the points' (`/weather/totals`, `/degree-days`), applied to every cell at once (D45, D56):

- A sum bridges interior gaps of up to MAX_GAP_DAYS steps by the variable's method (`interpolate`) unless
  `gaps=missing`, counting the estimated steps; precipitation (`zero`) is never estimated: its total sums the known
  steps and counts the rest as missing (no rain). A cell with no known step is missing.
- Mean, min and max are over the known steps, with the missing ones counted; nothing is estimated.
- Degree days for any setting come from each day's minimum and maximum, gaps bridged the same way, in °F. A day
  that can't be bridged adds nothing to a sum and is counted missing.

Only cells with a gap are filled (`fill_cells`): a season over Wisconsin is 17 million cell-days, and filling every
cell took a second where there were no gaps at all.
"""

from collections.abc import Callable
from typing import Literal

import numpy as np

from agdata.catalog import DD_AVERAGE_SETTINGS_F, DD_MODIFIED_PAIRS_F, DD_SINE_THRESHOLDS_F, GAP_FILL, dd_name
from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine
from agmodels.degree_days_grid import degree_days_c
from agmodels.gaps import MAX_GAP_DAYS, GapFill, fill_short_gaps, fill_zero

Stat = Literal["sum", "mean", "min", "max"]
Gaps = Literal["estimate", "missing"]
DDMethod = Literal["sine", "average", "modified"]
METHODS: dict[str, Callable] = {
    "sine": degree_days_sine,
    "average": degree_days_average,
    "modified": degree_days_modified,
}
BAND_CELL_DAYS = 2_000_000  # degree days are computed in bands of rows this size (~0.5 GB at peak)


def fill_cells(
    values: np.ndarray, max_gap: int = MAX_GAP_DAYS, method: GapFill = "interpolate"
) -> tuple[np.ndarray, np.ndarray]:
    """`agmodels.gaps.fill_short_gaps` (or `fill_zero`, `method="zero"`) along axis 0, run only on the cells that
    have a missing step."""
    values = np.asarray(values, dtype=np.float64)
    flat = values.reshape(values.shape[0], -1)
    out, filled = flat.copy(), np.zeros(flat.shape, dtype=bool)
    gappy = np.flatnonzero(np.isnan(flat).any(axis=0))
    if gappy.size:
        if method == "zero":
            out[:, gappy], filled[:, gappy] = fill_zero(flat[:, gappy])
        else:
            out[:, gappy], filled[:, gappy] = fill_short_gaps(flat[:, gappy], max_gap)
    return out.reshape(values.shape), filled.reshape(values.shape)


def reduce(
    values: np.ndarray, stat: Stat, name: str | None, gaps: Gaps = "estimate"
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(value, estimated steps, missing steps) per cell, each (y, x), from steps (n, y, x) of the catalog variable
    `name` (its gap method decides whether a sum bridges gaps; None: never)."""
    values = np.asarray(values, dtype=np.float64)
    estimated = np.zeros(values.shape, dtype=bool)
    if stat == "sum" and gaps == "estimate" and name is not None and GAP_FILL.get(name) == "interpolate":
        values, estimated = fill_cells(values)
    known = np.isfinite(values)
    count = known.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        if stat == "sum":
            value = np.where(count > 0, np.where(known, values, 0.0).sum(axis=0), np.nan)
        elif stat == "mean":
            value = np.where(count > 0, np.where(known, values, 0.0).sum(axis=0) / count, np.nan)
        elif stat == "min":
            value = np.where(count > 0, np.where(known, values, np.inf).min(axis=0), np.nan)
        else:
            value = np.where(count > 0, np.where(known, values, -np.inf).max(axis=0), np.nan)
    return value, estimated.sum(axis=0), (~known).sum(axis=0)


def degree_days(
    tmin_c: np.ndarray, tmax_c: np.ndarray, method: DDMethod, base_f: float, upper_f: float | None, gaps: Gaps
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(each day's degree days in °F·d, estimated, usable), each (days, y, x), from daily min and max in °C. A day
    is estimated where either temperature was bridged; unusable days are NaN. The degree days are one parallel pass
    (`agmodels.degree_days_grid`, the NumPy methods' formulas); gaps are bridged a band of rows at a time."""
    lo = np.asarray(tmin_c, dtype=np.float32)
    hi = np.asarray(tmax_c, dtype=np.float32)
    known = np.isfinite(lo) & np.isfinite(hi)
    usable = known
    gappy = np.flatnonzero(~known.all(axis=0).ravel()) if gaps == "estimate" else np.zeros(0, dtype=int)
    if gappy.size:  # bridge only the cells with a missing day, a block of them at a time (D45's fill)
        n = lo.shape[0]
        lo, hi = lo.reshape(n, -1).copy(), hi.reshape(n, -1).copy()  # a day missing either is missing both
        for k in range(0, gappy.size, max(1, BAND_CELL_DAYS // max(1, n))):
            cells = gappy[k : k + BAND_CELL_DAYS // max(1, n)]
            both = known.reshape(n, -1)[:, cells]
            lo[:, cells] = fill_cells(np.where(both, lo[:, cells], np.nan))[0]
            hi[:, cells] = fill_cells(np.where(both, hi[:, cells], np.nan))[0]
        lo, hi = lo.reshape(known.shape), hi.reshape(known.shape)
        usable = np.isfinite(lo) & np.isfinite(hi)
    dd = degree_days_c(lo, hi, method, base_f, upper_f)
    dd[~usable] = np.nan
    return dd, usable & ~known, usable


def cube_terms(method: DDMethod, base_f: float, upper_f: float | None) -> tuple[str, str | None] | None:
    """The running-total cubes a setting is (`agdata.cumulative`): (cube, cube to subtract or None), or None if it
    isn't one. Single sine with a cutoff is the base's cube less the upper's (D26)."""
    thresholds = {round(t, 3): t for t in DD_SINE_THRESHOLDS_F}
    if method == "sine" and round(base_f, 3) in thresholds:
        base = dd_name("sine", thresholds[round(base_f, 3)])
        if upper_f is None:
            return base, None
        if round(upper_f, 3) in thresholds:
            return base, dd_name("sine", thresholds[round(upper_f, 3)])
        return None
    if method == "modified" and upper_f is not None:
        for b, u in DD_MODIFIED_PAIRS_F:
            if round(b, 3) == round(base_f, 3) and round(u, 3) == round(upper_f, 3):
                return dd_name("modified", b, u), None
    if method == "average":
        for b, u in DD_AVERAGE_SETTINGS_F:
            same_upper = (u is None and upper_f is None) or (
                u is not None and upper_f is not None and round(u, 3) == round(upper_f, 3)
            )
            if round(b, 3) == round(base_f, 3) and same_upper:
                return dd_name("average", b, u), None
    return None
