from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata.catalog import variable
from agdata.grid import Window
from agdata.store import DAILY, HOURLY, GridStore, steps_in_year

WINDOW = Window(j0=900, j1=940, i0=1400, i1=1450)  # 40 x 50 cells in Wisconsin
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

    tile = reopened.read_block("air_temperature", t0 + 2, Window(j0=905, j1=915, i0=1410, i1=1430))
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
    t = hourly.index_of(when)
    hourly.write(when, {"air_temperature": np.full(WINDOW.shape, 1.0)}, source="rtma")
    hourly.write(when, {"air_temperature": np.full(WINDOW.shape, 2.0)}, source="urma")
    assert hourly.read_point("air_temperature", 920, 1440, t, t + 1)[0] == pytest.approx(2.0)
    assert hourly.sources("air_temperature")[t] == "urma"
    assert hourly.sources("air_temperature", t - 1, t + 2) == [None, "urma", None]  # only the steps asked for


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


def test_has_data_marks_the_steps_a_source_wrote(hourly):
    hourly.write(datetime(2025, 1, 1, 2, tzinfo=UTC), {"air_temperature": np.zeros((2, *WINDOW.shape))}, source="urma")
    assert hourly.has_data("air_temperature", 0, 5).tolist() == [False, False, True, True, False]


def test_a_write_past_the_end_of_the_year_is_refused_and_leaves_the_year_alone(hourly):
    last = datetime(2025, 12, 31, 22, tzinfo=UTC)
    with pytest.raises(IndexError, match="past the end of 2025"):
        hourly.write(last, {"air_temperature": np.full((3, *WINDOW.shape), 5.0)}, source="urma")
    assert np.isnan(hourly.read_point("air_temperature", 900, 1400, hourly.length - 2, hourly.length)).all()


def test_a_window_outside_the_store_is_refused(hourly):
    with pytest.raises(IndexError, match="reaches outside"):
        hourly.read_block("air_temperature", 0, Window(j0=930, j1=945, i0=1400, i1=1410))


def test_a_variable_the_store_was_not_opened_with_is_refused(tmp_path, hourly):
    reopened = GridStore.open(tmp_path, HOURLY, 2025, [TEMP])
    with pytest.raises(KeyError, match="isn't open in this store"):
        reopened.read_point("precipitation", 900, 1400, 0, 1)
    with pytest.raises(KeyError, match="isn't an array"):
        reopened._array("_meta")


def test_a_variable_a_store_lacks_is_an_error_unless_added_empty_and_stale(tmp_path, hourly):
    derived = variable("relative_humidity")
    assert derived.derived
    with pytest.raises(KeyError, match="relative_humidity"):
        GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived])
    assert GridStore.stale_variables(tmp_path, HOURLY, 2025, [TEMP, derived]) == {"relative_humidity"}  # read-only
    added = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived], add_missing=True)
    assert added.stale == {"relative_humidity"}
    assert np.isnan(added.read_point("relative_humidity", 900, 1400, 0, 3)).all()


def test_a_create_that_crashed_halfway_does_not_block_the_next(tmp_path):
    leftover = tmp_path / "hourly" / "2025.zarr.part"
    leftover.mkdir(parents=True)
    (leftover / "junk").write_text("half-written")
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, [TEMP])
    assert store.path.exists() and not leftover.exists()


@pytest.mark.parametrize("layout", ["hourly", "daily", "cumulative"])
def test_reopening_a_stores_year_checks_the_window(tmp_path, fx, layout):
    from agdata.cumulative import open_or_create_cumulative
    from agdata.daily import open_or_create_daily
    from agdata.ingest import open_or_create_hourly

    opener = {"hourly": open_or_create_hourly, "daily": open_or_create_daily, "cumulative": open_or_create_cumulative}[
        layout
    ]
    opener(tmp_path, 2025, fx.window)
    assert opener(tmp_path, 2025, fx.window).window == fx.window
    with pytest.raises(ValueError, match="widening the box needs a rebuild"):
        opener(tmp_path, 2025, Window(j0=fx.window.j0, j1=fx.window.j1 + 1, i0=fx.window.i0, i1=fx.window.i1))


def test_an_open_store_sees_another_writers_values_and_attributes(tmp_path, hourly):
    """Arrays are kept per process (`store._ARRAYS`) while their zarr.json is unchanged: values written by another
    handle show at once, and a metadata change (a rebuild's version, a store made again) opens the array afresh."""
    derived = variable("relative_humidity")
    reader = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived], add_missing=True)
    assert reader.stale == {"relative_humidity"}
    start = datetime(2025, 3, 1, tzinfo=UTC)
    hourly.write(start, {"air_temperature": np.full((1, *WINDOW.shape), 7.0)}, source="urma")
    assert GridStore.open(tmp_path, HOURLY, 2025, [TEMP]).read_point("air_temperature", 900, 1400, 1416, 1417)[0] == 7.0
    writer = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived])
    writer.mark_current(["relative_humidity"])
    assert GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived]).stale == set()
    # The store made again under the same path: its new arrays, not the kept ones
    import shutil

    shutil.rmtree(tmp_path / "hourly" / "2025.zarr")
    again = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, [TEMP], chunks=(48, 16, 16))
    again.write(start, {"air_temperature": np.full((1, *WINDOW.shape), -3.0)}, source="urma")
    found = GridStore.open(tmp_path, HOURLY, 2025, [TEMP]).read_point("air_temperature", 900, 1400, 1416, 1417)
    assert found[0] == -3.0
