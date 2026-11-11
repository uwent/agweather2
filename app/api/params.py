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
from pydantic import PrivateAttr, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

from agdata import areas, rolling
from agdata.rolling import Roll
from api.errors import ApiError, day_text, hour_text
from ops.points import AreaAsk

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
                raise fail(
                    "conflict",
                    "points",
                    "Give either lat and lng for one location, or points for several, but not both.",
                )
            self._parsed = _parse_points(self.points)
            return self
        if self.lat is None or self.lng is None:
            missing = "lat" if self.lat is None else "lng"
            raise fail(
                "missing",
                missing,
                "Give a location as lat and lng (such as lat=43.07&lng=-89.40), or several as points=lat,lng;lat,lng.",
            )
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
        raise fail(
            "missing",
            "points",
            "The points list is empty. Give latitude,longitude pairs separated by semicolons, such "
            "as points=43.07,-89.40;44.52,-89.57.",
        )
    if len(pairs) > MAX_POINTS:
        raise fail(
            "too_many",
            "points",
            f"You gave {len(pairs)} points; a request can include up to {MAX_POINTS}. Split them "
            "into several requests.",
        )
    found = []
    for n, pair in enumerate(pairs, start=1):
        parts = pair.split(",")
        try:
            lat, lng = (float(v) for v in parts)
        except ValueError:
            raise fail(
                "invalid",
                "points",
                f"Point {n} ({pair}) isn't a latitude and longitude. Give each point as two numbers "
                "separated by a comma.",
            ) from None
        _check_point(lat, lng, "points", "points")
        found.append((lat, lng))
    return found


def _check_point(lat: float, lng: float, lat_param: str, lng_param: str) -> None:
    if not -90 <= lat <= 90:
        raise fail("out_of_range", lat_param, f"The latitude {lat:g} isn't between -90 and 90 degrees.")
    if not -180 <= lng <= 180:
        raise fail(
            "out_of_range",
            lng_param,
            f"The longitude {lng:g} isn't between -180 and 180 degrees. Longitudes in the Americas are negative.",
        )


class DaysQuery(Schema):
    """Local calendar days: one `date`, or `start` to `end` inclusive. Defaults are the endpoint's (`span`)."""

    date: dt.date | None = None
    start: dt.date | None = None
    end: dt.date | None = None

    @model_validator(mode="after")
    def _check(self) -> "DaysQuery":
        if self.date is not None and (self.start is not None or self.end is not None):
            raise fail(
                "conflict", "date", "Give either date for one day, or start and end for a range of days, but not both."
            )
        if self.start is not None and self.end is not None and self.start > self.end:
            raise fail(
                "out_of_order",
                "start",
                f"The start date ({day_text(self.start)}) is after the end date "
                f"({day_text(self.end)}). Choose a start date on or before the end date.",
            )
        return self

    def span(self, default_end: dt.date) -> tuple[dt.date, dt.date]:
        """(first, last): `date`, or `start`..`end` with end defaulting to `default_end` and start to January 1
        of end's year."""
        if self.date is not None:
            return self.date, self.date
        last = self.end or default_end
        first = self.start or dt.date(last.year, 1, 1)
        if first > last:
            raise ApiError(
                "out_of_order",
                f"The start date ({day_text(first)}) is after the default end date "
                f"({day_text(last)}). Give an end date as well.",
                "start",
            )
        return first, last


class SeriesQuery(Schema):
    """How a series runs: through the forecast or not, gaps in running totals, times' zone, and whose clock sets the
    days (`day_basis`, D74: default the grid's CST inside the box and the point's own outside it)."""

    forecast: bool = True
    gaps: Literal["estimate", "missing"] = "estimate"
    tz: Literal["utc", "local"] = "utc"
    day_basis: Literal["central", "local"] | None = None

    def echo(self) -> dict[str, Any]:
        """`day_basis` for `meta.request` (and the ETag) when it was given."""
        return {"day_basis": self.day_basis} if self.day_basis is not None else {}


MAX_RADIUS = {"us": 10.0, "metric": 16.0}  # miles, km: well under a county (`agdata.areas.MAX_RADIUS_KM`)


class AreaQuery(Schema):
    """`radius` (miles, or km with `units=metric`) and `weighting`: each point's weather averaged over the grid
    cells around it (`agdata.areas`, `ops.points.AreaAsk`)."""

    radius: float | None = None
    weighting: Literal["equal", "center"] = "equal"

    def ask(self, units: str) -> AreaAsk | None:
        if self.radius is None:
            return None
        system = "metric" if units == "metric" else "us"
        label = "km" if system == "metric" else "miles"
        if not 0 < self.radius <= MAX_RADIUS[system]:
            raise ApiError(
                "out_of_range",
                f"A radius of {self.radius:g} {label} can't be used. Give a radius over 0 and up to "
                f"{MAX_RADIUS[system]:g} {label}, which keeps the area well under the size of a county.",
                "radius",
            )
        km = self.radius if system == "metric" else self.radius * 1.609344
        return AreaAsk(radius_km=min(km, areas.MAX_RADIUS_KM), weighting=self.weighting)

    def echo(self) -> dict[str, Any]:
        return {"radius": self.radius, "weighting": self.weighting} if self.radius is not None else {}


class RollQuery(Schema):
    """Rolling windows on a daily series (D81, `agdata.rolling`): `roll=7,14,28` adds a column per window."""

    roll: str | None = None
    roll_stat: Literal["sum", "mean", "min", "max"] | None = None
    roll_align: Literal["trailing", "centered"] = "trailing"
    roll_partial: bool = False
    roll_coverage: float = 75
    _windows: list[int] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "RollQuery":
        if not 0 <= self.roll_coverage <= 100:
            raise fail(
                "out_of_range",
                "roll_coverage",
                f"roll_coverage ({self.roll_coverage:g}) is a percentage of a window's days, from 0 to 100.",
            )
        if self.roll is None or not self.roll.strip():
            return self
        found = []
        for text in (t.strip() for t in self.roll.split(",") if t.strip()):
            n = int(text) if text.isdigit() else None
            if n is None or not rolling.MIN_DAYS <= n <= rolling.MAX_DAYS:
                raise fail(
                    "invalid",
                    "roll",
                    f"The window {text!r} isn't a number of days from {rolling.MIN_DAYS} to {rolling.MAX_DAYS}. "
                    "Give one or more lengths in days, separated by commas, such as roll=7,14,28.",
                )
            found.append(n)
        if len(set(found)) < len(found):
            raise fail("invalid", "roll", "The same window is given twice. List each length once.")
        self._windows = found
        return self

    def specs(self) -> list[Roll]:
        return [
            Roll(days=n, align=self.roll_align, partial=self.roll_partial, coverage=self.roll_coverage / 100)
            for n in self._windows
        ]

    def lead(self) -> tuple[int, int]:
        """The most days any window reaches before and after its day: what a request reads beyond its range."""
        offsets = [s.offsets for s in self.specs()]
        return max((b for b, _ in offsets), default=0), max((a for _, a in offsets), default=0)

    def echo(self) -> dict[str, Any]:
        """For `meta.request` (and the ETag), when windows were asked for."""
        if not self._windows:
            return {}
        return {
            "roll": self._windows,
            "roll_stat": self.roll_stat,
            "roll_align": self.roll_align,
            "roll_partial": self.roll_partial,
            "roll_coverage": self.roll_coverage,
        }


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
        raise ApiError(
            "unknown_variable",
            f"We don't have a variable named {', '.join(unknown)} here. Choose from: {listed}.",
            param,
        )
    return list(dict.fromkeys(names))


def resolve_biofix(text: str | dt.date | None, reference: dt.date, param: str = "biofix") -> dt.date | None:
    """A biofix as sent: a date (`2026-04-15`), or a month and day (`04-15`) taken in the latest year that puts it on
    or before `reference` (the request's last day), so `11-01` in February is last November's."""
    if text is None or text == "":
        return None
    if isinstance(text, dt.date):
        return text
    text = text.strip()
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        pass
    parts = text.split("-")
    if len(parts) == 2 and all(part.isdigit() and len(part) <= 2 for part in parts):
        month, day = int(parts[0]), int(parts[1])
        if (month, day) == (2, 29):
            raise ApiError(
                "invalid",
                "February 29 isn't in every year, so give the biofix as a full date, such as 2024-02-29.",
                param,
            )
        try:
            found = dt.date(reference.year, month, day)
        except ValueError:
            pass
        else:
            return found if found <= reference else found.replace(year=reference.year - 1)
    raise ApiError(
        "invalid",
        f"The {param} ({text}) isn't a date. Give a date as YYYY-MM-DD (2026-04-15), or a month and day as MM-DD "
        "(04-15) for the latest one on or before the end date.",
        param,
    )


EPOCH_DIGITS = 9  # a bare number this long or longer is Unix time; 8 digits is a compact date (20261105)
EPOCH_MS = 10**11  # from here a Unix time is in milliseconds (in seconds it would be the year 5138)
TIME_FORMS = "as 2025-07-08T15:00Z, or as Unix time in seconds (1751986800)"


def parse_time(value: str | int | float) -> dt.datetime:
    """A time as any endpoint takes it (ValueError if it isn't one): ISO 8601 with or without minutes, a zone (`Z`,
    `-05:00`), the `T` (a space works too) or the dashes (`20250708T15`); a bare date for its midnight; or Unix time
    (Wisconet's), in seconds or milliseconds, as text or a JSON number, always UTC. A time without a zone is returned
    naive: each caller decides what that means."""
    if isinstance(value, bool):
        raise ValueError(value)
    number: float | None = None
    if isinstance(value, int | float):
        number = value
    else:
        text = str(value).strip()
        if text.isdigit() and len(text) >= EPOCH_DIGITS:
            number = int(text)
    if number is not None:
        return dt.datetime.fromtimestamp(number / 1000 if abs(number) >= EPOCH_MS else number, dt.UTC)
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00").replace("z", "+00:00"))


def parse_hour(value: str | int | float, param: str) -> dt.datetime:
    """`parse_time` for a query parameter: in UTC (a time without a zone is UTC), on the hour, else ApiError."""
    try:
        found = parse_time(value)
    except (ValueError, OverflowError, OSError):
        raise ApiError(
            "invalid", f"The value of {param} ({value}) isn't a time. Give a time {TIME_FORMS}.", param
        ) from None
    found = found.replace(tzinfo=dt.UTC) if found.tzinfo is None else found.astimezone(dt.UTC)
    if found.minute or found.second or found.microsecond:
        raise ApiError(
            "invalid",
            f"The value of {param} ({found:%Y-%m-%dT%H:%M:%S}Z) isn't on the hour. Give a whole hour, such as "
            "2025-07-08T15:00Z.",
            param,
        )
    return found


class HoursQuery(Schema):
    """Hours by their UTC end, `start` to `end` inclusive, in any form `parse_hour` takes (an ISO time or Unix
    time, on the hour; without a zone, UTC). Defaults are the endpoint's (`span`)."""

    start: dt.datetime | None = None
    end: dt.datetime | None = None

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse(cls, value: Any, info: ValidationInfo) -> dt.datetime | None:
        if value is None or value == "":
            return None
        try:
            return parse_hour(value, str(info.field_name))
        except ApiError as error:
            raise fail("invalid", error.param, error.message) from None

    @model_validator(mode="after")
    def _check(self) -> "HoursQuery":
        if self.start is not None and self.end is not None and self.start > self.end:
            raise fail(
                "out_of_order",
                "start",
                f"The start time ({hour_text(self.start)}) is after the end time "
                f"({hour_text(self.end)}). Choose a start on or before the end.",
            )
        return self

    def span(self, default_start: dt.datetime, default_end: dt.datetime) -> tuple[dt.datetime, dt.datetime]:
        first, last = self.start or default_start, self.end or default_end
        if first > last:
            raise ApiError(
                "out_of_order",
                f"The start time ({hour_text(first)}) is after the end time ({hour_text(last)}). "
                "Choose a start on or before the end.",
                "start",
            )
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
CHILL = Bracket(what="a chill-hour bound", usual_f=(28, 60), reason="chill-hour ranges run 32–45 °F")
# With metric units, a value above these looks like °F given as °C (50 °C is a hot day's air, not a base)
LOOKS_LIKE_F_IN_C = {DD_BASE: 30, DD_UPPER: 45, FREEZE: 10, CHILL: 20}


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
            f"{bracket.what.capitalize()} of {value:g} {label} can never be reached: the air temperatures we store "
            f"run from {lowest:g} to {highest:g} {label}. Choose a value in that range.",
            param,
        )
    value_f = convert(value, unit, "degF")
    lo, hi = bracket.usual_f
    if units == "metric" and value > LOOKS_LIKE_F_IN_C[bracket]:
        warnings.append(
            f"With units=metric, {bracket.what} of {value:g} is read as {value:g} °C ({value_f:g} °F). If you meant "
            f"{value:g} °F, leave out units=metric or give {convert(value, 'degF', 'degC'):.1f}."
        )
    elif not lo <= value_f <= hi:
        hint = " If you meant °C, add units=metric." if units != "metric" and value_f < lo else ""
        usual = f"{convert(lo, 'degF', unit):g}–{convert(hi, 'degF', unit):g} {label}"
        warnings.append(
            f"{bracket.what.capitalize()} of {value:g} {label} is outside the usual range of {usual}, so check that "
            f"it's the value you meant.{hint}"
        )
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
        raise ApiError(
            "missing",
            "Give a degree-day setting as dd=method_base_upper (such as sine_50_86, modified_40 or average_43), or as "
            "base with an optional upper and method.",
            param,
        )
    found: list[DegreeDaySetting] = []
    for text in (t.strip() for t in raw.split(",") if t.strip()):
        parts = text.lower().removeprefix("dd_").split("_")
        if parts[0] not in METHODS or len(parts) not in (2, 3):
            raise ApiError(
                "invalid",
                f"The degree-day setting {text} isn't in the form method_base_upper. Give a method (sine, average or "
                "modified) and a base, with an optional upper threshold, such as sine_50_86.",
                param,
            )
        try:
            numbers = [float(p.replace("p", ".")) for p in parts[1:]]
        except ValueError:
            raise ApiError(
                "invalid",
                f"In the degree-day setting {text}, the base and upper threshold must be numbers, "
                "such as sine_50_86 or "
                "sine_39p2_86 (p for a decimal point).",
                param,
            ) from None
        found.append(setting(parts[0], numbers[0], numbers[1] if len(numbers) > 1 else None, units, warnings, param))
    if len({s.name for s in found}) < len(found):
        raise ApiError("invalid", "The same degree-day setting is given twice. List each setting once.", param)
    return found


def setting(
    method: str, base: float, upper: float | None, units: str, warnings: list[str], param: str
) -> DegreeDaySetting:
    if method not in METHODS:
        raise ApiError(
            "invalid",
            f"We don't compute degree days by a method called {method}. Choose sine, average or modified.",
            "method",
        )
    base_f = temperature_threshold(base, units, DD_BASE, param, warnings)
    upper_f = None if upper is None else temperature_threshold(upper, units, DD_UPPER, param, warnings)
    if upper is not None and upper <= base:
        raise ApiError(
            "invalid",
            f"The upper threshold ({upper:g}) must be above the base ({base:g}). Give a higher "
            "upper threshold, or leave it out.",
            param,
        )
    name = f"{method}_{_number(base)}" + (f"_{_number(upper)}" if upper is not None else "")
    return DegreeDaySetting(name=name, method=method, base_f=base_f, upper_f=upper_f)  # type: ignore[arg-type]


def _number(value: float) -> str:
    return f"{value:g}".replace(".", "p")
