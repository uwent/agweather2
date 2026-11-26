"""`DatasetStatus`: read from the stores whenever the write lock is released, so `/status` needn't open them."""

from datetime import UTC, datetime

import numpy as np
import pytest

from ops import locks, status
from ops.models import DatasetStatus

pytestmark = pytest.mark.django_db


def test_refresh_reads_each_datasets_extent_sources_and_staleness(archive_dir):
    status.refresh_dataset_status(archive_dir, now=datetime(2025, 7, 10, 16, tzinfo=UTC))
    rows = {row.dataset: row for row in DatasetStatus.objects.all()}
    assert set(rows) == {"hourly", "daily", "cumulative", "forecast"}
    assert rows["hourly"].first == datetime(2025, 7, 1, tzinfo=UTC)
    assert rows["hourly"].last == datetime(2025, 7, 10, 15, tzinfo=UTC)
    assert rows["hourly"].last_by_source == {"urma": "2025-07-10T15:00:00+00:00"}
    assert rows["daily"].last == datetime(2025, 7, 9, tzinfo=UTC)  # the days rolled up
    assert rows["cumulative"].last == datetime(2025, 7, 9, tzinfo=UTC)
    assert rows["forecast"].first == datetime(2025, 7, 10, 13, tzinfo=UTC)  # the run's cycle
    assert rows["forecast"].details["last_hour"] == "2025-07-21T13:00:00+00:00"
    assert all(row.stale == {} for row in rows.values())
    gaps = rows["hourly"].details["gaps"]
    assert (gaps["first"], gaps["last"]) == ("2025-06-11", "2025-07-10")  # 30 grid days through today
    air = gaps["variables"][0]
    assert air == {"variable": "air_temperature", "sources": ["urma"], "days": []}  # none before the archive's first


def test_recent_gaps_are_days_missing_hours_by_feed_up_to_its_newest(tmp_path, monkeypatch):
    """A day's hours are its grid day's (07Z to 06Z); hours past a feed's newest are late, not missing."""
    codes = np.zeros(8760, dtype=np.uint8)  # 2025's hours, by their UTC end from Jan 1 00Z
    july = 181 * 24  # July 1 00Z
    codes[july : july + 10 * 24] = 1  # URMA through July 10 23Z
    codes[july + 4 * 24 + 7 : july + 4 * 24 + 10] = 0  # three hours early on July 5 (grid day July 5)
    codes[july + 2 * 24 + 6] = 0  # July 3 06Z ends grid day July 2
    codes[july + 9 * 24 : july + 10 * 24] = 2  # RTMA on the last day
    soil = np.zeros(8760, dtype=np.uint8)
    soil[july : july + 6 * 24] = 8  # ERA5-Land, five days behind: late, not missing

    def meta(path, name):
        return soil if name == "soil_temperature_4cm" else codes

    monkeypatch.setattr(status, "_meta", meta)
    found = status.recent_gaps(
        tmp_path, datetime(2025, 7, 11, tzinfo=UTC), since=datetime(2025, 7, 1, tzinfo=UTC), days=10
    )
    assert (found["first"], found["last"]) == ("2025-07-01", "2025-07-10")
    air = found["variables"][0]
    assert air["sources"] == ["rtma", "urma"]
    assert air["days"] == [{"date": "2025-07-02", "missing_hours": 1}, {"date": "2025-07-05", "missing_hours": 3}]
    assert found["variables"][3] == {"variable": "soil_temperature_4cm", "sources": ["era5land"], "days": []}


def test_releasing_the_write_lock_refreshes_the_status(tmp_path):
    assert not DatasetStatus.objects.exists()
    with locks.write_lock(tmp_path):
        pass
    assert DatasetStatus.objects.count() == 4  # an empty archive: every extent None
    assert DatasetStatus.objects.get(dataset="hourly").first is None


def test_a_status_that_cant_be_refreshed_never_fails_the_writer(tmp_path, monkeypatch, caplog):
    def broken(data_dir):
        raise RuntimeError("no database")

    monkeypatch.setattr(status, "refresh_dataset_status", broken)
    with locks.write_lock(tmp_path):
        pass
    assert "couldn't refresh the dataset status" in caplog.text
    with locks.write_lock(tmp_path):  # and the lock was released
        pass
