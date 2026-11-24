import numpy as np
import pytest

from agdata import grids
from agdata.grids import Stat, cube_terms, degree_days, fill_cells, reduce
from agmodels.degree_days import degree_days_modified, degree_days_sine

NAN = np.nan


def _series(*values) -> np.ndarray:
    return np.array(values, dtype=float)[:, None, None]


def test_only_cells_with_gaps_are_filled_and_the_rest_untouched():
    values = np.stack([_series(1, NAN, 3)[:, 0, 0], _series(1, 2, 3)[:, 0, 0]], axis=1)[:, None, :]
    filled, mask = fill_cells(values)
    assert filled[:, 0, 0].tolist() == [1, 2, 3] and mask[:, 0, 0].tolist() == [False, True, False]
    assert not mask[:, 0, 1].any()


def test_a_sum_bridges_short_gaps_except_precipitation():
    et0 = _series(1, NAN, 3, 4)
    value, estimated, missing = reduce(et0, "sum", "et0_sum")
    assert value[0, 0] == 10 and estimated[0, 0] == 1 and missing[0, 0] == 0
    value, estimated, missing = reduce(et0, "sum", "et0_sum", gaps="missing")
    assert value[0, 0] == 8 and estimated[0, 0] == 0 and missing[0, 0] == 1
    rain = _series(1, NAN, 3, 4)
    value, estimated, missing = reduce(rain, "sum", "precipitation_sum")
    assert value[0, 0] == 8 and estimated[0, 0] == 0 and missing[0, 0] == 1


def test_levels_use_the_known_days_and_an_empty_cell_is_missing():
    temps = np.concatenate([_series(10, NAN, 30), _series(NAN, NAN, NAN)], axis=2)
    levels: tuple[tuple[Stat, float], ...] = (("mean", 20), ("min", 10), ("max", 30))
    for stat, expected in levels:
        value, estimated, missing = reduce(temps, stat, "air_temperature_max")
        assert value[0, 0] == expected and np.isnan(value[0, 1])
        assert missing.tolist() == [[1, 3]] and not estimated.any()
    value, _, missing = reduce(temps, "sum", "hours_rh_over_90")
    assert np.isnan(value[0, 1]) and missing[0, 1] == 3


def test_grid_degree_days_are_the_models_and_bands_dont_matter(monkeypatch):
    rng = np.random.default_rng(1)
    tmin = rng.uniform(0, 20, (40, 7, 9))
    tmax = tmin + rng.uniform(0, 15, tmin.shape)
    tmin[5, 2, 3] = NAN
    dd, estimated, usable = degree_days(tmin, tmax, "sine", 50, 86, "estimate")
    assert estimated[5, 2, 3] and usable.all()
    # A day missing either temperature is bridged in both, as at points (`/degree-days`)
    # (the grid's temperatures are float32, as the stores give them)
    f32 = {"lo": tmin.astype(np.float32).astype(np.float64), "hi": tmax.astype(np.float32).astype(np.float64)}
    lo, hi = f32["lo"].copy(), f32["hi"].copy()
    lo[5, 2, 3] = np.float32((f32["lo"][4, 2, 3] + f32["lo"][6, 2, 3]) / 2)
    hi[5, 2, 3] = np.float32((f32["hi"][4, 2, 3] + f32["hi"][6, 2, 3]) / 2)
    np.testing.assert_allclose(dd, degree_days_sine(lo * 1.8 + 32, hi * 1.8 + 32, 50, 86), rtol=1e-5, atol=1e-6)
    monkeypatch.setattr(grids, "BAND_CELL_DAYS", 40 * 9)  # a row at a time
    banded, _, _ = degree_days(tmin, tmax, "sine", 50, 86, "estimate")
    np.testing.assert_array_equal(banded, dd)
    dd, _, usable = degree_days(tmin, tmax, "modified", 50, 86, "missing")
    assert not usable[5, 2, 3] and np.isnan(dd[5, 2, 3])
    expected = degree_days_modified(f32["lo"] * 1.8 + 32, f32["hi"] * 1.8 + 32, 50, 86)
    np.testing.assert_allclose(dd, expected, rtol=1e-5, atol=1e-6)


def test_settings_kept_as_running_totals():
    assert cube_terms("sine", 50, None) == ("dd_sine_50", None)
    assert cube_terms("sine", 39.2, 86) == ("dd_sine_39p2", "dd_sine_86")
    assert cube_terms("modified", 50, 86) == ("dd_modified_50_86", None)
    assert cube_terms("sine", 48, 86) is None and cube_terms("average", 50, None) is None
    assert cube_terms("modified", 50, None) is None


@pytest.mark.parametrize("stat", ["mean", "min", "max", "sum"])
def test_reduce_keeps_the_cells_shape(stat: Stat):
    value, estimated, missing = reduce(np.ones((3, 4, 5)), stat, "et0_sum")
    assert value.shape == estimated.shape == missing.shape == (4, 5)


@pytest.mark.parametrize("gaps", ["estimate", "missing"])
def test_a_season_total_of_degree_days_is_the_sum_of_its_days(gaps):
    """`degree_days_total` (summed in the kernel) against `degree_days` then the sum the map took before."""
    from agdata.grids import degree_days, degree_days_total

    rng = np.random.default_rng(8)
    lo = rng.uniform(-5, 20, (60, 4, 5)).astype(np.float32)
    hi = (lo + rng.uniform(2, 15, lo.shape)).astype(np.float32)
    lo[rng.random(lo.shape) < 0.05] = np.nan
    hi[10:13, 2, 2] = np.nan  # a short gap
    lo[:, 3, 4] = np.nan  # a cell with no day (outside the coverage)
    dd, estimated, usable = degree_days(lo, hi, "sine", 50.0, 86.0, gaps)
    value, estimated_days, missing_days = degree_days_total(lo, hi, "sine", 50.0, 86.0, gaps)
    expected = np.where(usable.any(axis=0), np.where(usable, dd, 0.0).sum(axis=0, dtype=np.float64), np.nan)
    np.testing.assert_array_equal(value, expected)
    np.testing.assert_array_equal(estimated_days, estimated.sum(axis=0))
    np.testing.assert_array_equal(missing_days, (~usable).sum(axis=0))
    assert np.isnan(value[3, 4])
