import time
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.cumulative import update_days
from agdata.grid import service_window
from ops.locks import hold_write_lock


class Command(BaseCommand):
    help = "Roll up local days from the hourly archive and rebuild the running totals of the years they touch"

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first local day, YYYY-MM-DD")
        parser.add_argument("--end", required=True, help="last local day, YYYY-MM-DD (inclusive)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")

    def handle(self, *args, **options):
        try:
            first, last = date.fromisoformat(options["start"]), date.fromisoformat(options["end"])
        except ValueError as error:
            raise CommandError(error) from error
        window = service_window(options["box"] or settings.SERVICE_BOX)
        self.lock = hold_write_lock(settings.DATA_DIR)
        began = time.time()
        years = update_days(settings.DATA_DIR, window, first, last)
        self.stdout.write(
            f"Rolled up {first} to {last} and rebuilt the running totals of {years or 'no years'} "
            f"in {time.time() - began:.0f}s"
        )
