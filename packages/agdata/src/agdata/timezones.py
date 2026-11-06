"""Which hours make a day (PLAN.md §5.4, D74).

Grid days are Central Standard Time all year (`GRID_ZONE`, UTC−6 with no daylight saving): every cell shares one
day, so no map can show a time zone line, and every day has 24 hours. Points follow the grid's days inside the box and
their own zone outside it, and an API request can choose (`day_basis`: `central` or `local`). A day basis is a zone
name, so the windows below take either.

A point's own zone comes from timezonefinder's bundled boundaries (offline), which split the Great Lakes along state
and national lines; a point outside every zone (open ocean) takes a fixed offset from its longitude.
"""

from datetime import UTC, date, datetime, timedelta
from functools import cache
from typing import Literal
from zoneinfo import ZoneInfo

import numpy as np
from timezonefinder import TimezoneFinder

from agdata.grid import NDFD, Window
from agmodels.features import EVENING_HOUR, OVERNIGHT_HOUR

GRID_ZONE = "Etc/GMT+6"  # CST all year (POSIX sign: west is +)
DayBasis = Literal["central", "local"]
HOUR = timedelta(hours=1)


def window_timezones(window: Window) -> tuple[list[str], np.ndarray]:
    """The zone names in a window and each cell's index into them, (y, x) uint8."""
    lat, lon = NDFD.window_latlon(window)
    finder = _finder()
    names: dict[str, int] = {}
    index = np.zeros(window.shape, dtype=np.uint8)
    for (y, x), la, lo in zip(np.ndindex(window.shape), lat.ravel(), lon.ravel(), strict=True):
        zone = finder.timezone_at(lng=float(lo), lat=float(la)) or _fixed_zone(float(lo))
        index[y, x] = names.setdefault(zone, len(names))
    return list(names), index


@cache
def _finder() -> TimezoneFinder:
    return TimezoneFinder()  # loads its polygons once, not on every point request


def zone_at(latitude: float, longitude: float) -> str:
    """A point's time zone, as `window_timezones` finds a cell's."""
    return _finder().timezone_at(lng=longitude, lat=latitude) or _fixed_zone(longitude)


def basis_zone(basis: DayBasis, latitude: float, longitude: float) -> str:
    """The zone whose clock sets a point's days: the grid's for `central`, the point's own for `local`."""
    return GRID_ZONE if basis == "central" else zone_at(latitude, longitude)


def window_bounds(day: date, zone: str, end_hour: int) -> tuple[datetime, datetime]:
    """The UTC stamps of the first and last readings of a day's window that ends at clock hour `end_hour` (24 for
    midnight): the readings stamped after that hour the day before, through it on `day`. An hourly value at t is
    the hour ending at t (precipitation) or the reading at t, so a calendar day is readings 01:00 … 24:00. With a zone
    that keeps daylight saving, a window across a change has 23 or 25 readings."""
    tz = ZoneInfo(zone)

    def at(d: date, hour: int) -> datetime:
        d += timedelta(days=hour // 24)
        return datetime(d.year, d.month, d.day, hour % 24, tzinfo=tz).astimezone(UTC)

    return at(day - timedelta(days=1), end_hour) + HOUR, at(day, end_hour)


def day_bounds(day: date, zone: str) -> tuple[datetime, datetime]:
    """A calendar day: midnight to midnight (readings 01:00 … 24:00)."""
    return window_bounds(day, zone, 24)


def evening_bounds(day: date, zone: str) -> tuple[datetime, datetime]:
    """The day from 6 pm: 6 pm the evening before to 6 pm (readings 19:00 … 18:00)."""
    return window_bounds(day, zone, EVENING_HOUR)


def overnight_bounds(day: date, zone: str) -> tuple[datetime, datetime]:
    """Noon the day before to noon (readings 13:00 … 12:00), for the overnight minimum."""
    return window_bounds(day, zone, OVERNIGHT_HOUR)


def first_reading(day: date, zone: str) -> datetime:
    """The earliest reading any of a day's windows reads (the overnight window's first)."""
    return overnight_bounds(day, zone)[0]


def _fixed_zone(lon: float) -> str:
    hours = round(-lon / 15)
    return "Etc/GMT" + (f"+{hours}" if hours > 0 else f"-{-hours}" if hours < 0 else "")  # POSIX sign: west is +
