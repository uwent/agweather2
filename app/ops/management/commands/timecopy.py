from django.conf import settings

from agdata import pastyears, timecopy
from agdata.store import DAILY
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Copy each year's daily minimum and maximum temperature into the copy laid out for reading a season over the "
        "map (agdata.timecopy; the custom degree-day map): the days the daily store has written since the copy last "
        "copied them. The archive's rollups keep it current; this fills the years rolled up before it existed. "
        "Takes the write lock a year at a time."
    )
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="list the years the copy is behind on")

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        behind = {
            year: n for year in pastyears.years_on_disk(data_dir, DAILY) if (n := timecopy.behind(data_dir, year))
        }
        if options["check"]:
            for year, n in behind.items():
                self.report.step(f"{year}: {n} days behind")
            self.finish(f"{len(behind)} years behind" if behind else "every year's copy is current")
            return
        self.report.step(f"Copying {len(behind)} years: {', '.join(f'{y} ({n} days)' for y, n in behind.items())}")
        for k, year in enumerate(behind):
            if self.stopping.is_set():
                break
            with self.lock(polite=True):
                copied = timecopy.fill(data_dir, year)
            self.report.detail(f"{year}: {copied} days copied")
            self.report.progress("years", k + 1, len(behind))
        self.finish(f"{len(behind)} years copied")
