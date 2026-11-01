import json
from datetime import UTC, datetime, timedelta

import pytest

from agdata import forecast
from ops.forecast import forecast_health, refresh_forecast
from ops.locks import write_lock
from ops.models import IngestRecord

BOX = "43.05,-89.45,43.1,-89.4"
NOW = datetime(2025, 7, 15, 14, 15, tzinfo=UTC)
CYCLE = datetime(2025, 7, 15, 13, tzinfo=UTC)


def fake_build(failed=()):
    """Writes just a run's directory and run.json, as build_run would."""
    calls = []

    def build(data_dir, window, cycle, soil=None):
        calls.append((cycle, soil is not None))
        path = forecast.run_path(data_dir, cycle)
        path.mkdir(parents=True)
        info = {
            "cycle": cycle.isoformat(),
            "first_hour": (cycle + timedelta(hours=1)).isoformat(),
            "last_hour": (cycle + timedelta(hours=264)).isoformat(),
            "failed_leads": list(failed),
            "last_observed": (cycle + timedelta(hours=1)).isoformat(),
        }
        (path / "run.json").write_text(json.dumps(info))
        return path

    build.calls = calls  # type: ignore[attr-defined]
    return build


def refresh(tmp_path, build, cycle=CYCLE):
    return refresh_forecast(tmp_path, BOX, NOW, find_cycle=lambda now: cycle, build=build)


@pytest.mark.django_db
def test_a_new_run_is_built_published_and_recorded_once(tmp_path):
    build = fake_build()
    record = refresh(tmp_path, build)
    assert record is not None and (record.kind, record.status) == ("forecast", "ok")
    assert record.first_hour == CYCLE + timedelta(hours=1) and record.hours == 264
    assert build.calls == [(CYCLE, True)]  # with IFS's soil (D52)
    assert forecast.current_run(tmp_path) == forecast.run_path(tmp_path, CYCLE).resolve()
    assert refresh(tmp_path, build) is None  # already current
    assert len(build.calls) == 1 and IngestRecord.objects.count() == 1


@pytest.mark.django_db
def test_failed_leads_make_a_partial_run_and_a_failed_build_is_recorded(tmp_path):
    record = refresh(tmp_path, fake_build(failed=(7, 8)))
    assert record is not None and record.status == "partial"
    assert record.failed_hours == [(CYCLE + timedelta(hours=h)).isoformat() for h in (7, 8)]

    def broken(*args, **kwargs):
        raise RuntimeError("bucket unreachable")

    later = refresh(tmp_path, broken, cycle=CYCLE + timedelta(hours=6))
    assert later is not None and later.status == "failed" and "bucket unreachable" in later.error
    assert forecast.current_run(tmp_path) == forecast.run_path(tmp_path, CYCLE).resolve()  # the last good run stays


@pytest.mark.django_db
def test_a_failed_cycle_isnt_rebuilt_for_a_while_unless_asked(tmp_path):
    def broken(*args, **kwargs):
        raise RuntimeError("bucket unreachable")

    failed = refresh(tmp_path, broken)
    assert failed is not None and failed.status == "failed"
    build = fake_build()
    assert refresh(tmp_path, build) is None and build.calls == []  # the job waits
    retried = refresh_forecast(tmp_path, BOX, NOW, find_cycle=lambda now: CYCLE, build=build, retry_failed=True)
    assert retried is not None and retried.status == "ok"  # the command doesn't


def test_forecast_health(tmp_path):
    assert forecast_health(tmp_path, NOW) == ({"state": "not started"}, [])
    forecast.publish(tmp_path, fake_build()(tmp_path, None, CYCLE))
    body, problems = forecast_health(tmp_path, NOW)
    assert body["age_hours"] == 1.2 and body["cycle"] == CYCLE.isoformat() and problems == []
    _, problems = forecast_health(tmp_path, CYCLE + timedelta(hours=10))
    assert problems == ["forecast run more than 9 h old"]


def test_the_forecast_job_is_periodic_and_takes_the_lock(tmp_path, settings, monkeypatch):
    from procrastinate.contrib.django import app

    from ops import tasks

    periodic = [p for p in app.periodic_registry.periodic_tasks.values() if p.task.name == tasks.ingest_forecast.name]
    assert [p.cron for p in periodic] == ["15,45 * * * *"]
    settings.DATA_DIR = tmp_path
    monkeypatch.setattr(tasks, "refresh_forecast", lambda *args: pytest.fail("ran without the lock"))
    with write_lock(tmp_path):
        tasks.ingest_forecast(int(NOW.timestamp()))


def test_the_hourly_job_restitches_the_forecast_after_new_hours(tmp_path, settings, monkeypatch):
    from ops import tasks

    settings.DATA_DIR = tmp_path
    stitched = []
    monkeypatch.setattr(tasks, "restitch_current", lambda data_dir, box: stitched.append(box))
    monkeypatch.setattr(tasks, "refresh_recent", lambda *args: [])
    tasks.ingest_recent(int(NOW.timestamp()))
    assert stitched == []  # nothing new
    monkeypatch.setattr(tasks, "refresh_recent", lambda *args: ["a record"])
    tasks.ingest_recent(int(NOW.timestamp()))
    assert stitched == [settings.SERVICE_BOX]


def test_restitch_current_does_nothing_without_a_published_run(tmp_path, monkeypatch):
    from ops import forecast as ops_forecast

    monkeypatch.setattr(ops_forecast.forecast, "current_run", lambda data_dir: None)
    monkeypatch.setattr(ops_forecast.forecast, "stitch", lambda *args: pytest.fail("stitched nothing"))
    assert ops_forecast.restitch_current(tmp_path, "wisconsin") is None


def test_restitch_current_stitches_the_published_run_over_the_service_window(tmp_path, monkeypatch):
    from agdata.grid import service_window
    from ops import forecast as ops_forecast

    run_dir = tmp_path / "run"
    seen = []
    monkeypatch.setattr(ops_forecast.forecast, "current_run", lambda data_dir: run_dir)
    monkeypatch.setattr(
        ops_forecast.forecast, "stitch", lambda data_dir, current, window: seen.append((current, window)) or CYCLE
    )
    assert ops_forecast.restitch_current(tmp_path, "wisconsin") == CYCLE
    assert seen == [(run_dir, service_window("wisconsin"))]
