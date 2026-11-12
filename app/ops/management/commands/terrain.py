from django.conf import settings

from agdata import coast, terrain
from ops.management.base import ReportingCommand


class Command(ReportingCommand):
    help = (
        "Build each grid cell's share of open water and its elevation (PLAN.md Phase 6 D6) from NHDPlus V2.1: fetch "
        "the archives the service box needs (kept as received in data/nhdplus), then work out the water share from "
        "the lakes', reservoirs' and wide rivers' polygons and the elevation statistics from the 30 m elevation "
        "model, into data/terrain.zarr. Run again only when the service box or the source changes."
    )
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="say what a run would do, and do nothing")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--rebuild", action="store_true", help="build again even if current")

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        window = self.window(options["box"])
        reason = "asked for" if options["rebuild"] else terrain.status(data_dir, window)
        missing = terrain.missing_archives(data_dir, window)
        needed = terrain.archives_for(window)
        self.report.step(f"NHDPlus V2.1 for the box: {len(needed)} archives, {len(missing)} to fetch")
        self.report.step(f"terrain store: {reason or 'current'}")
        if options["check"] or (reason is None and not missing):
            self.finish("checked" if options["check"] else "nothing to do")
            return
        for k, (unit, file) in enumerate(missing):
            if self.stopping.is_set():
                self.finish("stopped before building")
                return
            self.report.progress("archives", k, len(missing))
            self.report.detail(f"{file} ==> GET {terrain.url(unit, file)}")
            try:
                size = terrain.fetch(unit, file, terrain.archive_path(data_dir, file))
            except OSError as error:
                self.report.fail(file, error)
                continue
            self.report.detail(f"{file}: {size / 1e6:.0f} MB")
        if missing:
            self.report.progress("archives", len(missing), len(missing))
        if self.report.failures:
            self.finish("some archives failed; rerun to fetch them")
            return
        built = terrain.build(
            data_dir,
            window,
            coast.water(window),
            report=self.report.step,
            progress=lambda name, done, total: self.report.progress(name, done, total),
            stopping=self.stopping.is_set,
        )
        self.finish("built" if built else "stopped; the current store stays")
