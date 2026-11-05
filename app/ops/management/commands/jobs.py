"""One place to see and run the jobs (v1's `RunTasks` and `DataImport.check_statuses`):

manage.py jobs                      # status: archive, soil, forecast, write lock, each job's last and next run
manage.py jobs days --days 14       # a line per UTC day: hours of air temperature, precip and soil, by source
manage.py jobs list                 # the jobs, their schedules and what they do
manage.py jobs run ingest_recent    # run jobs here and now (`all`: every periodic job, in catch-up order)
manage.py jobs run all --defer      # or queue them for the worker
manage.py jobs clear                # the failed jobs so far stop counting as a problem (and their run records go)
manage.py jobs start                # status, queue every periodic job once, then become the worker (bin/dev)
"""

import os
import sys
import time
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from procrastinate import exceptions as procrastinate_errors
from procrastinate.contrib.django import app

from ops import runs, tasks
from ops.management.base import ReportingCommand, positive
from ops.status import abort_stalled_jobs, day_lines, refresh_dataset_status, short_name, snapshot, status_lines


def _registered() -> dict[str, object]:
    return {short_name(name): task for name, task in app.tasks.items() if name.startswith("ops.tasks.")}


class Command(ReportingCommand):
    help = "Status of the archive and the job queue; run or queue jobs; start the worker after a catch-up."
    tracked = False  # not a data run: `jobs start` becomes the worker, which the dashboard shows on its own

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action")
        sub.add_parser("status", help="the archive, soil, forecast, lock and jobs (the default)")
        days = sub.add_parser("days", help="a line per UTC day of what the hourly store holds")
        days.add_argument("--days", type=int, default=14, help="how many days back from today (default 14)")
        sub.add_parser("list", help="the jobs, their schedules and what they do")
        run = sub.add_parser("run", help="run jobs now, or queue them with --defer")
        run.add_argument("names", nargs="+", help="job names (see `jobs list`), or `all`")
        run.add_argument("--defer", action="store_true", help="queue them for the worker instead of running here")
        sub.add_parser("clear", help="stop counting the failed jobs so far as a problem; forget their run records")
        sub.add_parser("start", help="print the status, queue every periodic job once, then run the worker")

    def handle(self, *args, **options):
        action = options.get("action") or "status"
        if action == "status":
            self.status(fail_on_problems=True)
        elif action == "days":
            self.days(positive(options["days"], "--days"))
        elif action == "list":
            self.list_jobs()
        elif action == "run":
            self.run_jobs(self.resolve(options["names"]), defer=options["defer"])
        elif action == "clear":
            self.clear()
        elif action == "start":
            self.start()

    def status(self, fail_on_problems: bool) -> bool:
        current = snapshot(settings.DATA_DIR, datetime.now(UTC))
        for line in status_lines(current):
            self.stdout.write(line)
        if current.problems and fail_on_problems:
            raise CommandError(f"{len(current.problems)} problem(s): {'; '.join(current.problems)}")
        return not current.problems

    def days(self, count: int) -> None:
        last = datetime.now(UTC).date()
        lines, bad = day_lines(settings.DATA_DIR, last - timedelta(days=count - 1), last)
        for line in lines:
            self.stdout.write(line)
        self.stdout.write(f"{bad} of {count} days not complete (today's last hours aren't out yet)")

    def list_jobs(self) -> None:
        periodic = {p.task.name: p.cron for p in app.periodic_registry.periodic_tasks.values()}
        for name, task in sorted(_registered().items()):
            doc = (task.func.__doc__ or "").strip().split("\n\n")[0].replace("\n", " ")  # type: ignore[attr-defined]
            schedule = periodic.get(f"ops.tasks.{name}", "on demand")
            self.stdout.write(f"{name}  [{schedule}]\n    {doc}")

    def resolve(self, names: list[str]) -> list:
        if names == ["all"]:
            return list(tasks.CATCH_UP)
        known = _registered()
        unknown = [n for n in names if n not in known]
        if unknown:
            raise CommandError(f"unknown job {', '.join(unknown)}; jobs: {', '.join(sorted(known))}, or all")
        return [known[n] for n in names]

    def run_jobs(self, jobs: list, defer: bool) -> None:
        now = int(time.time())
        if defer:
            queued = sum(self.defer(task, now) for task in jobs)
            self.finish(f"queued {queued} of {len(jobs)} job(s) for the worker")
            return
        self.report.step(f"running {', '.join(short_name(t.name) for t in jobs)} here (the worker may run them too)")
        for k, task in enumerate(jobs, 1):
            began = time.monotonic()
            self.report.step(f"{short_name(task.name)}: started")
            try:
                task(now)
            except Exception as error:  # the next job still runs; the summary lists this one
                self.report.fail(short_name(task.name), error)
                continue
            self.report.step(f"{short_name(task.name)}: done in {time.monotonic() - began:.0f} s")
            self.report.progress("jobs", k, len(jobs))
        self.finish(f"ran {len(jobs)} job(s)")

    def defer(self, task, timestamp: int) -> bool:
        """Queues one run; a run already queued (the task's queueing lock) is left as it is."""
        try:
            with transaction.atomic():  # a savepoint: the queueing lock's refusal mustn't abort an outer transaction
                task.defer(timestamp=timestamp)
        except procrastinate_errors.AlreadyEnqueued:
            self.report.step(f"{short_name(task.name)}: already queued")
            return False
        self.report.step(f"{short_name(task.name)}: queued")
        return True

    def clear(self) -> None:
        data_dir = settings.DATA_DIR
        gone = [r for r in runs.runs(data_dir) if r.is_job and not r.running]
        for run in gone:
            runs.forget(data_dir, run)
        runs.clear_jobs(data_dir)
        self.stdout.write(
            "Failed jobs until now cleared"
            + (f"; forgot {len(gone)} job record{'s' * (len(gone) != 1)}" if gone else "")
        )

    def start(self) -> None:
        """For bin/dev and the worker container: what state things are in, a catch-up run of every periodic job
        (each works from the data's state, so one run covers any outage up to its own lookback), then the worker."""
        try:
            self.status(fail_on_problems=False)
            refresh_dataset_status(settings.DATA_DIR)  # a deploy can make stores stale without a write
            self.report.step("dataset status refreshed for /api/v2/status")
            for job_id, name in abort_stalled_jobs():
                self.report.step(f"{short_name(name)}: job {job_id} was left by a stopped worker; marked aborted")
            now = int(time.time())
            for task in tasks.CATCH_UP:
                self.defer(task, now)
        except Exception as error:  # the worker starts anyway (the database may still be migrating)
            self.report.warn(f"no status or catch-up ({error!r}); starting the worker")
        sys.stdout.flush()
        manage = os.path.abspath(sys.argv[0])
        os.execv(sys.executable, [sys.executable, manage, "procrastinate", "worker"])
