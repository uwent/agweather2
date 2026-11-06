from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import CommandError

from agdata import pastyears
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Build the copies of past years' daily values laid out for reading a point over time (agdata.pastyears; "
        "the projection's, D63): every year before this one whose copy is missing or out of date (its daily store was "
        "written since, or its daily variables' code changed), "
        "or one --year. About 1.5 minutes and 0.3 GB a year. Reads the daily stores only, so it doesn't take the "
        "write lock: a write during a build leaves that year stale for the next run."
    )

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None, help="build this year (again) whatever its state")
        parser.add_argument("--check", action="store_true", help="list the years that need building, and why")

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        this_year = datetime.now(UTC).year
        if options["year"] is not None:
            years = {options["year"]: "asked for"}
            if options["year"] not in pastyears.years_on_disk(data_dir, pastyears.DAILY):
                raise CommandError(f"--year {options['year']}: the archive has no daily store for it")
        else:
            years = pastyears.stale_years(data_dir, before=this_year)
        if options["check"]:
            for year, reason in years.items():
                self.report.step(f"{year}: {reason}")
            self.finish(f"{len(years)} years to build" if years else "every past year is current")
            return
        self.report.step(f"Building {len(years)} years: {', '.join(f'{y} ({r})' for y, r in years.items()) or 'none'}")
        for year in years:
            try:
                pastyears.build(
                    data_dir, year, progress=lambda done, total, y=year: self.report.progress(str(y), done, total)
                )
            except ValueError as error:
                self.report.fail(str(year), error)
                continue
            self.report.step(f"{year} built")
        self.finish(f"{len(years) - len(self.report.failures)} years built")
