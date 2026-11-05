"""Query parameters shared by every endpoint (docs/api.md, "Locations, times, units"), parsed and checked once.

Each group is a schema an endpoint takes as `Query[...]`, so Ninja documents its fields and Pydantic checks them.
v1's names for a longitude (`lon`, `long`, `longitude`, and `latitude` for `lat`) become `lng` and `lat` as the query
is parsed (`QueryParser`). A failed check names its parameter (`fail`), which `api.errors` reports
as `{code, param, message}`. What's computed from them (default dates, the canonical names) is echoed in
`meta.request` by the endpoint.
"""

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, LiteralString

from django.http import HttpRequest
from django.utils.datastructures import MultiValueDict
from ninja import Schema
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

    lat: float | None = None
    lng: float | None = None
    points: str | None = None
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

    date: dt.date | None = None
    start: dt.date | None = None
    end: dt.date | None = None

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

    forecast: bool = True
    gaps: Literal["estimate", "missing"] = "estimate"
    tz: Literal["utc", "local"] = "utc"


class UnitsQuery(Schema):
    """The unit system; a catalog variable's name as a parameter overrides its unit (`precipitation=mm`)."""

    units: Literal["us", "metric"] = "us"


class OutputQuery(UnitsQuery):
    """Units and format, for endpoints that return a table."""

    format: str | None = None  # json (default), csv, and where offered netcdf or geotiff; else from Accept
    orient: Literal["columns", "records"] = "columns"
    headers: bool = True  # CSV: the meta lines (#) above the column names


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


class HoursQuery(Schema):
    """Hours by their UTC end, `start` to `end` inclusive: ISO times on the hour, with a zone (`Z`, `-05:00`) or
    taken as UTC; a bare date means its 00Z. Defaults are the endpoint's (`span`)."""

    start: dt.datetime | None = None
    end: dt.datetime | None = None

    @model_validator(mode="after")
    def _check(self) -> "HoursQuery":
        for name in ("start", "end"):
            value = getattr(self, name)
            if value is None:
                continue
            value = value.replace(tzinfo=dt.UTC) if value.tzinfo is None else value.astimezone(dt.UTC)
            if value.minute or value.second or value.microsecond:
                raise fail("invalid", name, f"{name} ({value:%Y-%m-%dT%H:%M}Z) isn't on the hour")
            setattr(self, name, value)
        if self.start is not None and self.end is not None and self.start > self.end:
            raise fail(
                "out_of_order", "start", f"start ({self.start:%Y-%m-%dT%H}Z) is after end ({self.end:%Y-%m-%dT%H}Z)"
            )
        return self

    def span(self, default_start: dt.datetime, default_end: dt.datetime) -> tuple[dt.datetime, dt.datetime]:
        first, last = self.start or default_start, self.end or default_end
        if first > last:
            raise ApiError("out_of_order", f"start ({first:%Y-%m-%dT%H}Z) is after end ({last:%Y-%m-%dT%H}Z)", "start")
        return first, last


# --- Thresholds ------------------------------------------------------------------------------------------------
#
# A temperature threshold is given in the request's units (`units=us`: °F, `metric`: °C) and checked in two tiers:
# one no stored temperature can cross is refused (the catalog's QC range for air temperature, so the limits follow
# what the archive can hold), and one outside the range such settings normally take runs with a warning. The usual
# ranges (°F) are wider than the models' own (degree-day bases 39.2–55, uppers 75–92).


@dataclass(frozen=True, kw_only=True)
class Bracket:
    what: str  # "a degree-day base", for messages
    usual_f: tuple[float, float]
    reason: str  # why that's usual, for the API docs


DD_BASE = Bracket(what="a degree-day base", usual_f=(32, 60), reason="crop and insect bases run 39–55 °F")
DD_UPPER = Bracket(what="a degree-day upper threshold", usual_f=(70, 95), reason="upper cutoffs run 75–92 °F")
FREEZE = Bracket(what="a freeze threshold", usual_f=(20, 36), reason="freeze and frost thresholds run 24–32 °F")
# With metric units, a value above these looks like °F given as °C (50 °C is a hot day's air, not a base)
LOOKS_LIKE_F_IN_C = {DD_BASE: 30, DD_UPPER: 45, FREEZE: 10}


def temperature_threshold(value: float, units: str, bracket: Bracket, param: str, warnings: list[str]) -> float:
    """A threshold in the request's units → °F, refused (422) if no stored temperature can reach it, with a warning
    added if it's unusual or looks like the other unit."""
    from agdata.catalog import VARIABLES
    from agdata.units import convert

    unit = "degC" if units == "metric" else "degF"
    label = "°C" if units == "metric" else "°F"
    air = VARIABLES["air_temperature"]
    lowest, highest = (convert(v, "degC", unit) for v in (air.valid_min, air.valid_max))
    if not lowest <= value <= highest:
        raise ApiError(
            "out_of_range",
            f"{bracket.what} of {value:g} {label} can't be reached: stored air temperatures run "
            f"{lowest:g} to {highest:g} {label}",
            param,
        )
    value_f = convert(value, unit, "degF")
    lo, hi = bracket.usual_f
    if units == "metric" and value > LOOKS_LIKE_F_IN_C[bracket]:
        warnings.append(
            f"{param}: {bracket.what} of {value:g} °C is {value_f:g} °F; thresholds follow units=metric, so if you "
            f"meant {value:g} °F, drop units=metric or give {convert(value, 'degF', 'degC'):.1f}"
        )
    elif not lo <= value_f <= hi:
        hint = " (if that's °C, add units=metric)" if units != "metric" and value_f < lo else ""
        usual = f"{convert(lo, 'degF', unit):g}–{convert(hi, 'degF', unit):g} {label}"
        warnings.append(f"{param}: {bracket.what} of {value:g} {label} is outside the usual {usual}{hint}")
    return value_f


@dataclass(frozen=True, kw_only=True)
class DegreeDaySetting:
    name: str  # as given, canonical: sine_48_86, modified_40, average_43, sine_39p2_84 (the catalog's naming)
    method: Literal["sine", "average", "modified"]
    base_f: float
    upper_f: float | None


METHODS = ("sine", "average", "modified")


def degree_day_settings(raw: str | None, units: str, warnings: list[str], param: str = "dd") -> list[DegreeDaySetting]:
    """`dd=sine_48_86,modified_40,average_43` (method, base, optional upper, in the request's units; a decimal as
    39.2 or 39p2)."""
    if raw is None or not raw.strip():
        raise ApiError("missing", "give dd=method_base[_upper] (sine_50_86, modified_40, average_43), or base", param)
    found: list[DegreeDaySetting] = []
    for text in (t.strip() for t in raw.split(",") if t.strip()):
        parts = text.lower().removeprefix("dd_").split("_")
        if parts[0] not in METHODS or len(parts) not in (2, 3):
            raise ApiError(
                "invalid", f"{text!r} isn't method_base[_upper] with a method of {', '.join(METHODS)}", param
            )
        try:
            numbers = [float(p.replace("p", ".")) for p in parts[1:]]
        except ValueError:
            raise ApiError("invalid", f"{text!r}: the base and upper must be numbers", param) from None
        found.append(setting(parts[0], numbers[0], numbers[1] if len(numbers) > 1 else None, units, warnings, param))
    if len({s.name for s in found}) < len(found):
        raise ApiError("invalid", "a setting is given twice", param)
    return found


def setting(
    method: str, base: float, upper: float | None, units: str, warnings: list[str], param: str
) -> DegreeDaySetting:
    if method not in METHODS:
        raise ApiError("invalid", f"method {method!r} isn't one of {', '.join(METHODS)}", "method")
    base_f = temperature_threshold(base, units, DD_BASE, param, warnings)
    upper_f = None if upper is None else temperature_threshold(upper, units, DD_UPPER, param, warnings)
    if upper is not None and upper <= base:
        raise ApiError("invalid", f"the upper threshold ({upper:g}) must be above the base ({base:g})", param)
    name = f"{method}_{_number(base)}" + (f"_{_number(upper)}" if upper is not None else "")
    return DegreeDaySetting(name=name, method=method, base_f=base_f, upper_f=upper_f)  # type: ignore[arg-type]


def _number(value: float) -> str:
    return f"{value:g}".replace(".", "p")
