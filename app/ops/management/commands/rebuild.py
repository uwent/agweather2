from django.conf import settings
from django.core.management.base import CommandError

from agdata.rebuild import find_stale, plan, rebuild_stale
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Recompute derived data written by an older version of its code (D29); run on deploy, like migrate. Waits "
        "for the write lock if a job holds it."
    )

    def add_arguments(self, parser):
        parser.add_argument("--stale", action="store_true", help="recompute stale variables")
        parser.add_argument(
            "--check", action="store_true", help="only list stale variables and what --stale would do (read-only)"
        )

    def handle(self, *args, **options):
        if options["check"]:
            report = find_stale(settings.DATA_DIR)
            for store, names in report.stale.items():
                self.stdout.write(f"{store}: {', '.join(names)}")
            if not report.stale:
                self.stdout.write("nothing stale")
                return
            self.stdout.write("\n--stale would:")
            for line in plan(report):
                self.stdout.write(f"  {line}")
            return
        if not options["stale"]:
            raise CommandError("pass --stale to recompute, or --check to list")
        with self.lock():
            left = rebuild_stale(settings.DATA_DIR, self.window(None), log=self.report.step)
        for store, names in left.stale.items():
            self.report.warn(f"still stale (hourly, derived at ingest; needs a refetch): {store}: {', '.join(names)}")
        self.finish()
