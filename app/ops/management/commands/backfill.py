import time
from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.grid import service_window
from agdata.ingest import blocks, ingest_block, open_or_create_hourly


class Command(BaseCommand):
    help = "Fill the hourly archive for a date range from URMA/RTMA/HRRR, a month at a time (resumable)"

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--workers", type=int, default=8, help="hours fetched in parallel")
        parser.add_argument("--redo", action="store_true", help="refetch blocks that are already complete")
        parser.add_argument("--block-days", type=int, default=10, help="days per block (memory grows with it)")

    def handle(self, *args, **options):
        try:
            start = datetime.fromisoformat(options["start"]).replace(tzinfo=UTC)
            end = datetime.fromisoformat(options["end"]).replace(tzinfo=UTC)
        except ValueError as error:
            raise CommandError(error) from error
        window = service_window(options["box"] or settings.SERVICE_BOX)
        data_dir = settings.DATA_DIR
        self.stdout.write(f"Backfill {start:%Y-%m-%d} to {end:%Y-%m-%d}, window {window}, into {data_dir}")

        for block_start, hours in blocks(start, end, options["block_days"]):
            store = open_or_create_hourly(data_dir, block_start.year, window)
            t0 = store.index_of(block_start)
            sources = store.sources("air_temperature")[t0 : t0 + hours]
            if not options["redo"] and all(s == "urma" for s in sources):
                self.stdout.write(f"{block_start:%Y-%m-%d}: complete, skipped", ending="\n")
                continue
            began = time.time()
            report = ingest_block(store, block_start, hours, workers=options["workers"])
            missing = {name: n for name, n in report.missing.items() if n}
            self.stdout.write(
                f"{block_start:%Y-%m-%d}: {hours} hours in {time.time() - began:.0f}s; "
                f"failed fetches {len(report.failed)}; missing hours {missing or 'none'}; "
                f"spikes {sum(report.spikes.values())}; cells filled {sum(report.filled.values())}"
            )
            self.stdout.flush()
