"""The compiled grid features (`features_grid`) against the NumPy references they repeat (`scab_features`, `livestock.cci`)."""

import numpy as np
import pytest

from agmodels import features, livestock
from agmodels.features_grid import NAMES, cci_grid, scab_features_grid

WINDOW = features.SCAB_HOURS


def _hours(rng, n: int, cells: tuple[int, int]):
    """Hours with long wet spells (rain and high humidity in runs), dry gaps between them, and some missing hours."""
    shape = (n, *cells)
    t = rng.uniform(-2, 28, shape).astype(np.float32)
    spell = np.repeat(rng.random((n // 6 + 1, *cells)) < 0.35, 6, axis=0)[:n]
    rh = np.where(spell, rng.uniform(85, 100, shape), rng.uniform(30, 95, shape))
    rain = np.where(spell & (rng.random(shape) < 0.5), rng.uniform(0, 3, shape), 0.0).astype(np.float32)
    rain[rng.random(shape) < 0.05] = np.float32(0.254)  # exactly the threshold
    t[rng.random(shape) < 0.002] = np.nan
    rh[rng.random(shape) < 0.002] = np.nan
    rain[rng.random(shape) < 0.002] = np.nan
    t[:, 0, 0] = np.float32(15.0)  # a cell wet for days on end: periods reach back past the window
    rh[:, 0, 0] = 99.0
    rain[:, 0, 0] = np.float32(1.0)
    return t, rh, rain


@pytest.mark.parametrize("rh_dtype", [np.float32, np.float64])
def test_the_kernel_matches_scab_features_day_by_day(rh_dtype):
    rng = np.random.default_rng(7)
    days = 9
    n = WINDOW + 24 * (days - 1) + 5  # hours to spare after the last window
    t, rh, rain = _hours(rng, n, (6, 8))
    rh = rh.astype(rh_dtype)
    starts = np.array([24 * d for d in range(days)])
    clock = np.arange(n) % 24
    local_hours = [clock[s : s + WINDOW] for s in starts]
    found = scab_features_grid(t, rh, rain, starts, local_hours)
    assert set(found) == set(NAMES)
    for d, s in enumerate(starts):
        expected = features.scab_features(t[s : s + WINDOW], rh[s : s + WINDOW], rain[s : s + WINDOW], local_hours[d])
        for name in NAMES:
            want = np.asarray(expected[name], dtype=np.float32)
            assert found[name].dtype == np.float32 and found[name].shape == (days, 6, 8)
            np.testing.assert_array_equal(found[name][d], want, err_msg=f"{name} on day {d}")
    # the data exercise what they should: infections, missing days, periods begun before the window
    assert np.nansum(found["scab_infection"]) > 0
    assert np.isnan(found["scab_infection"]).any() and np.isfinite(found["scab_infection"]).any()
    assert (found["scab_period_truncated"][:, 0, 0] == 1).all()


def test_the_kernel_refuses_windows_outside_the_hours():
    hours = np.zeros((WINDOW + 3, 2, 2), dtype=np.float32)
    clock = np.arange(WINDOW) % 24
    with pytest.raises(ValueError, match="outside the hours"):
        scab_features_grid(hours, hours, hours, np.array([4]), [clock])
    with pytest.raises(ValueError, match="clock hours"):
        scab_features_grid(hours, hours, hours, np.array([0]), [clock[:-1]])


def test_the_cci_kernel_matches_livestock_cci():
    rng = np.random.default_rng(3)
    shape = (30, 5, 7)
    t = rng.uniform(-30, 45, shape).astype(np.float32)
    rh = rng.uniform(5, 100, shape)
    wind = (rng.integers(0, 150, shape) * np.float32(0.1)).astype(np.float32)  # as stored, so the memo is used
    wind[1] = rng.uniform(0, 15, shape[1:])  # and values it hasn't seen
    sun = rng.uniform(0, 1000, shape).astype(np.float32)
    wind[0, 0, 0], sun[0, 0, 1] = -0.5, -3.0  # below zero: taken as calm and dark
    for values in (t, rh, wind, sun):
        values[rng.random(shape) < 0.03] = np.nan
    found = cci_grid(t, rh, wind, sun)
    expected = livestock.cci(t, rh, wind, sun)
    assert found.dtype == np.float64 and found.shape == shape
    # The same libm calls in the same order, equal to the bit on one machine; another CPU's math library (CI's) can differ
    # in the last bit, so the check allows a few ulps
    np.testing.assert_allclose(found, expected, rtol=1e-14, atol=0)
