"""The forecast's verification (D113): each published run's lead days kept at publish (`agdata.verification`), scored
against the archive as its days arrive and kept in `ForecastScore`, the daily `score_forecasts` job, `manage.py
verify`, and the summary and alarm in `/up`."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from django.db import transaction
from django.db.models import Count, F, Max, Min, Sum
from django.db.models.functions import ExtractHour

from agdata import verification
from agdata.forecast import last_observed_hour
from agdata.series import last_closed_day
from ops.models import ForecastScore

logger = logging.getLogger(__name__)

ALARM_MAE_C = 3.0  # lead-1 MAE of the daily max or min over 7 days; the backtest's is ~1.2-1.3 °C
ALARM_DAYS = 7
SILENT_DAYS = 3  # a day due this long ago and not scored is a problem
SUMMARY_VARIABLES = ("air_temperature_min", "air_temperature_max", "precipitation_sum", verification.DEGREE_DAYS)
SUMMARY_LEADS = (1, 3, 7)


def keep_published(data_dir: Path, run: Path, now: datetime) -> list[str] | None:
    """Keeps a just-published run's lead days and prunes the old ones; the days kept (ISO), or None when keeping
    failed. Never raises: verification must never stop a run from publishing. The caller holds the write lock."""
    try:
        kept = verification.keep(data_dir, run)
        verification.prune(data_dir, now)
    except Exception:
        logger.warning("keeping the published run %s for verification failed", run.name, exc_info=True)
        return None
    return [day.isoformat() for day in sorted(kept)]


@dataclass(frozen=True, kw_only=True)
class Due:
    """Days with kept runs: those to score now, those not yet observed (or closed), and the newest closed day."""

    due: list[date]
    waiting: list[date]
    closed: date | None


def due_days(data_dir: Path, now: datetime, runs: list[verification.Kept], rescore: bool = False) -> Due:
    """The kept runs' days the archive has closed (`series.last_closed_day`) and written, that have no scores or
    scores older than the archive's write (`rescore`: all of them)."""
    held = sorted({day for kept in runs for day in kept.leads})
    observed = last_observed_hour(data_dir, now, lookback=timedelta(days=verification.KEEP_DAYS))
    closed = last_closed_day(observed) if observed is not None else None
    candidates = [day for day in held if closed is not None and day <= closed]
    waiting = [day for day in held if day not in candidates]
    rows = (
        ForecastScore.objects.filter(valid_day__in=candidates)
        .values("cycle", "lead", "valid_day")
        .annotate(oldest=Min("observed_written"))
    )
    scored = {(row["cycle"], row["lead"]): row["oldest"] for row in rows}
    due = []
    for day in candidates:
        stamp = verification.observed_written(data_dir, day)
        if stamp is None:
            waiting.append(day)
            continue
        written = datetime.fromtimestamp(stamp, UTC)
        pairs = [(kept.cycle, kept.leads[day]) for kept in runs if day in kept.leads]
        if rescore or any(pair not in scored or scored[pair] < written for pair in pairs):
            due.append(day)
    return Due(due=due, waiting=sorted(waiting), closed=closed)


@dataclass(frozen=True, kw_only=True)
class Scored:
    days: int
    rows: int
    skipped: list[str]


def score(
    data_dir: Path,
    now: datetime,
    rescore: bool = False,
    on_day: Callable[[verification.DayScores], None] | None = None,
) -> Scored:
    """Scores the days due (`due_days`) and replaces their rows. Reads the stores and writes Postgres only, so it
    takes no write lock; a day the archive rewrites meanwhile has a newer stamp and is scored again next time."""
    runs = verification.kept_runs(data_dir)
    days = due_days(data_dir, now, runs, rescore=rescore).due
    rows, skipped = 0, []
    for day in days:
        result = verification.score_day(data_dir, day, runs)
        rows += save(result)
        skipped += [f"{day}: {note}" for note in dict.fromkeys(result.skipped)]
        if on_day is not None:
            on_day(result)
    for note in skipped:
        logger.warning("verification: %s", note)
    return Scored(days=len(days), rows=rows, skipped=skipped)


def save(result: verification.DayScores) -> int:
    """Replaces the rows of each run and lead scored on the day with the new scores; returns how many."""
    if result.observed_written is None or not result.scores:
        return 0
    written = datetime.fromtimestamp(result.observed_written, UTC)
    scored_at = datetime.now(UTC)
    pairs = {(s.cycle, s.lead) for s in result.scores}
    with transaction.atomic():
        for cycle, lead in pairs:
            ForecastScore.objects.filter(cycle=cycle, lead=lead).delete()
        ForecastScore.objects.bulk_create(
            ForecastScore(
                cycle=s.cycle,
                lead=s.lead,
                valid_day=result.day,
                variable=s.variable,
                n=s.n,
                bias=s.bias,
                mae=s.mae,
                rmse=s.rmse,
                hits=s.hits,
                misses=s.misses,
                false_alarms=s.false_alarms,
                observed_written=written,
                scored_at=scored_at,
            )
            for s in result.scores
        )
    return len(result.scores)


def pooled(
    since: date,
    until: date | None = None,
    variables: Iterable[str] | None = None,
    leads: Iterable[int] | None = None,
    by_cycle: bool = False,
) -> list[dict[str, Any]]:
    """Scores pooled over valid days since..until by variable and lead (and the cycle's hour, `by_cycle`), weighted by
    cells: n, bias, MAE and RMSE (exact: √(Σ n·rmse² / Σ n)), and for precipitation the wet-day counts. One query."""
    rows = ForecastScore.objects.filter(valid_day__gte=since, n__gt=0)
    if until is not None:
        rows = rows.filter(valid_day__lte=until)
    if variables is not None:
        rows = rows.filter(variable__in=list(variables))
    if leads is not None:
        rows = rows.filter(lead__in=list(leads))
    keys = ["variable", "lead"]
    if by_cycle:
        rows = rows.annotate(cycle_hour=ExtractHour("cycle", tzinfo=UTC))
        keys.append("cycle_hour")
    sums = (
        rows.values(*keys)
        .annotate(
            cells=Sum("n"),
            bias_sum=Sum(F("n") * F("bias")),
            mae_sum=Sum(F("n") * F("mae")),
            square_sum=Sum(F("n") * F("rmse") * F("rmse")),
            runs=Count("id"),
            hit_sum=Sum("hits"),
            miss_sum=Sum("misses"),
            false_sum=Sum("false_alarms"),
        )
        .order_by(*keys)
    )
    out = []
    for row in sums:
        cells = row["cells"]
        entry = {key: row[key] for key in keys} | {
            "n": cells,
            "scores": row["runs"],
            "bias": row["bias_sum"] / cells,
            "mae": row["mae_sum"] / cells,
            "rmse": (row["square_sum"] / cells) ** 0.5,
        }
        if row["hit_sum"] is not None:
            entry |= {"hits": row["hit_sum"], "misses": row["miss_sum"], "false_alarms": row["false_sum"]}
        out.append(entry)
    return out


def verification_health(data_dir: Path, now: datetime) -> tuple[dict[str, Any] | None, list[str]]:
    """The forecast's verification in `/up`: the newest day scored, and the last 7 days' MAE and bias at leads 1, 3
    and 7 of the daily min, max, precipitation and degree days 50/86 °F (catalog units: °C, mm, °F·d). Problems: a
    lead-1 MAE of the max or min above ALARM_MAE_C, or a kept day due SILENT_DAYS ago and not scored. None when
    nothing is kept or scored yet."""
    runs = verification.kept_runs(data_dir)
    newest = ForecastScore.objects.aggregate(day=Max("valid_day"))["day"]
    if not runs and newest is None:
        return None, []
    today = now.astimezone(UTC).date()
    since = (newest or today) - timedelta(days=ALARM_DAYS - 1)
    summary: dict[str, dict[str, dict[str, float]]] = {}
    problems = []
    for row in pooled(since=since, variables=SUMMARY_VARIABLES, leads=SUMMARY_LEADS):
        lead = str(row["lead"])
        summary.setdefault(row["variable"], {})[lead] = {"mae": round(row["mae"], 2), "bias": round(row["bias"], 2)}
        alarmed = row["lead"] == 1 and row["variable"] in ("air_temperature_min", "air_temperature_max")
        if alarmed and row["mae"] > ALARM_MAE_C:
            problems.append(f"forecast {row['variable']} lead-1 MAE {row['mae']:.1f} °C over {ALARM_DAYS} days")
    expected = last_closed_day(now) - timedelta(days=SILENT_DAYS)
    overdue = [day for kept in runs for day in kept.leads if day <= expected and (newest is None or day > newest)]
    if overdue:
        problems.append(f"no forecast day scored since {newest or 'the first run kept'}")
    body = {
        "runs_kept": len(runs),
        "last_scored_day": newest.isoformat() if newest else None,
        f"last_{ALARM_DAYS}_days": summary,
    }
    return body, problems
