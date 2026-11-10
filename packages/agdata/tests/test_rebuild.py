from datetime import UTC, date, datetime

import numpy as np

from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.daily import rollup_days
from agdata.grid import Window
from agdata.rebuild import find_stale, rebuild_stale
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)


def test_a_feature_from_older_code_is_found_and_recomputed(tmp_path):
    hourly = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())
    shape = (96, *WINDOW.shape)
    hourly.write(
        datetime(2025, 7, 1, tzinfo=UTC),
        {"air_temperature": np.full(shape, 22.0), "dew_point": np.full(shape, 21.0)},
        source="test",
    )
    rollup_days(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 3))
    # Rolled up directly, without the models' ingredients (the rollup hook's): reported until built
    assert find_stale(tmp_path).stale == {"ingredients/2025": ["(not built)"]}

    # Older code wrote a wrong value and its version
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    t = daily.index_of(date(2025, 7, 2))
    daily.write(date(2025, 7, 2), {"hours_rh_over_90": np.zeros((2, *WINDOW.shape))}, source="derived")
    daily._array("hours_rh_over_90").attrs["version"] = 0
    assert find_stale(tmp_path).stale == {"daily/2025": ["hours_rh_over_90"], "ingredients/2025": ["(not built)"]}

    assert rebuild_stale(tmp_path, WINDOW, log=lambda line: None).stale == {}
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    np.testing.assert_array_equal(daily.read_steps("hours_rh_over_90", t, t + 2), 24)  # RH 94%


def test_a_store_on_local_days_moves_to_grid_days(tmp_path):
    from agdata.daily import cell_timezones, on_grid_days

    hourly = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())
    hours = np.arange(96, dtype=float)[:, None, None] * 0.1 * np.ones((1, *WINDOW.shape))  # 0.1 °C more each hour
    hourly.write(datetime(2025, 7, 1, tzinfo=UTC), {"air_temperature": hours}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 2))
    # As a store written before D74 records it: each cell's local zone, and a local day's values (CDT, from 05:00Z)
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    daily.group.attrs["timezones"] = ["America/Chicago"]
    t = daily.index_of(date(2025, 7, 2))
    daily.write(date(2025, 7, 2), {"air_temperature_min": np.full((1, *WINDOW.shape), 3.0)}, source="derived")
    assert find_stale(tmp_path).stale["daily/2025"] == ["(local days, D74)"]

    rebuild_stale(tmp_path, WINDOW, log=lambda line: None)
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    assert on_grid_days(daily) and cell_timezones(daily)[0] == ["Etc/GMT+6"]
    np.testing.assert_allclose(daily.read_steps("air_temperature_min", t, t + 1), 3.1)  # July 2 07:00Z, CST
    assert "daily/2025" not in find_stale(tmp_path).stale


def test_a_total_from_older_code_is_rebuilt_from_the_daily_store(tmp_path, fx):
    from agdata.catalog import CUMULATIVE_VARIABLES

    fx.archive(tmp_path, datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 7, tzinfo=UTC))
    totals = GridStore.open(tmp_path, CUMULATIVE, 2025, CUMULATIVE_VARIABLES.values())
    t = totals.index_of(date(2025, 7, 5))
    right = totals.read_steps("dd_sine_50", t, t + 1)
    assert (right > 0).all()
    totals.write(date(2025, 7, 5), {"dd_sine_50": np.zeros((1, *WINDOW.shape))}, source="derived")  # older code's value
    totals._array("dd_sine_50").attrs["version"] = 0
    assert find_stale(tmp_path).stale == {"cumulative/2025": ["dd_sine_50"]}

    lines: list[str] = []
    assert rebuild_stale(tmp_path, WINDOW, log=lines.append).stale == {}
    assert lines == ["cumulative/2025: rebuilding for dd_sine_50"]
    totals = GridStore.open(tmp_path, CUMULATIVE, 2025, CUMULATIVE_VARIABLES.values())
    np.testing.assert_allclose(totals.read_steps("dd_sine_50", t, t + 1), right, atol=0.5)


def _written(data_dir, layout, name: str) -> np.ndarray:
    from agdata.catalog import CUMULATIVE_VARIABLES

    variables = DAILY_VARIABLES if layout is DAILY else CUMULATIVE_VARIABLES
    return GridStore.open(data_dir, layout, 2025, variables.values()).read_meta(f"{name}.written")


def test_a_stale_feature_rolls_up_alone_and_leaves_the_rest_as_it_was(tmp_path, fx):
    """C6's case: a feature from older code (or new) is rolled up from the hours it reads, and nothing that reads
    other variables is rewritten: the other daily variables, the running totals, the timecopy, the ingredients."""
    from agdata import modelmaps
    from agdata.daily import days_from_hours

    fx.archive(tmp_path, datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 7, tzinfo=UTC))
    modelmaps.build(tmp_path, WINDOW, 2025)
    before = {
        "tmin": _written(tmp_path, DAILY, "air_temperature_min"),
        "rh": _written(tmp_path, DAILY, "hours_rh_over_90"),
        "dd": _written(tmp_path, CUMULATIVE, "dd_sine_50"),
        "chill": _written(tmp_path, CUMULATIVE, "chill_portions"),
    }
    ingredient = next(iter(modelmaps.stored()))
    ingredients_before = GridStore.open(tmp_path, modelmaps.INGREDIENTS, 2025, modelmaps.variables()).read_meta(
        f"{ingredient}.written"
    )
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    t = daily.index_of(date(2025, 7, 3))
    daily.write(date(2025, 7, 3), {"thi_max": np.zeros((1, *WINDOW.shape))}, source="derived")  # older code's
    daily._array("thi_max").attrs["version"] = 0
    assert find_stale(tmp_path).stale == {"daily/2025": ["thi_max"]}

    lines: list[str] = []
    assert rebuild_stale(tmp_path, WINDOW, log=lines.append).stale == {}
    assert lines == ["daily/2025: rolling up 2025-07-02 to 2025-07-05 for thi_max"]
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    expected = days_from_hours(tmp_path, WINDOW, date(2025, 7, 3), date(2025, 7, 3), ["thi_max"])["thi_max"]
    np.testing.assert_allclose(daily.read_steps("thi_max", t, t + 1), expected, atol=0.05)
    np.testing.assert_array_equal(_written(tmp_path, DAILY, "air_temperature_min"), before["tmin"])
    np.testing.assert_array_equal(_written(tmp_path, DAILY, "hours_rh_over_90"), before["rh"])
    np.testing.assert_array_equal(_written(tmp_path, CUMULATIVE, "dd_sine_50"), before["dd"])
    np.testing.assert_array_equal(_written(tmp_path, CUMULATIVE, "chill_portions"), before["chill"])
    ingredients_after = GridStore.open(tmp_path, modelmaps.INGREDIENTS, 2025, modelmaps.variables()).read_meta(
        f"{ingredient}.written"
    )
    np.testing.assert_array_equal(ingredients_after, ingredients_before)


def test_a_rollup_of_some_names_gives_the_full_rollups_values(tmp_path, fx):
    from agdata.daily import days_from_hours, hourly_read_for

    fx.archive(tmp_path, datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 4, tzinfo=UTC))
    names = ["cci_max", "chill_hours", "hours_rh_over_90_night", "et0_sum_estimate", "air_temperature_min_overnight"]
    every = days_from_hours(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 3))
    some = days_from_hours(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 3), names)
    assert set(some) == set(names)
    for name in names:
        np.testing.assert_array_equal(some[name], every[name], err_msg=name)
    assert hourly_read_for(["chill_hours"]) == ["air_temperature"]
    assert set(hourly_read_for(["cci_max"])) == {"air_temperature", "dew_point", "wind_speed", "shortwave_radiation"}


def test_what_a_rebuild_rolls_up_and_what_follows():
    from agdata.cumulative import steps_for
    from agdata.rebuild import StaleReport, daily_to_roll_up, plan

    assert daily_to_roll_up(["thi_max"]) == ["thi_max"]
    assert daily_to_roll_up([], moved=True) is None
    corrected = daily_to_roll_up([], corrected=True)
    assert corrected is not None and {"shortwave_radiation_sum", "et0_sum", "cci_max"} <= set(corrected)
    assert "thi_max" not in corrected and "air_temperature_min" not in corrected
    feature = steps_for(["thi_max", "chill_hours"])
    assert not (feature.timecopy or feature.totals or feature.chill or feature.ingredients)
    tmin = steps_for(["air_temperature_min"])
    assert tmin.timecopy and tmin.totals and tmin.ingredients and not tmin.chill
    assert steps_for(None).chill and steps_for(None).ingredients is None
    lines = plan(StaleReport(stale={"daily/2025": ["thi_max"], "cumulative/2025": ["chill_portions"]}))
    assert lines[0] == "daily/2025: roll up 1 daily variable from 4 hourly ones, and nothing else follows"
    assert lines[1] == "cumulative/2025: rebuild chill portions' seasons"
