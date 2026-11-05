"""What a long-running command or script tells the person running it: timestamped steps, progress through a loop
with the time left, the detail of each file read (v1's `HOUR 05 ==> GET …` lines), warnings and failures as they
happen, and a summary at the end.

Commands (`ops.management.base.ReportingCommand`) and scripts make one `Reporter`. It writes to up to three places:

- **Text** (a log file, a pipe, or `live=False`): a timestamped line per step, detail and throttled progress.
  `quiet=True` (their `--quiet`) keeps all but warnings, failures and the summary off it.
- **Live** (a terminal): a display redrawn in place: a bar per progress label with the time left, a spinner row
  per activity in flight (an hour being fetched, a CDS request queued) and the last detail lines; steps, warnings
  and failures print above it and stay in the scrollback.
- **Events** (`events=path`): every call as a JSON line, which the dashboard (`ops.tui`) follows.

Code deep in a pipeline reports without being handed the reporter: `activate()` makes it the current one, and
`current()`, `activity()` and `file_read()` (called by `agdata.sources.grib.RemoteGrib`) find it. Without an
active reporter they do nothing, so the worker's jobs pay nothing.

    report = Reporter()
    with report.activate():
        for k, month in enumerate(months, 1):
            with report.activity(f"CDS {month}") as act:
                act.stage("queued")
                ...
            report.progress("months", k, len(months))
    report.finish()  # "Done in 12 min: 22 months; 1 failed: …"
"""

import contextlib
import itertools
import json
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

DETAIL_LINES = 10  # detail lines kept under the live display
EVENT_PROGRESS_S = 1.0  # progress events at most this often per label (and always the last)


@dataclass(kw_only=True)
class Activity:
    """Something in flight (one hour's fetch, one CDS request): a spinner row with its current stage."""

    id: int
    label: str
    began: float
    stage_text: str = ""
    reporter: "Reporter | None" = None

    def stage(self, text: str) -> None:
        self.stage_text = text
        if self.reporter is not None:
            self.reporter._event("activity", id=self.id, label=self.label, stage=text, state="stage")


@dataclass(kw_only=True)
class _Bar:
    done: int
    total: int
    began: float
    updated: float = 0.0


@dataclass(kw_only=True)
class _State:
    bars: dict[str, _Bar] = field(default_factory=dict)
    activities: dict[int, Activity] = field(default_factory=dict)
    details: deque = field(default_factory=lambda: deque(maxlen=DETAIL_LINES))


_active: list["Reporter"] = []  # a stack: the innermost activate() wins
_local = threading.local()  # the activity running on this thread, so file reads say which hour they're for


def current() -> "Reporter | None":
    return _active[-1] if _active else None


@contextlib.contextmanager
def activity(label: str) -> Iterator[Activity | None]:
    """The current reporter's activity, or None (and nothing shown) without one."""
    report = current()
    if report is None:
        yield None
        return
    with report.activity(label) as act:
        yield act


def file_read(url: str, messages: int, nbytes: int, get_s: float, decode_s: float) -> None:
    """A GRIB file's wanted messages downloaded and decoded (from `RemoteGrib`): a detail line on the current
    reporter, prefixed with the activity it was read for."""
    report = current()
    if report is None:
        return
    act: Activity | None = getattr(_local, "activity", None)
    prefix = f"{act.label}  " if act is not None else ""
    report.detail(
        f"{prefix}GET {_short_url(url)}: {messages} msg{'s' * (messages != 1)}, {nbytes / 1e6:.1f} MB "
        f"in {get_s:.1f} s, decoded in {decode_s:.1f} s"
    )


def file_opened(url: str) -> None:
    """A GRIB file about to be read: the current activity's stage."""
    act: Activity | None = getattr(_local, "activity", None)
    if act is not None:
        act.stage(f"GET {_short_url(url)}")


class Reporter:
    def __init__(
        self,
        out: TextIO | None = None,
        err: TextIO | None = None,
        quiet: bool = False,
        every_s: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
        live: bool | None = None,
        events: Path | None = None,
    ):
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self.quiet = quiet
        self.every_s = every_s  # text progress lines at most this often (and always the last)
        self.clock = clock
        self.began = clock()
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.last_summary = ""  # what finish() printed
        self.doing = ""  # the last step, which a wait for the lock interrupts and `got_lock()` puts back
        self._waiting_since: float | None = None
        self.live = (not quiet and _is_terminal(self.out)) if live is None else live
        self._last_progress: dict[str, float] = {}
        self._started: dict[str, float] = {}
        self._state = _State()
        self._lock = threading.RLock()
        self._ids = itertools.count(1)
        self._events: TextIO | None = None
        if events is not None:
            events.parent.mkdir(parents=True, exist_ok=True)
            self._events = open(events, "a", buffering=1)  # noqa: SIM115  (closed by close())
        self._display = None  # rich.live.Live while the live display runs

    # The live display and the current reporter

    def start(self) -> None:
        """Starts the live display (when live). Commands call this before their work and `close()` after."""
        if not self.live or self._display is not None:
            return
        from rich.console import Console
        from rich.live import Live

        console = Console(file=self.out, stderr=False)  # type: ignore[arg-type]
        self._display = Live(get_renderable=self._render, console=console, refresh_per_second=8, transient=True)
        self._display.start()

    def close(self) -> None:
        if self._display is not None:
            self._display.stop()
            self._display = None
        if self._events is not None:
            self._events.close()
            self._events = None

    @contextlib.contextmanager
    def activate(self) -> Iterator["Reporter"]:
        """Makes this the reporter `current()`, `activity()` and `file_read()` find, and runs the live display."""
        self.start()
        _active.append(self)
        try:
            yield self
        finally:
            _active.remove(self)

    # What commands call

    def step(self, message: str) -> None:
        """A line saying what's happening now."""
        self.doing = message
        self._event("step", message=message)
        if not self.quiet:
            self._print(self.out, message)

    def detail(self, message: str) -> None:
        """A finer line than a step (each file read, each hour written): in the text log, and under the live display's
        bars; not kept in a terminal's scrollback, where there would be thousands."""
        self._event("detail", message=message)
        if self.quiet:
            return
        if self._display is not None:
            with self._lock:
                self._state.details.append(f"{datetime.now().astimezone():%H:%M:%S} {message}")
        else:
            self._write(self.out, message)

    def progress(self, label: str, done: int, total: int) -> None:
        """A bar on the live display; in text, `label: done/total (pct), elapsed, ~time left`, throttled to one line
        every `every_s` seconds per label. The first call for a label starts its clock."""
        now = self.clock()
        start = self._started.setdefault(label, now)
        with self._lock:
            bar = self._state.bars.setdefault(label, _Bar(done=done, total=total, began=start))
            bar.done, bar.total = done, total
            if done >= total or now - bar.updated >= EVENT_PROGRESS_S:
                bar.updated = now
                self._event("progress", label=label, done=done, total=total, elapsed=now - start)
        if self._display is not None:
            if done >= total:
                with self._lock:
                    self._state.bars.pop(label, None)
                if not self.quiet:
                    self._print(self.out, _progress_line(label, done, total, now - start))
            return
        if done < total and now - self._last_progress.get(label, -float("inf")) < self.every_s:
            return
        self._last_progress[label] = now
        if not self.quiet:
            self._write(self.out, _progress_line(label, done, total, now - start))

    @contextlib.contextmanager
    def activity(self, label: str) -> Iterator[Activity]:
        """A spinner row for something in flight; `.stage(text)` says what it's doing. File reads on this thread
        while it runs are prefixed with its label."""
        act = Activity(id=next(self._ids), label=label, began=self.clock(), reporter=self)
        with self._lock:
            self._state.activities[act.id] = act
        self._event("activity", id=act.id, label=label, stage="", state="start")
        outer = getattr(_local, "activity", None)
        _local.activity = act
        try:
            yield act
        finally:
            _local.activity = outer
            with self._lock:
                self._state.activities.pop(act.id, None)
            self._event("activity", id=act.id, label=label, stage=act.stage_text, state="end")

    def warn(self, message: str) -> None:
        """Something the person should know that doesn't stop the run (always shown, on stderr)."""
        self.warnings.append(message)
        self._event("warn", message=message)
        self._print(self.err, f"warning: {message}")

    def fail(self, item: str, error: BaseException | str) -> None:
        """Something that failed and was left for a rerun (always shown, on stderr; counted in the summary)."""
        message = f"{item}: {error!r}" if isinstance(error, BaseException) else f"{item}: {error}"
        self.failures.append(message)
        self._event("fail", message=message)
        self._print(self.err, f"failed: {message}")

    def waiting_for_lock(self, holder: str) -> None:
        """For `ops.locks.write_lock(on_wait=)`: said when the wait starts and every minute after."""
        doing = self.doing
        if self._waiting_since is None:
            self._waiting_since = self.clock()
        self.step(f"waiting for the write lock (held by {holder})")
        self.doing = doing

    def got_lock(self) -> None:
        """For `ops.locks.write_lock(on_acquired=)`: the wait is over, so the step before it is what's happening
        again (a `resume` event, which the dashboard's "doing" shows, and a detail line saying how long it took)."""
        if self._waiting_since is None:
            return
        waited = self.clock() - self._waiting_since
        self._waiting_since = None
        self.detail(f"got the write lock after {_duration(waited)}")
        self._event("resume", message=self.doing)

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
        self.last_summary = line
        self._event("finish", ok=not self.failures, message=line)
        self._print(self.err if self.failures else self.out, line)  # the summary shows even when quiet
        return not self.failures

    # Output

    def _print(self, stream: TextIO, line: str) -> None:
        """A line that stays: above the live display, or in the text."""
        if self._display is not None:
            failed = line.startswith("failed") or (line.startswith("Done") and bool(self.failures))
            style = "red" if failed else "yellow" if line.startswith("warning") else None
            self._display.console.print(
                f"[dim]{datetime.now().astimezone():%H:%M:%S}[/dim] {_escape(line)}", style=style, highlight=False
            )
        else:
            self._write(stream, line)

    def _write(self, stream: TextIO, line: str) -> None:
        with self._lock:
            stream.write(f"{datetime.now().astimezone():%H:%M:%S} {line}\n")
            stream.flush()  # output to a file is block-buffered

    def _event(self, kind: str, **fields: Any) -> None:
        if self._events is None:
            return
        with self._lock:
            if self._events is not None:
                self._events.write(json.dumps({"t": round(time.time(), 2), "kind": kind, **fields}) + "\n")

    def _render(self):
        from rich.console import Group
        from rich.progress_bar import ProgressBar
        from rich.spinner import Spinner
        from rich.table import Table
        from rich.text import Text

        now = self.clock()
        with self._lock:
            bars = list(self._state.bars.items())
            acts = sorted(self._state.activities.values(), key=lambda a: a.id)
            details = list(self._state.details)
        parts: list[Any] = []
        if details:
            parts.append(Text("\n".join(details), style="dim", no_wrap=True, overflow="ellipsis"))
        if acts:
            table = Table.grid(padding=(0, 1))
            for act in acts[:12]:
                table.add_row(
                    Spinner("dots", style="cyan"),
                    Text(act.label, style="bold"),
                    Text(act.stage_text, no_wrap=True, overflow="ellipsis"),
                    Text(_duration(now - act.began), style="dim"),
                )
            if len(acts) > 12:
                table.add_row("", Text(f"and {len(acts) - 12} more", style="dim"), "", "")
            parts.append(table)
        if bars:
            table = Table.grid(padding=(0, 1))
            for label, bar in bars:
                elapsed = now - bar.began
                left = f"~{_duration(elapsed / bar.done * (bar.total - bar.done))} left" if bar.done else ""
                table.add_row(
                    Text(label, style="bold"),
                    ProgressBar(total=max(bar.total, 1), completed=bar.done, width=30),
                    Text(f"{bar.done}/{bar.total}"),
                    Text(_duration(elapsed), style="dim"),
                    Text(left, style="dim"),
                )
            parts.append(table)
        return Group(*parts)


def _progress_line(label: str, done: int, total: int, elapsed: float) -> str:
    line = f"{label}: {done}/{total}" + (f" ({100 * done / total:.0f}%)" if total else "")
    line += f", {_duration(elapsed)}"
    if 0 < done < total:
        line += f", ~{_duration(elapsed / done * (total - done))} left"
    return line


def _is_terminal(stream: TextIO) -> bool:
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def _escape(text: str) -> str:
    from rich.markup import escape

    return escape(text)


def _short_url(url: str) -> str:
    """The bucket and key, without the scheme and S3's host suffix."""
    rest = url.split("://", 1)[-1]
    host, _, path = rest.partition("/")
    return f"{host.split('.', 1)[0]}/{path}"


def _duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 90 * 60:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"
