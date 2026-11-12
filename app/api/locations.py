"""What `meta.location` says about a point (docs/api.md): the cell read, whether the archive covers it, and its time
zone, county and state; for daily answers, whose clock sets the days (D74). `/locate` (Phase 5 B) adds the cell's
corners and typical planting dates."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from django.conf import settings

from agdata import terrain
from agdata.grid import NDFD, service_window
from agdata.places import county_at
from agdata.timezones import GRID_ZONE, DayBasis, basis_zone, zone_at
from ops.points import day_basis


def days_text(zone: str, year: int) -> str:
    """What a day is on `zone`'s clock, with its hours in UTC, for `meta.location.days`."""
    if zone == GRID_ZONE:
        return "Midnight to midnight CST all year (06:00 to 06:00 UTC)."
    tz = ZoneInfo(zone)
    winter, summer = (datetime(year, month, 15, tzinfo=tz) for month in (1, 7))

    def utc(when: datetime) -> str:
        offset = when.utcoffset()
        hour = 0 if offset is None else int(-offset.total_seconds() // 3600) % 24
        return f"{hour:02d}:00 to {hour:02d}:00 UTC"

    if winter.utcoffset() == summer.utcoffset():
        return f"Midnight to midnight {winter.tzname()} ({utc(winter)})."
    return (
        f"Midnight to midnight local time: {winter.tzname()} ({utc(winter)}) in standard time and "
        f"{summer.tzname()} ({utc(summer)}) in daylight time."
    )


def describe_days(lat: float, lng: float, year: int, basis: DayBasis | None = None) -> dict[str, Any]:
    """`day_basis` (as resolved: `ops.points.day_basis`) and `days`, what a day is there."""
    found = day_basis(lat, lng, basis)
    return {"day_basis": found, "days": days_text(basis_zone(found, lat, lng), year)}


def describe(lat: float, lng: float) -> dict[str, Any]:
    """The point asked for, its NDFD cell (center rounded to 4 decimals, ~10 m) or None off the grid, `in_box`
    (inside the archive's window), its zone, county and state (None outside the US counties' grid), and from the
    terrain store (D6; None where it isn't built or has none) the point's elevation, its cell's mean elevation and
    the cell's share of open water. Nothing is moved: a cell mostly water is still the cell read."""
    found = NDFD.cell_of(lat, lng)
    cell = None
    if found is not None:
        center_lat, center_lng = (float(v) for v in NDFD.latlon(*found))
        cell = {"j": found[0], "i": found[1], "lat": round(center_lat, 4), "lng": round(center_lng, 4)}
    county = county_at(lat, lng)
    return {
        "lat": lat,
        "lng": lng,
        "cell": cell,
        "in_box": found is not None and service_window(settings.SERVICE_BOX).contains(*found),
        "timezone": zone_at(lat, lng),
        "county": county.name if county is not None else None,
        "state": county.state if county is not None else None,
        **_terrain(lat, lng, found),
    }


def _terrain(lat: float, lng: float, cell: tuple[int, int] | None) -> dict[str, Any]:
    found: dict[str, Any] = {"elevation_m": None, "cell_elevation_m": None, "water_percent": None}
    t = terrain.load(settings.DATA_DIR)
    if t is None or cell is None or not t.window.contains(*cell):
        return found
    j, i = cell
    y, x = j - t.window.j0, i - t.window.i0
    point = terrain.point_elevation(settings.DATA_DIR, lat, lng)
    mean = float(t.cells["elevation_mean"][y, x])
    found["elevation_m"] = None if point is None else round(point, 1)
    found["cell_elevation_m"] = None if np.isnan(mean) else round(mean, 1)
    found["water_percent"] = int(t.cells["water_share"][y, x])
    return found
