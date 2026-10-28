from datetime import date

import numpy as np
import pytest

from agdata.catalog import CUMULATIVE_VARIABLES
from agdata.cumulative import MAX_BRIDGE_DAYS, rebuild_year, running_totals
from agdata.daily import open_or_create_daily
from agdata.grid import Window
from agdata.store import CUMULATIVE, GridStore
from agmodels.degree_days import degree_days_modified, degree_days_sine

PAD = MAX_BRIDGE_DAYS
DAYS = 40
WINDOW = Window(900, 902, 1400, 1403)


def series(days=DAYS):
    """One cell's padded daily series: a warm-up from about 0 to 25 °C (linear, so interpolation is exact)."""
    n = np.arange(days + 2 * PAD, dtype=float)
    tmin = (n * 0.5 - 5)[:, None, None]
    tmax = tmin + 12
    et0 = np.full_like(tmin, 3.0)
    precip = np.full_like(tmin, 1.0)
    return tmin, tmax, et0, precip


def f(c):
    return c * 1.8 + 32


def test_complete_days_sum_exactly():
    tmin, tmax, et0, precip = series()
    out = running_totals(tmin, tmax, et0, precip)
    year = slice(PAD, PAD + DAYS)
    expected = np.cumsum(degree_days_sine(f(tmin[year]), f(tmax[year]), 50), axis=0)
    np.testing.assert_allclose(out["dd_sine_50"], expected)
    expected = np.cumsum(degree_days_modified(f(tmin[year]), f(tmax[year]), 50, 86), axis=0)
    np.testing.assert_allclose(out["dd_modified_50_86"], expected)
    np.testing.assert_allclose(out["precipitation"][-1], DAYS)
    np.testing.assert_allclose(out["et0"][-1], 3 * DAYS)
    for name in ("temperature_estimated_days", "temperature_missing_days", "et0_missing_days"):
        assert out[name][-1] == 0


def test_a_sine_pair_is_the_difference_of_two_cubes():
    tmin, tmax, et0, precip = series()
    out = running_totals(tmin, tmax, et0, precip)
    year = slice(PAD, PAD + DAYS)
    pair = np.cumsum(degree_days_sine(f(tmin[year]), f(tmax[year]), 50, 86), axis=0)
    np.testing.assert_allclose(out["dd_sine_50"] - out["dd_sine_86"], pair, atol=1e-9)


def test_short_gaps_are_bridged_and_counted():
    tmin, tmax, et0, precip = series()
    complete = running_totals(tmin, tmax, et0, precip)
    tmin[PAD + 10 : PAD + 13] = np.nan  # 3 days without a min
    et0[PAD + 20 : PAD + 22] = np.nan
    precip[PAD + 5] = np.nan
    out = running_totals(tmin, tmax, et0, precip)
    np.testing.assert_allclose(out["dd_sine_50"], complete["dd_sine_50"])  # linear weather: exact estimate
    assert out["temperature_estimated_days"][-1] == 3
    assert out["temperature_missing_days"][-1] == 0
    np.testing.assert_allclose(out["et0"][-1], 3 * DAYS)
    assert out["et0_estimated_days"][-1] == 2
    np.testing.assert_allclose(out["precipitation"][-1], DAYS - 1)  # never estimated
    assert out["precipitation_missing_days"][-1] == 1
    assert out["precipitation_missing_days"][4] == 0


def test_long_gaps_add_nothing_and_count_as_missing():
    tmin, tmax, et0, precip = series()
    tmax[PAD + 10 : PAD + 10 + MAX_BRIDGE_DAYS + 1] = np.nan
    out = running_totals(tmin, tmax, et0, precip)
    gap = slice(9, 10 + MAX_BRIDGE_DAYS)
    assert np.all(np.diff(out["dd_sine_41"][gap], axis=0) == 0)
    assert out["temperature_missing_days"][-1] == MAX_BRIDGE_DAYS + 1
    assert out["temperature_estimated_days"][-1] == 0


def test_the_first_days_bridge_from_the_previous_year():
    tmin, tmax, et0, precip = series()
    complete = running_totals(tmin, tmax, et0, precip)
    tmin[PAD : PAD + 2] = np.nan  # Jan 1-2, with Dec 25-31 known
    out = running_totals(tmin, tmax, et0, precip)
    np.testing.assert_allclose(out["dd_sine_39p2"], complete["dd_sine_39p2"])
    tmin[:PAD] = np.nan  # no previous year
    assert running_totals(tmin, tmax, et0, precip)["temperature_missing_days"][-1] == 2


def test_rebuild_writes_the_year_once_rounded(tmp_path):
    daily = open_or_create_daily(tmp_path, 2025, WINDOW)
    tmin, tmax, et0, precip = (a[PAD : PAD + DAYS] for a in series())
    shape = (DAYS, *WINDOW.shape)
    daily.write(
        date(2025, 1, 1),
        {
            "air_temperature_min": np.broadcast_to(tmin, shape),
            "air_temperature_max": np.broadcast_to(tmax, shape),
            "et0_sum": np.broadcast_to(et0, shape),
            "precipitation_sum": np.broadcast_to(precip, shape),
        },
        source="derived",
    )
    assert rebuild_year(tmp_path, WINDOW, 2025) == date(2025, 2, 9)
    store = GridStore.open(tmp_path, CUMULATIVE, 2025, CUMULATIVE_VARIABLES.values())
    exact = np.cumsum(degree_days_sine(f(tmin), f(tmax), 45), axis=0)[:, 0, 0]
    stored = store.read_point("dd_sine_45", 900, 1400, 0, DAYS)
    assert np.max(np.abs(stored - exact)) <= 0.25  # rounded once to 0.5 °F·d, never compounded
    assert np.isnan(store.read_point("dd_sine_45", 900, 1400, DAYS, DAYS + 1)).all()  # after the last day


def test_a_year_without_daily_data_is_skipped(tmp_path):
    assert rebuild_year(tmp_path, WINDOW, 2025) is None
    open_or_create_daily(tmp_path, 2025, WINDOW)
    assert rebuild_year(tmp_path, WINDOW, 2025) is None


@pytest.mark.parametrize("name", list(CUMULATIVE_VARIABLES))
def test_every_cumulative_variable_is_built(name):
    assert name in running_totals(*series())


def test_a_daily_et0_estimate_is_used_and_counted():
    tmin, tmax, et0, precip = series()
    estimate = np.full_like(et0, np.nan)
    et0[PAD + 3] = np.nan
    estimate[PAD + 3] = 2.5
    out = running_totals(tmin, tmax, et0, precip, estimate)
    np.testing.assert_allclose(out["et0"][-1], 3 * (DAYS - 1) + 2.5)
    assert out["et0_estimated_days"][-1] == 1


def test_a_partial_rebuild_writes_the_same_totals_from_the_changed_day(tmp_path):
    daily = open_or_create_daily(tmp_path, 2025, WINDOW)
    tmin, tmax, et0, precip = (a[PAD : PAD + DAYS] for a in series())
    shape = (DAYS, *WINDOW.shape)
    names = ("air_temperature_min", "air_temperature_max", "et0_sum", "precipitation_sum")
    daily.write(
        date(2025, 1, 1),
        {n: np.broadcast_to(v, shape) for n, v in zip(names, (tmin, tmax, et0, precip), strict=True)},
        source="derived",
    )
    rebuild_year(tmp_path, WINDOW, 2025)
    store = GridStore.open(tmp_path, CUMULATIVE, 2025, CUMULATIVE_VARIABLES.values())
    full = store.read_point("dd_sine_45", 900, 1400, 0, DAYS)
    daily.write(date(2025, 1, 30), {"air_temperature_max": np.full((1, *WINDOW.shape), np.nan)}, source="derived")
    rebuild_year(tmp_path, WINDOW, 2025, changed_from=date(2025, 1, 30))
    partial = store.read_point("dd_sine_45", 900, 1400, 0, DAYS)
    np.testing.assert_array_equal(partial[:29], full[:29])
    assert store.read_point("temperature_estimated_days", 900, 1400, DAYS - 1, DAYS)[0] == 1  # Jan 30 bridged
