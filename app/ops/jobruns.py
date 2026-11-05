"""The worker's jobs as runs (`ops.runs`), so the dashboard shows each one running with its steps and file reads,
and a failed or stopped one with its log and traceback.

`record` is a Procrastinate task middleware (`@app.task(task_middleware=JOB_MIDDLEWARE)`), run in the job's thread.
It does nothing unless `settings.JOB_RUNS` (development only: tests and production run jobs exactly as before). With
it on, a job records itself as `job-<id>` with an events-only reporter (the worker's output stays as it was), and
a job that succeeds removes its record again: the `jobs:` line already says when each last succeeded.
"""

import logging
import os
import threading
import traceback
from pathlib import Path
from typing import Any

from django.conf import settings
from procrastinate.exceptions import JobAborted

from agdata.progress import Reporter
from ops import runs


def record(call_next, context, worker) -> Any:
    """Runs the job, recorded as a run when `settings.JOB_RUNS` is on."""
    if not settings.JOB_RUNS:
        return call_next()
    job = context.job
    name = job.task_name.rsplit(".", 1)[-1]
    run = runs.start(settings.DATA_DIR, "job", [name], id=f"job-{job.id}")
    with open(os.devnull, "w") as quiet:
        report = Reporter(out=quiet, err=quiet, live=False, events=Path(run.events))
        ok, summary = False, ""
        try:
            handler = _ToReport(report)
            logging.getLogger().addHandler(handler)
            try:
                with report.activate():
                    report.step(f"job {job.id}: {name}")
                    result = call_next()
            finally:
                logging.getLogger().removeHandler(handler)
            ok = report.finish()
            summary = report.last_summary
            return result
        except JobAborted:
            summary = runs.INTERRUPTED
            raise
        except BaseException as error:
            report.fail(name, "".join(traceback.format_exception(error)).rstrip())
            summary = f"{type(error).__name__}: {error}"
            raise
        finally:
            report.close()
            if ok:
                runs.forget(settings.DATA_DIR, run)
            else:
                runs.finish(settings.DATA_DIR, run, ok, summary)


class _ToReport(logging.Handler):
    """What the job logs (on its own thread) into its run: INFO as details, warnings and errors as warnings."""

    def __init__(self, report: Reporter):
        super().__init__(level=logging.INFO)
        self.report, self.thread = report, threading.get_ident()

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread != self.thread or record.name.startswith("procrastinate"):
            return
        message = record.getMessage()
        if record.levelno >= logging.WARNING:
            self.report.warn(message)
        else:
            self.report.detail(message)


JOB_MIDDLEWARE = [record]
