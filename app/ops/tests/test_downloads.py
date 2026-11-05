"""The yearly NetCDF downloads (`ops.downloads`, D69), on a copy of the fixture archive's daily stores."""

import shutil
from datetime import date, timedelta

import numpy as np
import pytest
import xarray as xr

from agdata.catalog import DAILY_VARIABLES
from agdata.store import DAILY, GridStore
from api.tests import fixture_archive
from ops import downloads

NOW = fixture_archive.NOW
NAMES = ["air_temperature_max", "precipitation_sum", "hours_rh_over_90"]


@pytest.fixture
def data_dir(archive_dir, tmp_path, settings):
    shutil.copytree(archive_dir / "daily", tmp_path / "daily")
    settings.DATA_DIR = tmp_path
    settings.SERVICE_BOX = fixture_archive.BOX
    return tmp_path


def _store(data_dir, names=NAMES):
    return GridStore.open(data_dir, DAILY, 2025, [DAILY_VARIABLES[n] for n in names])


def test_a_file_holds_the_stores_values_through_the_last_day_rolled_up(data_dir):
    built = downloads.build_wanted(data_dir, NOW, NAMES)
    assert sorted(e.variable for e in built) == sorted(NAMES)
    entry = next(e for e in built if e.variable == "air_temperature_max")
    assert (entry.year, entry.first, entry.complete) == (2025, "2025-01-01", False)
    store = _store(data_dir)
    n = int(np.flatnonzero(store.has_data("air_temperature_max"))[-1]) + 1
    assert entry.last == (date(2025, 1, 1) + timedelta(days=n - 1)).isoformat()
    with xr.open_dataset(data_dir / "downloads" / entry.path) as ds:
        found = ds["air_temperature_max"]
        assert found.dtype == np.float32  # unpacked from int16 by its float32 scale_factor
        assert found.attrs["units"] == "degC"
        assert found.attrs["cell_methods"] == "time: maximum"
        assert found.encoding["dtype"] == np.int16
        assert ds.sizes["time"] == n
        expected = store.read_steps("air_temperature_max", 0, n)
        np.testing.assert_allclose(found.values, expected, atol=1e-4)
        assert np.isnan(found.values).sum() == np.isnan(expected).sum()  # missing stays missing
        assert "time_zones.nc" in ds.attrs["comment"]
        assert "lambert_conformal_conic" in ds


def test_hour_counts_have_no_cell_method(data_dir):
    entry = downloads.build(data_dir, "hours_rh_over_90", 2025, NOW)
    assert entry is not None
    with xr.open_dataset(data_dir / "downloads" / entry.path) as ds:
        assert "cell_methods" not in ds["hours_rh_over_90"].attrs


def test_the_index_lists_the_files_and_the_time_zones_are_beside_them(data_dir):
    downloads.build_wanted(data_dir, NOW, NAMES)
    assert {e.variable for e in downloads.read_index(data_dir)} == set(NAMES)
    with xr.open_dataset(data_dir / "downloads" / "daily" / "time_zones.nc") as ds:
        assert ds["time_zone"].attrs["flag_meanings"] == "America/Chicago"


def test_a_file_is_rebuilt_when_its_store_is_written_and_this_years_at_most_weekly(data_dir):
    downloads.build_wanted(data_dir, NOW, NAMES)
    assert downloads.wanted(data_dir, NOW, NAMES) == []
    store = _store(data_dir, ["air_temperature_max"])
    day = store.read_steps("air_temperature_max", 0, 1)
    store.write(date(2025, 1, 1), {"air_temperature_max": day}, source="urma")
    assert downloads.wanted(data_dir, NOW, NAMES) == []  # this year's: built less than a week ago
    later = downloads.wanted(data_dir, NOW + timedelta(days=8), NAMES)
    assert later == [("air_temperature_max", 2025, "the store has been written since")]
    next_year = NOW.replace(year=2026)
    assert downloads.wanted(data_dir, next_year, NAMES) == later  # a past year's: at once


def test_a_progress_callback_can_stop_between_files(data_dir):
    def stop(done, total, item):
        if done == 1:
            raise downloads.Stopped

    with pytest.raises(downloads.Stopped):
        downloads.build_wanted(data_dir, NOW, NAMES, progress=stop)
    assert len(downloads.read_index(data_dir)) == 1


@pytest.mark.django_db
def test_the_api_lists_and_serves_them(data_dir, client):
    downloads.build_wanted(data_dir, NOW, NAMES)
    body = client.get("/api/v2/downloads").json()["data"]
    assert body["time_zones"] == "http://testserver/downloads/daily/time_zones.nc"
    first = next(f for f in body["files"] if f["variable"] == "precipitation_sum")
    assert first["url"] == "http://testserver/downloads/daily/2025/precipitation_sum_2025.nc"
    response = client.get("/downloads/daily/2025/precipitation_sum_2025.nc")
    assert response.status_code == 200
    assert int(response["Content-Length"]) == first["bytes"]
    status = client.get("/api/v2/status").json()["data"]["downloads"]
    assert status["files"] == len(NAMES)
