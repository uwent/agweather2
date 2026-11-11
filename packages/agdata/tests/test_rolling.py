"""Rolling windows (`agdata.rolling`, D81) against a plain loop over days, and pandas' `rolling`."""

import math

import numpy as np
import pandas as pd
import pytest

from agdata.rolling import Roll, any_in_window, roll


def reference(values, days, align, partial, coverage, stat, extent=None, circular=False):
    """Day by day, as the rules read: the window's days, clipped to the series, then coverage."""
    n = len(values)
    lo, hi = extent or (0, n)
    before = days // 2 if align == "centered" else days - 1
    after = days - 1 - before
    out = []
    for d in range(n):
        if not circular and not lo <= d < hi:
            out.append(math.nan)
            continue
        idx = range(d - before, d + after + 1)
        window = [values[k % n] for k in idx] if circular else [values[k] for k in idx if lo <= k < hi]
        if len(window) < days and not partial:
            out.append(math.nan)
            continue
        known = [v for v in window if not math.isnan(v)]
        needed = max(1, math.ceil(len(window if partial else range(days)) * coverage - 1e-9))
        if len(known) < needed:
            out.append(math.nan)
            continue
        out.append({"sum": sum, "mean": lambda k: sum(k) / len(k), "min": min, "max": max}[stat](known))
    return np.array(out)


SERIES = [3.0, 1.0, math.nan, 4.0, 1.0, 5.0, 9.0, 2.0, math.nan, math.nan, 6.0, 5.0, 3.0, 5.0, 8.0, 9.0, 7.0]


@pytest.mark.parametrize("days", [2, 3, 4, 7])
@pytest.mark.parametrize("align", ["trailing", "centered"])
@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("coverage", [0.0, 0.5, 0.75, 1.0])
@pytest.mark.parametrize("stat", ["sum", "mean", "min", "max"])
def test_matches_the_loop(days, align, partial, coverage, stat):
    spec = Roll(days=days, align=align, partial=partial, coverage=coverage)
    got = roll(np.array(SERIES), spec, stat).values
    np.testing.assert_allclose(got, reference(SERIES, days, align, partial, coverage, stat), equal_nan=True)


@pytest.mark.parametrize("partial", [False, True])
def test_extent_and_circular(partial):
    spec = Roll(days=5, align="centered", partial=partial, coverage=0.0)
    got = roll(np.array(SERIES), spec, "mean", extent=(3, 14)).values
    np.testing.assert_allclose(
        got, reference(SERIES, 5, "centered", partial, 0.0, "mean", extent=(3, 14)), equal_nan=True
    )
    wrapped = roll(np.array(SERIES), spec, "mean", circular=True).values
    np.testing.assert_allclose(
        wrapped, reference(SERIES, 5, "centered", True, 0.0, "mean", circular=True), equal_nan=True
    )
    assert np.isfinite(wrapped[0]) and np.isfinite(wrapped[-1])  # the year's ends have whole windows


@pytest.mark.parametrize("days", [3, 4, 7, 14])
@pytest.mark.parametrize("center", [False, True])
@pytest.mark.parametrize("stat", ["sum", "mean", "min", "max"])
def test_pandas_conventions(days, center, stat):
    """pandas' `rolling(days, center=…)`: with `min_periods=days` our whole windows at coverage 1, and with
    `min_periods=1` our partial windows at coverage 0 (any one value, ends clipped)."""
    x = pd.Series(SERIES)
    align = "centered" if center else "trailing"
    whole = getattr(x.rolling(days, center=center, min_periods=days), stat)().to_numpy()
    ours = roll(np.array(SERIES), Roll(days=days, align=align, coverage=1.0), stat).values
    np.testing.assert_allclose(ours, whole, equal_nan=True)
    part = getattr(x.rolling(days, center=center, min_periods=1), stat)().to_numpy()
    ours = roll(np.array(SERIES), Roll(days=days, align=align, partial=True, coverage=0), stat).values
    np.testing.assert_allclose(ours, part, equal_nan=True)
    assert Roll(days=14, align="centered").offsets == (7, 6)
    assert Roll(days=7, align="centered").offsets == (3, 3)
    assert Roll(days=7).offsets == (6, 0)


def test_coverage_counts():
    """75%: 6 of 7 days, 11 of 14, 21 of 28."""
    assert list(Roll(days=7).needed(np.array([7, 14, 28]))) == [6, 11, 21]
    assert int(Roll(days=7, coverage=0).needed(7)) == 1
    one_gap = np.array([1.0, 1, 1, np.nan, 1, 1, 1])
    two_gaps = np.array([1.0, 1, np.nan, np.nan, 1, 1, 1])
    assert roll(one_gap, Roll(days=7), "mean").values[-1] == 1.0
    assert np.isnan(roll(two_gaps, Roll(days=7), "mean").values[-1])


def test_sums_follow_d45():
    """A sum of an interpolated variable bridges an interior gap (estimated); precipitation never does."""
    et0 = np.array([2.0, 2, 2, np.nan, 4, 4, 4])
    found = roll(et0, Roll(days=7, coverage=1.0), "sum", name="et0_sum")
    assert found.values[-1] == pytest.approx(21.0) and found.estimated[-1] == 1
    rain = roll(et0, Roll(days=7, coverage=1.0), "sum", name="precipitation_sum")
    assert np.isnan(rain.values[-1])
    rain = roll(et0, Roll(days=7), "sum", name="precipitation_sum")
    assert rain.values[-1] == pytest.approx(18.0) and rain.estimated[-1] == 0 and rain.known[-1] == 6
    assert roll(et0, Roll(days=7, coverage=1.0), "sum", name="et0_sum", gaps="missing").values[-1] != 21.0


def test_cells_as_trailing_axes():
    rng = np.random.default_rng(1)
    grid = rng.normal(size=(30, 3, 4))
    grid[rng.random(grid.shape) < 0.2] = np.nan
    spec = Roll(days=7, align="centered", partial=True)
    got = roll(grid, spec, "max").values
    for j in range(3):
        for i in range(4):
            np.testing.assert_allclose(
                got[:, j, i], reference(list(grid[:, j, i]), 7, "centered", True, 0.75, "max"), equal_nan=True
            )


def test_clipped_and_forecast_flags():
    x = np.arange(10.0)
    found = roll(x, Roll(days=4, align="centered", partial=True), "mean")
    assert list(found.clipped) == [True, True] + [False] * 7 + [True]  # two days before, one after
    assert list(found.held) == [2, 3, 4, 4, 4, 4, 4, 4, 4, 3]
    forecast = np.array([False] * 7 + [True] * 3)
    assert list(any_in_window(forecast, Roll(days=4, align="centered"))) == [False] * 6 + [True] * 4
    assert list(any_in_window(forecast, Roll(days=4))) == [False] * 7 + [True] * 3


def test_checks():
    with pytest.raises(ValueError):
        Roll(days=1)
    with pytest.raises(ValueError):
        Roll(days=7, coverage=1.5)
    with pytest.raises(ValueError):
        roll(np.zeros(3), Roll(days=2), "median")  # type: ignore[arg-type]
