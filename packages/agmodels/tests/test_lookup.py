import numpy as np

from agmodels.lookup import level_reached, steps_over


def test_steps_over_counts_thresholds_exceeded_and_keeps_missing_values_missing():
    found = steps_over([5.0, 10.0, 10.5, 41.0, np.nan], 10, 20, 30, 40)
    np.testing.assert_array_equal(found, [0, 0, 1, 4, np.nan])


def test_level_reached_counts_thresholds_reached():
    np.testing.assert_array_equal(level_reached([5.0, 10.0, np.nan], 10, 20), [0, 1, np.nan])
