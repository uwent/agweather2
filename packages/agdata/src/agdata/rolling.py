"""Rolling windows over days (D81; PLAN.md Phase 6 D0): a 7-, 14- or 28-day mean, sum, minimum or maximum on every
day of a series, at points (`/weather/daily`, `/degree-days`) and, through the same rules, on maps and in the normals.

A window of N days is trailing (the day and the N − 1 before it) or centered. A centered window of an even length
has one more day after the day than before, as R's zoo does (`rollapply`'s `seq(to = floor(w/2), length = w)`;
pandas puts the extra day before). Two separate rules decide whether a window has a value:

- **Ends** (`partial`): a window that runs past the series' ends, onto days that don't exist (before the first day
  with data, after the forecast's last), has no value unless `partial`, which clips it to the days there are (zoo's
  `partial = TRUE`). A day outside the series itself never has one.
- **Coverage**: of the window's days (the clipped window's, with `partial`), at least `coverage` (a share, default
  0.75) must have a value, and at least one; `coverage=0` takes any one, so `partial` with `coverage=0` is zoo's
  `rollapply(…, na.rm = TRUE, partial = TRUE)`.

A sum follows D45 as a range's does (`agdata.grids.reduce`): with `gaps="estimate"`, a variable that's interpolated
(`GAP_FILL`) has its interior gaps of up to MAX_GAP_DAYS bridged first, over the series, and those days count as
known and estimated; precipitation is never estimated, so a missing day adds nothing and counts against coverage.
Mean, minimum and maximum are over the known days.

`circular` treats the series as a year that wraps from its last day to its first (normals by day of year), so every
day has a whole window and nothing is clipped.
"""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from agdata.catalog import GAP_FILL
from agdata.grids import fill_cells

Align = Literal["trailing", "centered"]
Stat = Literal["sum", "mean", "min", "max"]
ALIGNS: tuple[Align, ...] = ("trailing", "centered")
STATS: tuple[Stat, ...] = ("sum", "mean", "min", "max")
MIN_DAYS = 2
MAX_DAYS = 365
COVERAGE = 0.75


@dataclass(frozen=True, kw_only=True)
class Roll:
    """A window: its length in days, its alignment, whether it may be clipped at the series' ends, and the share of
    its days that must have a value."""

    days: int
    align: Align = "trailing"
    partial: bool = False
    coverage: float = COVERAGE

    def __post_init__(self):
        if not MIN_DAYS <= self.days <= MAX_DAYS:
            raise ValueError(f"a window is {MIN_DAYS} to {MAX_DAYS} days, not {self.days}")
        if self.align not in ALIGNS:
            raise ValueError(f"align is trailing or centered, not {self.align!r}")
        if not 0 <= self.coverage <= 1:
            raise ValueError(f"coverage is a share from 0 to 1, not {self.coverage}")

    @property
    def offsets(self) -> tuple[int, int]:
        """(days before, days after) the day its window is for."""
        after = self.days // 2 if self.align == "centered" else 0
        return self.days - 1 - after, after

    def needed(self, days: np.ndarray | int) -> np.ndarray:
        """The days with a value a window of `days` days needs: the coverage's share, rounded up, and at least one."""
        return np.maximum(1, np.ceil(np.asarray(days) * self.coverage - 1e-9)).astype(int)


@dataclass(kw_only=True)
class Rolled:
    """Each day's window value (the input's shape, NaN where it has none), and per day: the days its window held
    (`held`, fewer than `days` where it was clipped), how many had a value (`known`, estimated ones included), how
    many were estimated, and whether it has a value only because it was clipped (`clipped`)."""

    values: np.ndarray
    held: np.ndarray
    known: np.ndarray
    estimated: np.ndarray
    clipped: np.ndarray


def roll(
    values: np.ndarray,
    spec: Roll,
    stat: Stat,
    *,
    name: str | None = None,
    gaps: Literal["estimate", "missing"] = "estimate",
    extent: tuple[int, int] | None = None,
    circular: bool = False,
) -> Rolled:
    """`values` (days, …) rolled along the first axis. `extent` is the series' days as [first, last + 1) along that
    axis (default all of them): days outside it don't exist, so windows reaching them are clipped. `name` is the
    catalog variable (its gap method decides whether a sum bridges gaps; None: never)."""
    if stat not in STATS:
        raise ValueError(f"stat is one of {STATS}, not {stat!r}")
    x = np.array(values, dtype=np.float64)
    n = x.shape[0]
    lo, hi = (0, n) if extent is None or circular else (max(0, extent[0]), min(n, extent[1]))
    exists = np.zeros(n, dtype=bool)
    exists[lo:hi] = True
    estimated = np.zeros(x.shape, dtype=bool)
    if stat == "sum" and gaps == "estimate" and name is not None and GAP_FILL.get(name) == "interpolate" and hi > lo:
        x[lo:hi], estimated[lo:hi] = fill_cells(x[lo:hi])
    x[~exists] = np.nan
    before, after = spec.offsets
    if circular:
        idx = np.arange(-before, n + after) % n
        xp, ep, sp = x[idx], exists[idx], estimated[idx]
    else:
        pad = [(before, after)] + [(0, 0)] * (x.ndim - 1)
        xp = np.pad(x, pad, constant_values=np.nan)
        ep = np.pad(exists, (before, after), constant_values=False)
        sp = np.pad(estimated, pad, constant_values=False)
    win = sliding_window_view(xp, spec.days, axis=0)  # (n, …, days)
    held_1d = sliding_window_view(ep, spec.days).sum(axis=-1)  # (n,)
    known_mask = np.isfinite(win)
    known = known_mask.sum(axis=-1)
    est = sliding_window_view(sp, spec.days, axis=0).sum(axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        if stat in ("sum", "mean"):
            total = np.where(known_mask, win, 0.0).sum(axis=-1)
            value = total if stat == "sum" else total / np.maximum(known, 1)
        elif stat == "min":
            value = np.where(known_mask, win, np.inf).min(axis=-1)
        else:
            value = np.where(known_mask, win, -np.inf).max(axis=-1)
    shape = (n,) + (1,) * (x.ndim - 1)
    held = np.broadcast_to(held_1d.reshape(shape), value.shape)
    clipped_day = (held_1d < spec.days).reshape(shape)
    base = held if spec.partial else spec.days
    ok = (known >= spec.needed(base)) & exists.reshape(shape)
    if not spec.partial:
        ok &= ~clipped_day
    return Rolled(
        values=np.where(ok, value, np.nan),
        held=np.array(held),
        known=known,
        estimated=est,
        clipped=np.broadcast_to(clipped_day, value.shape) & ok,
    )


def any_in_window(flags: np.ndarray, spec: Roll) -> np.ndarray:
    """Per day, whether any day in its window (as clipped at the ends) is flagged: a window holding forecast days."""
    before, after = spec.offsets
    padded = np.pad(np.asarray(flags, dtype=bool), (before, after), constant_values=False)
    return sliding_window_view(padded, spec.days).any(axis=-1)


def label(days: int) -> str:
    """A rolled column's suffix: `7d`."""
    return f"{days}d"


def coverage_share(percent: float) -> float:
    """A coverage given in percent (as the API takes it) as a share."""
    if not 0 <= percent <= 100 or math.isnan(percent):
        raise ValueError(percent)
    return percent / 100
