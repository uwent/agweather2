import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.grid import service_window
from agdata.sources import era5land
from ops.era5land import land_mask, missing_days, roll_up, spans, write_file
from ops.locks import write_lock

LOCK_WAIT_S = 3600  # the hourly ingest or a rollup may hold the lock; a downloaded month waits for it


class Command(BaseCommand):
    help = (
        "Fill the archive's soil temperature and snow depth from ERA5-Land (D52) for a date range: a month per CDS "
        "request, several in flight, each written and rolled up as it arrives (resumable: days ERA5-Land already "
        "filled are skipped)"
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--concurrent", type=int, default=3, help="CDS requests in flight")
        parser.add_argument("--redo", action="store_true", help="fetch days ERA5-Land already filled")
        parser.add_argument(
            "--downloads", default=None, help="keep the GRIB here (default: a temporary folder, deleted)"
        )

    def handle(self, *args, **options):
        key = settings.COPERNICUS_API_KEY
        if not key:
            raise CommandError("COPERNICUS_API_KEY isn't set")
        try:
            first, end = date.fromisoformat(options["start"]), date.fromisoformat(options["end"])
        except ValueError as error:
            raise CommandError(error) from error
        box = options["box"] or settings.SERVICE_BOX
        window = service_window(box)
        data_dir = settings.DATA_DIR
        last = end - timedelta(days=1)
        with write_lock(data_dir, wait=LOCK_WAIT_S):
            days = (
                [first + timedelta(days=n) for n in range((end - first).days)]
                if options["redo"]
                else missing_days(data_dir, window, first, last)
            )
        todo = spans(days)
        self.say(
            f"ERA5-Land {first} to {last}, window {window}: {len(days)} days in {len(todo)} requests "
            f"(pid {os.getpid()})"
        )
        if not todo:
            return
        land = land_mask(data_dir, window, key)
        folder = Path(options["downloads"]) if options["downloads"] else Path(data_dir) / "tmp" / "era5land"
        folder.mkdir(parents=True, exist_ok=True)
        keep = bool(options["downloads"])

        def download(span: tuple[date, date]) -> tuple[tuple[date, date], Path, float]:
            path = folder / f"{span[0]}_{span[1]}.grib"
            began = time.time()
            era5land.retrieve(span[0], span[1], window, path, key)
            return span, path, time.time() - began

        failed = []
        with ThreadPoolExecutor(options["concurrent"]) as pool:
            futures = {pool.submit(download, span): span for span in todo}
            for future in as_completed(futures):
                span = futures[future]
                try:
                    _, path, seconds = future.result()
                except Exception as error:  # the CDS's errors aren't typed; the span is retried on the next run
                    failed.append(span)
                    self.say(f"{span[0]}..{span[1]}: failed: {error!r}")
                    continue
                began = time.time()
                with write_lock(data_dir, wait=LOCK_WAIT_S):
                    covered = write_file(data_dir, window, path, land)
                    if covered is not None:
                        roll_up(data_dir, window, *covered)
                if not keep:
                    path.unlink()
                self.say(
                    f"{span[0]}..{span[1]}: downloaded in {seconds:.0f}s, written and rolled up in "
                    f"{time.time() - began:.0f}s"
                )
        self.say(f"Done; {len(failed)} requests failed" + (f": {failed}" if failed else ""))

    def say(self, line: str) -> None:
        self.stdout.write(f"{datetime.now().astimezone():%H:%M:%S} {line}")
        self.stdout.flush()
