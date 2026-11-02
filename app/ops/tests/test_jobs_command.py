"""`manage.py jobs`: the status screen, a line per day, running and queueing jobs, and `start`'s catch-up before it
becomes the worker."""

import os
from datetime import UTC, date, datetime
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from procrastinate.contrib.django.models import ProcrastinateJob

from ops import status, tasks
from ops.tests.test_up import write_hours

pytestmark = pytest.mark.django_db


def run(*args: str) -> tuple[str, str]:
    out, err = StringIO(), StringIO()
    call_command("jobs", *args, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


@pytest.fixture
def data_dir(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    return tmp_path


def fake(name: str, calls: list[str], fails: bool = False):
    def job(timestamp: int) -> None:
        calls.append(name)
        if fails:
            raise RuntimeError("no data")

    job.name = f"ops.tasks.{name}"  # type: ignore[attr-defined]
    return job


def test_status_of_an_empty_archive_says_so_and_lists_every_job(data_dir):
    out, _ = run()
    assert "archive: empty" in out
    assert "forecast: none published yet" in out
    assert "lock:    free" in out
    for task in tasks.CATCH_UP:
        assert f"{status.short_name(task.name)}" in out
    assert "never run; next" in out
    assert "problems: none" in out


def test_status_exits_nonzero_when_there_are_problems(data_dir):
    write_hours(data_dir, datetime(2025, 7, 1, tzinfo=UTC), hours=3)  # long ago: the archive is behind
    with pytest.raises(CommandError, match="problem"):
        run("status")


def test_the_lock_line_names_the_holder(data_dir):
    from ops.locks import hold_write_lock

    handle = hold_write_lock(data_dir)
    try:
        assert f"held by pid {os.getpid()}" in run()[0]
    finally:
        handle.close()
    assert "lock:    free" in run()[0]


def test_days_marks_each_day_ok_partial_or_missing(data_dir, monkeypatch):
    write_hours(data_dir, datetime(2026, 3, 2, 23, tzinfo=UTC), hours=36)  # Mar 1 12Z to Mar 2 23Z
    lines, bad = status.day_lines(data_dir, date(2026, 2, 28), date(2026, 3, 2))
    assert [line.split()[1] for line in lines] == ["MISSING", "PARTIAL", "PARTIAL"]  # no precip or soil written
    assert "air 12/24 (urma 12)" in lines[1]
    assert "air 24/24 (urma 24)" in lines[2]
    assert bad == 3


def test_run_all_runs_the_catch_up_in_order_and_goes_on_past_a_failure(data_dir, monkeypatch):
    calls: list[str] = []
    order = ("ingest_recent", "ingest_ifs", "ingest_era5land", "ingest_forecast")
    monkeypatch.setattr(tasks, "CATCH_UP", tuple(fake(n, calls, fails=n == "ingest_ifs") for n in order))
    out, err = StringIO(), StringIO()
    with pytest.raises(CommandError, match="1 failed"):
        call_command("jobs", "run", "all", stdout=out, stderr=err)
    assert calls == list(order)
    assert "ingest_ifs: RuntimeError('no data')" in err.getvalue()


def test_run_names_an_unknown_job_and_lists_the_known_ones(data_dir):
    with pytest.raises(CommandError, match=r"unknown job nope; jobs: .*ingest_recent"):
        run("run", "nope")


def test_defer_queues_once_and_says_when_already_queued(data_dir):
    out, _ = run("run", "ingest_recent", "--defer")
    assert "ingest_recent: queued" in out
    out, _ = run("run", "ingest_recent", "--defer")
    assert "ingest_recent: already queued" in out
    assert ProcrastinateJob.objects.filter(task_name="ops.tasks.ingest_recent", status="todo").count() == 1
    assert "1 queued" in run()[0]


def test_list_shows_schedules_and_what_each_job_does(data_dir):
    out, _ = run("list")
    assert "ingest_recent  [40 * * * *]" in out
    assert "Keeps the archive current" in out


def queue(task) -> int:
    return task.defer(timestamp=0)


def stall(task) -> int:
    """A job marked running by a worker whose heartbeat stopped an hour ago."""
    job_id = queue(task)
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO procrastinate_workers (last_heartbeat) VALUES (now() - interval '1 hour') RETURNING id"
        )
        row = cursor.fetchone()
        assert row is not None
        worker = row[0]
        cursor.execute("UPDATE procrastinate_jobs SET status = 'doing', worker_id = %s WHERE id = %s", [worker, job_id])
    return job_id


def test_start_fails_stalled_jobs_queues_the_catch_up_then_becomes_the_worker(data_dir, monkeypatch):
    stalled = stall(tasks.ingest_recent)
    assert "1 stalled" in run()[0]
    became: list[list[str]] = []
    monkeypatch.setattr(os, "execv", lambda path, argv: became.append(argv))
    out, _ = run("start")
    assert "archive: empty" in out  # the status first
    assert f"job {stalled} was left by a stopped worker; marked failed" in out
    assert ProcrastinateJob.objects.get(id=stalled).status == "failed"
    queued = set(ProcrastinateJob.objects.filter(status="todo").values_list("task_name", flat=True))
    assert queued == {task.name for task in tasks.CATCH_UP}
    assert became and became[0][-2:] == ["procrastinate", "worker"]


def test_start_still_becomes_the_worker_when_the_status_fails(data_dir, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("relation procrastinate_jobs does not exist")

    monkeypatch.setattr("ops.management.commands.jobs.snapshot", broken)
    became: list[list[str]] = []
    monkeypatch.setattr(os, "execv", lambda path, argv: became.append(argv))
    _, err = run("start")
    assert "no status or catch-up" in err
    assert became


def test_a_job_that_ran_shows_its_result_and_duration(data_dir):
    job_id = queue(tasks.ingest_ifs)
    with connection.cursor() as cursor:
        for state in ("doing", "succeeded"):
            cursor.execute("UPDATE procrastinate_jobs SET status = %s WHERE id = %s", [state, job_id])
        cursor.execute("DELETE FROM procrastinate_events WHERE job_id = %s", [job_id])  # the triggers' (now)
        for kind, at in (("started", "2026-11-02 18:50:00+00"), ("succeeded", "2026-11-02 18:56:18+00")):
            cursor.execute(
                "INSERT INTO procrastinate_events (job_id, type, at) VALUES (%s, %s, %s)", [job_id, kind, at]
            )
    line = next(line for line in run()[0].splitlines() if "ingest_ifs" in line)
    assert "last succeeded Nov 02 18:56Z in 6 min" in line
