"""Weather at a point, wherever it comes from (docs/api.md, "Locations"): inside the box and the archive's years,
the archive and the forecast (`agdata.series`); outside, or before the archive, Open-Meteo through the per-cell
cache (`ops.openmeteo`), fetched in the request if the cache doesn't have it (CLAUDE.md's one exception).

`stamp` gives the ETag's data stamp before anything is read: the stores' write times for the archive, None for
Open-Meteo (its cache refetches recent days on a timer, so a 304 there could hold an answer the cache has since
replaced; those answers are computed each time, from the cache)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
from django.conf import settings

from agdata import series
from agdata.grid import NDFD
from agdata.timezones import zone_at
from ops import openmeteo
from ops.points import day_zone, in_archive

HOUR = timedelta(hours=1)


def from_archive(lat: float, lng: float, first: date, last: date) -> bool:
    return in_archive(lat, lng, first, last)


def stamp(
    points: list[tuple[float, float]], first: date, last: date, now: datetime, names: list[str] | None = None
) -> str | None:
    """The data stamp for reading days first..last at these points, or None if any comes from Open-Meteo. With
    `names` (the daily variables read), only the hours they're made from are stamped: opening a store for all 16
    hourly variables was half a point's stamp."""
    if not all(from_archive(lat, lng, first, last) for lat, lng in points):
        return None
    hourly = None if names is None else series.hourly_needed(names)
    return series.last_written(settings.DATA_DIR, first, last, now=now, hourly=hourly)


def days(
    lat: float,
    lng: float,
    first: date,
    last: date,
    names: list[str],
    now: datetime,
    stores: series.Stores | None = None,
    zone: str | None = None,
) -> series.DailySeries:
    """Days first..last at a point by `zone`'s clock (default `ops.points.day_zone`'s), each with its kind; sources
    and corrections on the series. Points read in one request share `stores` (`shared_stores`)."""
    zone = zone or day_zone(lat, lng)
    if from_archive(lat, lng, first, last):
        cell = NDFD.cell_of(lat, lng)
        assert cell is not None
        return series.point_days(settings.DATA_DIR, *cell, first, last, names, now=now, stores=stores, zone=zone)
    found = openmeteo.point_days(lat, lng, first, last, names, now, zone=zone)
    found.sources = ("openmeteo",)
    return found


def many_days(
    sites: list[tuple[float, float]],
    first: date,
    last: date,
    names: list[str],
    now: datetime,
    zones: list[str],
    stores: series.Stores | None = None,
) -> list[series.DailySeries]:
    """`days` at each point (each by its zone in `zones`): those the archive covers on one read of their cells
    (`series.cells_days`), the rest from Open-Meteo one by one."""
    found: list[series.DailySeries | None] = [None] * len(sites)
    inside = [k for k, (lat, lng) in enumerate(sites) if from_archive(lat, lng, first, last)]
    if inside:
        cells = [NDFD.cell_of(*sites[k]) for k in inside]
        batch = series.cells_days(
            settings.DATA_DIR,
            [c for c in cells if c is not None],
            first,
            last,
            names,
            now=now,
            stores=stores,
            zones=[zones[k] for k in inside],
        )
        for k, series_k in zip(inside, batch, strict=True):
            found[k] = series_k
    for k, (lat, lng) in enumerate(sites):
        if found[k] is None:
            found[k] = days(lat, lng, first, last, names, now, zone=zones[k])
    return [d for d in found if d is not None]


def shared_stores(names: list[str]) -> series.Stores:
    """One request's store opens, shared by its points."""
    return series.Stores(series.hourly_needed(names))


@dataclass(kw_only=True)
class Hours:
    times: list[datetime]
    values: dict[str, np.ndarray]
    kinds: list[str | None]
    zone: str
    sources: tuple[str, ...]
    corrections: tuple[str, ...]


def hours(
    lat: float,
    lng: float,
    start: datetime,
    end: datetime,
    names: list[str],
    now: datetime,
    stores: series.Stores | None = None,
) -> Hours:
    """Hours ending start..end (UTC) at a point; points read in one request share `stores` (opening `names`)."""
    if from_archive(lat, lng, start.date(), end.date()):
        cell = NDFD.cell_of(lat, lng)
        assert cell is not None
        frame = series.point_hours(settings.DATA_DIR, *cell, start, end, names, now=now, stores=stores)
        return _archive_hours(frame, (lat, lng), names)
    values, kinds, applied = openmeteo.cell_hours(lat, lng, start, end, now)
    n = (end - start) // HOUR + 1
    return Hours(
        times=[start + k * HOUR for k in range(n)],
        values={name: values.get(name, np.full(n, np.nan)) for name in names},
        kinds=kinds,
        zone=zone_at(lat, lng),
        sources=("openmeteo",),
        corrections=applied,
    )


def many_hours(
    sites: list[tuple[float, float]], start: datetime, end: datetime, names: list[str], now: datetime
) -> list[Hours]:
    """`hours` at each point: those the archive covers on one read of their cells (`series.cells_hours`)."""
    found: list[Hours | None] = [None] * len(sites)
    inside = [k for k, (lat, lng) in enumerate(sites) if from_archive(lat, lng, start.date(), end.date())]
    if inside:
        cells = [c for k in inside if (c := NDFD.cell_of(*sites[k])) is not None]
        frames = series.cells_hours(settings.DATA_DIR, cells, start, end, names, now=now)
        for k, frame in zip(inside, frames, strict=True):
            found[k] = _archive_hours(frame, sites[k], names)
    for k, (lat, lng) in enumerate(sites):
        if found[k] is None:
            found[k] = hours(lat, lng, start, end, names, now)
    return [h for h in found if h is not None]


def _archive_hours(frame: series.HourlyFrame, site: tuple[float, float], names: list[str]) -> Hours:
    seen = {s for sources in frame.sources.values() for s in sources if s is not None}
    return Hours(
        times=frame.times,
        values=frame.values,
        kinds=frame.kinds,
        zone=zone_at(*site),
        sources=series.source_order(seen),
        corrections=series.in_box_corrections(frame.kinds, frame.forecast, names),
    )


def hour_stamp(points: list[tuple[float, float]], start: datetime, end: datetime, now: datetime) -> str | None:
    if not all(from_archive(lat, lng, start.date(), end.date()) for lat, lng in points):
        return None
    return series.last_written(settings.DATA_DIR, start.date(), end.date(), now=now)


def keep(kinds: list[str | None], forecast: bool, trim_end: bool) -> int:
    """How many leading rows a series keeps: through its last observed one with `forecast=false`, else, when the
    end was a default, through its last with any data (a default end reaches past every forecast)."""
    if not forecast:
        return next((k + 1 for k in range(len(kinds) - 1, -1, -1) if kinds[k] == series.OBSERVED), 0)
    if trim_end:
        return next((k + 1 for k in range(len(kinds) - 1, -1, -1) if kinds[k] is not None), 0)
    return len(kinds)
