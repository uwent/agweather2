import numpy as np

from agdata.catalog import variable
from agdata.qc import check_range, fill_short_gaps, remove_spikes, run_qc


def test_range_check_marks_implausible_values_missing():
    cleaned, bad = check_range(variable("air_temperature"), np.array([20.0, 75.0, -80.0, np.nan]))
    np.testing.assert_array_equal(np.isnan(cleaned), [False, True, True, True])
    assert bad == 2


def test_spikes_up_and_down_but_not_steady_changes():
    series = np.array([10.0, 11, 30, 12, 13, -5, 14, 20, 26, 32])
    cleaned, spikes = remove_spikes(series, 12)
    assert spikes == 2
    assert np.isnan(cleaned[2]) and np.isnan(cleaned[5])
    assert np.isfinite(cleaned[7:]).all()  # a steady 6-degree climb is not a spike


def test_short_interior_gaps_are_interpolated():
    series = np.array([np.nan, 1.0, np.nan, np.nan, 4.0, np.nan, np.nan, np.nan, np.nan, 9.0, np.nan])
    filled, mask = fill_short_gaps(series, max_gap=3)
    np.testing.assert_allclose(filled[:5], [np.nan, 1, 2, 3, 4])
    assert np.isnan(filled[5:9]).all()  # a 4-hour gap stays missing
    assert np.isnan(filled[0]) and np.isnan(filled[-1])  # edges aren't extrapolated
    np.testing.assert_array_equal(mask, [False, False, True, True] + [False] * 7)


def test_gap_filling_works_per_cell_on_a_grid():
    block = np.full((5, 2, 2), np.nan)
    block[0], block[4] = 0.0, 4.0
    block[:, 1, 1] = [0, np.nan, np.nan, np.nan, np.nan]
    filled, mask = fill_short_gaps(block, max_gap=3)
    np.testing.assert_allclose(filled[:, 0, 0], [0, 1, 2, 3, 4])
    assert np.isnan(filled[1:, 1, 1]).all() and not mask[:, 1, 1].any()


def test_precipitation_gaps_are_never_filled():
    result = run_qc(variable("precipitation"), np.array([1.0, np.nan, 3.0]))
    assert np.isnan(result.values[1]) and not result.filled.any()


def test_run_qc_counts():
    result = run_qc(variable("air_temperature"), np.array([20.0, 21, 99, 22, 45, 23]))
    assert result.out_of_range == 1
    assert result.spikes == 1  # 45 between 22 and 23
    np.testing.assert_allclose(result.values, [20, 21, 21.5, 22, 22.5, 23])  # both refilled from neighbors
    assert result.filled.sum() == 2
