import os
import time
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from agdata.cumulative import update_days
from agdata.grid import service_window
from agdata.ingest import blocks, ingest_block, open_or_create_hourly
from ops.ingest import record_run
from ops.locks import hold_write_lock
from ops.models import IngestRecord

PROGRESS_EVERY = 6  # hours fetched between progress lines


class Command(BaseCommand):
    help = (
        "Fill the hourly archive for a date range from URMA/RTMA/HRRR, a block of days at a time (resumable), "
        "rolling up each block's finished local days and the running totals"
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--workers", type=int, default=4, help="hours fetched in parallel")
        parser.add_argument("--redo", action="store_true", help="refetch blocks that are already complete")
        parser.add_argument("--block-days", type=int, default=5, help="days per block (memory grows with it)")

    def handle(self, *args, **options):
        try:
            start = datetime.fromisoformat(options["start"]).replace(tzinfo=UTC)
            end = datetime.fromisoformat(options["end"]).replace(tzinfo=UTC)
        except ValueError as error:
            raise CommandError(error) from error
        box = options["box"] or settings.SERVICE_BOX
        window = service_window(box)
        data_dir = settings.DATA_DIR
        self.lock = hold_write_lock(data_dir)  # held until the process exits
        self.say(f"Backfill {start:%Y-%m-%d} to {end:%Y-%m-%d}, window {window}, into {data_dir} (pid {os.getpid()})")

        for block_start, hours in blocks(start, end, options["block_days"]):
            store = open_or_create_hourly(data_dir, block_start.year, window)
            t0 = store.index_of(block_start)
            sources = store.sources("air_temperature")[t0 : t0 + hours]
            if not options["redo"] and all(s == "urma" for s in sources):
                self.say(f"{block_start:%Y-%m-%d}: complete, skipped")
                continue
            began = time.time()

            def progress(done: int, block_start=block_start, hours=hours, began=began) -> None:
                if done % PROGRESS_EVERY and done != hours:
                    return
                elapsed = time.time() - began
                left = elapsed / done * (hours - done)
                self.say(
                    f"  {block_start:%Y-%m-%d}: {done}/{hours} hours fetched, "
                    f"{elapsed / 60:.0f} min, ~{left / 60:.0f} min left"
                )

            started = timezone.now()
            try:
                report = ingest_block(store, block_start, hours, workers=options["workers"], progress=progress)
            except Exception as error:
                record_run(IngestRecord.Kind.BACKFILL, box, store, block_start, hours, started, None, repr(error))
                raise
            record_run(IngestRecord.Kind.BACKFILL, box, store, block_start, hours, started, report)
            missing = {name: n for name, n in report.missing.items() if n}
            self.say(
                f"{block_start:%Y-%m-%d}: {hours} hours in {time.time() - began:.0f}s; "
                f"failed fetches {len(report.failed)}; missing hours {missing or 'none'}; "
                f"spikes {sum(report.spikes.values())}"
            )
            self.roll_up(window, block_start, hours, start)
        self.say("Done")

    def say(self, line: str) -> None:
        self.stdout.write(f"{datetime.now().astimezone():%H:%M:%S} {line}")
        self.stdout.flush()  # stdout to a file is block-buffered

    def roll_up(self, window, block_start: datetime, hours: int, start: datetime) -> None:
        """Local days this block finished: the day before it started (its last hours were in this block) through
        the second-to-last UTC day it covers (the last runs into the next block's hours in every US zone)."""
        first = max((block_start - timedelta(days=1)).date(), start.date())  # the day before the start can't finish
        last = (block_start + timedelta(hours=hours) - timedelta(days=2)).date()
        if last < first:
            return
        began = time.time()
        years = update_days(settings.DATA_DIR, window, first, last)
        self.say(f"  rolled up {first} to {last}, running totals for {years} in {time.time() - began:.0f}s")
