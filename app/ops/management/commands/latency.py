from datetime import date

from django.conf import settings
from django.core.management.base import CommandError

from agdata import series
from api import clock
from ops import latency
from ops.management.base import ReportingCommand

MADISON = (43.07, -89.40)
MODELS = ("tar-spot", "early-blight-pdays")  # a plain disease, and one with a crop-stage biofix (each cell's emergence)


class Command(ReportingCommand):
    help = (
        "Time the requests that must be fast (PLAN.md §3) on this archive, in process: a risk map's first tile for "
        "a day and a week, a custom degree-day map from March 1, a point's hourly season, and every model at a "
        "point. Each is timed first (a map's compute) and then repeated. Reads only; run it with the worker quiet "
        "for numbers that mean something."
    )
    tracked = False

    def add_arguments(self, parser):
        parser.add_argument("--lat", type=float, default=MADISON[0])
        parser.add_argument("--lng", type=float, default=MADISON[1])
        parser.add_argument("--day", type=date.fromisoformat, help="the risk maps' day (default: July 15 last seen)")
        parser.add_argument("--models", default=",".join(MODELS), help="the risk maps' models, comma separated")
        parser.add_argument("--repeats", type=int, default=5, help="repeats after the first request (median)")

    def handle(self, *args, **options):
        observed = series.last_observed(settings.DATA_DIR, clock.now())
        if observed is None:
            raise CommandError("the archive has no observed hours")
        last_day = series.last_closed_day(observed)
        map_day = options["day"] or _last_july_15(last_day)
        found = latency.cases(
            lat=options["lat"],
            lng=options["lng"],
            map_day=map_day,
            season_start=date(last_day.year, 3, 1),
            last_day=last_day,
            models=tuple(m.strip() for m in options["models"].split(",") if m.strip()),
        )
        self.report.step(
            f"Timing {len(found)} requests at {options['lat']}, {options['lng']} "
            f"(maps on {map_day}, the season from March 1 to {last_day}, box {settings.SERVICE_BOX})"
        )

        def show(t: latency.Timing) -> None:
            if t.met:
                self.report.step(f"{t.case.name}: {latency.describe(t)}")
            else:
                self.report.fail(t.case.name, latency.describe(t))

        warm_up = latency.warm_up(
            lat=options["lat"], lng=options["lng"], day=date.fromordinal(map_day.toordinal() - 30)
        )
        self.report.detail(f"warmed up the process in {warm_up:,.0f} ms (a weather tile, a crop map and a point)")
        timings = latency.run(found, repeats=options["repeats"], on_timing=show)
        self.finish(f"{sum(t.met for t in timings)} of {len(timings)} within their targets")


def _last_july_15(last_day: date) -> date:
    july = date(last_day.year, 7, 15)
    return july if july <= last_day else date(last_day.year - 1, 7, 15)
