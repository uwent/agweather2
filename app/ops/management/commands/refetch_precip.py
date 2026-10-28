import time
from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.catalog import variable
from agdata.cumulative import update_days
from agdata.grid import service_window
from agdata.ingest import blocks, open_or_create_hourly, refetch_precipitation
from agdata.store import HOURLY, GridStore
from ops.locks import hold_write_lock


class Command(BaseCommand):
    help = (
        "Fetch hourly precip again at the catalog's precision (D28) for a date range, then roll up its days; "
        "with --rescale, first repack stores written at an older scale"
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--rescale", action="store_true", help="repack the years' precip to the catalog's scale")

    def handle(self, *args, **options):
        try:
            start = datetime.fromisoformat(options["start"]).replace(tzinfo=UTC)
            end = datetime.fromisoformat(options["end"]).replace(tzinfo=UTC)
        except ValueError as error:
            raise CommandError(error) from error
        window = service_window(settings.SERVICE_BOX)
        self.lock = hold_write_lock(settings.DATA_DIR)
        if options["rescale"]:
            for year in range(start.year, end.year + 1):
                GridStore.rescale(settings.DATA_DIR, HOURLY, year, variable("precipitation"))
                self.stdout.write(f"repacked {year}'s precip")
        for block_start, hours in blocks(start, end, 10):
            began = time.time()
            store = open_or_create_hourly(settings.DATA_DIR, block_start.year, window)
            written = refetch_precipitation(store, block_start, hours)
            self.stdout.write(f"{block_start:%Y-%m-%d}: {written}/{hours} hours in {time.time() - began:.0f}s")
            self.stdout.flush()
        update_days(settings.DATA_DIR, window, start.date(), end.date())
        self.stdout.write("rolled up")
