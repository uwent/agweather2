import time
from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ops.forecast import refresh_forecast
from ops.locks import hold_write_lock


class Command(BaseCommand):
    help = "Build and publish the newest complete long NBM run (or the one before --before), as the job does"

    def add_arguments(self, parser):
        parser.add_argument("--before", default=None, help="UTC time to look back from, YYYY-MM-DDTHH (default: now)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")

    def handle(self, *args, **options):
        try:
            now = (
                datetime.fromisoformat(options["before"]).replace(tzinfo=UTC)
                if options["before"]
                else datetime.now(UTC)
            )
        except ValueError as error:
            raise CommandError(error) from error
        self.lock = hold_write_lock(settings.DATA_DIR)
        began = time.time()
        record = refresh_forecast(settings.DATA_DIR, options["box"] or settings.SERVICE_BOX, now)
        if record is None:
            self.stdout.write("Nothing new: the newest complete run is already published")
        else:
            self.stdout.write(f"{record} in {time.time() - began:.0f}s")
