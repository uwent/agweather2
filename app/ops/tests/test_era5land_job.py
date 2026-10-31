import shutil
from contextlib import nullcontext
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from agdata.grid import service_window
from agdata.ingest import open_or_create_hourly
from ops.era5land import refresh_era5land, spans

FIXTURES = Path(__file__).parents[3] / "packages" / "agdata" / "tests" / "fixtures"
BOX = "43.0,-88.1,43.05,-88.05"  # inland Milwaukee, inside the fixture's area
NOW = datetime(2025, 12, 21, 12, tzinfo=UTC)  # ERA5-Land reaches Dec 16


@pytest.fixture
def data_dir(tmp_path):
    window = service_window(BOX)
    static = tmp_path / "static"
    static.mkdir()
    # The fixture's mask covers the box's request area, so it stands in for the downloaded one
    name = f"era5land_land_{window.j0}_{window.j1}_{window.i0}_{window.i1}.npz"
    shutil.copy(FIXTURES / "era5land_milwaukee_lsm.npz", static / name)
    return tmp_path


def fixture_retrieve(calls: list):
    """Serves the recorded Dec 16 for a span ending that day; any other span fails as unpublished days do."""

    def retrieve(first: date, last: date, window, path: Path, key: str) -> Path:
        calls.append((first, last))
        if last != date(2025, 12, 16):
            raise RuntimeError("the request failed")
        shutil.copy(FIXTURES / "era5land_milwaukee.grib", path)
        return path

    return retrieve


def test_the_job_writes_the_days_without_era5land_and_skips_them_next_time(data_dir):
    calls = []
    run = lambda: refresh_era5land(  # noqa: E731
        data_dir, BOX, NOW, "key", retrieve=fixture_retrieve(calls), lock=nullcontext
    )
    assert run() == [(date(2025, 12, 16), date(2025, 12, 16))]
    # The last 31 days through Dec 16, a request per month; November's failure doesn't stop December
    assert calls == [(date(2025, 11, 16), date(2025, 11, 30)), (date(2025, 12, 1), date(2025, 12, 16))]

    store = open_or_create_hourly(data_dir, 2025, service_window(BOX))
    t0 = store.index_of(datetime(2025, 12, 16, tzinfo=UTC))
    assert store.sources("soil_temperature_10cm")[t0 : t0 + 24] == ["era5land"] * 24
    assert store.sources("soil_temperature_10cm")[t0 - 1] is None
    soil = store.read_steps("soil_temperature_10cm", t0, t0 + 24)
    snow = store.read_steps("snow_depth", t0, t0 + 24)
    assert np.isfinite(soil).all() and soil.min() > -5 and soil.max() < 10
    assert np.isfinite(snow).all() and snow.max() > 5  # cm

    calls.clear()
    run()
    assert all(last < date(2025, 12, 16) for _, last in calls)  # Dec 16 isn't asked for again


def test_spans_split_at_gaps_and_months():
    days = [date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 3)]
    assert spans(days) == [
        (date(2025, 1, 30), date(2025, 1, 31)),
        (date(2025, 2, 1), date(2025, 2, 1)),
        (date(2025, 2, 3), date(2025, 2, 3)),
    ]


class Constant:
    """A fake IFS chunk: one value everywhere, for every hour."""

    def __init__(self, value: float):
        self.value = value

    def __getitem__(self, key):
        _, cells, steps = key
        return np.full((cells.stop - cells.start, steps.stop - steps.start), self.value)


def test_ifs_fills_the_hours_after_era5land_and_keeps_the_forecast_hours(data_dir):
    from agdata.sources import ifs
    from ops.ifs import refresh_ifs

    refresh_era5land(data_dir, BOX, NOW, "key", retrieve=fixture_retrieve([]), lock=nullcontext)
    run = datetime(2025, 12, 21, 6, tzinfo=UTC)
    meta = lambda: {"last_run_initialisation_time": run.timestamp()}  # noqa: E731
    read = lambda: refresh_ifs(  # noqa: E731
        data_dir,
        BOX,
        NOW,
        None,
        opener=lambda v, c: Constant(0.04 if v == "snow_depth" else 3.0),
        meta=meta,
        lock=nullcontext,
    )
    assert read() is True
    assert read() is False  # the same run isn't read twice

    store = open_or_create_hourly(data_dir, 2025, service_window(BOX))
    t = store.index_of(datetime(2025, 12, 17, tzinfo=UTC))  # the hour after ERA5-Land's last
    sources = store.sources("soil_temperature_10cm")
    assert sources[t - 1] == "era5land" and sources[t] == "ifs" and sources[store.index_of(NOW)] == "ifs"
    assert sources[store.index_of(NOW) + 1] is None  # nothing past now in the archive
    np.testing.assert_allclose(store.read_steps("snow_depth", t, t + 1), 4.0)  # cm

    later = [NOW + timedelta(hours=h) for h in (1, 100, 300)]
    kept = ifs.latest_at(ifs.latest_path(data_dir), later, service_window(BOX))
    np.testing.assert_allclose(kept["soil_temperature_10cm"][:2], 3.0)
    assert np.isnan(kept["soil_temperature_10cm"][2]).all()  # past the run's end (234 h after a 06Z run)
