from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from agdata.grid import service_window
from agdata.rebuild import find_stale, rebuild_stale
from ops.locks import hold_write_lock


class Command(BaseCommand):
    help = "Recompute derived data written by an older version of its code (D29); run on deploy, like migrate"

    def add_arguments(self, parser):
        parser.add_argument("--stale", action="store_true", help="recompute stale variables (the only mode)")
        parser.add_argument("--check", action="store_true", help="only list stale variables")

    def handle(self, *args, **options):
        if options["check"]:
            for store, names in find_stale(settings.DATA_DIR).stale.items():
                self.stdout.write(f"{store}: {', '.join(names)}")
            return
        if not options["stale"]:
            raise CommandError("pass --stale (or --check)")
        self.lock = hold_write_lock(settings.DATA_DIR)
        left = rebuild_stale(settings.DATA_DIR, service_window(settings.SERVICE_BOX), log=self.stdout.write)
        for store, names in left.stale.items():
            self.stdout.write(f"still stale (hourly, derived at ingest): {store}: {', '.join(names)}")
        self.stdout.write("done")
