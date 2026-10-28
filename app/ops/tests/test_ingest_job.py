from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata.daily import open_or_create_daily
from agdata.grid import service_window
from agdata.ingest import Hour
from ops import ingest as ops_ingest
from ops.ingest import refresh_recent
from ops.locks import WriteLocked, hold_write_lock, write_lock
from ops.models import IngestRecord

BOX = "43.05,-89.45,43.1,-89.4"  # a few cells in Madison
NOW = datetime(2025, 7, 15, 12, 40, tzinfo=UTC)
NEWEST = datetime(2025, 7, 15, 12, tzinfo=UTC)


def fake_fetch(rtma_from: datetime | None = None, down: set[datetime] | None = None):
    """Steady summer weather; URMA (RTMA from `rtma_from` on); hours in `down` fail."""

    def fetch(when, window, session):
        if down and when in down:
            raise ConnectionError("simulated outage")
        values = {
            name: np.full(window.shape, value)
            for name, value in {
                "air_temperature": 22.0,
                "dew_point": 14.0,
                "wind_speed": 3.0,
                "wind_gust": 6.0,
                "wind_direction": 180.0,
                "surface_pressure": 98.0,
                "cloud_cover": 20.0,
                "precipitation": 0.0,
                "shortwave_radiation": 300.0 if 11 <= when.hour <= 23 else 0.0,
                "soil_temperature_4cm": 20.0,
                "soil_temperature_10cm": 19.0,
            }.items()
        }
        analysis = "rtma" if rtma_from and when >= rtma_from else "urma"
        sources = {name: "hrrr" if name.startswith(("shortwave", "soil")) else analysis for name in values}
        return Hour(values, sources)

    return fetch


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    monkeypatch.setattr("agdata.ingest.RETRY_SECONDS", 0)


@pytest.mark.django_db
def test_a_first_run_fills_the_last_week_and_rolls_it_up(tmp_path):
    records = refresh_recent(tmp_path, BOX, NOW, fetch=fake_fetch(), urma_published=lambda when: False)
    assert len(records) == 1
    record = records[0]
    assert (record.kind, record.status, record.hours) == ("hourly", "ok", 7 * 24)
    assert record.first_hour == NEWEST - timedelta(days=7) + timedelta(hours=1)
    assert record.sources["air_temperature"] == {"urma": 168}
    daily = open_or_create_daily(tmp_path, 2025, service_window(BOX))
    mean = daily.read_block("air_temperature_mean", daily.index_of(date(2025, 7, 13)))
    np.testing.assert_allclose(mean, 22)
    assert IngestRecord.objects.count() == 1


@pytest.mark.django_db
def test_later_runs_fetch_only_new_and_replaceable_hours(tmp_path):
    rtma_from = NEWEST - timedelta(hours=2)
    refresh_recent(tmp_path, BOX, NOW, fetch=fake_fetch(rtma_from), urma_published=lambda when: False)
    assert refresh_recent(tmp_path, BOX, NOW, fetch=fake_fetch(), urma_published=lambda when: False) == []

    published = {rtma_from}
    later = refresh_recent(
        tmp_path, BOX, NOW + timedelta(hours=1), fetch=fake_fetch(), urma_published=published.__contains__
    )
    assert [(r.first_hour, r.hours) for r in later] == [(rtma_from, 1), (NEWEST + timedelta(hours=1), 1)]


@pytest.mark.django_db
def test_failed_hours_make_a_partial_run_and_are_retried(tmp_path):
    down = {NEWEST - timedelta(hours=5)}
    (record,) = refresh_recent(tmp_path, BOX, NOW, fetch=fake_fetch(down=down), urma_published=lambda when: False)
    assert record.status == "partial"
    assert record.failed_hours == [(NEWEST - timedelta(hours=5)).isoformat()]
    (retry,) = refresh_recent(tmp_path, BOX, NOW, fetch=fake_fetch(), urma_published=lambda when: False)
    assert (retry.first_hour, retry.hours, retry.status) == (NEWEST - timedelta(hours=5), 1, "ok")


@pytest.mark.django_db
def test_a_run_that_raises_is_recorded_as_failed(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ops_ingest, "ingest_block", broken)
    monkeypatch.setattr(ops_ingest, "update_days", lambda *args: [])
    (record,) = refresh_recent(tmp_path, BOX, NOW, fetch=fake_fetch(), urma_published=lambda when: False)
    assert record.status == "failed" and "disk full" in record.error


def test_one_writer_at_a_time(tmp_path):
    with write_lock(tmp_path), pytest.raises(WriteLocked, match="pid"):
        hold_write_lock(tmp_path)
    hold_write_lock(tmp_path).close()  # released


def test_the_ingest_job_is_periodic_at_40_past():
    from procrastinate.contrib.django import app

    from ops import tasks

    periodic = [p for p in app.periodic_registry.periodic_tasks.values() if p.task.name == tasks.ingest_recent.name]
    assert [p.cron for p in periodic] == ["40 * * * *"]


def test_the_ingest_job_skips_while_another_writer_holds_the_lock(tmp_path, settings, monkeypatch):
    from ops import tasks

    settings.DATA_DIR = tmp_path
    monkeypatch.setattr(tasks, "refresh_recent", lambda *args: pytest.fail("ran without the lock"))
    with write_lock(tmp_path):
        tasks.ingest_recent(int(NOW.timestamp()))
