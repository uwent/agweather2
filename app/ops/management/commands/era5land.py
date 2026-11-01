import os
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError

from agdata.sources import era5land
from ops.era5land import land_mask, missing_days, roll_up, spans, write_file
from ops.management.base import ReportingCommand, check_range, parse_day, positive

HEARTBEAT_S = 300  # while requests sit in the CDS's queue, say so this often


class Command(ReportingCommand):
    help = (
        "Fill the archive's soil temperature and snow depth from ERA5-Land (D52) for a date range: a month per CDS "
        "request, several in flight, each written and rolled up as it arrives. Resumable: days whose every ERA5-Land "
        "variable is already in are skipped. Requests queue at the CDS for minutes to tens of minutes. Exits "
        "nonzero if any request failed (rerun to retry them)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--concurrent", type=int, default=3, help="CDS requests in flight")
        parser.add_argument("--redo", action="store_true", help="fetch days ERA5-Land already filled")
        parser.add_argument(
            "--downloads",
            default=None,
            help="keep the GRIB here (default: data/tmp/era5land, each file deleted once written)",
        )

    def handle(self, *args, **options):
        key = settings.COPERNICUS_API_KEY
        if not key:
            raise CommandError("COPERNICUS_API_KEY isn't set")
        first, end = parse_day(options["start"], "--start"), parse_day(options["end"], "--end")
        check_range(first, end)
        concurrent = positive(options["concurrent"], "--concurrent")
        window = self.window(options["box"])
        data_dir = settings.DATA_DIR
        last = end - timedelta(days=1)
        with self.lock():
            days = (
                [first + timedelta(days=n) for n in range((end - first).days)]
                if options["redo"]
                else missing_days(data_dir, window, first, last)
            )
        todo = spans(days)
        self.report.step(
            f"ERA5-Land {first} to {last}, window {window}: {len(days)} days to fetch in {len(todo)} requests, "
            f"{concurrent} at a time (pid {os.getpid()})"
        )
        if not todo:
            self.finish("nothing to fetch")
            return
        land = land_mask(data_dir, window, key)
        folder = Path(options["downloads"]) if options["downloads"] else Path(data_dir) / "tmp" / "era5land"
        folder.mkdir(parents=True, exist_ok=True)
        keep = bool(options["downloads"])

        def download(span: tuple[date, date]) -> tuple[Path, float]:
            path = folder / f"{span[0]}_{span[1]}.grib"
            began = time.time()
            era5land.retrieve(span[0], span[1], window, path, key)
            return path, time.time() - began

        done = 0
        pool = ThreadPoolExecutor(concurrent)
        try:
            pending: dict[Future, tuple[date, date]] = {pool.submit(download, span): span for span in todo}
            while pending:
                finished, _ = wait(pending, timeout=HEARTBEAT_S, return_when=FIRST_COMPLETED)
                if not finished:
                    self.report.step(f"{len(pending)} requests still queued or downloading at the CDS")
                    continue
                for future in finished:
                    span = pending.pop(future)
                    done += 1
                    label = f"{span[0]}..{span[1]}"
                    try:
                        path, seconds = future.result()
                    except Exception as error:  # the CDS's errors aren't typed; the span is retried on the next run
                        self.report.fail(label, error)
                        continue
                    try:
                        began = time.time()
                        with self.lock():
                            covered = write_file(data_dir, window, path, land)
                            if covered is not None:
                                roll_up(data_dir, window, *covered)
                        self.report.step(
                            f"{label}: downloaded in {seconds:.0f} s, written and rolled up in "
                            f"{time.time() - began:.0f} s"
                        )
                    except Exception as error:
                        self.report.fail(label, error)
                    finally:
                        if not keep:
                            path.unlink(missing_ok=True)
                    self.report.progress("Requests", done, len(todo))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)  # on Ctrl-C, don't wait for queued requests
        self.finish(f"{len(todo) - len(self.report.failures)} of {len(todo)} requests written")
