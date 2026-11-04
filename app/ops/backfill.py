"""Filling the hourly archive over a date range (`manage.py backfill`, and `archive fill` a year at a time).

The range is planned once under the write lock: which hours lack an analysis, precip or HRRR shortwave, or are
RTMA's where URMA is now out (`agdata.ingest.stale_hours`). Then two things run at once:

- a fetcher thread downloads one block of those hours after another (`agdata.ingest.fetch_block`, `workers` hours
  in parallel), without the lock, keeping at most one block ready ahead;
- this thread writes each fetched block (`write_block`), records it and rolls up the local days it finished,
  holding the lock only for that (seconds), and politely, so the worker's hourly jobs get their turns.

So block N+1 downloads while block N is written, and a stop (`stopping`) lands between blocks: the blocks written
are kept, and a rerun resumes from the plan.
"""

import queue
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from django.utils import timezone

from agdata.cumulative import update_days
from agdata.daily import open_or_create_daily
from agdata.grid import Window
from agdata.ingest import FetchedBlock, blocks, fetch_block, hour_runs, open_or_create_hourly, stale_hours, write_block
from agdata.progress import Reporter
from agdata.sources.urma import URMA
from ops.ingest import record_run
from ops.models import IngestRecord

HOUR = timedelta(hours=1)
Lock = Callable[..., AbstractContextManager[None]]


@dataclass(kw_only=True)
class Plan:
    blocks: list[tuple[datetime, int]]  # (block start, hours), the whole range
    stale: dict[datetime, list[tuple[datetime, int]]]  # block start -> runs of hours to fetch in it
    hours: int  # hours to fetch in all

    @property
    def complete(self) -> bool:
        return self.hours == 0


@dataclass(kw_only=True)
class Result:
    fetched: int = 0
    failed: int = 0
    blocks_written: int = 0
    stopped: bool = False
    seconds: float = 0.0
    failures: list[str] = field(default_factory=list)


def plan(data_dir: Path, window: Window, start: datetime, end: datetime, block_days: int, redo: bool = False) -> Plan:
    """The hours to fetch between start and end (exclusive), by block. The caller holds the write lock."""
    todo = list(blocks(start, end, block_days))
    stale: dict[datetime, list[tuple[datetime, int]]] = {}
    session = requests.Session()
    for block_start, hours in todo:
        if redo:
            runs = [(block_start, hours)]
        else:
            found = stale_hours(
                data_dir,
                window,
                block_start,
                block_start + hours * HOUR,
                urma_published=lambda when: URMA.has_hour(when, session),
            )
            runs = hour_runs(found)
        if runs:
            stale[block_start] = runs
    return Plan(blocks=todo, stale=stale, hours=sum(n for runs in stale.values() for _, n in runs))


def run(
    *,
    data_dir: Path,
    window: Window,
    box: str,
    first: date,
    the_plan: Plan,
    report: Reporter,
    lock: Lock,
    workers: int,
    stopping: threading.Event,
    label: str = "hours",
    base: int = 0,
    total: int | None = None,
) -> Result:
    """Fetches and writes the plan's hours, block by block (see the module). `first` is the range's first day
    (the day before it can't be rolled up from this range's hours). `lock(polite=True)` gives the write lock."""
    result = Result()
    began = time.monotonic()
    ready: queue.Queue = queue.Queue(maxsize=1)  # a fetched block waiting to be written
    done_hours = base  # progress counts from `base` of `total` (a fill's years share one bar)
    total = the_plan.hours if total is None else total
    done_lock = threading.Lock()

    def fetcher() -> None:
        nonlocal done_hours
        try:
            for block_start, hours in the_plan.blocks:
                if stopping.is_set():
                    break
                fetched: list[tuple[FetchedBlock, datetime]] = []
                for run_start, n in the_plan.stale.get(block_start, []):
                    base = done_hours

                    def progress(k: int, base=base) -> None:
                        report.progress(label, base + k, total)

                    started = timezone.now()
                    fetched.append((fetch_block(window, run_start, n, workers=workers, progress=progress), started))
                    with done_lock:
                        done_hours += n
                ready.put(("block", block_start, hours, fetched))
        except BaseException as error:  # handed to the writer, which raises it
            ready.put(("error", error, None, None))
            return
        ready.put(("end", None, None, None))

    if the_plan.hours:
        report.progress(label, base, total)  # the bar from the start, before the first hour (or skipped block)
    thread = threading.Thread(target=fetcher, name="backfill-fetch", daemon=True)
    thread.start()
    k = 0
    while True:
        kind, block_start, hours, fetched = ready.get()
        if kind == "end":
            break
        if kind == "error":
            raise block_start  # the fetcher's exception
        k += 1
        tag = f"block {k}/{len(the_plan.blocks)} {block_start:%Y-%m-%d}"
        written = time.monotonic()
        with lock(polite=True):
            for block, started in fetched:
                store = open_or_create_hourly(data_dir, block.start.year, window)
                try:
                    block_report = write_block(store, block)
                except Exception as error:
                    record_run(
                        IngestRecord.Kind.BACKFILL, box, store, block.start, block.hours, started, None, repr(error)
                    )
                    raise
                record_run(IngestRecord.Kind.BACKFILL, box, store, block.start, block.hours, started, block_report)
                result.fetched += block.hours
                result.failed += len(block_report.failed)
                missing = {name: m for name, m in block_report.missing.items() if m}
                report.detail(
                    f"{tag}: wrote {block.hours} hours from {block.start:%m-%d %H}Z; "
                    f"failed {len(block_report.failed)}; missing {missing or 'none'}; "
                    f"spikes {sum(block_report.spikes.values())}"
                )
                if block_report.failed:
                    report.fail(tag, f"{len(block_report.failed)} hours not fetched (rerun to retry)")
                    result.failures.append(tag)
            rolled = roll_up(data_dir, window, block_start, hours, first, force=bool(fetched))
        result.blocks_written += 1
        what = "complete" if not fetched else f"written in {time.monotonic() - written:.0f} s"
        report.detail(f"{tag}: {what}" + (f"; rolled up {rolled}" if rolled else ""))
        if stopping.is_set():
            result.stopped = True
            break
    if result.stopped:
        while thread.is_alive():  # let the fetcher see the stop; its block in flight is dropped
            try:
                ready.get(timeout=1)
            except queue.Empty:
                continue
    thread.join(timeout=5)
    result.seconds = time.monotonic() - began
    return result


def roll_up(data_dir: Path, window: Window, block_start: datetime, hours: int, first: date, force: bool) -> str | None:
    """Local days this block finished: the day before it started (its last hours were in this block) through
    the second-to-last UTC day it covers (the last runs into the next block's hours in every US zone). A block
    that fetched nothing rolls up only days the daily store hasn't got (a run stopped between the two). The
    caller holds the write lock. Returns what it rolled up, or None."""
    day0 = max((block_start - timedelta(days=1)).date(), first)  # the day before the start can't finish
    day1 = (block_start + timedelta(hours=hours) - timedelta(days=2)).date()
    if day1 < day0 or (not force and rolled_up(data_dir, window, day0, day1)):
        return None
    years = update_days(data_dir, window, day0, day1)
    return f"{day0} to {day1} and the running totals of {years}"


def rolled_up(data_dir: Path, window: Window, day0: date, day1: date) -> bool:
    """Whether every local day day0..day1 has its daily min temperature in the daily store."""
    day = day0
    while day <= day1:
        store = open_or_create_daily(data_dir, day.year, window)
        t0 = store.index_of(day)
        last = min(day1, date(day.year, 12, 31))
        if any(s is None for s in store.sources("air_temperature_min", t0, t0 + (last - day).days + 1)):
            return False
        day = last + timedelta(days=1)
    return True
