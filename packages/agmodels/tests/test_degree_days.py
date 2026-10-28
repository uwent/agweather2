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
