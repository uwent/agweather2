from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError

from ops.era5land import backfill_era5land, rederive_era5land
from ops.management.base import ReportingCommand, check_range, parse_day, positive


class Command(ReportingCommand):
    help = (
        "Fill the archive's soil temperature and snow depth from ERA5-Land (D52) for a date range: a month per CDS "
        "request, several in flight, each written and rolled up as it arrives. Resumable: days whose every ERA5-Land "
        "variable is already in are skipped. Requests queue at the CDS for minutes to tens of minutes. Exits "
        "nonzero if any request failed (rerun to retry them). A first stop drops the requests not yet answered."
    )
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD (UTC)")
        parser.add_argument("--end", required=True, help="day after the last, YYYY-MM-DD (UTC)")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--concurrent", type=int, default=3, help="CDS requests in flight")
        parser.add_argument("--redo", action="store_true", help="fetch days ERA5-Land already filled")
        parser.add_argument(
            "--rederive",
            action="store_true",
            help="derive the hourly soil and snow again from ERA5-Land as kept (D79), without downloading",
        )
        parser.add_argument(
            "--downloads",
            default=None,
            help="keep the GRIB here (default: data/tmp/era5land, each file deleted once written)",
        )

    def handle(self, *args, **options):
        key = settings.COPERNICUS_API_KEY
        if not key:
            raise CommandError("COPERNICUS_API_KEY isn't set")
        first, end = parse_day(options["start"], "--start"), parse_day(options["end"], "--end")
        check_range(first, end)
        if options["rederive"]:
            hours = rederive_era5land(
                data_dir=settings.DATA_DIR,
                window=self.window(options["box"]),
                first=first,
                end=end,
                key=key,
                report=self.report,
                lock=self.lock,
                stopping=self.stopping,
            )
            self.finish(f"{hours} hours derived again")
            return
        written, total = backfill_era5land(
            data_dir=settings.DATA_DIR,
            window=self.window(options["box"]),
            first=first,
            end=end,
            key=key,
            report=self.report,
            lock=self.lock,
            concurrent=positive(options["concurrent"], "--concurrent"),
            redo=options["redo"],
            downloads=Path(options["downloads"]) if options["downloads"] else None,
            stopping=self.stopping,
        )
        self.finish(f"{written} of {total} requests written" if total else "nothing to fetch")
