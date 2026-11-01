import csv
from pathlib import Path

import numpy as np
import pytest

from agmodels import degree_days as dd

LEGACY = Path(__file__).parent / "fixtures" / "degree_days_legacy.csv"  # make_degree_days_legacy.rb
METHODS = {
    "sine": lambda lo, hi, base, upper: dd.degree_days_sine(lo, hi, base, upper),
    "average": lambda lo, hi, base, upper: dd.degree_days_average(lo, hi, base),
    "modified": lambda lo, hi, base, upper: dd.degree_days_modified(lo, hi, base, upper),
}


def legacy_cases():
    with LEGACY.open() as f:
        rows = list(csv.DictReader(f))
    groups: dict[tuple[str, float, float | None], list[dict]] = {}
    for row in rows:
        key = (row["method"], float(row["base"]), float(row["upper"]) if row["upper"] else None)
        groups.setdefault(key, []).append(row)
    return groups


@pytest.mark.parametrize(("method", "base", "upper"), sorted(legacy_cases(), key=str))
def test_matches_the_old_api(method, base, upper):
    rows = legacy_cases()[(method, base, upper)]
    lo = np.array([float(r["min"]) for r in rows])
    hi = np.array([float(r["max"]) for r in rows])
    expected = np.array([float(r["dd"]) for r in rows])
    np.testing.assert_allclose(METHODS[method](lo, hi, base, upper), expected, atol=1e-6)


def test_sine_pair_is_the_difference_of_its_thresholds():
    rng = np.random.default_rng(0)
    lo = rng.uniform(-10, 90, 1000)
    hi = lo + rng.uniform(0, 40, 1000)
    np.testing.assert_allclose(
        dd.degree_days_sine(lo, hi, 50, 86), dd.degree_days_sine(lo, hi, 50) - dd.degree_days_sine(lo, hi, 86)
    )


def test_known_values():
    assert dd.degree_days_sine(60, 80, 50) == pytest.approx(20)  # all above the base: the mean minus the base
    assert dd.degree_days_sine(40, 60, 50) == pytest.approx(10 / np.pi)  # half the sine above: amplitude / π
    assert dd.degree_days_sine(90, 100, 50, 86) == pytest.approx(36)  # all above the upper
    assert dd.degree_days_modified(40, 95, 50, 86) == pytest.approx(18)  # (50 + 86) / 2 − 50
    assert dd.degree_days_average(40, 50, 50) == 0


def test_missing_or_inverted_input_is_nan():
    for f in (dd.degree_days_sine, dd.degree_days_average, dd.degree_days_modified):
        np.testing.assert_array_equal(np.isnan(f(np.array([np.nan, 50, 60]), np.array([70, np.nan, 50]), 50)), True)


def test_a_grid_broadcasts():
    lo = np.full((3, 4, 5), 45.0)
    hi = np.full((3, 4, 5), 75.0)
    out = dd.degree_days_sine(lo, hi, 50, 86)
    assert out.shape == (3, 4, 5)
    assert np.all(out == out.flat[0])


def integrated_sine_dd(lo, hi, base, upper=None, steps=200_000):
    """Degree days by numerical integration of the day's temperature curve, independent of the closed form: the
    sine T(t) = mean + amplitude sin(2πt) over one day (Baskerville and Emin 1969), counted above the base and not
    above the upper threshold (horizontal cutoff): the day's mean of min(max(T - base, 0), upper - base)."""
    t = (np.arange(steps) + 0.5) / steps
    temperature = (lo + hi) / 2 + (hi - lo) / 2 * np.sin(2 * np.pi * t)
    above = np.maximum(temperature - base, 0)
    if upper is not None:
        above = np.minimum(above, upper - base)
    return above.mean()


@pytest.mark.parametrize(
    ("lo", "hi", "base", "upper"),
    [
        (45, 65, 50, None),  # the minimum under the base: the sine is cut at the base
        (45, 65, 50, 86),  # under the base, never near the upper
        (60, 100, 50, 86),  # the maximum over the upper: the peak is cut flat
        (45, 95, 50, 86),  # crossing both thresholds
        (30, 40, 50, 86),  # all under the base
        (88, 96, 50, 86),  # all over the upper: the cap, upper - base
        (50, 50, 50, 86),  # no daily range, at the base
        (10, 35, 10, 29),  # Celsius, the same function
    ],
)
def test_sine_matches_the_numerical_integral_of_its_curve(lo, hi, base, upper):
    assert dd.degree_days_sine(lo, hi, base, upper) == pytest.approx(integrated_sine_dd(lo, hi, base, upper), abs=2e-4)


def test_sine_day_crossing_the_base_by_hand():
    # mean 55, amplitude 10, base 50: θ = asin(-0.5) = -π/6, DD = [5 (π/2 + π/6) + 10 cos(π/6)] / π (Baskerville and
    # Emin's closed form), done by hand
    expected = (5 * (np.pi / 2 + np.pi / 6) + 10 * np.cos(np.pi / 6)) / np.pi
    assert expected == pytest.approx(6.0899, abs=1e-4)
    assert dd.degree_days_sine(45, 65, 50) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("lo", "hi", "expected"),
    [
        (55, 70, 12.5),  # both above the base, under the upper: (55 + 70) / 2 - 50
        (40, 70, 10.0),  # the minimum raised to the base: (50 + 70) / 2 - 50
        (60, 100, 23.0),  # the maximum cut to the upper: (60 + 86) / 2 - 50
        (30, 45, 0.0),  # all under the base
        (90, 100, 36.0),  # all over the upper: 86 - 50
    ],
)
def test_modified_average_by_hand(lo, hi, expected):
    assert dd.degree_days_modified(lo, hi, 50, 86) == pytest.approx(expected)


def test_modified_average_without_an_upper_only_raises_the_minimum():
    assert dd.degree_days_modified(40, 100, 50) == pytest.approx(25.0)  # (50 + 100) / 2 - 50


@pytest.mark.parametrize(
    ("lo", "hi", "base", "upper", "expected"),
    [
        (40, 80, 50, None, 10.0),  # (40 + 80) / 2 - 50, with a minimum under the base kept as it is
        (40, 50, 50, None, 0.0),  # a mean under the base counts nothing, never negative
        (10, 35, 10, 29, 9.5),  # Funderburk et al.'s cap: both capped at 29 first, (10 + 29) / 2 - 10
    ],
)
def test_simple_average_by_hand(lo, hi, base, upper, expected):
    assert dd.degree_days_average(lo, hi, base, upper) == pytest.approx(expected)


def test_a_mean_just_below_the_base_is_zero_for_the_sine_when_the_max_is_below_it():
    assert dd.degree_days_sine(40, 50, 50) == 0  # the maximum at the base: nothing above it
