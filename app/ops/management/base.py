"""What every data command shares: `--quiet`, a `Reporter` for progress and the summary, the write lock taken with
a wait that says whose lock it's waiting for, date arguments checked, and a nonzero exit when anything failed (so a
script or cron line running the command notices)."""

from contextlib import AbstractContextManager
from datetime import UTC, date, datetime
from functools import cached_property

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.grid import service_window
from agdata.progress import Reporter
from ops.locks import write_lock

LOCK_WAIT_S = 3600  # a command waits this long for a job's or another command's write to finish


class ReportingCommand(BaseCommand):
    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="print only warnings, failures and the summary (for jobs and background runs)",
        )
        return parser

    def execute(self, *args, **options):
        self.quiet = bool(options.get("quiet"))
        return super().execute(*args, **options)

    @cached_property
    def report(self) -> Reporter:
        return Reporter(out=self.stdout, err=self.stderr, quiet=getattr(self, "quiet", False))  # type: ignore[arg-type]

    def lock(self, wait: float | None = None) -> AbstractContextManager[None]:
        """The archive's write lock, waiting up to `wait` seconds (default LOCK_WAIT_S) for it and saying so."""
        wait = LOCK_WAIT_S if wait is None else wait
        return write_lock(settings.DATA_DIR, wait=wait, on_wait=self.report.waiting_for_lock)

    def window(self, box: str | None):
        try:
            return service_window(box or settings.SERVICE_BOX)
        except (KeyError, ValueError) as error:
            raise CommandError(f"--box {box!r}: {error}") from error

    def finish(self, done: str = "") -> None:
        """The summary; a CommandError (exit 1) if anything failed, so whoever ran it notices."""
        if not self.report.finish(done):
            raise CommandError(f"{len(self.report.failures)} failed (listed above); rerun to retry them")


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
