from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from django.utils import timezone

from agdata.grid import service_window
from agdata.ingest import open_or_create_hourly

BOX = "43.05,-89.45,43.1,-89.4"


def write_hours(data_dir, last: datetime, hours: int, source="urma"):
    window = service_window(BOX)
    t = last - timedelta(hours=hours - 1)
    while t <= last:  # one write per year's store
        n = min(
            hours,
            int((datetime(t.year + 1, 1, 1, tzinfo=UTC) - t) / timedelta(hours=1)),
            int((last - t) / timedelta(hours=1)) + 1,
        )
        store = open_or_create_hourly(data_dir, t.year, window)
        store.write(t, {"air_temperature": np.zeros((n, *window.shape))}, source=source)
        t += timedelta(hours=n)


@pytest.mark.django_db
def test_an_empty_archive_is_ok_and_not_started(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    response = client.get("/up")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "dev",
        "database": "ok",
        "ingest": {"state": "not started"},
        "problems": [],
    }


@pytest.mark.django_db
def test_a_current_archive_is_ok(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    newest = timezone.now().astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    write_hours(tmp_path, newest - timedelta(hours=6), 24 * 8, "urma")
    write_hours(tmp_path, newest, 6, "rtma")
    body = client.get("/up").json()
    assert body["status"] == "ok", body["problems"]
    assert body["ingest"]["newest_hour"] == newest.isoformat()
    assert 5.9 < body["ingest"]["urma_lag_hours"] < 7.1
    assert body["ingest"]["missing_hours_7d"] == 0


@pytest.mark.django_db
def test_a_stale_archive_is_degraded_but_up(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    newest = timezone.now().astimezone(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=20)
    write_hours(tmp_path, newest, 24)
    response = client.get("/up")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["problems"] == ["newest hour more than 3 h old", "newest URMA hour more than 12 h old"]
    assert body["ingest"]["missing_hours_7d"] > 0
