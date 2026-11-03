"""`DatasetStatus`: read from the stores whenever the write lock is released, so `/status` needn't open them."""

from datetime import UTC, datetime

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
