import os
from datetime import date, datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone

from agdata.cumulative import update_days
from agdata.daily import open_or_create_daily
from agdata.ingest import blocks, hour_runs, ingest_block, open_or_create_hourly, stale_hours
from agdata.sources.urma import URMA
from ops.ingest import record_run
from ops.management.base import ReportingCommand, check_range, parse_day, positive, utc_midnight
from ops.models import IngestRecord

HOUR = timedelta(hours=1)


class Command(ReportingCommand):
    help = (
        "Fill the hourly archive for a date range from URMA/RTMA/HRRR, a block of days at a time, then roll up "
        "each block's finished local days and the running totals. Resumable: a block fetches only the hours it "
        "lacks (no analysis, precip or shortwave, or RTMA where URMA is now out), and rolls up any of its days the "
        "daily store hasn't got. Takes the write lock a block at a time, so the worker's jobs run in between."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--workers", type=int, default=4, help="hours fetched in parallel")
        parser.add_argument("--redo", action="store_true", help="refetch every hour, even ones already complete")
        parser.add_argument("--block-days", type=int, default=5, help="days per block (memory grows with it)")

    def handle(self, *args, **options):
        first, end = parse_day(options["start"], "--start"), parse_day(options["end"], "--end")
        check_range(first, end)
        workers = positive(options["workers"], "--workers")
        block_days = positive(options["block_days"], "--block-days")
        box = options["box"] or settings.SERVICE_BOX
        window = self.window(options["box"])
        data_dir = settings.DATA_DIR
        todo = list(blocks(utc_midnight(first), utc_midnight(end), block_days))
        self.report.step(
            f"Backfill {first} to {end - timedelta(days=1)} ({len(todo)} blocks of {block_days} days), "
            f"window {window}, into {data_dir} (pid {os.getpid()})"
        )
        session = requests.Session()
        fetched = failed = 0
        for k, (block_start, hours) in enumerate(todo, 1):
            label = f"block {k}/{len(todo)}, {block_start:%Y-%m-%d}"
            with self.lock():
                if options["redo"]:
                    runs = [(block_start, hours)]
                else:
                    stale = stale_hours(
                        data_dir,
                        window,
                        block_start,
                        block_start + hours * HOUR,
                        urma_published=lambda when: URMA.has_hour(when, session),
                    )
                    runs = hour_runs(stale)
                todo_hours = sum(n for _, n in runs)
                if not todo_hours:
                    self.report.step(f"{label}: complete")
                for run_start, n in runs:
                    store = open_or_create_hourly(data_dir, run_start.year, window)
                    started = timezone.now()

                    def progress(done: int, n=n, run_start=run_start, label=label) -> None:
                        self.report.progress(f"  {label}: {run_start:%m-%d %H}Z hours", done, n)

                    try:
                        report = ingest_block(store, run_start, n, workers=workers, progress=progress)
                    except Exception as error:
                        record_run(IngestRecord.Kind.BACKFILL, box, store, run_start, n, started, None, repr(error))
                        raise
                    record_run(IngestRecord.Kind.BACKFILL, box, store, run_start, n, started, report)
                    fetched += n
                    failed += len(report.failed)
                    missing = {name: m for name, m in report.missing.items() if m}
                    self.report.step(
                        f"{label}: {n} hours from {run_start:%Y-%m-%d %H}Z; failed fetches {len(report.failed)}; "
                        f"missing {missing or 'none'}; spikes {sum(report.spikes.values())}"
                    )
                    if report.failed:
                        self.report.fail(f"{label}", f"{len(report.failed)} hours not fetched (rerun to retry)")
                self.roll_up(window, block_start, hours, first, force=bool(todo_hours))
            self.report.progress("Backfill", k, len(todo))
        self.report.step(
            f"The last local day ({end - timedelta(days=1)}) is rolled up once the hours after it are in "
            "(the hourly job, or `manage.py rollup`)"
        )
        self.finish(f"{fetched} hours fetched, {failed} failed")

    def roll_up(self, window, block_start: datetime, hours: int, first: date, force: bool) -> None:
        """Local days this block finished: the day before it started (its last hours were in this block) through
        the second-to-last UTC day it covers (the last runs into the next block's hours in every US zone). A block
        that fetched nothing rolls up only days the daily store hasn't got (a run stopped between the two)."""
        day0 = max((block_start - timedelta(days=1)).date(), first)  # the day before the start can't finish
        day1 = (block_start + timedelta(hours=hours) - timedelta(days=2)).date()
        if day1 < day0 or (not force and _rolled_up(settings.DATA_DIR, window, day0, day1)):
            return
        years = update_days(settings.DATA_DIR, window, day0, day1)
        self.report.step(f"  rolled up {day0} to {day1}, and the running totals for {years}")


def _rolled_up(data_dir, window, day0: date, day1: date) -> bool:
    """Whether every local day day0..day1 has its daily min temperature in the daily store."""
    day = day0
    while day <= day1:
        store = open_or_create_daily(data_dir, day.year, window)
        t0 = store.index_of(day)
        last = min(day1, date(day.year, 12, 31))
        if any(s is None for s in store.sources("air_temperature_min")[t0 : t0 + (last - day).days + 1]):
            return False
        day = last + timedelta(days=1)
    return True
