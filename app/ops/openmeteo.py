"""Open-Meteo hours for points outside the box or before the archive, through the per-cell cache (D42). CLAUDE.md's
one exception to fetching weather only in jobs: a request may fill a cell's cache."""

import io
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

import numpy as np
import requests
from django.conf import settings

from agdata.point import daily_at_point
from agdata.series import FORECAST, OBSERVED, DailySeries, day_kinds
from agdata.sources import openmeteo
from agdata.timezones import zone_at
from ops.models import WeatherCellCache

HOUR = timedelta(hours=1)
FORECAST_TTL = timedelta(hours=3)
RECENT_TTL = timedelta(days=1)


def spans(first: date, last: date, today: date) -> list[tuple[str, date, date]]:
    """The cache spans covering UTC days first..last: whole months of history (to the day before the forecast's
    reach), then the forecast endpoint's span, as (endpoint, first day, last day)."""
    recent = today - timedelta(days=openmeteo.RECENT_DAYS)
    out: list[tuple[str, date, date]] = []
    month = date(first.year, first.month, 1)
    while month < recent and month <= last:
        following = date(month.year + month.month // 12, month.month % 12 + 1, 1)
        end = min(following - timedelta(days=1), recent - timedelta(days=1))
        out.append((openmeteo.endpoint_for(month, today), month, end))
        month = following
    if last >= recent:
        out.append(("forecast", recent, today + timedelta(days=openmeteo.FORECAST_DAYS - 1)))
    return out


def cell_hours(
    latitude: float, longitude: float, start: datetime, end: datetime, now: datetime, session=None
) -> tuple[dict[str, np.ndarray], list[str | None], tuple[str, ...]]:
    """Each catalog variable's hours ending start..end (UTC, inclusive) at the point's O1280 cell, each hour's kind
    (observed up to `now`, forecast after, None past the forecast), and the corrections applied (D51; the cache
    keeps Open-Meteo's values, corrected as they're read), filling the cache as needed."""
    cell = openmeteo.cell_for(latitude, longitude)
    session = session or requests.Session()
    n = (end - start) // HOUR + 1
    values: dict[str, np.ndarray] = {}
    reached = start - HOUR
    applied: list[str] = []
    for endpoint, first, last in spans((start - HOUR).date(), end.date(), now.date()):
        hours = openmeteo.correct(_cached(cell, endpoint, first, last, now, session), cell, endpoint)
        applied += [c for c in hours.corrections if c not in applied]
        k0 = (hours.start - start) // HOUR
        for name, series in hours.values.items():
            target = values.setdefault(name, np.full(n, np.nan))
            lo, hi = max(0, k0), min(n, k0 + len(series))
            if hi > lo:
                target[lo:hi] = series[lo - k0 : hi - k0]
        reached = max(reached, hours.start + (hours.count - 1) * HOUR)
    times = [start + k * HOUR for k in range(n)]
    kinds = [None if t > reached else (OBSERVED if t <= now else FORECAST) for t in times]
    return values, kinds, tuple(applied)


def point_days(
    latitude: float, longitude: float, first: date, last: date, names: list[str], now: datetime, session=None
) -> DailySeries:
    """Local days first..last at a point from Open-Meteo, by the rollup's definitions (`daily_at_point`)."""
    zone = zone_at(latitude, longitude)
    start = datetime(first.year, first.month, first.day, tzinfo=UTC) - timedelta(days=1)
    end = datetime(last.year, last.month, last.day, tzinfo=UTC) + timedelta(days=1, hours=8)
    values, kinds, applied = cell_hours(latitude, longitude, start, end, now, session)
    days = daily_at_point(start, values, zone, first, last)
    dates = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    times = [start + k * HOUR for k in range(len(kinds))]
    from agdata.series import Forecast

    return DailySeries(
        dates=dates,
        values={name: days[name] for name in names},
        kinds=day_kinds(times, kinds, zone, dates),
        forecast=Forecast(path=None, reason="openmeteo"),
        zone=zone,
        corrections=applied,
    )


def _cached(cell, endpoint: str, first: date, last: date, now: datetime, session) -> openmeteo.Hours:
    row = WeatherCellCache.objects.filter(cell=cell.key, endpoint=endpoint, first_day=first).first()
    if row is not None and row.last_day >= last and (row.expires_at is None or row.expires_at > now):
        return _unpack(bytes(row.data))
    hours, calls = openmeteo.fetch(endpoint, cell, first, last, session, getattr(settings, "OPEN_METEO_API_KEY", None))
    if endpoint == "forecast":
        expires = now + FORECAST_TTL
        WeatherCellCache.objects.filter(cell=cell.key, endpoint="forecast").exclude(first_day=first).delete()
    elif last >= now.date() - timedelta(days=openmeteo.RECENT_DAYS + 1) or (last.day < 28 and last.month == now.month):
        expires = now + RECENT_TTL  # a month not yet over, or its last days still settling
    else:
        expires = None
    WeatherCellCache.objects.update_or_create(
        cell=cell.key,
        endpoint=endpoint,
        first_day=first,
        defaults={
            "last_day": last,
            "fetched_at": now,
            "expires_at": expires,
            "calls": calls,
            "data": _pack(hours),
        },
    )
    return hours


def _pack(hours: openmeteo.Hours) -> bytes:
    buffer = io.BytesIO()
    arrays = {name: values.astype(np.float32) for name, values in hours.values.items()}
    arrays["_start"] = np.array(int(hours.start.timestamp()))
    np.savez_compressed(buffer, **cast(dict[str, Any], arrays))  # pyright reads the names as savez's flags
    return buffer.getvalue()


def _unpack(data: bytes) -> openmeteo.Hours:
    with np.load(io.BytesIO(data)) as z:
        start = datetime.fromtimestamp(int(z["_start"]), UTC)
        values = {name: z[name].astype(float) for name in z.files if name != "_start"}
    return openmeteo.Hours(start=start, values=values)
