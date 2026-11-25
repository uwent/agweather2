from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata.catalog import Variable, variable
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


def test_a_rescale_stopped_part_way_carries_on_where_it_left_off(tmp_path, monkeypatch):
    from dataclasses import replace

    old = replace(RAIN, scale=0.1)
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, [TEMP, old], chunks=(48, 16, 16))
    first, later = datetime(2025, 1, 1, 1, tzinfo=UTC), datetime(2025, 6, 1, 1, tzinfo=UTC)
    for when in (first, later):
        store.write(when, {"precipitation": np.full((1, *WINDOW.shape), 0.3)}, source="urma")
    calls = 0
    real = Variable.encode

    def stop_on_the_second_block(self, values):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return real(self, values)

    monkeypatch.setattr(Variable, "encode", stop_on_the_second_block)
    with pytest.raises(KeyboardInterrupt):
        GridStore.rescale(tmp_path, HOURLY, 2025, RAIN, steps=4000)
    with pytest.raises(ValueError, match="rescale"):  # not finished: the store still won't open
        GridStore.open(tmp_path, HOURLY, 2025, [TEMP, RAIN])
    monkeypatch.setattr(Variable, "encode", real)
    GridStore.rescale(tmp_path, HOURLY, 2025, RAIN, steps=4000)  # the first block isn't repacked twice
    reopened = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, RAIN])
    for when in (first, later):
        t = reopened.index_of(when)
        np.testing.assert_allclose(reopened.read_point("precipitation", 900, 1400, t, t + 1), [0.3])
    assert "rescaling" not in reopened._array("precipitation").attrs


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


def _tree(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


def test_a_read_only_store_reads_a_variable_it_lacks_as_missing_and_adds_nothing(tmp_path, hourly):
    """A request's open (`read_only`): a variable the store lacks reads as `add_missing` would have added it (all
    missing, no source, never written, stale if derived), and nothing is written to the store."""
    derived = variable("relative_humidity")
    hourly.write(datetime(2025, 3, 1, tzinfo=UTC), {"air_temperature": np.full((2, *WINDOW.shape), 7.0)}, source="urma")
    before = _tree(hourly.path)
    reader = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived], read_only=True)
    assert reader.absent == {"relative_humidity"} and reader.stale == {"relative_humidity"}
    t = reader.index_of(datetime(2025, 3, 1, tzinfo=UTC))
    assert reader.read_point("air_temperature", 900, 1400, t, t + 2).tolist() == [7.0, 7.0]
    assert np.isnan(reader.read_point("relative_humidity", 900, 1400, t, t + 2)).all()
    assert np.isnan(reader.read_cells("relative_humidity", [(900, 1400), (901, 1401)], t, t + 2)).all()
    assert np.isnan(reader.read_steps("relative_humidity", t, t + 2)).all()
    assert reader.written("relative_humidity") is None
    assert reader.sources("relative_humidity", t, t + 2) == [None, None]
    assert not reader.has_data("relative_humidity").any()
    assert reader.written("air_temperature") is not None
    assert _tree(hourly.path) == before
    # The same reads through a store that added it empty
    added = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived], add_missing=True)
    assert added.stale == reader.stale
    assert added.written("relative_humidity") is None and not added.has_data("relative_humidity").any()


def test_a_read_only_store_refuses_writes(tmp_path, hourly):
    reader = GridStore.open(tmp_path, HOURLY, 2025, [TEMP], read_only=True)
    start = datetime(2025, 3, 1, tzinfo=UTC)
    with pytest.raises(PermissionError, match="read-only"):
        reader.write(start, {"air_temperature": np.zeros((1, *WINDOW.shape))}, source="urma")
    with pytest.raises(PermissionError, match="read-only"):
        reader.record(["air_temperature"], start, 1, "urma")
    with pytest.raises(PermissionError, match="read-only"):
        reader.mark_current(["air_temperature"])
    with pytest.raises(ValueError, match="can't add"):
        GridStore.open(tmp_path, HOURLY, 2025, [TEMP], add_missing=True, read_only=True)
    # An array a read-only store opened isn't handed to a writer (`_ARRAYS` keeps them apart)
    GridStore.open(tmp_path, HOURLY, 2025, [TEMP]).write(
        start, {"air_temperature": np.full((1, *WINDOW.shape), 3.0)}, source="urma"
    )
    assert reader.read_point("air_temperature", 900, 1400, 1416, 1417)[0] == 3.0


def test_a_read_only_store_reads_a_variable_being_added_as_absent(tmp_path, hourly):
    """`_add_array` makes the values before the `_meta` arrays: a reader that finds only the values reads the
    variable as absent rather than failing on its sources."""
    derived = variable("relative_humidity")
    GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived], add_missing=True)
    import shutil

    shutil.rmtree(hourly.path / "_meta" / "relative_humidity.written")
    reader = GridStore.open(tmp_path, HOURLY, 2025, [TEMP, derived], read_only=True)
    assert reader.absent == {"relative_humidity"} and reader.written("relative_humidity") is None


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
