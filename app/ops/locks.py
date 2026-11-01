"""One writer at a time for the Zarr archive: two would write the same chunks and double the memory and bandwidth."""

import fcntl
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from django.core.management.base import CommandError


class WriteLocked(CommandError):
    pass


def hold_write_lock(data_dir: Path) -> IO[str]:
    """Takes `data_dir/write.lock` (holding this process's pid) until the returned file closes or the process exits."""
    data_dir.mkdir(parents=True, exist_ok=True)
    handle = open(data_dir / "write.lock", "a+")  # noqa: SIM115
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.seek(0)
        holder = handle.read().strip() or "?"
        handle.close()
        raise WriteLocked(f"another backfill, rollup or ingest is writing to {data_dir} (pid {holder})") from None
    handle.truncate(0)
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


@contextmanager
def write_lock(data_dir: Path, wait: float = 0, poll: float = 5) -> Iterator[None]:
    """The write lock for a block of code, for long-lived processes like the job worker. With `wait`, tries again
    every `poll` seconds for up to `wait` seconds before raising WriteLocked (a backfill that has just downloaded
    a month waits out the hourly ingest rather than losing it)."""
    deadline = time.monotonic() + wait
    while True:
        try:
            handle = hold_write_lock(data_dir)
            break
        except WriteLocked:
            if time.monotonic() >= deadline:
                raise
            time.sleep(poll)
    try:
        yield
    finally:
        handle.close()
