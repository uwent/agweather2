"""Keeping the archive current: the hourly job's refresh of recent hours, the days rolled up from them when an
update is due (D108), and the ingest records both the job and the backfill write (Phase 2 F).

The hours are fetched and written every hour; the work that follows them (the days' statistics, the running
totals, chill portions, the models' ingredients and the forecast's restitch) costs about as much for one new hour
as for six, so it waits: the days behind their hours are rolled up when a grid day has all its hours but not its
values (soon after midnight CST), when an hour has waited UPDATE_EVERY, or before a forecast run is built. Points
read the hours themselves, so only maps wait.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import requests
from django.utils import timezone

from agdata.cumulative import update_days
from agdata.daily import open_or_create_daily
from agdata.grid import Window, service_window
from agdata.ingest import BlockReport, Fetcher, fetch_hour, hour_runs, ingest_block, open_or_create_hourly, stale_hours
from agdata.sources.urma import URMA
from agdata.store import DAILY, HOURLY, GridStore
from agdata.timezones import GRID_ZONE, day_bounds
from ops.models import IngestRecord

logger = logging.getLogger(__name__)

RECENT_DAYS = 7
HOUR = timedelta(hours=1)
UPDATE_EVERY = timedelta(hours=6)  # the longest an hour written waits for its day to be rolled up (D108)
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
        for source in store.sources(name, t0, t0 + hours):
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
    """Fetches and writes the last RECENT_DAYS days' missing, incomplete and replaceable RTMA hours; their days are
    rolled up later (`update_if_due`). The caller holds the write lock."""
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
    logger.info("refreshed %d recent hours in %d runs", len(stale), len(records))
    return records


@dataclass(frozen=True, kw_only=True)
class Behind:
    """The recent grid days whose hours were written after the day was last rolled up."""

    days: list[date]
    waiting_since: datetime | None  # when the oldest hour still waiting was written
    ended: date | None  # the newest of them with all its hours in and no values yet: a day just over

    def due(self, now: datetime) -> bool:
        """Whether to roll them up now: a day is over, or an hour has waited UPDATE_EVERY."""
        if not self.days:
            return False
        return self.ended is not None or (self.waiting_since is not None and now - self.waiting_since >= UPDATE_EVERY)


def behind(data_dir: Path, window: Window, now: datetime) -> Behind:
    """The last RECENT_DAYS + 1 grid days through today's, compared by write time: each day's hours (any of the
    analysis, precipitation and shortwave, as `stale_hours` reads them) against its daily statistics."""
    hours = _HourStamps(data_dir, window)
    today = now.astimezone(ZoneInfo(GRID_ZONE)).date()
    days, waiting, ended = [], [], None
    for k in range(RECENT_DAYS + 1, -1, -1):
        day = today - timedelta(days=k)
        first, last = day_bounds(day, GRID_ZONE)
        stamps = hours.between(first, last)  # (hours, names)
        newest = np.nanmax(stamps) if np.isfinite(stamps).any() else None
        if newest is None:
            continue
        daily = _daily(data_dir, window, day.year)
        t = daily.index_of(day) if daily is not None else 0
        rolled = daily.written("air_temperature_max", t, t + 1) if daily is not None else None
        if rolled is not None and newest <= rolled:
            continue
        days.append(day)
        newer = stamps[stamps > rolled] if rolled is not None else stamps[np.isfinite(stamps)]
        waiting.append(float(newer.min()))
        has_values = daily is not None and daily.sources("air_temperature_min", t, t + 1)[0] is not None
        if day < today and np.isfinite(stamps).all() and not has_values:
            ended = day
    since = datetime.fromtimestamp(min(waiting), UTC) if waiting else None
    return Behind(days=days, waiting_since=since, ended=ended)


def update_if_due(data_dir: Path, box: str, now: datetime, force: bool = False) -> list[date]:
    """Rolls up the days behind their hours if an update is due (`Behind.due`), or whenever any are with `force`
    (before a forecast run is built); returns the days rolled up. The caller holds the write lock."""
    window = service_window(box)
    found = behind(data_dir, window, now)
    if not found.days or not (force or found.due(now)):
        return []
    update_days(data_dir, window, found.days[0], found.days[-1])
    logger.info("rolled up %s to %s (%d days behind their hours)", found.days[0], found.days[-1], len(found.days))
    return found.days


class _HourStamps:
    """When each recent hour was written, by the hourly stores' `_meta` (a year's array read once)."""

    def __init__(self, data_dir: Path, window: Window):
        self.data_dir, self.window = data_dir, window
        self.years: dict[int, np.ndarray | None] = {}

    def between(self, first: datetime, last: datetime) -> np.ndarray:
        """(hours first..last, names): each hour's write time per name, NaN where never written."""
        times = [first + k * HOUR for k in range(int((last - first) / HOUR) + 1)]
        out = np.full((len(times), len(SOURCE_SUMMARY)), np.nan)
        for row, t in enumerate(times):
            stamps = self._year(t.year)
            if stamps is not None:
                out[row] = stamps[:, int((t - datetime(t.year, 1, 1, tzinfo=UTC)) / HOUR)]
        return out

    def _year(self, year: int) -> np.ndarray | None:
        if year not in self.years:
            if not HOURLY.path(self.data_dir, year).exists():
                self.years[year] = None
            else:
                store = GridStore.open(self.data_dir, HOURLY, year, [])
                self.years[year] = np.stack([store.read_meta(f"{name}.written") for name in SOURCE_SUMMARY])
        return self.years[year]


def _daily(data_dir: Path, window: Window, year: int) -> GridStore | None:
    return open_or_create_daily(data_dir, year, window) if DAILY.path(data_dir, year).exists() else None
