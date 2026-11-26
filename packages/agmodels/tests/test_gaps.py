import numpy as np

from agmodels.gaps import MAX_GAP_DAYS, fill_inputs, fill_short_gaps, fill_zero, no_value

NAN = np.nan


def test_interpolation_fills_short_interior_gaps_only():
    values = np.array([NAN, 1.0, NAN, NAN, 4.0, NAN])
    filled, mask = fill_short_gaps(values, MAX_GAP_DAYS)
    np.testing.assert_allclose(filled, [NAN, 1, 2, 3, 4, NAN], equal_nan=True)
    assert mask.tolist() == [False, False, True, True, False, False]


def test_interpolation_leaves_long_gaps_missing():
    values = np.array([1.0, *[NAN] * (MAX_GAP_DAYS + 1), 2.0])
    filled, mask = fill_short_gaps(values, MAX_GAP_DAYS)
    assert np.isnan(filled[1:-1]).all() and not mask.any()


def test_rain_is_none_where_missing_inside_the_data_but_the_future_stays_empty():
    values = np.array([NAN, 3.0, NAN, NAN, NAN, NAN, NAN, NAN, NAN, NAN, 2.0, NAN])
    filled, mask = fill_zero(values)
    np.testing.assert_allclose(filled, [NAN, 3, 0, 0, 0, 0, 0, 0, 0, 0, 2, NAN], equal_nan=True)
    assert mask.sum() == 8


def test_grids_fill_each_cell_along_time():
    grid = np.array([[1.0, 5.0], [NAN, NAN], [3.0, NAN]])  # (days, cells)
    filled, mask = fill_short_gaps(grid, MAX_GAP_DAYS)
    np.testing.assert_allclose(filled, [[1, 5], [2, NAN], [3, NAN]], equal_nan=True)
    assert mask.tolist() == [[False, False], [True, False], [False, False]]


def test_inputs_without_a_method_pass_through():
    daily = {"air_temperature_min": np.array([1.0, NAN, 3.0]), "other": np.array([1.0, NAN, 3.0])}
    filled, estimated = fill_inputs(daily, {"air_temperature_min": "interpolate"})
    assert filled["air_temperature_min"][1] == 2.0 and np.isnan(filled["other"][1])
    assert estimated["air_temperature_min"].tolist() == [False, True, False]
    assert not estimated["other"].any()


def test_a_conditional_means_null_on_a_day_without_its_hours_is_no_gap():
    # Humid hours' temperature: none on days 1 and 5 (no humid hours: the answer), missing on day 3 (no data)
    hours = np.array([5.0, 0.0, 6.0, NAN, 4.0, 0.0])
    temperature = np.array([15.0, NAN, 17.0, NAN, 19.0, NAN])
    t = "temperature_mean_rh_over_90_from_6pm"
    daily = {"hours_rh_over_90_from_6pm": hours, t: temperature}
    assert no_value(daily)[t].tolist() == [False, True, False, False, False, True]
    filled, estimated = fill_inputs(daily, dict.fromkeys(daily, "interpolate"))
    np.testing.assert_allclose(filled[t], [15, NAN, 17, 18, 19, NAN], equal_nan=True)
    assert estimated[t].tolist() == [False, False, False, True, False, False]
    assert estimated["hours_rh_over_90_from_6pm"].tolist() == [False, False, False, True, False, False]


def test_a_conditional_mean_read_without_its_companion_is_filled_as_any_input():
    t = "temperature_mean_rh_over_90_from_6pm"
    filled, estimated = fill_inputs({t: np.array([15.0, NAN, 17.0])}, {t: "interpolate"})
    assert filled[t][1] == 16 and estimated[t][1]
