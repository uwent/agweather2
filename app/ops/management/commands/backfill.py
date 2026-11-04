import os
from datetime import timedelta

from django.conf import settings

from ops import backfill
from ops.management.base import ReportingCommand, check_range, parse_day, positive, utc_midnight


class Command(ReportingCommand):
    help = (
        "Fill the hourly archive for a date range from URMA/RTMA/HRRR, then roll up the local days it finished and "
        "the running totals. Resumable: it fetches only hours without an analysis, precip or shortwave (or RTMA's "
        "where URMA is now out), and rolls up days the daily store hasn't got. Downloads the next block while it "
        "writes this one, holding the write lock only to write, and politely (the worker's jobs go first). A first "
        "stop (SIGTERM, Ctrl-C, `archive stop`) ends it after the block in hand. For whole years, `archive fill`."
    )
    stoppable = True

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
        with self.lock():
            the_plan = backfill.plan(
                data_dir, window, utc_midnight(first), utc_midnight(end), block_days, redo=options["redo"]
            )
        self.report.step(
            f"Backfill {first} to {end - timedelta(days=1)}: {the_plan.hours} hours to fetch in "
            f"{len(the_plan.stale)} of {len(the_plan.blocks)} blocks of {block_days} days, {workers} at a time; "
            f"window {window}, into {data_dir} (pid {os.getpid()})"
        )
        result = backfill.run(
            data_dir=data_dir,
            window=window,
            box=box,
            first=first,
            the_plan=the_plan,
            report=self.report,
            lock=self.lock,
            workers=workers,
            stopping=self.stopping,
        )
        if not result.stopped:
            self.report.step(
                f"The last local day ({end - timedelta(days=1)}) is rolled up once the hours after it are in "
                "(the hourly job, or `manage.py rollup`)"
            )
        self.finish(f"{result.fetched} hours fetched, {result.failed} failed")
