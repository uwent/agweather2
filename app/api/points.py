"""Weather at a point, wherever it comes from (docs/api.md, "Locations"): inside the box and the archive's years,
the archive and the forecast (`agdata.series`); outside, or before the archive, Open-Meteo through the per-cell
cache (`ops.openmeteo`), fetched in the request if the cache doesn't have it (CLAUDE.md's one exception).

Inside the box, while our forecast is stale or missing, a point's forecast comes from Open-Meteo too (D114,
`ops.points.forecast_filler`), and `forecast_warnings` says so.

`stamp` gives the ETag's data stamp before anything is read: the stores' write times for the archive, None for
Open-Meteo (its cache refetches recent days on a timer, so a 304 there could hold an answer the cache has since
replaced; those answers are computed each time, from the cache), and None for the archive's points too while their
forecast would come from it."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import numpy as np
from django.conf import settings

from agdata import computed, series
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.timezones import zone_at
from api import clock
from ops import openmeteo
from ops.points import AreaAsk, FallbackBudget, day_zone, fallback_on, forecast_filler, in_archive, place_at

HOUR = timedelta(hours=1)

# meta.warnings for a series in the box whose forecast isn't ours (D114; `forecast_warnings`)
STALE_FALLBACK = "Our forecast hasn't been updated for more than 12 hours, so the forecast for this location comes from Open-Meteo until ours is current again. Our maps show no forecast until then."
STALE_UNAVAILABLE = "Our forecast hasn't been updated for more than 12 hours, and we couldn't reach Open-Meteo for a replacement, so the series ends with the last observed day. Please try again in a few minutes."
STALE = "The forecast is out of date, so the series ends with the last observed day."
SOIL_UNAVAILABLE = "We couldn't reach Open-Meteo for the soil forecast beyond our own, so the soil values end before the rest of the forecast. Please try again in a few minutes."


def forecast_warnings(forecasts: Iterable[series.Forecast | None], forecast_asked: bool) -> list[str]:
    """The warnings for the forecasts a request's series came with (`series.Forecast`, one per series or model run):
    Open-Meteo standing in for our stale forecast, or not reachable for it (D114), or for the soil past our run's."""
    if not forecast_asked:
        return []
    found: list[str] = []
    for f in forecasts:
        if f is None:
            continue
        if f.fallback == series.OPENMETEO:
            text = STALE_FALLBACK
        elif f.fallback == series.UNAVAILABLE:
            text = STALE_UNAVAILABLE
        elif f.reason == "stale":
            text = STALE
        elif f.soil_unavailable:
            text = SOIL_UNAVAILABLE
        else:
            continue
        if text not in found:
            found.append(text)
    return found


def _fallback_reads(first: date, last: date, now: datetime) -> bool:
    """Whether a read of days first..last in the box may take Open-Meteo's forecast now (D114): the fallback is on,
    our run isn't in use, and the days reach the forecast endpoint's (a week back)."""
    if not fallback_on() or last < now.date() - timedelta(days=7):
        return False
    return series.current_forecast(settings.DATA_DIR, now).path is None


def from_archive(lat: float, lng: float, first: date, last: date) -> bool:
    """Whether the archive serves days first..last at a point: in the box, and a daily store for each year through
    today's (days after today have no data from anywhere, so a season next year, to be projected, reads here too)."""
    return in_archive(lat, lng, first, min(last, clock.now().date()))


def stamp(
    points: list[tuple[float, float]],
    first: date,
    last: date,
    now: datetime,
    names: list[str] | None = None,
    past_years: list[int] | None = None,
    area: AreaAsk | None = None,
) -> str | None:
    """The data stamp for reading days first..last at these points, or None if any comes from Open-Meteo. With
    `names` (the daily variables read), only the hours they're made from are stamped: opening a store for all 16
    hourly variables was half a point's stamp. `past_years` adds a projection's reads of those years (with `names`;
    `series.past_years_stamp`): an attribute a year from the past-years copies, where stamping each year's hours
    read ~100 arrays over ten years (0.21 s)."""
    if not all(from_archive(lat, lng, first, last) for lat, lng in points) or _fallback_reads(first, last, now):
        return None
    hourly = None if names is None else series.hourly_needed(names)
    found = series.last_written(settings.DATA_DIR, first, last, now=now, hourly=hourly)
    if past_years:
        cells = (
            [cell for lat, lng in points if (cell := NDFD.cell_of(lat, lng)) is not None]
            if area is None
            else [cell for lat, lng in points for cell in area.at(lat, lng).cells]
        )
        found += "|" + series.past_years_stamp(
            settings.DATA_DIR, cells=cells, years=past_years, names=names or list(DAILY_VARIABLES), now=now
        )
    return found


def days(
    lat: float,
    lng: float,
    first: date,
    last: date,
    names: list[str],
    now: datetime,
    stores: series.Stores | None = None,
    zone: str | None = None,
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> series.DailySeries:
    """Days first..last at a point by `zone`'s clock (default `ops.points.day_zone`'s), each with its kind; sources
    and corrections on the series. Points read in one request share `stores` (`shared_stores`) and `budget`."""
    zone = zone or day_zone(lat, lng)
    if from_archive(lat, lng, first, last):
        cell = NDFD.cell_of(lat, lng)
        assert cell is not None
        return series.point_days(
            settings.DATA_DIR,
            *cell,
            first,
            last,
            names,
            now=now,
            stores=stores,
            zone=zone,
            area=area.at(lat, lng) if area is not None else None,
            fill_forecast=forecast_filler(lat, lng, now, budget or FallbackBudget()),
        )
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
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> list[series.DailySeries]:
    """`days` at each point (each by its zone in `zones`): those the archive covers on one read of their cells
    (`series.cells_days`), the rest from Open-Meteo one by one."""
    budget = budget or FallbackBudget()
    found: list[series.DailySeries | None] = [None] * len(sites)
    inside = [k for k, (lat, lng) in enumerate(sites) if from_archive(lat, lng, first, last)]
    if inside:
        batch = series.cells_days(
            settings.DATA_DIR,
            [place_at(*sites[k], area) for k in inside],
            first,
            last,
            names,
            now=now,
            stores=stores,
            zones=[zones[k] for k in inside],
            fill_forecast=[forecast_filler(*sites[k], now, budget) for k in inside],
        )
        for k, series_k in zip(inside, batch, strict=True):
            found[k] = series_k
    for k, (lat, lng) in enumerate(sites):
        if found[k] is None:
            found[k] = days(lat, lng, first, last, names, now, zone=zones[k], area=area)
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
    forecast: series.Forecast | None = field(default=None)  # in the box, the forecast the hours came with


def hours(
    lat: float,
    lng: float,
    start: datetime,
    end: datetime,
    names: list[str],
    now: datetime,
    stores: series.Stores | None = None,
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> Hours:
    """Hours ending start..end (UTC) at a point; points read in one request share `stores` (opening `names`) and
    `budget`."""
    if from_archive(lat, lng, start.date(), end.date()):
        cell = NDFD.cell_of(lat, lng)
        assert cell is not None
        frame = series.point_hours(
            settings.DATA_DIR,
            *cell,
            start,
            end,
            names,
            now=now,
            stores=stores,
            area=area.at(lat, lng) if area is not None else None,
            fill_forecast=forecast_filler(lat, lng, now, budget or FallbackBudget()),
        )
        return _archive_hours(frame, (lat, lng), names)
    values, kinds, applied = openmeteo.cell_hours(lat, lng, start, end, now)
    n = (end - start) // HOUR + 1
    read = computed.expand(names, computed.HOURLY_COMPUTED)
    found = {name: values.get(name, np.full(n, np.nan)) for name in read}
    return Hours(
        times=[start + k * HOUR for k in range(n)],
        values=computed.complete(found, names, computed.HOURLY_COMPUTED),
        kinds=kinds,
        zone=zone_at(lat, lng),
        sources=("openmeteo",),
        corrections=applied,
    )


def many_hours(
    sites: list[tuple[float, float]],
    start: datetime,
    end: datetime,
    names: list[str],
    now: datetime,
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> list[Hours]:
    """`hours` at each point: those the archive covers on one read of their cells (`series.cells_hours`)."""
    budget = budget or FallbackBudget()
    found: list[Hours | None] = [None] * len(sites)
    inside = [k for k, (lat, lng) in enumerate(sites) if from_archive(lat, lng, start.date(), end.date())]
    if inside:
        places = [place_at(*sites[k], area) for k in inside]
        fallbacks = [forecast_filler(*sites[k], now, budget) for k in inside]
        frames = series.cells_hours(settings.DATA_DIR, places, start, end, names, now=now, fill_forecast=fallbacks)
        for k, frame in zip(inside, frames, strict=True):
            found[k] = _archive_hours(frame, sites[k], names)
    for k, (lat, lng) in enumerate(sites):
        if found[k] is None:
            found[k] = hours(lat, lng, start, end, names, now, area=area)
    return [h for h in found if h is not None]


def _archive_hours(frame: series.HourlyFrame, site: tuple[float, float], names: list[str]) -> Hours:
    seen = {s for sources in frame.sources.values() for s in sources if s is not None}
    return Hours(
        times=frame.times,
        values=frame.values,
        kinds=frame.kinds,
        zone=zone_at(*site),
        sources=series.source_order(seen),
        corrections=series.in_box_corrections(
            frame.kinds, frame.forecast, computed.expand(names, computed.HOURLY_COMPUTED)
        ),
        forecast=frame.forecast,
    )


def hour_stamp(points: list[tuple[float, float]], start: datetime, end: datetime, now: datetime) -> str | None:
    if not all(from_archive(lat, lng, start.date(), end.date()) for lat, lng in points):
        return None
    if _fallback_reads(start.date(), end.astimezone(UTC).date(), now):
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
