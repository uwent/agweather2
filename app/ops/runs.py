"""The data commands running now and lately, for `manage.py archive` and the dashboard (`ops.tui`).

Each data command (`ops.management.base.ReportingCommand`) records itself in `data_dir/runs/` while it runs: a
`<key>.json` (what it is, when it started, its log) and a `<key>.events.jsonl` of everything it reported
(`agdata.progress.Reporter(events=)`), which the dashboard follows. A command's key is its pid. A command started
with `--background` runs detached with its output in `<started>-<command>.log` beside them.

In development the worker's jobs record themselves too (`ops.jobruns`), keyed `job-<id>` since they share the
worker's pid; a job that succeeds removes its record, so what stays is the ones that failed or were stopped.
`clear()` forgets finished runs and marks the job failures seen so far as cleared (`jobs_cleared_at`), which the
health checks' "failed jobs" count starts from.

Nothing here talks to the database, so the dashboard can list runs while the worker or a migration holds it.
"""

import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

JOBS_CLEARED = "jobs.cleared"  # in runs/: when the job failures were last cleared (ISO)
KEEP_DAYS = 14  # finished runs' records and logs are removed after this
INTERRUPTED = "Interrupted (Ctrl-C, or stopped twice); rerun to resume"
LAUNCH_NICE = 10  # launched runs' niceness (lower CPU priority than the dashboard)
LOG_ENV = "AGWX_RUN_LOG"  # a background run's log, passed to the detached process


@dataclass(kw_only=True)
class Run:
    pid: int  # a job's is its worker's
    command: str  # `backfill`, `archive`, …
    args: list[str]  # the arguments after the command's name
    started: str  # ISO time
    events: str  # path of its events file
    log: str | None = None  # a background run's output
    finished: str | None = None
    ok: bool | None = None
    summary: str = ""
    id: str = ""  # the record's key when it isn't the pid (`job-<id>`)

    @property
    def key(self) -> str:
        return self.id or str(self.pid)

    @property
    def is_job(self) -> bool:
        return self.id.startswith("job-")

    @property
    def label(self) -> str:
        return " ".join([self.command, *self.args])

    @property
    def running(self) -> bool:
        return self.finished is None and _alive(self.pid)

    @property
    def state(self) -> str:
        if self.finished is not None:
            if self.summary.startswith(INTERRUPTED):
                return "stopped"
            return "done" if self.ok else "failed"
        return "running" if _alive(self.pid) else "stopped"  # killed, or the machine restarted


def folder(data_dir: Path) -> Path:
    return data_dir / "runs"


def start(data_dir: Path, command: str, args: list[str], id: str = "") -> Run:
    """Records this process as a run of `command` (keyed `id`, else its pid); returns it (its `events` path is the
    reporter's)."""
    base = folder(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    _prune(base)
    pid = os.getpid()
    run = Run(
        pid=pid,
        command=command,
        args=args,
        started=datetime.now().astimezone().isoformat(timespec="seconds"),
        events=str(base / f"{id or pid}.events.jsonl"),
        log=None if id else os.environ.get(LOG_ENV),
        id=id,
    )
    Path(run.events).unlink(missing_ok=True)  # a reused key's old events
    _save(base, run)
    return run


def finish(data_dir: Path, run: Run, ok: bool, summary: str = "") -> None:
    run.finished = datetime.now().astimezone().isoformat(timespec="seconds")
    run.ok, run.summary = ok, summary
    _save(folder(data_dir), run)


def runs(data_dir: Path) -> list[Run]:
    """Every recorded run, newest first."""
    base = folder(data_dir)
    out = []
    for path in base.glob("*.json") if base.exists() else []:
        with contextlib.suppress(OSError, ValueError, TypeError):
            out.append(Run(**json.loads(path.read_text())))
    return sorted(out, key=lambda r: r.started, reverse=True)


def running(data_dir: Path) -> list[Run]:
    return [r for r in runs(data_dir) if r.running]


def events(run: Run, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
    """The run's events from byte `offset` on, and the offset to read from next (a partial last line waits)."""
    path = Path(run.events)
    if not path.exists():
        return [], offset
    with open(path, "rb") as handle:
        handle.seek(offset)
        data = handle.read()
    end = data.rfind(b"\n") + 1
    out = []
    for line in data[:end].splitlines():
        with contextlib.suppress(ValueError):
            out.append(json.loads(line))
    return out, offset + end


def forget(data_dir: Path, run: Run) -> None:
    """Removes a run's record, events and log."""
    _remove(folder(data_dir), run)


def clear(data_dir: Path) -> int:
    """Removes every run that isn't running (its record, events and log) and marks the job failures so far as
    cleared; returns how many runs it removed."""
    removed = 0
    for run in runs(data_dir):
        if run.running:
            continue
        _remove(folder(data_dir), run)
        removed += 1
    clear_jobs(data_dir)
    return removed


def clear_jobs(data_dir: Path) -> None:
    """Marks the jobs that failed until now as cleared: the "failed jobs" problem counts only later ones."""
    base = folder(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    (base / JOBS_CLEARED).write_text(datetime.now().astimezone().isoformat())  # to the microsecond: failures race it


def jobs_cleared_at(data_dir: Path) -> datetime | None:
    """When the job failures were last cleared, or None."""
    with contextlib.suppress(OSError, ValueError):
        return datetime.fromisoformat((folder(data_dir) / JOBS_CLEARED).read_text().strip())
    return None


def stop(run: Run) -> bool:
    """Asks a run to stop (SIGTERM): data commands finish their current block first; a second stop interrupts."""
    try:
        os.kill(run.pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    return True


def launch(data_dir: Path, argv: list[str]) -> tuple[int, Path]:
    """Starts `manage.py <argv>` detached (its own session, so closing the terminal or the dashboard doesn't stop
    it), with its output in a log under `runs/`; returns its pid and the log's path."""
    base = folder(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    log = base / f"{datetime.now().astimezone():%Y-%m-%dT%H%M%S}-{argv[0]}.log"
    manage = Path(__file__).resolve().parents[1] / "manage.py"
    with open(log, "ab") as out:
        process = subprocess.Popen(
            [sys.executable, str(manage), *argv],
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, LOG_ENV: str(log), "PYTHONUNBUFFERED": "1"},
            cwd=manage.parents[1],
            preexec_fn=_lower_priority,
        )
    return process.pid, log


def _lower_priority() -> None:
    """In the launched process before it starts: a lower CPU priority, so the dashboard and the shell stay quick
    while a build uses every core (it runs as fast as before when nothing else wants the CPU)."""
    with contextlib.suppress(OSError):
        os.nice(LAUNCH_NICE)


def tail(path: Path, lines: int = 200) -> list[str]:
    """The last `lines` lines of a log."""
    if not path.exists():
        return []
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - 200 * lines))
        text = handle.read().decode(errors="replace")
    return text.splitlines()[-lines:]


def _save(base: Path, run: Run) -> None:
    path = base / f"{run.key}.json"
    partial = path.with_suffix(".json.part")
    partial.write_text(json.dumps(asdict(run)))
    partial.replace(path)


def _prune(base: Path) -> None:
    cutoff = datetime.now().astimezone() - timedelta(days=KEEP_DAYS)
    for run in runs(base.parent):
        if run.running or datetime.fromisoformat(run.started) >= cutoff:
            continue
        _remove(base, run)


def _remove(base: Path, run: Run) -> None:
    for path in (
        base / f"{run.key}.json",
        Path(run.events) if run.events else None,
        Path(run.log) if run.log else None,
    ):
        if path is not None:
            path.unlink(missing_ok=True)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def iter_lines(run: Run) -> Iterator[str]:
    """A finished or running run's text: its log if it has one, else its events as lines."""
    if run.log and Path(run.log).exists():
        yield from tail(Path(run.log))
        return
    found, _ = events(run)
    for event in found:
        if "message" in event:
            yield event["message"]


@dataclass(kw_only=True)
class Latest:
    """What a run said last: its last step, its bars (label → done, total, elapsed), its activities in flight, its
    last details and warnings/failures."""

    step: str = ""
    bars: dict[str, tuple[int, int, float]] | None = None
    activities: dict[int, tuple[str, str, float]] | None = None  # id → label, stage, started (epoch)
    details: list[str] | None = None
    problems: list[str] | None = None
    updated: float = 0.0  # epoch of its last event


def latest(run: Run, nbytes: int = 256_000) -> Latest:
    """The run's state from the tail of its events file (bars and steps are re-sent often enough to be in it)."""
    path = Path(run.events)
    out = Latest(bars={}, activities={}, details=[], problems=[])
    if not path.exists():
        return out
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - nbytes))
        data = handle.read()
    lines = data.splitlines()[1 if size > nbytes else 0 :]  # the first may be cut
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        apply(out, event)
    return out


def apply(state: Latest, event: dict[str, Any]) -> None:
    """Folds one event into `state` (the dashboard does this as events arrive)."""
    assert state.bars is not None and state.activities is not None
    assert state.details is not None and state.problems is not None
    kind = event.get("kind")
    state.updated = event.get("t", state.updated)
    if kind in ("step", "resume"):  # resume: the step before a wait for the lock, once it's over
        state.step = event["message"]
    elif kind == "progress":
        if event["done"] >= event["total"]:
            state.bars.pop(event["label"], None)
        else:
            state.bars[event["label"]] = (event["done"], event["total"], event.get("elapsed", 0.0))
    elif kind == "activity":
        if event["state"] == "end":
            state.activities.pop(event["id"], None)
        elif event["state"] == "start":
            state.activities[event["id"]] = (event["label"], event.get("stage", ""), event["t"])
        elif event["id"] in state.activities:
            label, _, began = state.activities[event["id"]]
            state.activities[event["id"]] = (label, event.get("stage", ""), began)
    elif kind == "detail":
        state.details.append(event["message"])
        del state.details[:-200]
    elif kind in ("warn", "fail"):
        state.problems.append(("warning: " if kind == "warn" else "failed: ") + event["message"])
    elif kind == "finish":
        state.step = event["message"]
