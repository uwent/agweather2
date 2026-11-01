import time
from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import CommandError

from ops.forecast import refresh_forecast
from ops.management.base import ReportingCommand
from ops.models import IngestRecord


class Command(ReportingCommand):
    help = (
        "Build and publish the newest complete long NBM run (or the one before --before), as the job does; exits "
        "nonzero if the build fails. Holds the write lock for the build (several minutes)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--before", default=None, help="UTC time to look back from, YYYY-MM-DDTHH (default: now)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")

    def handle(self, *args, **options):
        now = datetime.now(UTC)
        if options["before"]:
            try:
                now = datetime.fromisoformat(options["before"])
            except ValueError:
                raise CommandError(f"--before {options['before']!r}: expected YYYY-MM-DDTHH (UTC)") from None
            if now.tzinfo is not None and now.utcoffset():
                raise CommandError("--before is UTC: leave the offset off")
            now = now.replace(tzinfo=UTC)
        box = options["box"] or settings.SERVICE_BOX
        self.window(options["box"])  # checks the box
        self.report.step(f"Looking for the newest complete long NBM run before {now:%Y-%m-%d %H}Z")
        began = time.time()
        with self.lock():
            record = refresh_forecast(settings.DATA_DIR, box, now, retry_failed=True)
        if record is None:
            self.finish("nothing new: the newest complete run is already published (or none was found)")
            return
        if record.status == IngestRecord.Status.FAILED:
            self.report.fail(f"the run from {record.first_hour}", record.error)
        elif record.failed_hours:
            self.report.warn(f"{len(record.failed_hours)} hours failed to fetch: {record.failed_hours}")
        self.finish(f"{record} in {time.time() - began:.0f} s")
