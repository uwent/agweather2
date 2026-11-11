"""Normals: a reference period's typical weather by day of year (D61, D82; PLAN.md Phase 6 D1).

Every year's days are laid out on one calendar of 366 slots (`slot`: a leap year's day of year, from 0), so a date
means the same slot in every year; February 29 is missing in the years without one. From that layout:

- **Daily statistics** (`pooled`): each slot's mean, percentiles, and the share of values within bounds (a frost
  chance) pool every year's days in a window centered on it (15 days by default, wrapping from December 31 to
  January 1, `agdata.rolling`'s centered offsets): 150 values from 10 years, 75 from 5, so a day's statistics are
  steady where one day's values across five years would step by 20%. February 29 pools its neighbours like any slot.
- **Running totals** (`running`): each year's own total from a start slot by calendar date, then their mean and
  spread across years, never a total of averaged days (D61: a normal day of 45/65 °F gives other degree days than
  thirty real days do). A year's total counts at a slot only while it has missed at most `max_missing` days.
- **Freeze dates** (`freezes`): each year's last day at or below a threshold from January 1 through June 30 and
  first from July 1 through December 31, then the chance of a freeze after (spring) or by (fall) each date, the
  10th/50th/90th percentile dates and the season's length between them. A year with no such day counts as "none"
  (it had none), unlike a year with too many missing days in the season, which is left out and counted.

Periods (`period`): `last5` and `last10` are the complete years before the current one that the archive has
(D82); `last30` takes the archive's years and gridMET's before them, adjusted to the archive's basis
(`agdata.climatestore`, D84). The current year never counts. Points read a period's years from the past-years copies
and gridMET's derived years (`read_point`); maps read them in blocks of cells (D4).

Arrays put the years first and the slots second: (years, 366, …cells).
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from agdata.areas import Area

SLOTS = 366
LEAP = 2000  # the calendar slots are a leap year's days
FEB29 = 59
POOL_DAYS = 15
COVERAGE = 0.75  # of a pool's possible values, for a slot to have statistics; of the years, for a running total's
MAX_MISSING = 7  # days a year's running total may miss and still count
SEASON_MISSING = 0.1  # share of a freeze season's days a year may miss and still count
PERIODS = {"last5": 5, "last10": 10, "last30": 30}
PeriodName = Literal["last5", "last10", "last30"]


def enough_years(n: int) -> int:
    """The years of `n` a running total or freeze statistic needs: `COVERAGE` of them, at least one."""
    return max(1, math.ceil(COVERAGE * n))


def slot(day: date) -> int:
    """A date's calendar slot: its day of year in a leap year, from 0 (March 1 is 60 in every year)."""
    return (date(LEAP, day.month, day.day) - date(LEAP, 1, 1)).days


def slot_date(index: int, year: int) -> date | None:
    """The date of a slot in a year (None for February 29 in a year without one)."""
    day = date(LEAP, 1, 1) + timedelta(days=int(index))
    try:
        return date(year, day.month, day.day)
    except ValueError:
        return None


# --- Periods and reading ---------------------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Period:
    """A reference period: its name, the years it asks for, and those it has."""

    name: str
    asked: tuple[int, ...]
    years: tuple[int, ...]

    @property
    def missing(self) -> tuple[int, ...]:
        return tuple(y for y in self.asked if y not in self.years)


def period(name: str, today: date, available: Sequence[int]) -> Period:
    """`last5`, `last10` or `last30`: that many complete years before `today`'s, those in `available`."""
    if name not in PERIODS:
        raise ValueError(f"a period is one of {', '.join(PERIODS)}, not {name!r}")
    asked = tuple(range(today.year - PERIODS[name], today.year))
    return Period(name=name, asked=asked, years=tuple(y for y in asked if y in set(available)))


def layout(values: np.ndarray, year: int) -> np.ndarray:
    """A year's days (days, …) on the 366 slots, February 29 missing in a year without one."""
    values = np.asarray(values, dtype=np.float64)
    out = np.full((SLOTS, *values.shape[1:]), np.nan)
    if values.shape[0] == SLOTS:
        out[:] = values
    else:
        out[:FEB29] = values[:FEB29]
        out[FEB29 + 1 :] = values[FEB29:]
    return out


ReadYear = Callable[[int, list[str]], dict[str, np.ndarray]]


def read_years(read: ReadYear, years: Sequence[int], names: list[str]) -> dict[str, np.ndarray]:
    """Each name's (years, 366, …) from `read(year, names)`, which gives a whole year's days per name."""
    found = {name: [] for name in names}
    for year in years:
        days = read(year, names)
        for name in names:
            found[name].append(layout(days[name], year))
    return {name: np.stack(found[name]) if found[name] else np.full((0, SLOTS), np.nan) for name in names}


def read_point(
    data_dir: Path, j: int, i: int, years: Sequence[int], names: list[str], area: Area | None = None
) -> dict[str, np.ndarray]:
    """A cell's years (or `area`'s around it, averaged day by day: `agdata.areas`) as (years, 366) per name: the
    archive's from the past-years copies, or rolled up from the hours where a year has no copy
    (`series.past_reader`); a year before the archive from gridMET's, on the archive's basis (`agdata.climatestore`,
    D84), where a name gridMET doesn't give (the daily mean temperature, soil) is missing."""
    from agdata import climatestore
    from agdata.series import archive_years, past_reader

    archive = set(archive_years(data_dir))
    reader = past_reader(data_dir, j, i, area=area)
    gridmet = climatestore.reader(data_dir)

    def read(year: int, wanted: list[str]) -> dict[str, np.ndarray]:
        first, last = date(year, 1, 1), date(year, 12, 31)
        if year in archive:
            return reader(first, last, wanted)
        n = (last - first).days + 1
        out = {name: np.full(n, np.nan) for name in wanted}
        for name in wanted:  # one at a time: the gridMET store has some names, not all
            found = (
                gridmet.read(j, i, first, last, [name])
                if area is None
                else gridmet.read_area(area, first, last, [name])
            )
            if found is not None:
                out[name] = found[name]
        return out

    return read_years(read, years, names)


def available_years(data_dir: Path) -> list[int]:
    """The years a period can draw on: the archive's and gridMET's derived ones (`period`'s `available`)."""
    from agdata import climatestore
    from agdata.series import archive_years

    return sorted(set(archive_years(data_dir)) | set(climatestore.years(data_dir)))


# --- Daily statistics, pooled ----------------------------------------------------------------------------------


@dataclass(kw_only=True)
class Pooled:
    """Per slot (366, …): the mean, the percentiles asked for (`percentiles[p]`), the shares within each bounds
    asked for (`shares[name]`, 0 to 1), the values pooled (`count`) and the most there could have been (`possible`,
    one per slot)."""

    mean: np.ndarray
    percentiles: dict[float, np.ndarray]
    shares: dict[str, np.ndarray]
    count: np.ndarray
    possible: np.ndarray


Bounds = tuple[float | None, float | None]


def pool(values: np.ndarray, days: int = POOL_DAYS) -> np.ndarray:
    """(366, years × days, …): every year's values in each slot's centered window, wrapping the year."""
    values = np.asarray(values, dtype=np.float64)
    before = days // 2
    after = days - 1 - before
    idx = np.arange(-before, SLOTS + after) % SLOTS
    padded = values[:, idx]  # (years, 366 + days - 1, …)
    windows = sliding_window_view(padded, days, axis=1)  # (years, 366, …, days)
    windows = np.moveaxis(windows, -1, 1)  # (years, days, 366, …)
    n_years = values.shape[0]
    return np.moveaxis(windows.reshape(n_years * days, *windows.shape[2:]), 0, 1)


def possible(years: Sequence[int], days: int = POOL_DAYS) -> np.ndarray:
    """Per slot, how many values its pool could hold: a value per year and day, less February 29 in the years
    without one."""
    exists = np.stack([~np.isnan(layout(np.zeros(366 if _leap(y) else 365), y)) for y in years]) if years else None
    if exists is None:
        return np.zeros(SLOTS, dtype=int)
    return pool(exists.astype(float), days).sum(axis=1).astype(int)


def pooled(
    values: np.ndarray,
    years: Sequence[int],
    *,
    percentiles: Sequence[float] = (),
    shares: dict[str, Bounds] | None = None,
    days: int = POOL_DAYS,
    coverage: float = COVERAGE,
) -> Pooled:
    """Each slot's statistics over its pool (`pool`) of `values` (years, 366, …), where `years` are the years
    their rows are. A slot whose pool has fewer than `coverage` of its possible values has none. `shares` are bounds
    (low, high), both included, in the values' unit: `{"frost": (None, 0.0)}` for days at or below 0 °C."""
    pooled_values = pool(values, days)  # (366, n, …)
    known = np.isfinite(pooled_values)
    count = known.sum(axis=1)
    can = possible(years, days)
    enough = count >= np.maximum(1, np.ceil(can * coverage - 1e-9)).reshape((SLOTS,) + (1,) * (count.ndim - 1))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(enough, np.where(known, pooled_values, 0.0).sum(axis=1) / np.maximum(count, 1), np.nan)
        found_percentiles = {
            float(p): np.where(enough, _percentile(pooled_values, p, axis=1), np.nan) for p in percentiles
        }
        found_shares = {}
        for name, (low, high) in (shares or {}).items():
            within = known.copy()
            if low is not None:
                within &= pooled_values >= low
            if high is not None:
                within &= pooled_values <= high
            found_shares[name] = np.where(enough, within.sum(axis=1) / np.maximum(count, 1), np.nan)
    return Pooled(mean=mean, percentiles=found_percentiles, shares=found_shares, count=count, possible=can)


def _percentile(values: np.ndarray, p: float, axis: int) -> np.ndarray:
    """`np.nanpercentile`, NaN without a warning where there are no values."""
    return nan_quantiles(values, [p / 100], axis=axis)[0]


def nan_quantiles(
    values: np.ndarray, qs: Sequence[float], axis: int, method: Literal["linear", "lower", "higher"] = "linear"
) -> list[np.ndarray]:
    """`np.nanquantile` of `values` along `axis` at each of `qs` (0 to 1), NaN where a row has no values: one sort
    for every quantile, where NumPy's goes row by row once there's a NaN (33 s against 0.2 for a block's deciles)."""
    values = np.moveaxis(np.asarray(values), axis, 0)
    if values.shape[0] == 0:
        return [np.full(values.shape[1:], np.nan) for _ in qs]
    ordered = np.sort(values, axis=0)  # NaNs last
    n = np.isfinite(ordered).sum(axis=0)
    last = np.maximum(n - 1, 0)
    out = []
    for q in qs:
        position = last * float(q)
        low = np.floor(position).astype(np.int64)
        high = np.minimum(low + 1, last) if method == "linear" else np.ceil(position).astype(np.int64)
        a = np.take_along_axis(ordered, low[None], axis=0)[0]
        b = np.take_along_axis(ordered, high[None], axis=0)[0]
        if method == "lower":
            found = a
        elif method == "higher":
            found = b
        else:
            t = position - low
            found = np.where(t >= 0.5, b - (b - a) * (1 - t), a + (b - a) * t)  # NumPy's lerp
        out.append(np.where(n > 0, found, np.nan))
    return out


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


# --- Running totals --------------------------------------------------------------------------------------------


@dataclass(kw_only=True)
class Running:
    """Per slot from the start (366, …; missing before it): each year's running total (`years`, (years, 366, …)),
    their mean and percentiles across the years that count, and how many count (`count`)."""

    totals: np.ndarray
    mean: np.ndarray
    percentiles: dict[float, np.ndarray]
    count: np.ndarray


def running(
    daily: np.ndarray,
    years: Sequence[int],
    start: int = 0,
    *,
    percentiles: Sequence[float] = (),
    max_missing: int = MAX_MISSING,
) -> Running:
    """Each year's running total of `daily` (years, 366, …: a day's value already worked out from that year's own
    days, as its degree days) from slot `start` through December 31, and their mean and spread by slot. February 29
    adds nothing in a year without one; another missing day adds nothing and counts against the year, which stops
    counting once it has missed more than `max_missing`. A slot's statistics need `enough_years` of the years to
    count there, so a period isn't summarized by the few years it has (gridMET's 30 over a lake, which it leaves
    out, would otherwise be the archive's 10)."""
    daily = np.asarray(daily, dtype=np.float64)
    missing = np.isnan(daily)
    for k, year in enumerate(years):
        if not _leap(year):
            missing[k, FEB29] = False  # not a day that year
    totals = np.cumsum(np.where(np.isnan(daily), 0.0, daily)[:, start:], axis=1)
    missed = np.cumsum(missing[:, start:], axis=1)
    totals = np.where(missed > max_missing, np.nan, totals)
    full = np.full(daily.shape, np.nan)
    full[:, start:] = totals
    known = np.isfinite(full)
    count = known.sum(axis=0)
    enough = count >= enough_years(len(years))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(enough, np.where(known, full, 0.0).sum(axis=0) / np.maximum(count, 1), np.nan)
        found = {float(p): np.where(enough, _percentile(full, p, axis=0), np.nan) for p in percentiles}
    return Running(totals=full, mean=mean, percentiles=found, count=count)


# --- Freeze dates -----------------------------------------------------------------------------------------------

SPRING = (0, slot(date(LEAP, 6, 30)) + 1)  # slots January 1 – June 30
FALL = (slot(date(LEAP, 7, 1)), SLOTS)  # July 1 – December 31
NONE_SPRING = -1.0  # a spring with no freeze: before every date
NONE_FALL = float(SLOTS)  # a fall with no freeze: after every date


@dataclass(kw_only=True)
class Freezes:
    """At one threshold, per year: the slot of the last spring freeze and the first fall freeze (`NONE_SPRING`,
    `NONE_FALL` for none; NaN for a season left out for missing days). Per slot: the chance (0 to 1) that a freeze
    comes after it in spring (`after_spring`) or has come by it in fall (`by_fall`), among the years that count."""

    spring: np.ndarray  # (years, …)
    fall: np.ndarray
    after_spring: np.ndarray  # (366, …)
    by_fall: np.ndarray
    years_spring: np.ndarray  # (…): the years that count
    years_fall: np.ndarray

    def dates(self, q: float) -> tuple[np.ndarray, np.ndarray]:
        """(spring, fall) slots by which a share `q` of years had their last spring freeze, and their first fall
        freeze; NaN where that share falls among years with none (or there are no years)."""
        return _quantile(self.spring, q), _quantile(self.fall, q)

    def season_length(self, q: float) -> np.ndarray:
        """The frost-free season's length in days (first fall freeze less last spring freeze, a year's own), at
        quantile `q` across years; a spring or fall with none counts as the year's start or end."""
        spring = np.where(self.spring == NONE_SPRING, 0.0, self.spring)
        fall = np.where(self.fall == NONE_FALL, float(SLOTS), self.fall)
        return _quantile(fall - spring, q, nones=False)


def freezes(tmin: np.ndarray, threshold: float, max_missing: float = SEASON_MISSING) -> Freezes:
    """Freeze dates and chances from daily minimums (years, 366, …) at or below `threshold` (their unit). A season
    with fewer than `enough_years` of the years counting has none of its statistics."""
    tmin = np.asarray(tmin, dtype=np.float64)
    spring = _event(tmin, threshold, SPRING, "last", NONE_SPRING, max_missing)
    fall = _event(tmin, threshold, FALL, "first", NONE_FALL, max_missing)
    need = enough_years(tmin.shape[0])
    spring = np.where(np.isfinite(spring).sum(axis=0) >= need, spring, np.nan)
    fall = np.where(np.isfinite(fall).sum(axis=0) >= need, fall, np.nan)
    slots = np.arange(SLOTS, dtype=np.float64).reshape((SLOTS, 1) + (1,) * (tmin.ndim - 2))  # (366, years, …)
    with np.errstate(invalid="ignore", divide="ignore"):
        years_spring = np.isfinite(spring).sum(axis=0)
        years_fall = np.isfinite(fall).sum(axis=0)
        after = (np.isfinite(spring)[None] & (spring[None] > slots)).sum(axis=1) / years_spring
        by = (np.isfinite(fall)[None] & (fall[None] <= slots)).sum(axis=1) / years_fall
    return Freezes(
        spring=spring,
        fall=fall,
        after_spring=np.where(years_spring > 0, after, np.nan),
        by_fall=np.where(years_fall > 0, by, np.nan),
        years_spring=years_spring,
        years_fall=years_fall,
    )


def _event(tmin, threshold, season, kind, none, max_missing) -> np.ndarray:
    lo, hi = season
    part = tmin[:, lo:hi]
    known = np.isfinite(part)
    exists = np.ones(hi - lo, dtype=bool)
    if lo <= FEB29 < hi:
        exists[FEB29 - lo] = False  # February 29 isn't a missing day in a year without one
    present = known | ~exists.reshape((1, hi - lo) + (1,) * (tmin.ndim - 2))
    missing = (~present).sum(axis=1)
    with np.errstate(invalid="ignore"):
        hit = known & (part <= threshold)
    any_hit = hit.any(axis=1)
    index = np.argmax(hit, axis=1) if kind == "first" else (hi - lo) - 1 - np.argmax(hit[:, ::-1], axis=1)
    found = np.where(any_hit, lo + index.astype(np.float64), none)
    return np.where(missing > max_missing * (hi - lo), np.nan, found)


def _quantile(values: np.ndarray, q: float, nones: bool = True) -> np.ndarray:
    """A quantile across years (axis 0) by linear interpolation, NaN where there are no years; with `nones`, also
    where it reaches a year with none (`NONE_SPRING`, `NONE_FALL`), which has no date to interpolate."""
    if values.shape[0] == 0:
        return np.full(values.shape[1:], np.nan)
    (found,) = nan_quantiles(values, [q], axis=0)
    if not nones:
        return found
    (low,) = nan_quantiles(values, [q], axis=0, method="lower")
    (high,) = nan_quantiles(values, [q], axis=0, method="higher")
    return np.where((low == NONE_SPRING) | (high == NONE_FALL), np.nan, found)
