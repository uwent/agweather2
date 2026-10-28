import time
from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.cumulative import update_days
from agdata.grid import service_window
from agdata.ingest import blocks, open_or_create_hourly, refetch_soil_temperature
from agdata.sources.hrrr import SOIL_LEVELS
from ops.locks import hold_write_lock


class Command(BaseCommand):
    help = (
        "Fetch HRRR soil temperature levels again for a date range (a level added to the catalog after those hours "
        "were ingested), then roll up its days"
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument(
            "--levels", nargs="+", default=["soil_temperature_30cm"], choices=sorted(SOIL_LEVELS), help="which"
        )
        parser.add_argument("--workers", type=int, default=8, help="hours fetched in parallel")

    def handle(self, *args, **options):
        try:
            start = datetime.fromisoformat(options["start"]).replace(tzinfo=UTC)
            end = datetime.fromisoformat(options["end"]).replace(tzinfo=UTC)
        except ValueError as error:
            raise CommandError(error) from error
        window = service_window(settings.SERVICE_BOX)
        self.lock = hold_write_lock(settings.DATA_DIR)
        names = tuple(options["levels"])
        for block_start, hours in blocks(start, end, 10):
            began = time.time()
            store = open_or_create_hourly(settings.DATA_DIR, block_start.year, window)
            written = refetch_soil_temperature(store, block_start, hours, names, workers=options["workers"])
            self.stdout.write(f"{block_start:%Y-%m-%d}: {written}/{hours} hours in {time.time() - began:.0f}s")
            self.stdout.flush()
        update_days(settings.DATA_DIR, window, start.date(), end.date())
        self.stdout.write("rolled up")
