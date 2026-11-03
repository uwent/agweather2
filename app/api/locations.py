"""What `meta.location` says about a point (docs/api.md): the cell read, whether the archive covers it, and its time
zone, county and state. `/locate` (Phase 5 B) adds the cell's corners and typical planting dates."""

from typing import Any

from django.conf import settings

from agdata.grid import NDFD, service_window
from agdata.places import county_at
from agdata.timezones import zone_at


def describe(lat: float, lng: float) -> dict[str, Any]:
    """The point asked for, its NDFD cell (center rounded to 4 decimals, ~10 m) or None off the grid, `in_box`
    (inside the archive's window), and its zone, county and state (None outside the US counties' grid)."""
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
    }
