"""Running totals from local January 1, so any range is cum[end] − cum[start − 1] (PLAN.md §5.3, D25–D27).

The year is rebuilt from the daily store whenever a day changes: totals are summed in float64 and each day
rounded once on writing, so rounding never compounds. Degree days are cubes per threshold (single sine) plus
corn's modified 50/86; a sine pair is the difference of its two thresholds' cubes.

Gaps (D25): a day without a daily min or max temperature is estimated by linear interpolation of both across
gaps of up to `MAX_BRIDGE_DAYS` days, with the year's neighbours on either side (the previous year's last days
and the next year's first days count). ET0 takes the daily rollup's estimate for a day missing some hours
(`agdata.gaps`), and is bridged the same way across whole missing days. Precip is never estimated. A day that can't
be estimated adds nothing and counts as missing. Running counts of estimated and missing days let a range report
"N days estimated" with the same subtraction. Days after the last day with data are left empty.
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, DD_MODIFIED_PAIRS_F, DD_SINE_THRESHOLDS_F, dd_name
from agdata.daily import rollup_days
from agdata.grid import Window
from agdata.qc import fill_short_gaps
from agdata.store import CUMULATIVE, DAILY, GridStore, steps_in_year
from agmodels.degree_days import degree_days_modified, degree_days_sine

MAX_BRIDGE_DAYS = 7
BAND_ROWS = 128


def open_or_create_cumulative(data_dir: Path, year: int, window: Window) -> GridStore:
    try:
        store = GridStore.open(data_dir, CUMULATIVE, year, CUMULATIVE_VARIABLES.values())
    except FileNotFoundError:
        return GridStore.create(data_dir, CUMULATIVE, year, window, CUMULATIVE_VARIABLES.values())
    if store.window != window:
        raise ValueError(f"{store.path} covers {store.window}, not {window}; widening the box needs a rebuild")
    return store


def rebuild_year(data_dir: Path, window: Window, year: int) -> date | None:
    """Rebuilds a year's running totals from its daily store; returns the last day with data (None: no data)."""
    days = _DailyYear(data_dir, year)
    if days.store is None:
        return None
    last = days.last_day_with_data()
    if last is None:
        return None
    n = last.timetuple().tm_yday  # days Jan 1 .. last
    store = open_or_create_cumulative(data_dir, year, window)
    for j in range(window.j0, window.j1, BAND_ROWS):
        band = Window(j, min(j + BAND_ROWS, window.j1), window.i0, window.i1)
        names = ("air_temperature_min", "air_temperature_max", "et0_sum", "precipitation_sum", "et0_sum_estimate")
        tmin, tmax, et0, precip, et0_estimate = (days.read_with_neighbours(name, band, n) for name in names)
        out = running_totals(tmin, tmax, et0, precip, et0_estimate)
        store.write(date(year, 1, 1), out, source="derived", window=band)
    return last


def running_totals(
    tmin_c: np.ndarray,
    tmax_c: np.ndarray,
    et0_mm: np.ndarray,
    precip_mm: np.ndarray,
    et0_estimate_mm: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """The cumulative store's variables from daily series (days, y, x) padded with MAX_BRIDGE_DAYS of neighbours
    on each side (NaN where there are none); the result covers the unpadded days. `et0_estimate_mm` is the daily
    store's ET0 with missing hours estimated, used where `et0_mm` is missing."""
    pad = MAX_BRIDGE_DAYS
    year = slice(pad, tmin_c.shape[0] - pad)
    out: dict[str, np.ndarray] = {}

    known = np.isfinite(tmin_c) & np.isfinite(tmax_c)
    lo, _ = fill_short_gaps(np.where(known, tmin_c, np.nan), MAX_BRIDGE_DAYS)
    hi, _ = fill_short_gaps(np.where(known, tmax_c, np.nan), MAX_BRIDGE_DAYS)
    lo_f, hi_f = lo[year] * 1.8 + 32, hi[year] * 1.8 + 32
    usable = np.isfinite(lo_f) & np.isfinite(hi_f)
    for t in DD_SINE_THRESHOLDS_F:
        out[dd_name("sine", t)] = _cumsum(degree_days_sine(lo_f, hi_f, t), usable)
    for base, upper in DD_MODIFIED_PAIRS_F:
        out[dd_name("modified", base, upper)] = _cumsum(degree_days_modified(lo_f, hi_f, base, upper), usable)
    out["temperature_estimated_days"] = np.cumsum(usable & ~known[year], axis=0)
    out["temperature_missing_days"] = np.cumsum(~usable, axis=0)

    if et0_estimate_mm is not None:
        et0_mm_or_estimate = np.where(np.isfinite(et0_mm), et0_mm, et0_estimate_mm)
    else:
        et0_mm_or_estimate = et0_mm
    et0, _ = fill_short_gaps(et0_mm_or_estimate, MAX_BRIDGE_DAYS)
    et0 = et0[year]
    out["et0"] = _cumsum(et0, np.isfinite(et0))
    out["et0_estimated_days"] = np.cumsum(np.isfinite(et0) & ~np.isfinite(et0_mm[year]), axis=0)
    out["et0_missing_days"] = np.cumsum(~np.isfinite(et0), axis=0)

    precip = precip_mm[year]
    out["precipitation"] = _cumsum(precip, np.isfinite(precip))
    out["precipitation_missing_days"] = np.cumsum(~np.isfinite(precip), axis=0)
    return out


def _cumsum(values: np.ndarray, usable: np.ndarray) -> np.ndarray:
    return np.cumsum(np.where(usable, values, 0.0), axis=0, dtype=np.float64)


class _DailyYear:
    """A year's daily store, read with the neighbouring years' days around it."""

    def __init__(self, data_dir: Path, year: int):
        self.data_dir = data_dir
        self.year = year
        self.store = self._open(year)

    def last_day_with_data(self) -> date | None:
        """The last day whose daily min temperature or precip was rolled up."""
        assert self.store is not None
        written = np.flatnonzero(self.store.read_meta("air_temperature_min.source") > 0)
        return None if written.size == 0 else date(self.year, 1, 1) + timedelta(days=int(written[-1]))

    def read_with_neighbours(self, name: str, window: Window, days: int) -> np.ndarray:
        """Days 1..`days` of the year, with MAX_BRIDGE_DAYS of the years before and after on either side."""
        assert self.store is not None
        pad = MAX_BRIDGE_DAYS
        out = np.full((days + 2 * pad, *window.shape), np.nan)
        out[pad : pad + days] = self.store.read_steps(name, 0, days, window)
        before = self._open(self.year - 1)
        if before is not None:
            n = steps_in_year(self.year - 1, "day")
            out[:pad] = before.read_steps(name, n - pad, n, window)
        if days == steps_in_year(self.year, "day"):
            after = self._open(self.year + 1)
            if after is not None:
                out[pad + days :] = after.read_steps(name, 0, pad, window)
        return out

    def _open(self, year: int) -> GridStore | None:
        try:
            return GridStore.open(self.data_dir, DAILY, year, DAILY_VARIABLES.values())
        except FileNotFoundError:
            return None


def update_days(data_dir: Path, window: Window, first: date, last: date) -> list[int]:
    """Rolls up local days first..last and rebuilds every year whose running totals they reach (a year's first
    and last days bridge into its neighbours); returns the years rebuilt."""
    rollup_days(data_dir, window, first, last)
    reach = timedelta(days=MAX_BRIDGE_DAYS)
    years = list(range((first - reach).year, (last + reach).year + 1))
    return [year for year in years if rebuild_year(data_dir, window, year) is not None]
