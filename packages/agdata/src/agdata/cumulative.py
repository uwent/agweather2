"""Running totals from local January 1, so any range is cum[end] − cum[start − 1] (PLAN.md §5.3, D25–D27).

The year is rebuilt from the daily store whenever a day changes: totals are summed in float64 and each day
rounded once on writing, so rounding never compounds. Degree days are cubes per threshold (single sine) plus
corn's modified 50/86 and two simple averages; a sine pair is the difference of its two thresholds' cubes.

Gaps (D25): a day without a daily min or max temperature is estimated by linear interpolation of both across
gaps of up to `MAX_BRIDGE_DAYS` days, with the year's neighbours on either side (the previous year's last days
and the next year's first days count). ET0 takes the daily rollup's estimate for a day missing some hours
(`agdata.gaps`), and is bridged the same way across whole missing days. Precip is never estimated. Water balance
(precipitation − ET0, `agdata.computed`) takes that ET0 and a day without rain data as no rain, both counted as
estimated (D75). A day that can't be estimated adds nothing and counts as missing. Running counts of estimated and
missing days let a range report "N days estimated" with the same subtraction. Days after the last day with data are
left empty.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata import chillseason, timecopy
from agdata.catalog import (
    CUMULATIVE_VARIABLES,
    DAILY_VARIABLES,
    DD_AVERAGE_SETTINGS_F,
    DD_MODIFIED_PAIRS_F,
    DD_SINE_THRESHOLDS_F,
    dd_name,
)
from agdata.computed import DAILY_COMPUTED
from agdata.daily import rollup_days
from agdata.grid import Window
from agdata.qc import fill_short_gaps
from agdata.store import CUMULATIVE, DAILY, GridStore, steps_in_year
from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine

MAX_BRIDGE_DAYS = 7
# The daily variables the running totals are built from (D25-D27, D75)
INPUTS = ("air_temperature_min", "air_temperature_max", "et0_sum", "precipitation_sum", "et0_sum_estimate")
WATER_BALANCE = DAILY_COMPUTED["water_balance"]
BAND_CELL_DAYS = 3_000_000  # cells × days per band: about 300 bytes each at peak, so about 1 GB


def open_or_create_cumulative(data_dir: Path, year: int, window: Window) -> GridStore:
    try:
        store = GridStore.open(data_dir, CUMULATIVE, year, CUMULATIVE_VARIABLES.values(), add_missing=True)
    except FileNotFoundError:
        return GridStore.create(data_dir, CUMULATIVE, year, window, CUMULATIVE_VARIABLES.values())
    if store.window != window:
        raise ValueError(f"{store.path} covers {store.window}, not {window}; widening the box needs a rebuild")
    return store


def rebuild_year(data_dir: Path, window: Window, year: int, changed_from: date | None = None) -> date | None:
    """Rebuilds a year's running totals from its daily store; returns the last day with data (None: no data).

    Totals are always summed from Jan 1, but only days from `changed_from` (less the bridging reach, since an
    estimate can move) are written: earlier ones can't have changed, and each day is a chunk to write."""
    days = _DailyYear(data_dir, year)
    if days.store is None:
        return None
    last = days.last_day_with_data()
    if last is None:
        return None
    n = last.timetuple().tm_yday  # days Jan 1 .. last
    store = open_or_create_cumulative(data_dir, year, window)
    skip = 0
    if changed_from is not None and changed_from.year == year:
        skip = max(0, min((changed_from - date(year, 1, 1)).days - MAX_BRIDGE_DAYS, n - 1))
    rows = max(1, BAND_CELL_DAYS // ((n + 2 * MAX_BRIDGE_DAYS) * window.shape[1]))
    for j in range(window.j0, window.j1, rows):
        band = Window(j0=j, j1=min(j + rows, window.j1), i0=window.i0, i1=window.i1)
        tmin, tmax, et0, precip, et0_estimate = (days.read_with_neighbours(name, band, n) for name in INPUTS)
        out = running_totals(tmin, tmax, et0, precip, et0_estimate)
        out = {name: values[skip:] for name, values in out.items()}
        store.write(date(year, 1, 1) + timedelta(days=skip), out, source="derived", window=band)
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
    for base, upper in DD_AVERAGE_SETTINGS_F:
        out[dd_name("average", base, upper)] = _cumsum(degree_days_average(lo_f, hi_f, base, upper), usable)
    out["temperature_estimated_days"] = np.cumsum(usable & ~known[year], axis=0, dtype=np.int16)
    out["temperature_missing_days"] = np.cumsum(~usable, axis=0, dtype=np.int16)

    if et0_estimate_mm is not None:
        et0_mm_or_estimate = np.where(np.isfinite(et0_mm), et0_mm, et0_estimate_mm)
    else:
        et0_mm_or_estimate = et0_mm
    et0, _ = fill_short_gaps(et0_mm_or_estimate, MAX_BRIDGE_DAYS)
    et0 = et0[year]
    out["et0"] = _cumsum(et0, np.isfinite(et0))
    out["et0_estimated_days"] = np.cumsum(np.isfinite(et0) & ~np.isfinite(et0_mm[year]), axis=0, dtype=np.int16)
    out["et0_missing_days"] = np.cumsum(~np.isfinite(et0), axis=0, dtype=np.int16)

    precip = precip_mm[year]
    out["precipitation"] = _cumsum(precip, np.isfinite(precip))
    out["precipitation_missing_days"] = np.cumsum(~np.isfinite(precip), axis=0, dtype=np.int16)

    # Over the padded days, so a gap in rain at the year's edge is filled as within it
    balance, filled = WATER_BALANCE.for_total({"precipitation_sum": precip_mm, "et0_sum": et0_mm_or_estimate})
    balance, usable = balance[year], np.isfinite(balance[year])
    estimated = usable & (filled[year] | ~np.isfinite(et0_mm[year]))  # an ET0 from part of a day's hours too
    out["water_balance"] = _cumsum(balance, usable)
    out["water_balance_estimated_days"] = np.cumsum(estimated, axis=0, dtype=np.int16)
    out["water_balance_missing_days"] = np.cumsum(~usable, axis=0, dtype=np.int16)
    return out


def _cumsum(values: np.ndarray, usable: np.ndarray) -> np.ndarray:
    """Summed in float64 and kept as float32 (exact to about 0.001 at 16,000, far inside the stored 0.5)."""
    return np.cumsum(np.where(usable, values, 0.0), axis=0, dtype=np.float64).astype(np.float32)


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
        out = np.full((days + 2 * pad, *window.shape), np.nan, dtype=np.float32)
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
            # A neighbour made before a variable joined the catalog gets it, empty, as the rollup does
            return GridStore.open(self.data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
        except FileNotFoundError:
            return None


def update_days(
    data_dir: Path,
    window: Window,
    first: date,
    last: date,
    ingredients: bool = True,
    names: Collection[str] | None = None,
) -> list[int]:
    """Rolls up local days first..last and updates what reads them: the season-read copy of the minimum and maximum
    (`agdata.timecopy`), every year whose running totals they reach (a year's first and last days bridge into its
    neighbours), chill portions, and unless `ingredients` is False (a backfill, which builds a year's at its end)
    the models' ingredients (`agdata.modelmaps`); returns the years whose running totals were rebuilt.

    By default every daily variable, after new hours (ingest, a fill). With `names` (a rebuild of stale daily
    variables) only those are rolled up and only what reads them follows (`steps_for`): the hours didn't change, so
    chill portions don't either."""
    from agdata import modelmaps  # it reads the model registry: import only when used

    steps = steps_for(names)
    rollup_days(data_dir, window, first, last, names)
    if steps.timecopy:
        timecopy.update(data_dir, first, last)
    rebuilt = []
    if steps.totals:
        reach = timedelta(days=MAX_BRIDGE_DAYS)
        years = list(range((first - reach).year, (last + reach).year + 1))
        rebuilt = [year for year in years if rebuild_year(data_dir, window, year, changed_from=first) is not None]
    if steps.chill:
        chillseason.update(data_dir, window, first, last)  # the Dynamic model's chill, forward from `first`
    if ingredients and (steps.ingredients is None or steps.ingredients):
        modelmaps.update(data_dir, window, first, last, keys=steps.ingredients)
    return rebuilt


@dataclass(frozen=True, kw_only=True)
class Steps:
    """What follows a rollup of some daily variables (`update_days`)."""

    timecopy: bool  # the minimum or maximum was rewritten
    totals: bool  # an input of the running totals was
    chill: bool  # new hours (chill portions come from them, not from the daily store)
    ingredients: list[str] | None  # the ingredients whose models read one (None: all of them)


def steps_for(names: Collection[str] | None) -> Steps:
    """What a rollup of `names` (None: every daily variable, after new hours) must update after it."""
    if names is None:
        return Steps(timecopy=True, totals=True, chill=True, ingredients=None)
    from agdata import modelmaps

    wanted = set(names)
    return Steps(
        timecopy=bool(wanted & set(timecopy.NAMES)),
        totals=bool(wanted & set(INPUTS)),
        chill=False,
        ingredients=modelmaps.keys_reading(wanted),
    )
