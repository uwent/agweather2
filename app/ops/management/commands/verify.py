from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.management.base import CommandError

from agdata import forecast, verification
from ops import verification as scores
from ops.management.base import ReportingCommand, positive


def clock() -> datetime:
    return datetime.now(UTC)


class Command(ReportingCommand):
    help = "Score the kept forecast runs against the archive (D113): each published run's lead days 1-10 are kept for 45 days and scored as the archive closes them, and again when it rewrites them. By default scores what's due; --check lists what's kept and waiting, --report pools the scores by variable and lead. Reads the stores and writes the database; only --keep-current takes the write lock."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check", action="store_true", help="list the kept runs, the days due and the days waiting"
        )
        parser.add_argument("--rescore", action="store_true", help="score every kept day again, due or not")
        parser.add_argument("--report", action="store_true", help="bias, MAE and RMSE by variable and lead")
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="--report: the valid days pooled, back from the newest scored (default 30)",
        )
        parser.add_argument(
            "--by-cycle", action="store_true", help="--report: by the cycle's hour too (01, 07, 13, 19Z)"
        )
        parser.add_argument(
            "--keep-current",
            action="store_true",
            help="keep the published run's lead days (a first deploy: runs are otherwise kept as they're published)",
        )

    def is_tracked(self, options) -> bool:
        return not (options.get("check") or options.get("report"))

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR
        now = clock()
        if options["report"]:
            return self.report_scores(positive(options["days"], "--days"), options["by_cycle"])
        if options["check"]:
            return self.check(now)
        if options["keep_current"]:
            current = forecast.current_run(data_dir)
            if current is None:
                raise CommandError("No forecast run is published yet; run `manage.py forecast` first.")
            with self.lock():
                kept = verification.keep(data_dir, current)
                pruned = verification.prune(data_dir, now)
            self.report.step(f"Kept {len(kept)} days of the {current.name} run; pruned {pruned} old runs")
        self.report.step("Scoring the kept forecast days the archive has closed")

        def on_day(result: verification.DayScores) -> None:
            self.report.detail(f"{result.day}: {len(result.scores)} scores")

        done = scores.score(data_dir, now, rescore=options["rescore"], on_day=on_day)
        for note in done.skipped:
            self.report.warn(note)
        self.finish(f"{done.days} days scored, {done.rows} rows")

    def check(self, now: datetime) -> None:
        runs = verification.kept_runs(settings.DATA_DIR)
        due = scores.due_days(settings.DATA_DIR, now, runs)
        first = f"{runs[0].cycle:%Y-%m-%d %H}Z" if runs else "none"
        last = f"{runs[-1].cycle:%Y-%m-%d %H}Z" if runs else "none"
        self.report.step(f"Kept runs: {len(runs)} (oldest {first}, newest {last})")
        self.report.step(f"Archive's last closed day: {due.closed or 'none'}")
        self.report.step(f"Days due: {', '.join(map(str, due.due)) or 'none'}")
        self.report.step(
            f"Days waiting for the archive: {len(due.waiting)}"
            + (f" ({due.waiting[0]} to {due.waiting[-1]})" if due.waiting else "")
        )
        self.finish(f"{len(due.due)} days due")

    def report_scores(self, days: int, by_cycle: bool) -> None:
        from ops.models import ForecastScore

        newest = ForecastScore.objects.order_by("-valid_day").values_list("valid_day", flat=True).first()
        if newest is None:
            self.finish("no scores yet")
            return
        since = newest - timedelta(days=days - 1)
        rows = scores.pooled(since=since, until=newest, by_cycle=by_cycle)
        self.report.step(f"Forecast − observed, {since} to {newest}, pooled over cells (catalog units)")
        header = (
            f"{'variable':<30} {'lead':>4} "
            + ("cycle " if by_cycle else "")
            + f"{'bias':>8} {'MAE':>8} {'RMSE':>8} {'runs':>5}"
        )
        self.stdout.write(header)
        for row in sorted(
            rows,
            key=lambda r: (
                verification.SCORED.index(r["variable"]) if r["variable"] in verification.SCORED else 99,
                r["lead"],
                r.get("cycle_hour", 0),
            ),
        ):
            cycle = f"{row['cycle_hour']:02d}Z   " if by_cycle else ""
            line = f"{row['variable']:<30} {row['lead']:>4} {cycle}{row['bias']:>8.2f} {row['mae']:>8.2f} {row['rmse']:>8.2f} {row['scores']:>5}"
            if "hits" in row:
                line += f"  hits {row['hits']}, misses {row['misses']}, false alarms {row['false_alarms']}"
            self.stdout.write(line)
        self.finish(f"{len(rows)} rows")
