"""Variables computed when read (`agdata.computed`): the formula and its gaps, a point's days and hours, and a map's
steps, each against computing the same from the stored inputs. The archive has 0.1 mm of rain and 0.05 mm of ET0 an
hour (a balance of +1.2 mm a day), with a block of hours missing from the rain alone."""

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import computed, series, testing
from agdata.catalog import VARIABLES, Variable
from agdata.computed import DAILY_COMPUTED, Computed
from agdata.cumulative import update_days
from agdata.point import daily_at_point, hourly_sources
from agdata.store import DAILY, HOURLY, GridStore
from agdata.timezones import GRID_ZONE

HOUR = timedelta(hours=1)
START = datetime(2025, 6, 1, 6, tzinfo=UTC)  # midnight CST
END = START + 6 * 24 * HOUR
NOW = END + 3 * HOUR
RAIN_GAP = (START + 3 * 24 * HOUR, START + 3 * 24 * HOUR + 5 * HOUR)  # hours ending 06Z–11Z on June 4: no rain data
CELL = (900, 1401)
WATER = DAILY_COMPUTED["water_balance"]


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    path = tmp_path_factory.mktemp("computed")
    times = [START + k * HOUR for k in range((END - START) // HOUR + 1)]
    values = testing.weather(times, warm=18.0)
    shape = values["air_temperature"].shape
    values |= {
        "surface_pressure": np.full(shape, 98.0),
        "relative_humidity": np.full(shape, 75.0),
        "et0": np.full(shape, 0.05),
    }
    gap = [k for k, t in enumerate(times) if RAIN_GAP[0] < t <= RAIN_GAP[1]]
    values["precipitation"][gap] = np.nan
    store = GridStore.create(path, HOURLY, 2025, testing.WINDOW, VARIABLES.values())
    store.write(times[0], values, source="urma")
    update_days(path, testing.WINDOW, date(2025, 6, 1), date(2025, 6, 6), ingredients=False)
    return path


def test_a_computed_value_is_missing_wherever_an_input_is():
    rain = np.array([5.0, np.nan, 1.0, 0.0])
    et0 = np.array([2.0, 3.0, np.nan, 4.0])
    found = WATER.compute({"precipitation_sum": rain, "et0_sum": et0})
    np.testing.assert_array_equal(found, [3.0, np.nan, np.nan, -4.0])


def test_a_computed_variable_reads_stored_ones_on_its_axis_and_isnt_one_itself():
    v = Variable(name="spread", long_name="Spread", unit="degC", scale=0.1, valid_min=-60, valid_max=60)
    with pytest.raises(ValueError, match="aren't stored day variables"):
        Computed(variable=v, axis="day", inputs=("air_temperature",), formula=lambda air_temperature: air_temperature)
    stored = Variable(name="et0_sum", long_name="ET0", unit="mm", scale=0.01, valid_min=0, valid_max=20)
    with pytest.raises(ValueError, match="stored variable already"):
        Computed(
            variable=stored,
            axis="day",
            inputs=("precipitation_sum",),
            formula=lambda precipitation_sum: precipitation_sum,
        )


def test_expand_and_complete_read_the_inputs_and_keep_what_was_asked():
    names = ["precipitation_sum", "water_balance", "et0_sum", "air_temperature_max"]
    read = computed.expand(names, DAILY_COMPUTED)
    assert read == ["precipitation_sum", "et0_sum", "air_temperature_max"]
    values = {"precipitation_sum": np.array([4.0]), "et0_sum": np.array([1.5]), "air_temperature_max": np.array([20])}
    found = computed.complete(values, ["water_balance", "et0_sum"], DAILY_COMPUTED)
    assert list(found) == ["water_balance", "et0_sum"] and found["water_balance"][0] == 2.5


def test_a_points_days_compute_it_from_the_rolled_up_inputs():
    first_hour = datetime(2025, 6, 1, tzinfo=UTC)
    n = 4 * 24
    hours = {"precipitation": np.full(n, 0.2), "et0": np.full(n, 0.05)}
    hours["precipitation"][20] = np.nan  # 20Z on June 1: that day has no rain total, so no balance
    days = daily_at_point(first_hour, hours, GRID_ZONE, date(2025, 6, 1), date(2025, 6, 2), names=["water_balance"])
    np.testing.assert_allclose(days["water_balance"], days["precipitation_sum"] - days["et0_sum"])
    assert np.isnan(days["water_balance"][0]) and days["water_balance"][1] == pytest.approx(3.6)  # 4.8 − 1.2
    assert hourly_sources()["water_balance"] == ("precipitation", "et0")


def test_a_cells_days_match_its_inputs_read_alone(archive):
    first, last = date(2025, 6, 1), date(2025, 6, 6)
    names = ["water_balance", "precipitation_sum"]
    found = series.point_days(archive, *CELL, first, last, names, now=NOW)
    inputs = series.point_days(archive, *CELL, first, last, ["precipitation_sum", "et0_sum"], now=NOW)
    expected = inputs.values["precipitation_sum"] - inputs.values["et0_sum"]
    np.testing.assert_allclose(found.values["water_balance"], expected)
    assert list(found.values) == names
    balance = found.values["water_balance"]
    assert np.isnan(balance[3]) and balance[0] == pytest.approx(1.2)  # June 4 lacks 6 hours of rain


def test_a_computed_hourly_variable_comes_from_its_inputs_hours(archive, monkeypatch):
    spread = Computed(
        variable=Variable(name="spread", long_name="Spread", unit="delta_degC", scale=0.1, valid_min=0, valid_max=80),
        axis="hour",
        inputs=("air_temperature", "dew_point"),
        formula=lambda air_temperature, dew_point: air_temperature - dew_point,
    )
    monkeypatch.setitem(computed.HOURLY_COMPUTED, "spread", spread)
    start, end = START + HOUR, START + 30 * HOUR
    found = series.cells_hours(archive, [CELL], start, end, ["spread", "precipitation"], now=NOW)[0]
    stored = series.cells_hours(archive, [CELL], start, end, ["air_temperature", "dew_point"], now=NOW)[0]
    assert list(found.values) == ["spread", "precipitation"]
    np.testing.assert_allclose(found.values["spread"], stored.values["air_temperature"] - stored.values["dew_point"])
    assert found.sources["spread"] == stored.sources["air_temperature"]


def test_a_maps_steps_combine_each_inputs_read(archive):
    first, last = date(2025, 6, 2), date(2025, 6, 5)
    reads = {name: series.grid_days(archive, DAILY, name, first, last, testing.WINDOW, NOW) for name in WATER.inputs}
    found = series.combine(WATER, reads)
    expected = reads["precipitation_sum"].values.astype(np.float64) - reads["et0_sum"].values
    np.testing.assert_allclose(found.values, expected, rtol=1e-6)
    assert found.values.dtype == np.float32 and found.steps == reads["et0_sum"].steps
    assert np.isnan(found.values[2]).all()  # June 4: no rain total anywhere
    assert found.kinds == [series.OBSERVED, series.OBSERVED, None, series.OBSERVED]
    assert found.sources == ("urma",)


def test_water_balance_totals_take_missing_rain_as_none_and_bridge_et0():
    rain = np.array([2.0, np.nan, np.nan, 1.0, 0.0, np.nan])  # the last day is past the data: not a gap
    et0 = np.array([3.0, 3.0, np.nan, 5.0, np.nan, 4.0])
    each, estimated = WATER.for_total({"precipitation_sum": rain, "et0_sum": et0})
    np.testing.assert_allclose(each[:5], [-1.0, -3.0, -4.0, -4.0, -4.5])  # ET0 bridged 3→5 and 5→4
    assert np.isnan(each[5]) and list(estimated) == [False, True, True, False, True, False]
    raw, none = WATER.for_total({"precipitation_sum": rain, "et0_sum": et0}, gaps="missing")
    assert np.isfinite(raw).sum() == 2 and not none.any()  # nothing filled: a day missing either input is missing
    grid, _ = WATER.for_total({"precipitation_sum": rain[:, None, None], "et0_sum": et0[:, None, None]})
    np.testing.assert_allclose(grid[:, 0, 0], each)  # the same along axis 0 on a map
