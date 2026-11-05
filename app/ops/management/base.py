"""What every data command shares:

- `--quiet`, and a `Reporter` for steps, details, progress and the summary: a live display on a terminal, text in
  a log or pipe (`agdata.progress`);
- `--background`: the same command started detached, its output in a log under `data/runs/`;
- a record of the run in `data/runs/` with its events, which `manage.py archive` and the dashboard (`ops.tui`) read;
- the write lock taken with a wait that says whose lock it's waiting for, labelled with this command;
- a first SIGTERM (`archive stop`, the dashboard) asks a `stoppable` command to stop after its current block;
- date arguments checked, and a nonzero exit when anything failed (so a script or cron line notices).
"""

import contextlib
import signal
import threading
from contextlib import AbstractContextManager
from datetime import UTC, date, datetime
from functools import cached_property
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, OutputWrapper

from agdata.grid import service_window
from agdata.progress import Reporter
from ops import locks, runs
from ops.locks import write_lock

LOCK_WAIT_S = 3600  # a command waits this long for a job's or another command's write to finish


class ReportingCommand(BaseCommand):
    tracked = True  # recorded in data/runs/ (status commands that only read set this False)
    stoppable = False  # checks `self.stopping` between blocks, so a first SIGTERM can let it finish one

    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="print only warnings, failures and the summary (for jobs and background runs)",
        )
        if self.tracked:
            parser.add_argument(
                "--background",
                action="store_true",
                help="run detached, output to a log under data/runs/ (follow it in `manage.py` or with tail -f)",
            )
        return parser

    def run_from_argv(self, argv):
        self._argv = argv[2:]  # for --background, which starts the same command again without it
        return super().run_from_argv(argv)

    def is_tracked(self, options) -> bool:
        """Whether this invocation is recorded as a run (a command whose status subcommand only reads says no)."""
        return self.tracked

    @property
    def command_name(self) -> str:
        return self.__module__.rsplit(".", 1)[-1]

    def execute(self, *args, **options):
        self.quiet = bool(options.get("quiet"))
        self.stopping = threading.Event()
        # As BaseCommand.execute does, but before the reporter is made from them
        if options.get("stdout"):
            self.stdout = OutputWrapper(options["stdout"])
        if options.get("stderr"):
            self.stderr = OutputWrapper(options["stderr"])
        if options.get("background"):
            return self.launch_background()
        if not self.is_tracked(options):
            return super().execute(*args, **options)
        argv = [a for a in getattr(self, "_argv", []) if a != "--quiet"]
        locks.set_label(" ".join([self.command_name, *argv]))
        self.run_record = runs.start(settings.DATA_DIR, self.command_name, argv)
        ok, summary = False, ""
        previous = self._install_signals()
        try:
            with self.report.activate():
                result = super().execute(*args, **options)
            ok = not self.report.failures
            summary = self.report.last_summary or self.report.summary()
            return result
        except BaseException as error:
            if isinstance(error, KeyboardInterrupt):
                summary = runs.INTERRUPTED  # Ctrl-C, or a second stop
            elif isinstance(error, CommandError):
                summary = self.report.last_summary or self.report.summary()
            else:
                summary = f"{type(error).__name__}: {error}"
            raise
        finally:
            self.report.close()
            self._restore_signals(previous)
            runs.finish(settings.DATA_DIR, self.run_record, ok, summary)

    def launch_background(self) -> None:
        argv = [a for a in getattr(self, "_argv", []) if a != "--background"]
        if not argv:
            raise CommandError("--background works from the command line only")
        pid, log = runs.launch(settings.DATA_DIR, [self.command_name, *argv])
        self.stdout.write(
            f"Started `{' '.join([self.command_name, *argv])}` in the background (pid {pid}).\n"
            f"  watch: uv run app/manage.py        (the dashboard), or tail -f {log}\n"
            f"  stop:  uv run app/manage.py archive stop {pid}"
        )

    @cached_property
    def report(self) -> Reporter:
        run = getattr(self, "run_record", None)
        return Reporter(
            out=getattr(self.stdout, "_out", self.stdout),  # type: ignore[arg-type]  # raw: the wrapper adds newlines
            err=getattr(self.stderr, "_out", self.stderr),  # type: ignore[arg-type]
            quiet=getattr(self, "quiet", False),
            events=None if run is None else Path(run.events),
        )

    def lock(self, wait: float | None = None, polite: bool = False) -> AbstractContextManager[None]:
        """The archive's write lock, waiting up to `wait` seconds (default LOCK_WAIT_S) for it and saying so;
        `polite` (a long run taking it block after block) lets anyone waiting go first."""
        wait = LOCK_WAIT_S if wait is None else wait
        return write_lock(
            settings.DATA_DIR,
            wait=wait,
            on_wait=self.report.waiting_for_lock,
            on_acquired=self.report.got_lock,
            polite=polite,
        )

    def window(self, box: str | None):
        try:
            return service_window(box or settings.SERVICE_BOX)
        except (KeyError, ValueError) as error:
            raise CommandError(f"--box {box!r}: {error}") from error

    def finish(self, done: str = "") -> None:
        """The summary; a CommandError (exit 1) if anything failed, so whoever ran it notices."""
        if self.stopping.is_set():
            done = (done + "; " if done else "") + "stopped early (rerun to resume)"
        if not self.report.finish(done):
            raise CommandError(f"{len(self.report.failures)} failed (listed above); rerun to retry them")

    def _install_signals(self):
        if threading.current_thread() is not threading.main_thread():
            return None

        def on_signal(signum, frame):
            if self.stoppable and not self.stopping.is_set():
                self.stopping.set()
                self.report.step("Stopping after the current block (stop again to interrupt)")
                return
            raise KeyboardInterrupt

        return {sig: signal.signal(sig, on_signal) for sig in (signal.SIGTERM, signal.SIGINT)}

    def _restore_signals(self, previous) -> None:
        for sig, handler in (previous or {}).items():
            with contextlib.suppress(ValueError, TypeError):
                signal.signal(sig, handler)


def parse_day(text: str, flag: str) -> date:
    """A YYYY-MM-DD argument; anything else (a time, an offset) is an error rather than silently dropped."""
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise CommandError(f"{flag} {text!r}: expected a date, YYYY-MM-DD") from None


def utc_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def check_range(first: date, end: date, end_flag: str = "--end", exclusive: bool = True) -> None:
    """`--end` must be after `--start` (or on or after it, for an inclusive end)."""
    if end < first or (exclusive and end == first):
        relation = "after" if exclusive else "on or after"
        raise CommandError(f"{end_flag} {end} must be {relation} --start {first}")


def positive(value: int, flag: str) -> int:
    if value < 1:
        raise CommandError(f"{flag} must be at least 1 (got {value})")
    return value
