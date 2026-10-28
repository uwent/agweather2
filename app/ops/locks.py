"""One writer at a time for the Zarr archive: two would write the same chunks and double the memory and bandwidth."""

import fcntl
import os
from pathlib import Path
from typing import IO

from django.core.management.base import CommandError


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
        raise CommandError(f"another backfill or rollup is writing to {data_dir} (pid {holder})") from None
    handle.truncate(0)
    handle.write(str(os.getpid()))
    handle.flush()
    return handle
