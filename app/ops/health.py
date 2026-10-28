"""Ingest health for `/up`: how far behind the archive is, gaps in the last week, failed jobs, the last run."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from procrastinate.contrib.django.models import ProcrastinateJob

from agdata.catalog import VARIABLES
from agdata.rebuild import find_stale
from agdata.store import HOURLY, SOURCES, GridStore, steps_in_year
from ops.models import IngestRecord

MAX_LAG_HOURS = 3  # newest hour from any source
MAX_URMA_LAG_HOURS = 12  # URMA runs about 6 h behind
RECENT = timedelta(days=7)
UNPUBLISHED = timedelta(hours=2)  # the newest hours may not be out yet, so they don't count as missing


def ingest_health(data_dir: Path, now: datetime) -> tuple[dict[str, Any], list[str]]:
    """The ingest section of `/up`, and the problems that make it degraded. An empty archive is not started
    rather than degraded, so a fresh install (or the browser tests' empty archive) reports ok."""
    hours = _recent_sources(data_dir, now)
    if hours is None:
        return {"state": "not started"}, []
    times, codes = hours
    newest = _last(times, codes > 0)
    newest_urma = _last(times, codes == SOURCES["urma"])
    now64 = _utc64(now)
    recent = (times > now64 - np.timedelta64(RECENT)) & (times <= now64 - np.timedelta64(UNPUBLISHED))
    since = now - timedelta(days=1)
    failed_jobs = (
        ProcrastinateJob.objects.filter(
            status="failed", procrastinateevent__type="failed", procrastinateevent__at__gte=since
        )
        .distinct()
        .count()
    )
    last = IngestRecord.objects.first()
    info: dict[str, Any] = {
        "newest_hour": _iso(newest),
        "lag_hours": _lag(newest, now),
        "newest_urma_hour": _iso(newest_urma),
        "urma_lag_hours": _lag(newest_urma, now),
        "missing_hours_7d": int((recent & (codes == 0)).sum()),
        "failed_jobs_24h": failed_jobs,
        "last_run": None
        if last is None
        else {"kind": last.kind, "status": last.status, "finished_at": last.finished_at.isoformat()},
    }
    stale = find_stale(data_dir).stale
    info["stale"] = stale
    problems = []
    if stale:
        problems.append("derived data from older code: run manage.py rebuild --stale")
    if info["lag_hours"] is None or info["lag_hours"] > MAX_LAG_HOURS:
        problems.append(f"newest hour more than {MAX_LAG_HOURS} h old")
    if info["urma_lag_hours"] is None or info["urma_lag_hours"] > MAX_URMA_LAG_HOURS:
        problems.append(f"newest URMA hour more than {MAX_URMA_LAG_HOURS} h old")
    if failed_jobs:
        problems.append(f"{failed_jobs} failed jobs in the last day")
    return info, problems


def _recent_sources(data_dir: Path, now: datetime) -> tuple[np.ndarray, np.ndarray] | None:
    """Each hour's UTC end (datetime64) and analysis source code (0: none), over this year and last."""
    times, codes, found = [], [], False
    for year in (now.year - 1, now.year):
        try:
            year_codes = GridStore.open(data_dir, HOURLY, year, VARIABLES.values()).read_meta("air_temperature.source")
            found = True
        except FileNotFoundError:
            year_codes = np.zeros(steps_in_year(year, "hour"), dtype=np.uint8)  # a year not started: all missing
        times.append(np.datetime64(f"{year}-01-01T00", "h") + np.arange(year_codes.size))
        codes.append(year_codes)
    return (np.concatenate(times), np.concatenate(codes)) if found else None


def _utc64(when: datetime) -> np.datetime64:
    return np.datetime64(when.astimezone(UTC).replace(tzinfo=None), "s")


def _last(times: np.ndarray, mask: np.ndarray) -> datetime | None:
    found = np.flatnonzero(mask)
    if found.size == 0:
        return None
    return datetime.fromisoformat(str(times[found[-1]].astype("datetime64[s]"))).replace(tzinfo=UTC)


def _lag(when: datetime | None, now: datetime) -> float | None:
    return None if when is None else round((now - when) / timedelta(hours=1), 1)


def _iso(when: datetime | None) -> str | None:
    return None if when is None else when.isoformat()
