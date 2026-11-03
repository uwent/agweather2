"""Query parameters shared by every endpoint (docs/api.md, "Locations, times, units"), parsed and checked once.

Each group is a schema an endpoint takes as `Query[...]`, so Ninja documents its fields and Pydantic checks them.
v1's names for a longitude (`lon`, `long`, `longitude`, and `latitude` for `lat`) become `lng` and `lat` as the query
is parsed (`QueryParser`). A failed check names its parameter (`fail`), which `api.errors` reports
as `{code, param, message}`. What's computed from them (default dates, the canonical names) is echoed in
`meta.request` by the endpoint.
"""

import datetime as dt
from collections.abc import Mapping
from typing import Any, Literal, LiteralString

from django.http import HttpRequest
from django.utils.datastructures import MultiValueDict
from ninja import Field, Schema
from ninja.parser import Parser
from pydantic import PrivateAttr, model_validator
from pydantic_core import PydanticCustomError

from api.errors import ApiError

MAX_POINTS = 50  # per GET; more go by POST (docs/api.md)
ALIASES = {"lat": ("latitude",), "lng": ("lon", "long", "longitude")}


def fail(code: LiteralString, param: str | None, message: str) -> PydanticCustomError:
    """A failed check inside a schema, naming its parameter (`raise fail(...)`)."""
    return PydanticCustomError(code, "{message}", {"param": param, "message": message})


class QueryParser(Parser):
    """Ninja's parser, with v1's names for a point read as `lat` and `lng` (the canonical name wins if both are
    sent). Every API takes it (`NinjaAPI(parser=QueryParser())`)."""

    def parse_querydict(self, data: MultiValueDict, list_fields: list[str], request: HttpRequest) -> dict[str, Any]:
        result = super().parse_querydict(data, list_fields, request)
        for name, aliases in ALIASES.items():
            if result.get(name) in (None, ""):
                found = next((result[a] for a in aliases if result.get(a) not in (None, "")), None)
                if found is not None:
                    result[name] = found
        return result


class PointsQuery(Schema):
    """One point (`lat`, `lng`) or several (`points`)."""

    lat: float | None = Field(None, description="Latitude, decimal degrees (alias `latitude`)")
    lng: float | None = Field(
        None, description="Longitude, decimal degrees, west negative (aliases `lon`, `long`, `longitude`)"
    )
    points: str | None = Field(
        None, description=f"Several points as `lat,lng;lat,lng` (up to {MAX_POINTS}), in place of `lat` and `lng`"
    )
    _parsed: list[tuple[float, float]] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "PointsQuery":
        if self.points is not None:
            if self.lat is not None or self.lng is not None:
                raise fail("conflict", "points", "give either lat and lng, or points, not both")
            self._parsed = _parse_points(self.points)
            return self
        if self.lat is None or self.lng is None:
            missing = "lat" if self.lat is None else "lng"
            raise fail("missing", missing, "give a point as lat and lng (or several as points=lat,lng;lat,lng)")
        _check_point(self.lat, self.lng, "lat", "lng")
        self._parsed = [(self.lat, self.lng)]
        return self

    def locations(self) -> list[tuple[float, float]]:
        return list(self._parsed)

    def echo(self) -> dict[str, Any]:
        """For `meta.request`: `lat` and `lng`, or `points` as a list of [lat, lng]."""
        if self.points is not None:
            return {"points": [list(p) for p in self._parsed]}
        return {"lat": self.lat, "lng": self.lng}


def _parse_points(text: str) -> list[tuple[float, float]]:
    pairs = [p for p in text.replace(" ", "").split(";") if p]
    if not pairs:
        raise fail("missing", "points", "points is empty: give lat,lng pairs separated by ;")
    if len(pairs) > MAX_POINTS:
        raise fail("too_many", "points", f"{len(pairs)} points; up to {MAX_POINTS} per request (more by POST)")
    found = []
    for n, pair in enumerate(pairs, start=1):
        parts = pair.split(",")
        try:
            lat, lng = (float(v) for v in parts)
        except ValueError:
            raise fail("invalid", "points", f"point {n} ({pair!r}) isn't lat,lng") from None
        _check_point(lat, lng, "points", "points")
        found.append((lat, lng))
    return found


def _check_point(lat: float, lng: float, lat_param: str, lng_param: str) -> None:
    if not -90 <= lat <= 90:
        raise fail("out_of_range", lat_param, f"latitude {lat} isn't between -90 and 90")
    if not -180 <= lng <= 180:
        raise fail("out_of_range", lng_param, f"longitude {lng} isn't between -180 and 180")


class DaysQuery(Schema):
    """Local calendar days: one `date`, or `start` to `end` inclusive. Defaults are the endpoint's (`span`)."""

    date: dt.date | None = Field(None, description="One day (ISO, YYYY-MM-DD), in place of start and end")
    start: dt.date | None = Field(None, description="First day (ISO), inclusive; default January 1 of end's year")
    end: dt.date | None = Field(None, description="Last day (ISO), inclusive; default today")

    @model_validator(mode="after")
    def _check(self) -> "DaysQuery":
        if self.date is not None and (self.start is not None or self.end is not None):
            raise fail("conflict", "date", "give either date, or start and end, not both")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise fail("out_of_order", "start", f"start ({self.start}) is after end ({self.end})")
        return self

    def span(self, default_end: dt.date) -> tuple[dt.date, dt.date]:
        """(first, last): `date`, or `start`..`end` with end defaulting to `default_end` and start to January 1
        of end's year."""
        if self.date is not None:
            return self.date, self.date
        last = self.end or default_end
        first = self.start or dt.date(last.year, 1, 1)
        if first > last:
            raise ApiError("out_of_order", f"start ({first}) is after the default end ({last}); give end", "start")
        return first, last


class SeriesQuery(Schema):
    """How a series runs: through the forecast or not, gaps in running totals, and times' zone."""

    forecast: bool = Field(
        True, description="Run through the forecast (each row's kind says which); false: stop at the last observed day"
    )
    gaps: Literal["estimate", "missing"] = Field(
        "estimate", description="Cumulative values: bridge missing days with a flagged estimate, or leave them missing"
    )
    tz: Literal["utc", "local"] = Field("utc", description="Hourly times in UTC; local adds a local_time column")


class OutputQuery(Schema):
    """Units and format. A catalog variable's name as a parameter overrides its unit (`precipitation=mm`)."""

    units: Literal["us", "metric"] = Field(
        "us", description="Unit system: us (°F, in, mph) or metric (°C, mm, km/h); a variable's name overrides it"
    )
    format: str | None = Field(None, description="json (default) or csv, where offered; else from the Accept header")
    orient: Literal["columns", "records"] = Field(
        "columns", description="JSON data as an object of columns, or as an array of row objects"
    )
    headers: bool = Field(True, description="CSV: the meta lines (#) above the column names; false drops them")


def check_vars(raw: str | None, valid: Mapping[str, Any], default: list[str], param: str = "vars") -> list[str]:
    """A comma list of names from `valid` (a catalog), in the order given; `default` when not given."""
    if raw is None or not raw.strip():
        return list(default)
    names = [n.strip() for n in raw.split(",") if n.strip()]
    unknown = [n for n in names if n not in valid]
    if unknown:
        listed = ", ".join(valid)
        raise ApiError("unknown_variable", f"unknown {', '.join(unknown)}; valid names: {listed}", param)
    return list(dict.fromkeys(names))
