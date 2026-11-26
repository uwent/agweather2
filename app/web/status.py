"""The shared `status` prop (D117): how current the data are, for every page's "data through" line and the
stale-data banner.

Read from `ops.models.DatasetStatus`, which every write to the archive refreshes, so no store is opened; the rows
are kept for `TTL` so a burst of page views costs one query. A new install with no rows yet says nothing rather than
reading the stores (that's `/api/v2/status`'s job).
"""

import threading
import time
from datetime import UTC, datetime, timedelta

from django.conf import settings

from agdata.series import MAX_RUN_AGE
from ops.points import fallback_on
from web.props import Behind, DataStatus

# Seconds a read of the rows is kept; none in tests, which change the rows between requests
TTL = 0.0 if settings.TESTING else 30.0

# Past these, a page says the data are behind. Looser than `/up`'s alarms (ops.health): the analyses come out an
# hour or two after the hour, and URMA's about 6 hours, so a banner only shows when something is really late.
OBSERVED_LAG = timedelta(hours=6)
# Each source of observed hours, and how far behind it normally runs before it counts as late
SOURCE_LAG = {"rtma": timedelta(hours=4), "urma": timedelta(hours=14), "hrrr": timedelta(hours=4)}

_lock = threading.Lock()
_kept: tuple[float, DataStatus | None] | None = None


def clear() -> None:
    """Forgets the kept read (tests, after changing the rows)."""
    global _kept
    with _lock:
        _kept = None


def data_status(now: datetime | None = None) -> DataStatus | None:
    """The status, kept for `TTL` seconds; None when the rows haven't been written yet."""
    global _kept
    clock = time.monotonic()
    with _lock:
        if _kept is not None and clock - _kept[0] < TTL:
            return _kept[1]
    found = read_status(now or datetime.now(UTC))
    with _lock:
        _kept = (clock, found)
    return found


def read_status(now: datetime) -> DataStatus | None:
    from ops.models import DatasetStatus

    rows = {row.dataset: row for row in DatasetStatus.objects.all()}
    hourly, daily, run = rows.get("hourly"), rows.get("daily"), rows.get("forecast")
    if hourly is None:
        return None
    observed = hourly.last
    behind: list[Behind] = []
    if observed is None or now - observed > OBSERVED_LAG:
        behind.append("observed")
    cycle = run.first if run is not None else None
    in_use = cycle is not None and now - cycle <= MAX_RUN_AGE
    if not in_use:
        behind.append("forecast")
    stale_sources = []
    for source, lag in SOURCE_LAG.items():
        last = hourly.last_by_source.get(source)
        if last is not None and now - datetime.fromisoformat(last) > lag:
            stale_sources.append(source)
    return DataStatus(
        observed_through=observed,
        daily_through=daily.last.date() if daily is not None and daily.last is not None else None,
        forecast_cycle=cycle,
        forecast_through=run.last if run is not None else None,
        forecast_fallback="openmeteo" if not in_use and fallback_on() else None,
        behind=behind,
        stale_sources=stale_sources,
    )
