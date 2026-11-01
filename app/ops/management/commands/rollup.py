from django.conf import settings

from agdata.cumulative import update_days
from ops.management.base import ReportingCommand, check_range, parse_day


class Command(ReportingCommand):
    help = (
        "Roll up local days from the hourly archive and rebuild the running totals of the years they touch. Note "
        "--end is the last local day (inclusive), unlike backfill's."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first local day, YYYY-MM-DD")
        parser.add_argument("--end", required=True, help="last local day, YYYY-MM-DD (inclusive)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")

    def handle(self, *args, **options):
        first, last = parse_day(options["start"], "--start"), parse_day(options["end"], "--end")
        check_range(first, last, exclusive=False)
        window = self.window(options["box"])
        self.report.step(f"Rolling up {first} to {last} ({(last - first).days + 1} days)")
        with self.lock():
            years = update_days(settings.DATA_DIR, window, first, last)
        self.finish(f"rolled up {first} to {last} and rebuilt the running totals of {years or 'no years'}")
