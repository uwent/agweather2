"""Keeping the archive current: the hourly job's refresh of recent hours, and the ingest records both it and the
backfill write (PLAN.md Phase 2 F)."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests
from django.utils import timezone

from agdata.cumulative import update_days
from agdata.grid import service_window
from agdata.ingest import BlockReport, Fetcher, fetch_hour, hour_runs, ingest_block, open_or_create_hourly, stale_hours
from agdata.sources.urma import URMA
from agdata.store import GridStore
from ops.models import IngestRecord

logger = logging.getLogger(__name__)

RECENT_DAYS = 7
HOUR = timedelta(hours=1)
SOURCE_SUMMARY = ("air_temperature", "precipitation", "shortwave_radiation")


def record_run(
    kind: IngestRecord.Kind,
    box: str,
    store: GridStore,
    first_hour: datetime,
    hours: int,
    started_at: datetime,
    report: BlockReport | None,
    error: str = "",
) -> IngestRecord:
    """Saves what an ingest run did; `report` is None when it raised (`error` says what)."""
    if report is None:
        status = IngestRecord.Status.FAILED
    elif report.failed or any(report.missing.values()):
        status = IngestRecord.Status.PARTIAL
    else:
        status = IngestRecord.Status.OK
    t0 = store.index_of(first_hour)
    sources = {}
    for name in SOURCE_SUMMARY:
        counts: dict[str, int] = {}
        for source in store.sources(name)[t0 : t0 + hours]:
            counts[source or "none"] = counts.get(source or "none", 0) + 1
        sources[name] = counts
    return IngestRecord.objects.create(
        kind=kind,
        status=status,
        box=box,
        first_hour=first_hour,
        hours=hours,
        started_at=started_at,
        finished_at=timezone.now(),
        failed_hours=[t.isoformat() for t in report.failed] if report else [],
        missing={k: v for k, v in report.missing.items() if v} if report else {},
        spikes={k: v for k, v in report.spikes.items() if v} if report else {},
        out_of_range={k: v for k, v in report.out_of_range.items() if v} if report else {},
        sources=sources,
        error=error,
    )


def refresh_recent(
    data_dir: Path,
    box: str,
    now: datetime,
    fetch: Fetcher = fetch_hour,
    urma_published: Callable[[datetime], bool] | None = None,
    workers: int = 4,
) -> list[IngestRecord]:
    """Fetches the last RECENT_DAYS days' missing, incomplete and replaceable RTMA hours, then rolls up the local
    days they touch. The caller holds the write lock."""
    window = service_window(box)
    if urma_published is None:
        session = requests.Session()
        urma_published = lambda when: URMA.has_hour(when, session)  # noqa: E731

    stop = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0) + HOUR  # the hour ending at or before now
    stale = stale_hours(data_dir, window, stop - timedelta(days=RECENT_DAYS), stop, urma_published)
    records = []
    for first, hours in hour_runs(stale):
        store = open_or_create_hourly(data_dir, first.year, window)
        started = timezone.now()
        try:
            report = ingest_block(store, first, hours, fetch=fetch, workers=workers)
        except Exception as error:
            logger.exception("ingesting %s +%d h failed", first, hours)
            records.append(record_run(IngestRecord.Kind.HOURLY, box, store, first, hours, started, None, repr(error)))
            continue
        records.append(record_run(IngestRecord.Kind.HOURLY, box, store, first, hours, started, report))
    if stale:
        # An hour belongs to the local day of its UTC date or the day before, in every US zone
        update_days(data_dir, window, (stale[0] - timedelta(days=1)).date(), stale[-1].date())
    logger.info("refreshed %d recent hours in %d runs", len(stale), len(records))
    return records
