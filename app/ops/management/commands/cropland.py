from django.conf import settings
from django.core.management.base import CommandError

from agdata import coverage, cropland
from ops.management.base import ReportingCommand


def parse_years(text: str) -> tuple[int, ...]:
    """`2021-2025` or `2021,2023,2025`."""
    try:
        if "-" in text:
            first, last = (int(v) for v in text.split("-"))
            years = tuple(range(first, last + 1))
        else:
            years = tuple(sorted(int(v) for v in text.split(",")))
    except ValueError:
        raise CommandError(f"--years {text!r}: expected FIRST-LAST or a list, such as 2021-2025") from None
    if not years or years[0] < 2008:
        raise CommandError(f"--years {text!r}: NASS's national 30 m layers start in 2008")
    return years


class Command(ReportingCommand):
    help = "Build each grid cell's cropland (Phase 6 step 6, D116) from USDA NASS's Cropland Data Layer: fetch the national 30 m zips of the years counted (kept as received in data/cdl), unpack each year's raster, count every 30 m pixel in the grid cell holding its centre, and keep each crop's average share and share in any year, and the cultivated share, in data/cropland.zarr; the unpacked rasters are deleted after. Run again each February with the newest five years (--years)."
    stoppable = True

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="say what a run would do, and do nothing")
        parser.add_argument("--box", default=None, help="service box (default: SERVICE_BOX)")
        parser.add_argument("--rebuild", action="store_true", help="build again even if current")
        parser.add_argument(
            "--years",
            default=None,
            help="the CDL years to count, FIRST-LAST or a list (default: the built store's, else 2021-2025)",
        )
        parser.add_argument("--fetch-only", action="store_true", help="fetch the missing zips, and build nothing")
        parser.add_argument(
            "--keep-extracted", action="store_true", help="keep the unpacked rasters in data/cdl/extracted"
        )

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        spec = options["box"] or settings.SERVICE_BOX
        window = coverage.extent(self.window(spec))  # a coverage's extent: readers pad the rest (`Cropland.share`)
        covered = coverage.of(spec).over(window)
        years = (
            parse_years(options["years"]) if options["years"] else (cropland.stored_years(data_dir) or cropland.YEARS)
        )
        reason = "asked for" if options["rebuild"] else cropland.status(data_dir, window, years)
        missing = cropland.missing_years(data_dir, years)
        self.report.step(f"Cropland Data Layer {years[0]}–{years[-1]}: {len(years)} zips, {len(missing)} to fetch")
        self.report.step(f"cropland store: {reason or 'current'}")
        if options["check"] or (reason is None and not missing):
            self.finish("checked" if options["check"] else "nothing to do")
            return
        for year in missing:
            if self.stopping.is_set():
                self.finish("stopped before building")
                return
            label = f"{cropland.zip_name(year)} (MB)"
            self.report.detail(f"{year} ==> GET {cropland.url(year)}")
            try:
                size = cropland.fetch(
                    year,
                    cropland.zip_path(data_dir, year),
                    progress=lambda done, total, label=label: self.report.progress(label, done >> 20, total >> 20),
                )
            except OSError as error:
                self.report.fail(cropland.zip_name(year), error)
                continue
            self.report.detail(f"{cropland.zip_name(year)}: {size / 1e9:.2f} GB")
        if self.report.failures:
            self.finish("some zips failed; rerun to resume them")
            return
        if reason is None or options["fetch_only"]:
            self.finish("fetched" + ("; the store is current" if reason is None else ""))
            return
        paths = {}
        try:
            for year in years:
                if self.stopping.is_set():
                    self.finish("stopped before building")
                    return
                self.report.step(f"unpacking {year}'s raster")
                label = f"{year} raster (MB)"
                paths[year] = cropland.extract(
                    data_dir,
                    year,
                    progress=lambda done, total, label=label: self.report.progress(label, done >> 20, total >> 20),
                )
            summary = cropland.build(
                data_dir,
                window,
                covered,
                paths,
                report=self.report.step,
                progress=lambda done, total: self.report.progress("blocks", done, total),
                stopping=self.stopping.is_set,
            )
        except cropland.Misaligned as error:
            self.report.fail("years", error)
            summary = None
        finally:
            if not options["keep_extracted"]:
                freed = cropland.delete_extracted(data_dir)
                if freed:
                    self.report.detail(f"deleted the unpacked rasters ({freed / 1e9:.1f} GB)")
        if summary is None:
            self.finish("" if self.report.failures else "stopped; the current store stays")
            return
        self.report.step(
            f"{summary['covered_cells']:,} covered cells, {summary['observed_cells']:,} with CDL data, {summary['cultivated_share']:.1%} cultivated on average"
        )
        self.finish("built")
