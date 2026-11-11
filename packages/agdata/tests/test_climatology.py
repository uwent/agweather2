"""Normals (`agdata.climatology`, D61, D82): the calendar slots, pooled daily statistics against a plain loop,
running totals by year, and freeze dates and chances on years built to known answers."""

from datetime import date, timedelta

import numpy as np
import pytest

from agdata import climatology as clim
from agdata.climatology import FEB29, SLOTS, slot


def test_slots_are_a_leap_year_s_days():
    assert slot(date(2025, 1, 1)) == 0 and slot(date(2024, 2, 29)) == FEB29 == 59
    assert slot(date(2025, 3, 1)) == slot(date(2024, 3, 1)) == 60 and slot(date(2025, 12, 31)) == 365
    assert clim.slot_date(59, 2024) == date(2024, 2, 29) and clim.slot_date(59, 2025) is None
    days = np.arange(365.0)
    laid = clim.layout(days, 2025)
    assert np.isnan(laid[FEB29]) and laid[58] == 58 and laid[60] == 59 and laid[365] == 364
    assert clim.layout(np.arange(366.0), 2024)[FEB29] == 59


def test_periods_are_the_complete_years_before_this_one():
    available = list(range(2016, 2027))
    p = clim.period("last5", date(2026, 11, 10), available)
    assert p.years == (2021, 2022, 2023, 2024, 2025) and p.missing == ()
    p = clim.period("last10", date(2026, 11, 10), [y for y in available if y != 2017])
    assert p.asked == tuple(range(2016, 2026)) and p.missing == (2017,) and len(p.years) == 9
    assert clim.period("last30", date(2026, 1, 2), available).years == tuple(range(2016, 2026))
    with pytest.raises(ValueError):
        clim.period("1991-2020", date(2026, 1, 1), available)


YEARS = (2020, 2021, 2022, 2023, 2024)


def _years(rng, gaps=0.0) -> np.ndarray:
    out = []
    for year in YEARS:
        n = 366 if year % 4 == 0 else 365
        days = rng.normal(10, 8, n)
        days[rng.random(n) < gaps] = np.nan
        out.append(clim.layout(days, year))
    return np.stack(out)


def _pool_of(values, s, days=15):
    before = days // 2
    picks = [(s + k) % SLOTS for k in range(-before, days - before)]
    found = values[:, picks].ravel()
    return found[np.isfinite(found)]


def test_pooled_statistics_match_a_loop():
    values = _years(np.random.default_rng(3), gaps=0.05)
    found = clim.pooled(values, YEARS, percentiles=(10, 50, 90), shares={"cold": (None, 2.0)}, coverage=0.5)
    for s in (0, 30, FEB29, 200, 365):
        pool = _pool_of(values, s)
        assert found.count[s] == pool.size
        assert found.mean[s] == pytest.approx(pool.mean())
        assert found.percentiles[90.0][s] == pytest.approx(np.percentile(pool, 90))
        assert found.shares["cold"][s] == pytest.approx((pool <= 2.0).mean())
    # The pool's size: 15 days a year, less February 29 in three of the five years where it's in the window
    assert found.possible[200] == 75 and found.possible[FEB29] == 72 and found.possible[0] == 75


def test_a_slot_with_too_few_values_has_none():
    values = _years(np.random.default_rng(4))
    values[:, 100:130] = np.nan
    values[0, 90:100] = np.nan
    found = clim.pooled(values, YEARS)
    assert np.isnan(found.mean[115]) and np.isfinite(found.mean[80])
    assert np.isnan(found.mean[100])  # its window holds 7 empty slots of 15 and one year's 10 more: under 75%


def test_pooling_smooths_a_seasonal_cycle_and_wraps_the_year():
    cycle = 10 - 12 * np.cos(2 * np.pi * np.arange(SLOTS) / SLOTS)
    values = np.stack([cycle + np.random.default_rng(y).normal(0, 4, SLOTS) for y in YEARS])
    for k, year in enumerate(YEARS):
        if year % 4:
            values[k, FEB29] = np.nan
    found = clim.pooled(values, YEARS)
    assert np.nanmax(np.abs(found.mean - cycle)) < 2.5  # a day alone would err by up to ~5 °C
    assert np.isfinite(found.mean[0]) and np.isfinite(found.mean[365])
    assert found.mean[0] == pytest.approx(_pool_of(values, 0).mean())  # its window takes late December


def test_cells_as_trailing_axes():
    rng = np.random.default_rng(5)
    values = np.stack([_years(rng, gaps=0.1) for _ in range(6)], axis=-1).reshape(len(YEARS), SLOTS, 2, 3)
    found = clim.pooled(values, YEARS, percentiles=(50,))
    for j in range(2):
        for i in range(3):
            one = clim.pooled(values[:, :, j, i], YEARS, percentiles=(50,))
            np.testing.assert_allclose(found.mean[:, j, i], one.mean, equal_nan=True)
            np.testing.assert_allclose(found.percentiles[50.0][:, j, i], one.percentiles[50.0], equal_nan=True)


def test_running_totals_by_year_then_across_years():
    daily = np.stack([clim.layout(np.ones(366 if y % 4 == 0 else 365), y) for y in YEARS])
    found = clim.running(daily, YEARS, percentiles=(10, 90))
    assert found.totals[0, 365] == 366 and found.totals[1, 365] == 365  # 2020 has a February 29
    assert found.totals[1, FEB29] == found.totals[1, FEB29 - 1] == 59  # nothing added, not counted missing
    assert found.mean[365] == pytest.approx((366 * 2 + 365 * 3) / 5) and found.count[365] == 5
    late = clim.running(daily, YEARS, start=slot(date(2025, 4, 1)))
    assert np.isnan(late.mean[slot(date(2025, 3, 31))]) and late.mean[slot(date(2025, 4, 1))] == 1
    gappy = daily.copy()
    gappy[2, 100:108] = np.nan  # 8 days: past MAX_MISSING, so 2022 stops counting
    found = clim.running(gappy, YEARS)
    assert found.count[106] == 5 and found.count[107] == 4 and found.count[365] == 4
    assert found.mean[365] == pytest.approx((366 * 2 + 365 * 2) / 4)


def _tmin(year: int, spring: date | None, fall: date | None) -> np.ndarray:
    """A year at 10 °C with −2 °C on its last spring and first fall freeze (and the spring days before it)."""
    first = date(year, 1, 1)
    n = (date(year, 12, 31) - first).days + 1
    t = np.full(n, 10.0)
    if spring is not None:
        t[: (spring - first).days + 1 : 7] = -2.0
        t[(spring - first).days] = -2.0
    if fall is not None:
        t[(fall - first).days] = -2.0
    return clim.layout(t, year)


def test_freeze_dates_and_chances():
    years = [
        _tmin(2021, date(2021, 4, 20), date(2021, 10, 1)),
        _tmin(2022, date(2022, 5, 1), date(2022, 10, 15)),
        _tmin(2023, None, None),  # no freeze at all: counts as "none", not as missing
    ]
    found = clim.freezes(np.stack(years), 0.0)
    assert list(found.spring) == [slot(date(2021, 4, 20)), slot(date(2022, 5, 1)), clim.NONE_SPRING]
    assert found.years_spring == 3 and found.years_fall == 3
    assert found.after_spring[slot(date(2025, 4, 19))] == pytest.approx(2 / 3)
    assert found.after_spring[slot(date(2025, 4, 25))] == pytest.approx(1 / 3)
    assert found.after_spring[slot(date(2025, 5, 1))] == 0
    assert found.by_fall[slot(date(2025, 10, 10))] == pytest.approx(1 / 3)
    assert found.by_fall[slot(date(2025, 12, 31))] == pytest.approx(2 / 3)
    spring, fall = found.dates(0.5)
    assert spring == slot(date(2025, 4, 20)) and fall == slot(date(2025, 10, 15))
    assert np.isnan(found.dates(0.1)[0])  # a tenth of years had their last freeze before... none: no date
    # Seasons of 164, 167 and 366 days (a year without a freeze is frost-free all year): the median is 2022's
    assert found.season_length(0.5) == slot(date(2022, 10, 15)) - slot(date(2022, 5, 1)) == 167


def test_a_season_with_many_missing_days_is_left_out():
    year = _tmin(2021, date(2021, 4, 20), date(2021, 10, 1))
    year[slot(date(2021, 2, 1)) : slot(date(2021, 3, 15))] = np.nan  # 42 days: over a tenth of the spring
    found = clim.freezes(np.stack([year, _tmin(2022, date(2022, 5, 1), None)]), 0.0)
    assert np.isnan(found.spring[0]) and found.years_spring == 1 and found.years_fall == 2
    assert found.after_spring[slot(date(2025, 4, 25))] == 1.0


def test_read_years_lays_out_each_year():
    def read(year, names):
        n = (date(year, 12, 31) - date(year, 1, 1)).days + 1
        return {name: np.arange(n, dtype=float) + year for name in names}

    found = clim.read_years(read, [2023, 2024], ["a"])["a"]
    assert found.shape == (2, SLOTS) and np.isnan(found[0, FEB29]) and found[1, FEB29] == 2024 + 59
    assert found[0, 365] == 2023 + 364 and found[1, 365] == 2024 + 365
    assert (date(2023, 1, 1) + timedelta(days=int(found[0, 60] - 2023))) == date(2023, 3, 1)
