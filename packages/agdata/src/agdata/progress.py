"""What a long-running command or script tells the person running it: timestamped steps, progress through a loop
with the time left, warnings and failures as they happen, and a summary at the end.

Commands (`ops.management.base.ReportingCommand`) and scripts make one `Reporter`; `quiet=True` (their `--quiet`)
keeps steps and progress off the terminal for jobs and background runs, while warnings and failures still go to
stderr. Everything also goes to `logging`, so a quiet run's log has it.

    report = Reporter()
    for k, month in enumerate(months, 1):
        ...
        report.progress("months", k, len(months))
    report.finish()  # "Done in 12 min: 22 months; 1 failed: …"
"""

import logging
import sys
import time
from collections.abc import Callable
from datetime import datetime
from typing import TextIO

logger = logging.getLogger("agdata.progress")


class Reporter:
    def __init__(
        self,
        out: TextIO | None = None,
        err: TextIO | None = None,
        quiet: bool = False,
        every_s: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self.quiet = quiet
        self.every_s = every_s  # progress lines at most this often (and always the last)
        self.clock = clock
        self.began = clock()
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self._last_progress: dict[str, float] = {}
        self._started: dict[str, float] = {}

    def step(self, message: str) -> None:
        """A line saying what's happening now."""
        logger.info(message)
        if not self.quiet:
            self._write(self.out, message)

    def progress(self, label: str, done: int, total: int) -> None:
        """`label: done/total (pct), elapsed, ~time left`, throttled to one line every `every_s` seconds per label;
        the first call for a label starts its clock."""
        now = self.clock()
        start = self._started.setdefault(label, now)
        if done < total and now - self._last_progress.get(label, -float("inf")) < self.every_s:
            return
        self._last_progress[label] = now
        elapsed = now - start
        line = f"{label}: {done}/{total}" + (f" ({100 * done / total:.0f}%)" if total else "")
        line += f", {_duration(elapsed)}"
        if 0 < done < total:
            line += f", ~{_duration(elapsed / done * (total - done))} left"
        self.step(line)

    def warn(self, message: str) -> None:
        """Something the person should know that doesn't stop the run (always shown, on stderr)."""
        logger.warning(message)
        self.warnings.append(message)
        self._write(self.err, f"warning: {message}")

    def fail(self, item: str, error: BaseException | str) -> None:
        """Something that failed and was left for a rerun (always shown, on stderr; counted in the summary)."""
        message = f"{item}: {error!r}" if isinstance(error, BaseException) else f"{item}: {error}"
        logger.error(message)
        self.failures.append(message)
        self._write(self.err, f"failed: {message}")

    def waiting_for_lock(self, holder: str) -> None:
        """For `ops.locks.write_lock(on_wait=)`: said when the wait starts and every minute after."""
        self.step(f"waiting for the write lock (held by pid {holder})")

    def summary(self, done: str = "") -> str:
        """`Done in <time>[: done]; N failed: …` (the failures listed)."""
        line = f"Done in {_duration(self.clock() - self.began)}" + (f": {done}" if done else "")
        if self.warnings:
            line += f"; {len(self.warnings)} warning{'s' * (len(self.warnings) != 1)}"
        if self.failures:
            line += f"; {len(self.failures)} failed:\n  " + "\n  ".join(self.failures)
        return line

    def finish(self, done: str = "") -> bool:
        """Prints the summary (failures to stderr even when quiet) and returns whether everything succeeded."""
        line = self.summary(done)
        if self.failures:
            logger.error(line)
            self._write(self.err, line)
        else:
            logger.info(line)
            self._write(self.out, line)  # the summary shows even when quiet
        return not self.failures

    def _write(self, stream: TextIO, line: str) -> None:
        stream.write(f"{datetime.now().astimezone():%H:%M:%S} {line}\n")
        stream.flush()  # output to a file is block-buffered


def _duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 90 * 60:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"
