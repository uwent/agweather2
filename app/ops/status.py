"""What `manage.py jobs status` prints (and `jobs start` before the worker): the archive, soil and forecast as `/up`
sees them, who holds the write lock, and each job's last run, next run and queue. v1's `DataImport.check_statuses`
in one screen. `day_lines` is `jobs days`: a line per UTC day of what the hourly store holds.

Everything reads; nothing here writes the archive or takes the lock (the lock is probed with a shared lock released
at once)."""

import fcntl
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from django.db import connection
from django.db.models import Count, Max, Q
from procrastinate import sql
from procrastinate.contrib.django import app
from procrastinate.contrib.django.models import ProcrastinateEvent, ProcrastinateJob

from agdata import forecast
from agdata.ingest import SOIL
from agdata.rebuild import find_stale
from agdata.store import CUMULATIVE, DAILY, HOURLY, SOURCE_NAMES, StoreLayout
from ops.forecast import forecast_health
from ops.health import failures_since, ingest_health
from ops.ifs import last_read
from ops.locks import parse_holder, waiting

STALLED_AFTER_S = 60  # a running job whose worker hasn't sent a heartbeat this long was left by a stopped worker


@dataclass(kw_only=True)
class JobState:
    name: str  # the task's short name, as `jobs run` takes it
    schedule: str | None  # cron, for a periodic job
    next_run: datetime | None
    last_status: str | None  # succeeded, failed, …
    last_finished: datetime | None
    last_seconds: float | None
    queued: int
    running: int
    stalled: int
    failed_recently: int


@dataclass(kw_only=True)
class Status:
    now: datetime
    ingest: dict[str, Any]
    forecast: dict[str, Any]
    problems: list[str]
    daily_through: date | None
    era5land_through: datetime | None
    ifs_run: str | None
    lock_holder: str | None  # who holds the write lock (pid, label, since), or None when free
    lock_waiting: list[str] = field(default_factory=list)  # who's waiting for it
    jobs: list[JobState]
    failures: list[str] = field(default_factory=list)  # recent failed jobs, one line each


def snapshot(data_dir: Path, now: datetime) -> Status:
    ingest, problems = ingest_health(data_dir, now)
    forecast, forecast_problems = forecast_health(data_dir, now)
    run, _seam = last_read(data_dir)
    return Status(
        now=now,
        ingest=ingest,
        forecast=forecast,
        problems=problems + forecast_problems,
        daily_through=daily_through(data_dir, now.year),
        era5land_through=last_hour_from(data_dir, now.year, SOIL[0], "era5land"),
        ifs_run=run,
        lock_holder=lock_holder(data_dir),
        lock_waiting=[str(h) for h in waiting(data_dir)],
        jobs=job_states(data_dir, now),
        failures=recent_failures(data_dir, now),
    )


def short_name(task_name: str) -> str:
    return task_name.rsplit(".", 1)[-1]


def job_states(data_dir: Path, now: datetime) -> list[JobState]:
    """Every registered task in `ops.tasks` (periodic or not), with its schedule and queue."""
    periodic = {p.task.name: p for p in app.periodic_registry.periodic_tasks.values()}
    names = sorted(name for name in app.tasks if name.startswith("ops.tasks."))
    since = failures_since(data_dir, now)
    counts = {
        row["task_name"]: row
        for row in ProcrastinateJob.objects.filter(task_name__in=names)
        .values("task_name")
        .annotate(
            queued=Count("id", filter=Q(status="todo"), distinct=True),
            running=Count("id", filter=Q(status="doing"), distinct=True),
            failed=Count(
                "id",
                filter=Q(status="failed", procrastinateevent__type="failed", procrastinateevent__at__gte=since),
                distinct=True,
            ),
        )
    }
    stalled = stalled_jobs()
    states = []
    for name in names:
        last = (
            ProcrastinateJob.objects.filter(task_name=name, status__in=("succeeded", "failed"))
            .annotate(finished=Max("procrastinateevent__at"))
            .order_by("-finished")
            .first()
        )
        seconds = None
        if last is not None:
            started = last.procrastinateevent_set.filter(type="started").order_by("-at").first()  # type: ignore[attr-defined]
            if started is not None:
                seconds = (last.finished - started.at).total_seconds()  # type: ignore[attr-defined]
        task = periodic.get(name)
        row = counts.get(name, {})
        states.append(
            JobState(
                name=short_name(name),
                schedule=task.cron if task else None,
                next_run=_next_run(task, now) if task else None,
                last_status=last.status if last else None,
                last_finished=last.finished if last else None,  # type: ignore[attr-defined]
                last_seconds=seconds,
                queued=row.get("queued", 0),
                running=row.get("running", 0) - sum(1 for _, n in stalled if n == name),
                stalled=sum(1 for _, n in stalled if n == name),
                failed_recently=row.get("failed", 0),
            )
        )
    return states


def stalled_jobs() -> list[tuple[int, str]]:
    """(id, task name) of jobs still marked running whose worker stopped (no heartbeat for STALLED_AFTER_S), by
    Procrastinate's own query."""
    with connection.cursor() as cursor:
        cursor.execute(
            sql.queries["select_stalled_jobs_by_heartbeat"],
            {"queue": None, "task_name": None, "seconds_since_heartbeat": STALLED_AFTER_S},
        )
        return [(row[0], row[2]) for row in cursor.fetchall()]


def abort_stalled_jobs() -> list[tuple[int, str]]:
    """Marks stalled jobs aborted (their worker is gone, so they'll never finish) and returns them. Aborted, not
    failed: a job cut off by a restart (bin/dev stopped, a deploy) isn't a problem, and reruns on the next turn."""
    jobs = stalled_jobs()
    with connection.cursor() as cursor:
        for job_id, _ in jobs:
            cursor.execute(sql.queries["finish_job"], {"job_id": job_id, "status": "aborted", "delete_job": False})
    return jobs


def _next_run(task: Any, now: datetime) -> datetime:
    cron = task.croniter
    cron.set_current(start_time=now.timestamp())
    return datetime.fromtimestamp(cron.get_next(ret_type=float), UTC)


def recent_failures(data_dir: Path, now: datetime) -> list[str]:
    """The jobs that failed in the last day and since the failures were last cleared (`runs.clear_jobs`)."""
    events = (
        ProcrastinateEvent.objects.filter(type="failed", job__status="failed", at__gte=failures_since(data_dir, now))
        .select_related("job")
        .order_by("-at")[:10]
    )
    return [f"{e.at:%Y-%m-%d %H:%MZ} {short_name(e.job.task_name)} (job {e.job.id})" for e in events]  # type: ignore[attr-defined]


def lock_holder(data_dir: Path) -> str | None:
    """Who holds `write.lock` now (`pid 123 (backfill …, since 11:59)`), else None."""
    path = data_dir / "write.lock"
    if not path.exists():
        return None
    with open(path) as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return str(parse_holder(handle.read()))
        fcntl.flock(handle, fcntl.LOCK_UN)
    return None


def _meta(path: Path, name: str) -> np.ndarray | None:
    try:
        return np.asarray(zarr.open_group(path, mode="r")[f"_meta/{name}.source"][:])  # type: ignore[index]
    except (FileNotFoundError, KeyError):
        return None


def daily_through(data_dir: Path, year: int) -> date | None:
    """The last local day rolled up (daily min temperature written), this year or last."""
    for y in (year, year - 1):
        codes = _meta(DAILY.path(data_dir, y), "air_temperature_min")
        if codes is not None and (written := np.flatnonzero(codes > 0)).size:
            return date(y, 1, 1) + timedelta(days=int(written[-1]))
    return None


def last_hour_from(data_dir: Path, year: int, name: str, source: str) -> datetime | None:
    """The last hour of `name` written by `source`, this year or last."""
    code = {v: k for k, v in SOURCE_NAMES.items()}[source]
    for y in (year, year - 1):
        codes = _meta(HOURLY.path(data_dir, y), name)
        if codes is not None and (written := np.flatnonzero(codes == code)).size:
            return datetime(y, 1, 1, tzinfo=UTC) + timedelta(hours=int(written[-1]))
    return None


def day_lines(data_dir: Path, first: date, last: date) -> tuple[list[str], int]:
    """One line per UTC day first..last: hours with air temperature (by source), precip and soil (by source), and OK
    when all 24 of each are there. Returns the lines and how many days weren't OK."""
    cache: dict[int, dict[str, np.ndarray | None]] = {}
    lines, bad = [], 0
    day = first
    while day <= last:
        if day.year not in cache:
            path = HOURLY.path(data_dir, day.year)
            cache[day.year] = {n: _meta(path, n) for n in ("air_temperature", "precipitation", SOIL[0])}
        n = (day - date(day.year, 1, 1)).days * 24
        parts, counts = [], []
        for label, name in (("air", "air_temperature"), ("precip", "precipitation"), ("soil", SOIL[0])):
            codes = cache[day.year][name]
            hours = np.zeros(24, dtype=np.uint8) if codes is None else codes[n : n + 24]
            counts.append(int((hours > 0).sum()))
            by_source = ", ".join(
                f"{SOURCE_NAMES.get(int(c), c)} {int((hours == c).sum())}" for c in np.unique(hours[hours > 0])
            )
            parts.append(f"{label} {counts[-1]}/24" + (f" ({by_source})" if by_source else ""))
        state = "OK" if min(counts) == 24 else "MISSING" if max(counts) == 0 else "PARTIAL"
        bad += state != "OK"
        lines.append(f"{day}  {state:<7}  " + "  ".join(parts))
        day += timedelta(days=1)
    return lines, bad


def status_lines(status: Status) -> list[str]:
    """The snapshot as the lines `jobs status` prints."""
    i, f = status.ingest, status.forecast
    out = [f"AgWeather status at {status.now.astimezone():%Y-%m-%d %H:%M %Z}"]
    if i.get("state") == "not started":
        out.append("  archive: empty (run manage.py backfill)")
    else:
        out.append(
            f"  archive: newest hour {_when(i['newest_hour'])} ({_hours(i['lag_hours'])} ago); "
            f"URMA {_when(i['newest_urma_hour'])} ({_hours(i['urma_lag_hours'])} ago); "
            f"{i['missing_hours_7d']} missing hours in 7 days"
        )
        out.append(f"  daily:   rolled up through {status.daily_through or 'nothing yet'}")
        if i.get("stale"):
            out.append(f"  stale:   {', '.join(sorted(i['stale']))} (run manage.py rebuild --stale)")
    out.append(
        f"  soil:    ERA5-Land through {_when(status.era5land_through)}; "
        f"IFS run {_when(status.ifs_run) if status.ifs_run else 'none read'} after it"
    )
    if f.get("state") == "not started":
        out.append("  forecast: none published yet")
    else:
        failed = f", {f['failed_leads']} failed leads" if f["failed_leads"] else ""
        out.append(
            f"  forecast: {_when(f['cycle'])} run ({_hours(f['age_hours'])} old), through {_when(f['last_hour'])}"
            + failed
        )
    out.append(f"  lock:    {'held by ' + status.lock_holder if status.lock_holder else 'free'}")
    for waiter in status.lock_waiting:
        out.append(f"           waiting: {waiter}")
    out.append("  jobs:")
    width = max((len(j.name) for j in status.jobs), default=0)
    for j in status.jobs:
        last = (
            f"last {j.last_status} {_when(j.last_finished)}"
            + (f" in {_seconds(j.last_seconds)}" if j.last_seconds is not None else "")
            if j.last_status
            else "never run"
        )
        queue = ", ".join(
            text
            for n, text in (
                (j.running, f"{j.running} running"),
                (j.stalled, f"{j.stalled} stalled (its worker stopped)"),
                (j.queued, f"{j.queued} queued"),
                (j.failed_recently, f"{j.failed_recently} failed in 24 h"),
            )
            if n
        )
        nxt = f"next {_when(j.next_run)}" if j.next_run else "on demand"
        out.append(f"    {j.name:<{width}}  {last}; {nxt}" + (f"; {queue}" if queue else ""))
    for line in status.failures:
        out.append(f"  failed: {line}")
    out.append("  problems: " + ("; ".join(status.problems) if status.problems else "none"))
    return out


def _when(value: datetime | str | None) -> str:
    if value is None:
        return "never"
    when = datetime.fromisoformat(value) if isinstance(value, str) else value
    return f"{when.astimezone(UTC):%b %d %H:%MZ}"


def _hours(value: float | None) -> str:
    return "?" if value is None else f"{value:.0f} h" if value >= 2 else f"{value * 60:.0f} min"


def _seconds(value: float) -> str:
    return f"{value:.0f} s" if value < 90 else f"{value / 60:.0f} min"


def span(data_dir: Path, layout: StoreLayout, name: str) -> tuple[datetime | None, datetime | None]:
    """The first and last steps of `name` any source has written, across every year's store: hours as their UTC
    end, days as midnight UTC of the day."""
    step = timedelta(hours=1) if layout.step == "hour" else timedelta(days=1)
    found: list[datetime] = []
    for path in sorted(layout.path(data_dir, 2000).parent.glob("[0-9][0-9][0-9][0-9].zarr")):
        codes = _meta(path, name)
        if codes is not None and (written := np.flatnonzero(codes > 0)).size:
            start = datetime(int(path.stem), 1, 1, tzinfo=UTC)
            found += [start + int(written[0]) * step, start + int(written[-1]) * step]
    return (min(found), max(found)) if found else (None, None)


def last_hour_by_source(data_dir: Path, year: int, names) -> dict[str, datetime]:
    """Each source's last hour in the archive over `names`, this year and last."""
    found: dict[str, datetime] = {}
    for y in (year - 1, year):
        for name in names:
            codes = _meta(HOURLY.path(data_dir, y), name)
            if codes is None:
                continue
            for code in np.unique(codes[codes > 0]).tolist():
                if (source := SOURCE_NAMES.get(code)) is not None:
                    hour = datetime(y, 1, 1, tzinfo=UTC) + timedelta(hours=int(np.flatnonzero(codes == code)[-1]))
                    found[source] = max(found.get(source, hour), hour)
    return dict(sorted(found.items()))


# The variables whose sources say what each feed last delivered: URMA and RTMA (temperature, precip), HRRR
# (shortwave), ERA5-Land and IFS (soil); the others add reads and nothing new
SOURCE_VARIABLES = ("air_temperature", "precipitation", "shortwave_radiation", "soil_temperature_4cm")
SPAN_VARIABLES = {"hourly": "air_temperature", "daily": "air_temperature_min", "cumulative": "dd_sine_50"}


def refresh_dataset_status(data_dir: Path, now: datetime | None = None) -> None:
    """Reads each dataset's extent, sources and stale variables from the stores into `DatasetStatus` (~0.5 s: the
    stale check opens every store). Called with the write lock held, as it's released (`ops.locks.write_lock`), and
    by `manage.py jobs start`, since a deploy can make stores stale without any write."""
    from ops.models import DatasetStatus

    now = now or datetime.now(UTC)
    stale: dict[str, dict[str, list[str]]] = {}
    for key, names in find_stale(data_dir).stale.items():
        kind, year = key.split("/")
        stale.setdefault(kind, {})[year] = names
    rows: dict[str, dict[str, Any]] = {}
    for layout in (HOURLY, DAILY, CUMULATIVE):
        first, last = span(data_dir, layout, SPAN_VARIABLES[layout.kind])
        rows[layout.kind] = {"first": first, "last": last, "stale": stale.get(layout.kind, {})}
    sources = last_hour_by_source(data_dir, now.year, SOURCE_VARIABLES)
    rows["hourly"]["last_by_source"] = {k: v.isoformat() for k, v in sources.items() if k != "derived"}
    run = forecast.current_run(data_dir)
    info = forecast.run_info(run) if run is not None else {}
    rows["forecast"] = {
        "first": datetime.fromisoformat(info["cycle"]) if "cycle" in info else None,
        "last": datetime.fromisoformat(info["last_hour"]) if "last_hour" in info else None,
        "details": {key: info.get(key) for key in ("cycle", "last_hour", "last_observed")} if info else {},
    }
    for dataset, values in rows.items():
        DatasetStatus.objects.update_or_create(dataset=dataset, defaults={**values, "refreshed_at": now})


def dataset_status(data_dir: Path) -> dict[str, Any]:
    """The `DatasetStatus` rows by dataset, refreshed first if there are none yet (a new install)."""
    from ops.models import DatasetStatus

    rows = {row.dataset: row for row in DatasetStatus.objects.all()}
    if len(rows) < len(DatasetStatus.Dataset):
        refresh_dataset_status(data_dir)
        rows = {row.dataset: row for row in DatasetStatus.objects.all()}
    return rows
