from datetime import UTC, datetime

from django.conf import settings
from django.core.management.base import CommandError

from agdata.catalog import DAILY_VARIABLES
from ops import downloads
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Build the yearly NetCDF downloads of the daily variables (ops.downloads, D69): every file that's missing or "
        "built from an older write of its store, the current year's at most weekly. About 1.5 s and 5–15 MB a file "
        "over Wisconsin. Reads the daily stores only, so it doesn't take the write lock."
    )
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--variables", help="only these daily variables, comma separated")
        parser.add_argument("--check", action="store_true", help="list the files that need building, and why")

    def handle(self, *args, **options):
        names = None
        if options["variables"]:
            names = [n.strip() for n in options["variables"].split(",") if n.strip()]
            unknown = [n for n in names if n not in DAILY_VARIABLES]
            if unknown:
                raise CommandError(f"not daily variables: {', '.join(unknown)}")
        now = datetime.now(UTC)
        if options["check"]:
            todo = downloads.wanted(settings.DATA_DIR, now, names)
            for name, year, why in todo:
                self.report.step(f"{name} {year}: {why}")
            self.finish(f"{len(todo)} files to build" if todo else "every file is current")
            return
        self.report.step(f"Building the downloads in {downloads.folder(settings.DATA_DIR)}")

        def progress(done: int, total: int, item: str) -> None:
            if item:
                self.report.detail(item)
            self.report.progress("files", done, total)
            if self.stopping.is_set():
                raise downloads.Stopped

        try:
            built = downloads.build_wanted(settings.DATA_DIR, now, names, progress=progress)
        except downloads.Stopped:
            built = []
        size = sum(e.bytes for e in built) / 1e6
        self.finish(f"{len(built)} files built ({size:,.0f} MB)")
