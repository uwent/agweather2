"""The archive a year at a time, and the data commands running on it:

manage.py archive                         # each year: hours, precip, shortwave, ERA5-Land, rolled up, past years;
                                          # the lock, who's waiting, and the runs in progress
manage.py archive fill --from 2016        # fill 2016 to last year, newest first (add --background to detach)
manage.py archive fill --from 2016 --dry-run   # what it would fetch, and about how long
manage.py archive runs                    # the data commands run lately
manage.py archive log [PID] [-n 50]       # a run's last lines (the newest run without PID)
manage.py archive stop [PID]              # ask a run (or every run) to stop after its current block
manage.py archive clear                   # forget the runs that aren't running (their records and logs)

`uv run app/manage.py` with no command opens the dashboard (`ops.tui`), which shows all of this live.
"""

import time
from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import CommandError

from ops import archive, locks, runs
from ops.management.base import ReportingCommand, positive
from ops.status import lock_holder


class Command(ReportingCommand):
    help = "The archive by year, filling whole years, and the data commands running on it (see `archive --help`)."
    stoppable = True

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action")
        sub.add_parser("status", help="each year's state, the lock and the runs in progress (the default)")
        fill = sub.add_parser("fill", help="fill whole years: hours, December 31, ERA5-Land, past-years copy")
        fill.add_argument("--from", dest="first", type=int, required=True, help="first year")
        fill.add_argument("--to", dest="last", type=int, default=None, help="last year (default: last year)")
        fill.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        fill.add_argument("--workers", type=int, default=4, help="hours fetched in parallel")
        fill.add_argument("--block-days", type=int, default=5, help="days per block (memory grows with it)")
        fill.add_argument("--no-overlap", action="store_true", help="finish each year's soil before the next year")
        fill.add_argument("--no-soil", action="store_true", help="skip ERA5-Land")
        fill.add_argument("--no-past-years", action="store_true", help="skip the past-years copies")
        fill.add_argument("--dry-run", action="store_true", help="print the plan and the estimate only")
        sub.add_parser("runs", help="the data commands run lately")
        log = sub.add_parser("log", help="a run's last lines")
        log.add_argument("pid", nargs="?", type=int, help="the run (default: the newest)")
        log.add_argument("-n", type=int, default=40, help="lines (default 40)")
        stop = sub.add_parser("stop", help="ask runs to stop after their current block")
        stop.add_argument("pid", nargs="?", type=int, help="the run (default: every running one)")
        sub.add_parser("clear", help="forget the runs that aren't running (records, events and logs)")

    def is_tracked(self, options) -> bool:
        return options.get("action") == "fill" and not options.get("dry_run")

    def handle(self, *args, **options):
        action = options.get("action") or "status"
        if action == "status":
            self.status()
        elif action == "fill":
            self.fill(options)
        elif action == "runs":
            self.list_runs()
        elif action == "log":
            self.log(options["pid"], positive(options["n"], "-n"))
        elif action == "stop":
            self.stop(options["pid"])
        elif action == "clear":
            removed = runs.clear(settings.DATA_DIR)
            self.stdout.write(
                f"Cleared {removed} finished run{'s' * (removed != 1)}" if removed else "Nothing to clear"
            )

    # status

    def status(self) -> None:
        data_dir = settings.DATA_DIR
        now = datetime.now(UTC)
        self.stdout.write(f"Archive in {data_dir} ({settings.SERVICE_BOX}), {now.astimezone():%Y-%m-%d %H:%M %Z}")
        self.stdout.write(
            f"  {'year':<5} {'hours':>13} {'URMA':>6} {'RTMA':>6} {'precip':>7} {'shortwave':>9} "
            f"{'ERA5-Land':>11} {'rolled up':>11}  past years"
        )
        for y in archive.year_states(data_dir, now=now):
            mark = "✓" if y.complete else " "
            self.stdout.write(
                f"{mark} {y.year:<5} {_frac(y.analysis, y.hours):>13} {y.urma:>6,} {y.rtma:>6,} "
                f"{_pct(y.precip, y.hours):>7} {_pct(y.shortwave, y.hours):>9} {_frac(y.era5land_days, y.days):>11} "
                f"{_frac(y.rolled_up, y.days):>11}  {y.past_years}"
                + ("  (manage.py pastyears rebuilds it)" if _rebuildable(y) else "")
                + (f"  stale: {', '.join(y.stale)}" if y.stale else "")
            )
        holder = lock_holder(data_dir)
        self.stdout.write(f"Lock: {'held by ' + holder if holder else 'free'}")
        for waiter in locks.waiting(data_dir):
            self.stdout.write(f"  waiting: {waiter}")
        active = runs.running(data_dir)
        self.stdout.write("Running:" + ("" if active else " nothing"))
        for run in active:
            state = runs.latest(run)
            self.stdout.write(f"  pid {run.pid}: {run.label} (since {_since(run.started)})")
            for label, (done, total, elapsed) in (state.bars or {}).items():
                left = f", ~{_duration(elapsed / done * (total - done))} left" if done else ""
                self.stdout.write(f"    {label}: {done:,}/{total:,} ({100 * done / max(total, 1):.0f}%){left}")
            if state.step:
                self.stdout.write(f"    {state.step}")

    # fill

    def fill(self, options) -> None:
        this_year = datetime.now(UTC).year
        first, last = options["first"], options["last"] or this_year - 1
        if not 2016 <= first <= last <= this_year:
            raise CommandError(f"--from {first} --to {last}: years from 2016 to {this_year}, --from first")
        workers = positive(options["workers"], "--workers")
        block_days = positive(options["block_days"], "--block-days")
        window = self.window(options["box"])
        data_dir = settings.DATA_DIR
        years = list(range(first, last + 1))
        self.report.step(f"Planning {first}–{last} (reading what each year holds)")
        with self.lock():
            plans = archive.plan_years(data_dir, window, years, block_days)
        per_hour = archive.seconds_per_hour()
        for plan in plans:
            self.report.step(
                f"  {plan.year}: {plan.hours.hours:,} hours to fetch, {plan.era5land_days} days of ERA5-Land, "
                f"past-years copy {'to build' if plan.past_years else 'current'}"
            )
        estimate = archive.estimate_s(plans, per_hour)
        self.report.step(
            f"About {_duration(estimate)} at {per_hour:.1f} s per hour of data ({workers} at a time)"
            + ("" if options["no_overlap"] else "; ERA5-Land overlaps the next year's hours")
        )
        if options["dry_run"]:
            self.finish("dry run: nothing fetched")
            return
        result = archive.fill(
            data_dir=data_dir,
            window=window,
            box=options["box"] or settings.SERVICE_BOX,
            plans=plans,
            report=self.report,
            lock=self.lock,
            stopping=self.stopping,
            workers=workers,
            key=None if options["no_soil"] else settings.COPERNICUS_API_KEY,
            overlap=not options["no_overlap"],
            soil=not options["no_soil"],
            past=not options["no_past_years"],
        )
        years_done = ", ".join(str(y) for y in result.years) or "none"
        self.finish(f"years {years_done}: {result.fetched:,} hours fetched, {result.failed} failed")

    # runs

    def list_runs(self) -> None:
        found = runs.runs(settings.DATA_DIR)
        if not found:
            self.stdout.write("No runs recorded")
        for run in found[:30]:
            ended = f", ended {_since(run.finished)}" if run.finished else ""
            self.stdout.write(f"{run.pid:>8}  {run.state:<8} {_since(run.started)}{ended}  {run.label}")
            if run.summary and not run.running:
                self.stdout.write(f"{'':>10}{run.summary.splitlines()[0]}")

    def log(self, pid: int | None, lines: int) -> None:
        run = self._find(pid)
        self.stdout.write(f"pid {run.pid}: {run.label} ({run.state})" + (f", log {run.log}" if run.log else ""))
        for line in list(runs.iter_lines(run))[-lines:]:
            self.stdout.write(line)

    def stop(self, pid: int | None) -> None:
        targets = [self._find(pid)] if pid else [r for r in runs.running(settings.DATA_DIR) if not r.is_job]
        if not targets:
            self.stdout.write("Nothing running")
            return
        for run in targets:
            if run.is_job:  # its pid is the worker's
                self.stdout.write(f"{run.label} is a job: it stops with the worker (bin/dev)")
                continue
            if runs.stop(run):
                self.stdout.write(f"Asked pid {run.pid} ({run.label}) to stop after its current block")
            else:
                self.stdout.write(f"pid {run.pid} isn't running")

    def _find(self, pid: int | None) -> runs.Run:
        found = runs.runs(settings.DATA_DIR)
        if pid is None:
            if not found:
                raise CommandError("no runs recorded")
            return found[0]
        for run in sorted(found, key=lambda r: r.is_job):  # a command before a job of the worker with that pid
            if run.pid == pid:
                return run
        raise CommandError(f"no run with pid {pid} (see `archive runs`)")


def _frac(done: int, total: int) -> str:
    return f"{done:,}/{total:,}"


def _pct(done: int, total: int) -> str:
    return f"{100 * done / total:.0f}%" if total else "–"


def _since(iso: str | None) -> str:
    if not iso:
        return "?"
    when = datetime.fromisoformat(iso)
    age = time.time() - when.timestamp()
    return f"{when:%m-%d %H:%M}" if age > 86400 else f"{when:%H:%M}"


def _duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 90 * 60:
        return f"{seconds / 60:.0f} min"
    if seconds < 48 * 3600:
        return f"{seconds / 3600:.1f} h"
    return f"{seconds / 86400:.1f} days"


def _rebuildable(y) -> bool:
    """A year whose past-years copy `pastyears` can build now: rolled up whole, and the copy missing or out of date
    (a year still being filled gets its copy from `archive fill` when it's done)."""
    return y.past_years not in ("current", "–") and y.rolled_up == y.days
