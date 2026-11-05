import time

from django.conf import settings
from django.core.management.base import CommandError

from agdata import modelmaps
from agdata.catalog import DAILY_VARIABLES
from agdata.store import DAILY, GridStore
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Build the models' ingredients on the grid (agdata.modelmaps, Phase 5 F, D66): each year with a daily store "
        "whose ingredients aren't built, are stale or are behind it, or one --year (again, whatever its state). "
        "Reads and computes outside the write lock and takes it, politely, to write each band of rows. The hourly "
        "ingest and forecast keep them current after this; `archive fill` builds each year it fills."
    )
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, action="append", help="build this year (repeat for more)")
        parser.add_argument("--check", action="store_true", help="list the years that need building, and why")

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        on_disk = sorted((int(p.stem) for p in (data_dir / DAILY.kind).glob("*.zarr")), reverse=True)
        if options["year"]:
            missing = [y for y in options["year"] if y not in on_disk]
            if missing:
                raise CommandError(f"--year {missing}: the archive has no daily store for it")
            years = dict.fromkeys(options["year"], "asked for")
        else:
            years = {year: reason for year in on_disk if (reason := modelmaps.status(data_dir, year))}
        if options["check"]:
            for year, reason in years.items():
                self.report.step(f"{year}: {reason}")
            self.finish(f"{len(years)} years to build" if years else "every year's ingredients are current")
            return
        self.report.step(f"Building {len(years)} years: {', '.join(f'{y} ({r})' for y, r in years.items()) or 'none'}")
        built = 0
        for year in years:
            if self.stopping.is_set():
                break
            began = time.monotonic()
            self.report.step(f"{year}: building ({years[year]})")
            window = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True).window
            try:
                days = modelmaps.build(
                    data_dir,
                    window,
                    year,
                    lock=lambda: self.lock(polite=True),
                    progress=lambda done, n, y=year: self.report.progress(str(y), done, n),
                )
            except (OSError, ValueError) as error:
                self.report.fail(str(year), error)
                continue
            built += 1
            if days is not None:
                self.report.step(f"{year}: {days[0]} to {days[1]} in {time.monotonic() - began:.0f} s")
        self.finish(f"{built} years built")
