"""ERA5-Land into the archive (D52, PLAN.md Phase 4 I): soil temperature and snow depth over the HRRR stand-in hours.

ERA5-Land reaches about 5 days behind real time. The daily job asks the CDS for the days of the last month that
don't have it yet, up to `LAG_DAYS` ago, then writes them and rolls up their local days. Requests queue at the
CDS for minutes, so downloads run outside the write lock; only writing and rolling up take it. The backfill
(`manage.py era5land`) uses the same pieces, several months in flight at once.
"""

import contextlib
import logging
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import AbstractContextManager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.cumulative import update_days
from agdata.grid import Window, service_window
from agdata.ingest import SOIL, open_or_create_hourly, write_soil
from agdata.progress import Reporter
from agdata.progress import activity as progress_activity
from agdata.sources import era5land
from ops.locks import write_lock

logger = logging.getLogger(__name__)

HEARTBEAT_S = 300  # while requests sit in the CDS's queue, say so this often
LAG_DAYS = 5  # ERA5-Land's usual delay; asking for later days fails and is retried the next run
CATCH_UP_DAYS = 31  # how far back the daily job looks for days still without ERA5-Land
HOUR = timedelta(hours=1)

Retrieve = Callable[[date, date, Window, Path, str], Path]
RetrieveMask = Callable[[Path, str], Path]
Lock = Callable[[], AbstractContextManager[None]]


def land_mask(data_dir: Path, window: Window, key: str, retrieve: RetrieveMask = era5land.retrieve_land_mask):
    """ERA5-Land's land mask over the window's request area, downloaded once (the CDS sends the whole globe) and
    kept cropped under `data_dir/static`."""
    path = data_dir / "static" / f"era5land_land_{window.j0}_{window.j1}_{window.i0}_{window.i1}.npz"
    if path.exists():
        return era5land.LandMask.load(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        mask = era5land.read_land_mask(retrieve(Path(tmp) / "land_sea_mask.grib", key)).crop(window)
    partial = path.with_name(path.stem + ".part.npz")  # np.savez adds .npz to a name without it
    mask.save(partial)
    partial.replace(path)  # atomic: the job and a command may both be here, and a crash leaves no half file
    return mask


def missing_days(data_dir: Path, window: Window, first: date, last: date) -> list[date]:
    """UTC days first..last whose 24 hours aren't all ERA5-Land's yet, in every variable it fills (a day written
    before snow depth was added has ERA5-Land's soil but not its snow)."""
    out = []
    stores: dict[int, list[list[str | None]]] = {}
    for day in _days(first, last):
        if day.year not in stores:
            store = open_or_create_hourly(data_dir, day.year, window)
            stores[day.year] = [store.sources(name) for name in SOIL]
        n = (day - date(day.year, 1, 1)).days * 24
        if any(s != "era5land" for sources in stores[day.year] for s in sources[n : n + 24]):
            out.append(day)
    return out


def spans(days: list[date]) -> list[tuple[date, date]]:
    """Days as (first, last) runs of consecutive days, each within one calendar month (a CDS request)."""
    out: list[tuple[date, date]] = []
    for day in sorted(days):
        if out:
            first, last = out[-1]
            if day == last + timedelta(days=1) and day.month == first.month:
                out[-1] = (first, day)
                continue
        out.append((day, day))
    return out


def write_file(data_dir: Path, window: Window, path: Path, land: era5land.LandMask) -> tuple[date, date] | None:
    """Writes a downloaded file's hours into the hourly stores of their years; returns its first and last UTC
    days (None if it held nothing). The caller holds the write lock."""
    hours = era5land.read(path, window, land)
    if not hours.times:
        return None
    for year in sorted({t.year for t in hours.times}):
        store = open_or_create_hourly(data_dir, year, window)
        written = write_soil(store, hours, "era5land")
        logger.info("ERA5-Land: %d hours into %d", written, year)
    covered = [t for k, t in enumerate(hours.times) if np.isfinite(hours.values[SOIL[0]][k]).any()]
    if not covered:
        return None
    return covered[0].date(), covered[-1].date()


def roll_up(data_dir: Path, window: Window, first: date, last: date) -> None:
    """The local days UTC days first..last touch (an hour belongs to its UTC date or the day before in every US
    zone, D30), and the running totals they reach."""
    update_days(data_dir, window, first - timedelta(days=1), last)


def refresh_era5land(
    data_dir: Path,
    box: str,
    now: datetime,
    key: str,
    retrieve: Retrieve = era5land.retrieve,
    retrieve_mask: RetrieveMask = era5land.retrieve_land_mask,
    lock: Lock | None = None,
) -> list[tuple[date, date]]:
    """Fetches and writes the last CATCH_UP_DAYS days without ERA5-Land, through LAG_DAYS ago; returns the spans
    written. Takes the write lock only to write (`lock`, default `write_lock(data_dir)`)."""
    window = service_window(box)
    lock = lock or (lambda: write_lock(data_dir))
    last = now.astimezone(UTC).date() - timedelta(days=LAG_DAYS)
    with lock():
        days = missing_days(data_dir, window, last - timedelta(days=CATCH_UP_DAYS - 1), last)
    if not days:
        return []
    land = land_mask(data_dir, window, key, retrieve_mask)
    written = []
    for first_day, last_day in spans(days):
        with _download(retrieve, first_day, last_day, window, key) as path:
            if path is None:
                continue  # not published yet, or the CDS failed: the next run asks again
            with lock():
                span = write_file(data_dir, window, path, land)
                if span is not None:
                    roll_up(data_dir, window, *span)
                    written.append(span)
    logger.info("ERA5-Land: wrote %s", written or "nothing")
    return written


@contextlib.contextmanager
def _download(retrieve: Retrieve, first: date, last: date, window: Window, key: str) -> Iterator[Path | None]:
    """A span downloaded to a temporary file (None when the CDS refuses it, as for days not published yet)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"era5land_{first}_{last}.grib"
        try:
            retrieve(first, last, window, path, key)
        except Exception as error:  # the CDS's errors aren't typed; days past its last are the usual one
            logger.warning("ERA5-Land %s..%s: %r", first, last, error)
            yield None
            return
        yield path


def _days(first: date, last: date) -> Iterator[date]:
    day = first
    while day <= last:
        yield day
        day += timedelta(days=1)


def backfill_era5land(
    *,
    data_dir: Path,
    window: Window,
    first: date,
    end: date,
    key: str,
    report: Reporter,
    lock: Callable[..., AbstractContextManager[None]],
    concurrent: int = 3,
    redo: bool = False,
    downloads: Path | None = None,
    stopping: threading.Event | None = None,
    retrieve: Retrieve | None = None,
    label: str = "ERA5-Land requests",
) -> tuple[int, int]:
    """Soil and snow from ERA5-Land for UTC days first..end (exclusive): a month per CDS request, `concurrent` in
    flight, each written and rolled up as it arrives (`lock(polite=True)` for that). Days already all ERA5-Land's
    are skipped unless `redo`. Each request is an activity on `report`; a failed one is a failure there and is
    asked again on the next run. A set `stopping` asks no more and drops requests not yet answered. Returns
    (requests written, requests in all)."""
    fetch = retrieve or era5land.retrieve
    last = end - timedelta(days=1)
    with lock():
        days = list(_days(first, last)) if redo else missing_days(data_dir, window, first, last)
    todo = spans(days)
    report.step(
        f"ERA5-Land {first} to {last}: {len(days)} days to fetch in {len(todo)} requests, {concurrent} at a time"
    )
    if not todo:
        return 0, 0
    land = land_mask(data_dir, window, key)
    folder = downloads or data_dir / "tmp" / "era5land"
    folder.mkdir(parents=True, exist_ok=True)

    def download(span: tuple[date, date]) -> tuple[Path, float]:
        path = folder / f"{span[0]}_{span[1]}.grib"
        began = time.time()
        with progress_activity(f"CDS {span[0]:%Y-%m}") as act:
            if act is not None:
                act.stage(f"requested {span[0]:%m-%d}..{span[1]:%m-%d}: queued or downloading at the CDS")
            fetch(span[0], span[1], window, path, key)
        return path, time.time() - began

    done = written = 0
    heard = time.monotonic()
    report.progress(label, 0, len(todo))
    pool = ThreadPoolExecutor(concurrent)
    try:
        pending: dict[Future, tuple[date, date]] = {pool.submit(download, span): span for span in todo}
        while pending:
            if stopping is not None and stopping.is_set():
                report.step(f"ERA5-Land: stopping; {len(pending)} requests dropped (asked again on the next run)")
                break
            finished, _ = wait(pending, timeout=min(5, HEARTBEAT_S), return_when=FIRST_COMPLETED)  # a stop is seen soon
            if not finished:
                if time.monotonic() - heard >= HEARTBEAT_S:
                    report.step(f"{len(pending)} requests still queued or downloading at the CDS")
                    heard = time.monotonic()
                continue
            heard = time.monotonic()
            for future in finished:
                span = pending.pop(future)
                done += 1
                tag = f"{span[0]}..{span[1]}"
                try:
                    path, seconds = future.result()
                except Exception as error:  # the CDS's errors aren't typed; the span is retried on the next run
                    report.fail(tag, error)
                    continue
                try:
                    began = time.time()
                    with lock(polite=True):
                        covered = write_file(data_dir, window, path, land)
                        if covered is not None:
                            roll_up(data_dir, window, *covered)
                    written += 1
                    report.detail(
                        f"{tag}: downloaded in {seconds:.0f} s, written and rolled up in {time.time() - began:.0f} s"
                    )
                except Exception as error:
                    report.fail(tag, error)
                finally:
                    if downloads is None:
                        path.unlink(missing_ok=True)
                report.progress(label, done, len(todo))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)  # on a stop or Ctrl-C, don't wait for queued requests
    return written, len(todo)
