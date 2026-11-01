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
        "forecast": {"state": "not started"},
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


@pytest.mark.django_db
def test_stale_derived_data_makes_it_degraded(client, settings, tmp_path):
    from agdata.daily import open_or_create_daily

    settings.DATA_DIR = tmp_path
    newest = timezone.now().astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    write_hours(tmp_path, newest, 24 * 8)
    daily = open_or_create_daily(tmp_path, newest.year, service_window(BOX))
    daily._array("hours_rh_over_90").attrs["version"] = 0  # written by older code
    body = client.get("/up").json()
    assert body["status"] == "degraded"
    assert body["ingest"]["stale"] == {f"daily/{newest.year}": ["hours_rh_over_90"]}


@pytest.fixture
def counted_checks(monkeypatch, settings, tmp_path):
    """/up with the two health checks replaced by counters (and the cache emptied around the test)."""
    from django.core.cache import cache

    from ops import views

    settings.DATA_DIR = tmp_path
    cache.clear()
    calls = []
    monkeypatch.setattr(views, "ingest_health", lambda data_dir, now: calls.append("ingest") or ({"state": "x"}, ["a"]))
    monkeypatch.setattr(views, "forecast_health", lambda data_dir, now: calls.append("forecast") or ({"y": 1}, ["b"]))
    yield calls
    cache.clear()


@pytest.mark.django_db
def test_up_reuses_the_checks_for_30_seconds(client, counted_checks):
    first = client.get("/up").json()
    second = client.get("/up").json()
    assert counted_checks == ["ingest", "forecast"]  # the second call recomputed nothing
    assert first == second
    assert first["status"] == "degraded" and first["problems"] == ["a", "b"]  # both checks' problems, in order
    assert (first["ingest"], first["forecast"]) == ({"state": "x"}, {"y": 1})


@pytest.mark.django_db
def test_up_checks_again_once_the_cache_has_expired(client, counted_checks):
    from django.core.cache import cache

    client.get("/up")
    cache.clear()  # what the 30 s timeout does
    client.get("/up")
    assert counted_checks == ["ingest", "forecast"] * 2


@pytest.mark.django_db
def test_the_cache_is_per_data_directory(client, counted_checks, settings, tmp_path):
    client.get("/up")
    settings.DATA_DIR = tmp_path / "other"
    client.get("/up")
    assert counted_checks == ["ingest", "forecast"] * 2


@pytest.mark.django_db
def test_up_is_503_when_the_database_does_not_answer(client, counted_checks, monkeypatch, caplog):
    from django.db import connection

    def broken(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(connection, "cursor", broken)
    response = client.get("/up")
    assert response.status_code == 503
    assert response.json() == {"status": "down", "version": "dev", "database": "down"}
    assert counted_checks == []  # no point opening stores when the database is down
    assert "the database didn't answer" in caplog.text
