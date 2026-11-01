from datetime import timedelta

from django.conf import settings

from agdata.catalog import variable
from agdata.cumulative import update_days
from agdata.ingest import blocks, open_or_create_hourly, refetch_precipitation
from agdata.store import HOURLY, GridStore
from ops.management.base import ReportingCommand, check_range, parse_day, utc_midnight

BLOCK_DAYS = 10


class Command(ReportingCommand):
    help = (
        "Fetch hourly precip again at the catalog's precision (D28) for a date range, then roll up its local days; "
        "with --rescale, first repack stores written at an older scale. Hours neither URMA nor RTMA has keep what "
        "they had, so it's safe to rerun."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--rescale", action="store_true", help="repack the years' precip to the catalog's scale")

    def handle(self, *args, **options):
        first, end = parse_day(options["start"], "--start"), parse_day(options["end"], "--end")
        check_range(first, end)
        window = self.window(options["box"])
        data_dir = settings.DATA_DIR
        last = end - timedelta(days=1)
        if options["rescale"]:
            for year in range(first.year, last.year + 1):
                with self.lock():
                    GridStore.rescale(data_dir, HOURLY, year, variable("precipitation"))
                self.report.step(f"repacked {year}'s precip")
        todo = list(blocks(utc_midnight(first), utc_midnight(end), BLOCK_DAYS))
        self.report.step(f"Refetching precip {first} to {last}: {len(todo)} blocks of {BLOCK_DAYS} days")
        replaced = total = 0
        for k, (block_start, hours) in enumerate(todo, 1):
            with self.lock():
                store = open_or_create_hourly(data_dir, block_start.year, window)
                written = refetch_precipitation(store, block_start, hours)
            replaced, total = replaced + written, total + hours
            self.report.step(f"{block_start:%Y-%m-%d}: {written}/{hours} hours replaced")
            self.report.progress("Refetch", k, len(todo))
        # A UTC day's first hours belong to the local day before it, so that day changed too
        with self.lock():
            years = update_days(data_dir, window, first - timedelta(days=1), last)
        self.report.step(f"rolled up {first - timedelta(days=1)} to {last}, and the running totals for {years}")
        self.finish(f"{replaced} of {total} hours replaced")
