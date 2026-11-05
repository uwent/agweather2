"""The worker's jobs as runs (`ops.jobruns`): nothing unless JOB_RUNS; with it, a running job's record, gone once it
succeeds, kept with its traceback when it fails, and stopped when it's aborted."""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from procrastinate.exceptions import JobAborted

from agdata import progress
from ops import jobruns, runs

logger = logging.getLogger("ops.tasks")


def context(job_id: int = 7):
    return SimpleNamespace(job=SimpleNamespace(id=job_id, task_name="ops.tasks.ingest_recent"))


@pytest.fixture
def recorded(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    settings.JOB_RUNS = True
    return tmp_path


def test_off_it_only_runs_the_job(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    assert settings.JOB_RUNS is False  # tests (and production) run jobs as before
    assert jobruns.record(lambda: 42, context(), None) == 42
    assert not (tmp_path / "runs").exists()


def test_a_running_job_is_a_run_and_a_job_that_succeeds_removes_it(recorded):
    seen = []

    def job():
        (run,) = runs.runs(recorded)
        seen.append((run.key, run.label, run.running, progress.current() is not None))
        return "done"

    assert jobruns.record(job, context(), None) == "done"
    assert seen == [("job-7", "job ingest_recent", True, True)]
    assert runs.runs(recorded) == []


def test_a_failed_job_keeps_its_record_with_what_it_logged_and_its_traceback(recorded):
    def job():
        logger.info("2026-11-05 04Z ==> OK")
        logger.warning("ingest_recent skipped: the lock")
        raise RuntimeError("no data")

    with pytest.raises(RuntimeError):
        jobruns.record(job, context(262), None)
    (run,) = runs.runs(recorded)
    assert (run.key, run.state, run.summary) == ("job-262", "failed", "RuntimeError: no data")
    events = [json.loads(line) for line in Path(run.events).read_text().splitlines()]
    said = {(e["kind"], e["message"].splitlines()[0]) for e in events if "message" in e}
    assert ("step", "job 262: ingest_recent") in said
    assert ("detail", "2026-11-05 04Z ==> OK") in said and ("warn", "ingest_recent skipped: the lock") in said
    (failure,) = [e["message"] for e in events if e["kind"] == "fail"]
    assert failure.startswith("ingest_recent: Traceback") and failure.endswith("RuntimeError: no data")


def test_an_aborted_job_is_stopped_not_failed(recorded):
    def job():
        raise JobAborted

    with pytest.raises(JobAborted):
        jobruns.record(job, context(), None)
    (run,) = runs.runs(recorded)
    assert run.state == "stopped"
