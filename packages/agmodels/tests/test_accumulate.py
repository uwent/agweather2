"""`agmodels.accumulate`'s running sum over a grid, a day at a time."""

import numpy as np
import pytest

from agmodels.accumulate import cumsum_days


@pytest.mark.parametrize("dtype", [np.float32, np.float64, bool, np.int16])
def test_cumsum_days_is_numpys_running_sum_to_the_bit(dtype):
    rng = np.random.default_rng(5)
    for shape in ((40,), (40, 3, 5)):
        values = (rng.uniform(-3, 9, shape) > 2 if dtype is bool else rng.uniform(-3, 9, shape)).astype(dtype)
        assert_bits = np.testing.assert_array_equal
        assert_bits(cumsum_days(values), np.cumsum(values, axis=0))
        assert_bits(cumsum_days(values, dtype=np.float64), np.cumsum(values, axis=0, dtype=np.float64))
        assert cumsum_days(values).dtype == np.cumsum(values, axis=0).dtype
