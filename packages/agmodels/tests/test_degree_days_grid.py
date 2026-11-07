"""The parallel degree-day kernel (`degree_days_grid`) against the NumPy methods it repeats (`degree_days`)."""

import numpy as np
import pytest

from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine
from agmodels.degree_days_grid import degree_days_c

NUMPY = {"sine": degree_days_sine, "average": degree_days_average, "modified": degree_days_modified}


def _temperatures(rng):
    lo = rng.uniform(-20, 30, (40, 7, 9)).astype(np.float32)
    hi = (lo + rng.uniform(0, 18, lo.shape)).astype(np.float32)
    lo[rng.random(lo.shape) < 0.05] = np.nan
    hi[rng.random(hi.shape) < 0.05] = np.nan
    crossed = rng.random(lo.shape) < 0.02  # min above max: NaN in both
    lo[crossed], hi[crossed] = hi[crossed] + 1, lo[crossed]
    lo[0, 0, :3] = hi[0, 0, :3] = np.float32((50 - 32) / 1.8)  # a day at the base
    return lo, hi


@pytest.mark.parametrize("method", list(NUMPY))
@pytest.mark.parametrize(("base", "upper"), [(50.0, 86.0), (50.0, None), (41.0, 88.0), (32.0, None)])
def test_the_kernel_matches_the_numpy_methods(method, base, upper):
    lo, hi = _temperatures(np.random.default_rng(4))
    expected = NUMPY[method](lo.astype(np.float64) * 1.8 + 32, hi.astype(np.float64) * 1.8 + 32, base, upper)
    found = degree_days_c(lo, hi, method, base, upper)
    assert found.dtype == np.float32 and found.shape == lo.shape
    np.testing.assert_array_equal(np.isnan(found), np.isnan(expected))
    np.testing.assert_allclose(found, expected.astype(np.float32), rtol=1e-6, atol=1e-6)


def test_the_kernel_refuses_shapes_that_differ():
    with pytest.raises(ValueError, match="differ in shape"):
        degree_days_c(np.zeros((2, 2)), np.zeros((2, 3)), "sine", 50.0, None)
