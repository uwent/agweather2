"""One writer at a time for the Zarr archive: two would write the same chunks and double the memory and bandwidth.

The lock is `data_dir/write.lock`, an flock that also holds who has it (`pid`, a label such as `backfill 2024`, and
since when), so anything waiting can say whose it's waiting for.

Long runs take the lock again and again (a backfill, once per block), and a waiter polling every few seconds would
almost never catch it free. So a waiter leaves a marker in `data_dir/write.waiting/` while it waits, and a long run
takes the lock `polite`ly: it lets any (impolite) waiter go first. The flock is still what keeps writers apart; the
markers only order them, so a stale marker costs a polite writer at most `POLITE_MAX_S`.
"""

import contextlib
import fcntl
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO

from django.core.management.base import CommandError

POLITE_MAX_S = 600  # a polite writer waits at most this long for others' turns before taking its own
_label = " ".join(os.path.basename(a) for a in sys.argv[:3])  # this process's default label; commands set theirs


def set_label(label: str) -> None:
    """What this process's locks say it is (`manage.py` commands set their name and arguments)."""
    global _label
    _label = label


@dataclass(kw_only=True)
class Holder:
    pid: str
    label: str = ""
    since: datetime | None = None

    def __str__(self) -> str:
        what = self.label + (f", since {self.since:%H:%M}" if self.since else "")
        return f"pid {self.pid}" + (f" ({what})" if what else "")


class WriteLocked(CommandError):
    def __init__(self, message: str, holder: str = "?", description: str | None = None):
        super().__init__(message)
        self.holder = holder  # the pid
        self.description = description or f"pid {holder}"  # pid, label and since


def parse_holder(text: str) -> Holder:
    """The lock file's `pid\\tlabel\\tsince` (or a bare pid, as written before labels)."""
    pid, _, rest = text.strip().partition("\t")
    label, _, since = rest.partition("\t")
    try:
        when = datetime.fromisoformat(since) if since else None
    except ValueError:
        when = None
    return Holder(pid=pid or "?", label=label, since=when)


def hold_write_lock(data_dir: Path, label: str | None = None) -> IO[str]:
    """Takes `data_dir/write.lock` (holding this process's pid and `label`) until the returned file closes or the
    process exits."""
    data_dir.mkdir(parents=True, exist_ok=True)
    handle = open(data_dir / "write.lock", "a+")  # noqa: SIM115
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.seek(0)
        holder = parse_holder(handle.read())
        handle.close()
        raise WriteLocked(
            f"another job or command is writing to {data_dir} ({holder})", holder=holder.pid, description=str(holder)
        ) from None
    handle.truncate(0)
    handle.write(f"{os.getpid()}\t{label or _label}\t{datetime.now().astimezone().isoformat(timespec='seconds')}")
    handle.flush()
    return handle


@contextmanager
def write_lock(
    data_dir: Path,
    wait: float = 0,
    poll: float = 5,
    on_wait: Callable[[str], None] | None = None,
    label: str | None = None,
    polite: bool = False,
) -> Iterator[None]:
    """The write lock for a block of code. With `wait`, tries again every `poll` seconds for up to `wait` seconds
    before raising WriteLocked, leaving a marker so polite holders let it in; `on_wait(holder)` is called when the
    wait starts and about every minute after, so a command can say why it's quiet. `polite` (long runs that take
    the lock over and over) first lets anyone waiting go first."""
    if polite:
        _let_waiters_go(data_dir, poll)
    deadline = time.monotonic() + wait
    said = -float("inf")
    marker: Path | None = None
    try:
        while True:
            try:
                handle = hold_write_lock(data_dir, label)
                break
            except WriteLocked as error:
                if time.monotonic() >= deadline:
                    raise
                if marker is None and not polite:
                    marker = _mark_waiting(data_dir, label)
                if on_wait is not None and time.monotonic() - said >= 60:
                    on_wait(error.description)
                    said = time.monotonic()
                time.sleep(min(poll, max(deadline - time.monotonic(), 0.01)))
    finally:
        if marker is not None:
            marker.unlink(missing_ok=True)
    try:
        yield
    finally:
        try:
            _refresh_status(data_dir)
        finally:
            handle.close()


def waiting(data_dir: Path) -> list[Holder]:
    """Who's waiting for the lock now (dead processes' markers are removed)."""
    folder = data_dir / "write.waiting"
    out = []
    for path in sorted(folder.glob("*")) if folder.exists() else []:
        pid = path.name.split(".", 1)[0]
        if not _alive(pid):
            path.unlink(missing_ok=True)
            continue
        with contextlib.suppress(OSError):
            out.append(parse_holder(path.read_text()))
    return out


def _mark_waiting(data_dir: Path, label: str | None) -> Path:
    folder = data_dir / "write.waiting"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{os.getpid()}.{threading.get_ident()}"
    path.write_text(f"{os.getpid()}\t{label or _label}\t{datetime.now().astimezone().isoformat(timespec='seconds')}")
    return path


def _let_waiters_go(data_dir: Path, poll: float) -> None:
    deadline = time.monotonic() + POLITE_MAX_S
    while waiting(data_dir) and time.monotonic() < deadline:
        time.sleep(min(poll, 1.0))


def _alive(pid: str) -> bool:
    try:
        os.kill(int(pid), 0)
    except (ValueError, ProcessLookupError):
        return False
    except PermissionError:
        return True
    return True


def _refresh_status(data_dir: Path) -> None:
    """`/status` from what the writer left, still under its lock. Never fails the writer: a status that can't be
    refreshed is logged and stays as it was until the next write."""
    from ops.status import refresh_dataset_status

    try:
        refresh_dataset_status(data_dir)
    except Exception:
        logging.getLogger(__name__).warning("couldn't refresh the dataset status for %s", data_dir, exc_info=True)
