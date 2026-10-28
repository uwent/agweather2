"""Each cell's time zone, for local calendar days (PLAN.md §5.4).

Looked up once per window from timezonefinder's bundled boundaries (offline), which split the Great Lakes along
state and national lines. Cells outside every zone (open ocean) take a fixed offset from their longitude.
Zones that share a UTC offset on a day are rolled up together, so a day costs one pass per distinct offset.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from timezonefinder import TimezoneFinder

from agdata.grid import NDFD, Window


def window_timezones(window: Window) -> tuple[list[str], np.ndarray]:
    """The zone names in a window and each cell's index into them, (y, x) uint8."""
    lat, lon = NDFD.window_latlon(window)
    finder = TimezoneFinder()
    names: dict[str, int] = {}
    index = np.zeros(window.shape, dtype=np.uint8)
    for (y, x), la, lo in zip(np.ndindex(window.shape), lat.ravel(), lon.ravel(), strict=True):
        zone = finder.timezone_at(lng=float(lo), lat=float(la)) or _fixed_zone(float(lo))
        index[y, x] = names.setdefault(zone, len(names))
    return list(names), index


def day_bounds(day: date, zone: str) -> tuple[datetime, datetime]:
    """The UTC times of a local day's first and last hour ends: (local midnight + 1 h, next local midnight].

    An hourly value at t covers the hour ending at t, so the day's hours end at local 01:00 … 24:00 (23 or 25
    of them on daylight-saving changes).
    """
    tz = ZoneInfo(zone)
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(UTC)
    nxt = day + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz).astimezone(UTC)
    return start + timedelta(hours=1), end


def _fixed_zone(lon: float) -> str:
    hours = round(-lon / 15)
    return "Etc/GMT" + (f"+{hours}" if hours > 0 else f"-{-hours}" if hours < 0 else "")  # POSIX sign: west is +
