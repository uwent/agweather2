from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata.catalog import variable
from agdata.grid import Window
from agdata.store import DAILY, HOURLY, GridStore, steps_in_year

WINDOW = Window(900, 940, 1400, 1450)  # 40 x 50 cells in Wisconsin
TEMP, RAIN = variable("air_temperature"), variable("precipitation")


@pytest.fixture
def hourly(tmp_path):
    return GridStore.create(tmp_path, HOURLY, 2025, WINDOW, [TEMP, RAIN], chunks=(48, 16, 16))


def test_layout_and_length(tmp_path, hourly):
    assert hourly.path == tmp_path / "hourly" / "2025.zarr"
    assert hourly.length == 8760
    assert steps_in_year(2024, "hour") == 8784
    assert steps_in_year(2024, "day") == 366


def test_write_block_then_read_point_and_block(tmp_path, hourly):
    rng = np.random.default_rng(1)
    block = rng.uniform(-10, 30, size=(5, *WINDOW.shape))
    start = datetime(2025, 7, 1, 6, tzinfo=UTC)
    hourly.write(start, {"air_temperature": block}, source="urma")

    reopened = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, RAIN])
    t0 = reopened.index_of(start)
    series = reopened.read_point("air_temperature", 910, 1420, t0 - 1, t0 + 6)
    assert np.isnan(series[0]) and np.isnan(series[-1])  # never written
    np.testing.assert_allclose(series[1:6], block[:, 10, 20], atol=0.05)

    tile = reopened.read_block("air_temperature", t0 + 2, Window(905, 915, 1410, 1430))
    np.testing.assert_allclose(tile, block[2, 5:15, 10:30], atol=0.05)

    sources = reopened.sources("air_temperature")
    assert sources[t0 : t0 + 5] == ["urma"] * 5
    assert sources[t0 + 5] is None


def test_missing_stays_missing_and_zero_stays_zero(hourly):
    rain = np.zeros(WINDOW.shape)
    rain[0, 0] = np.nan
    when = datetime(2025, 1, 1, tzinfo=UTC)
    hourly.write(when, {"precipitation": rain}, source="urma")
    assert np.isnan(hourly.read_point("precipitation", 900, 1400, 0, 1)[0])
    assert hourly.read_point("precipitation", 900, 1401, 0, 1)[0] == 0.0


def test_rewriting_an_hour_replaces_it_and_its_source(hourly):
    when = datetime(2025, 3, 1, 12, tzinfo=UTC)
    hourly.write(when, {"air_temperature": np.full(WINDOW.shape, 1.0)}, source="rtma")
    hourly.write(when, {"air_temperature": np.full(WINDOW.shape, 2.0)}, source="urma")
    t = hourly.index_of(when)
    assert hourly.read_point("air_temperature", 920, 1440, t, t + 1)[0] == pytest.approx(2.0)
    assert hourly.sources("air_temperature")[t] == "urma"


def test_time_checks(hourly):
    with pytest.raises(ValueError):
        hourly.index_of(datetime(2025, 1, 1, 0, 30, tzinfo=UTC))
    with pytest.raises(ValueError):
        hourly.index_of(datetime(2025, 1, 1))  # naive  # noqa: DTZ001
    with pytest.raises(IndexError):
        hourly.index_of(datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        hourly.write(datetime(2025, 1, 1, tzinfo=UTC), {"air_temperature": np.zeros((3, 3))}, source="urma")
    with pytest.raises(IndexError):
        hourly.read_point("air_temperature", 0, 0)


def test_daily_store_by_date(tmp_path):
    daily = GridStore.create(tmp_path, DAILY, 2024, WINDOW, [TEMP])
    assert daily.length == 366
    daily.write(date(2024, 12, 31), {"air_temperature": np.full(WINDOW.shape, -5.0)}, source="derived")
    assert daily.read_block("air_temperature", daily.index_of(date(2024, 12, 31)))[0, 0] == pytest.approx(-5.0)
    assert daily.time_of(365) == datetime(2024, 12, 31, tzinfo=UTC)


def test_create_refuses_to_overwrite(tmp_path, hourly):
    with pytest.raises(FileExistsError):
        GridStore.create(tmp_path, HOURLY, 2025, WINDOW, [TEMP])


def test_a_store_at_another_scale_must_be_rescaled_before_it_opens(tmp_path):
    from dataclasses import replace

    old = replace(RAIN, scale=0.1)
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, [TEMP, old], chunks=(48, 16, 16))
    start = datetime(2025, 1, 14, 6, tzinfo=UTC)
    store.write(start, {"precipitation": np.full((2, *WINDOW.shape), [[[0.3]], [[np.nan]]])}, source="urma")
    with pytest.raises(ValueError, match="rescale"):
        GridStore.open(tmp_path, HOURLY, 2025, [TEMP, RAIN])
    GridStore.rescale(tmp_path, HOURLY, 2025, RAIN, steps=1000)
    reopened = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, RAIN])
    t0 = reopened.index_of(start)
    np.testing.assert_allclose(reopened.read_point("precipitation", 900, 1400, t0, t0 + 2), [0.3, np.nan])
    assert reopened.sources("precipitation")[t0] == "urma"
