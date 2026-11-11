from datetime import UTC, datetime

from django.conf import settings

from ops import climatology
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Keep the 30-year normal's gridMET years (D82, D84): fetch the files the trailing 30 complete years need "
        "(the box's part of each, kept as received in data/gridmet), fit the adjustment to the archive over the "
        "years both have, derive the years the archive lacks onto the 2.5 km grid, and drop what the period no longer "
        "needs. Downloads run outside the write lock. Resumable: a rerun fetches what's missing."
    )
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="say what a run would do, and do nothing")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--refit", action="store_true", help="fit the adjustment again")
        parser.add_argument("--rederive", action="store_true", help="derive every gridMET year again")

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        window = self.window(options["box"])
        p = climatology.plan(
            data_dir, datetime.now(UTC).date(), window, refit=options["refit"], rederive=options["rederive"]
        )
        for line in climatology.describe(p):
            self.report.step(line)
        if options["check"] or p.nothing:
            self.finish("checked" if options["check"] else "nothing to do")
            return
        derived = climatology.run(
            data_dir,
            window,
            p,
            report=self.report,
            lock=lambda: self.lock(polite=True),
            stopping=self.stopping.is_set,
        )
        self.finish(f"{len(p.fetch)} files fetched, {derived} years derived" + (", fit again" if p.refit else ""))
