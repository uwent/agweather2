"""The envelope every endpoint answers in (docs/api.md): `{meta, data}`, or `{meta, errors}` for a failure.

An endpoint builds a `Result` (a table of named columns, each number column with its stored unit, or a plain `data`
payload for discovery) and returns `respond(request, result)`, which does the rest once for every endpoint:

- units: each number column goes to the request's system (`units=us|metric`), or to the unit a parameter named
  for its variable asks for (`precipitation=mm` covers `precipitation_sum` too), and `meta.units` says which;
- rounding to the stored precision (a column's `step`, the catalog's scale) in the unit shown: no more digits than
  the archive holds, and none fewer;
- missing as `null` (NaN never reaches JSON), an empty cell in CSV;
- the summary's missing counts and statistics per summarized column, in the units shown;
- the format (`format=` first, then `Accept`): JSON, columnar or `orient=records`, or CSV with `meta` as `#` lines;
  a grid also offers NetCDF and GeoTIFF, which the endpoint renders itself (`Result.render`);
- headers: `Server-Timing`, and `Cache-Control: no-cache` (keep it, but ask before reusing it) with the ETag the
  endpoint computed before reading anything (`etag_for`); `not_modified` answers a matching `If-None-Match` with 304.
"""

import csv
import hashlib
import io
import json
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers

from agdata import units as agunits
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES, Variable
from agdata.computed import DAILY_COMPUTED, HOURLY_COMPUTED
from api.errors import ApiError

API_VERSION = "2.0"
# The code's version in an ETag: the deployed commit, or in development this process's start (uvicorn restarts on a
# code change), so a change to how answers are computed is a change of answer even where the data isn't
CODE_VERSION = settings.APP_VERSION if settings.APP_VERSION != "dev" else f"dev-{time.time()}"
SYSTEMS: dict[str, agunits.System] = {"us": "imperial", "metric": "metric"}
_COMPUTED = {c.name: c.variable for c in [*DAILY_COMPUTED.values(), *HOURLY_COMPUTED.values()]}  # `agdata.computed`
# A name in two is the first's: water balance is daily (computed) before it's a running total
CATALOGS = (DAILY_VARIABLES, VARIABLES, _COMPUTED, CUMULATIVE_VARIABLES)
TOTALLED = ("depth", "radiant_exposure", "duration")  # dimensions whose values add up over days (a total is shown)


def attribution(year: int) -> str:
    """D53: the sources whose licences ask to be credited."""
    return (
        "AgWeather, University of Wisconsin–Madison. Weather from NOAA (URMA, RTMA, HRRR, NBM), Open-Meteo "
        f"(CC BY 4.0) and ECMWF; contains modified Copernicus Climate Change Service information {year}."
    )


@dataclass(kw_only=True)
class Column:
    """One column. Numbers carry their stored unit and precision (`step`, in that unit); other columns (dates,
    kinds, flags, text) pass through as they are."""

    name: str
    values: Sequence[Any] | np.ndarray
    unit: str | None = None
    step: float | None = None
    variable: str | None = None  # the catalog name a unit override is matched against (default: name)
    summarize: bool = False  # count its missing values and give min, max, mean (and a total where values add)
    total: bool | None = None  # give that total (default: where the unit's values add); a map's cells don't add


def catalog_column(name: str, values: Sequence[Any] | np.ndarray, *, variable: str | None = None) -> Column:
    """A column of a catalog variable (daily, hourly, computed or cumulative, in that order), summarized."""
    v = find_variable(variable or name)
    return Column(name=name, values=values, unit=v.unit, step=v.scale, variable=v.name, summarize=True)


def find_variable(name: str) -> Variable:
    for catalog in CATALOGS:
        if name in catalog:
            return catalog[name]
    raise KeyError(f"{name} isn't in the catalog")


@dataclass(kw_only=True)
class Result:
    """What an endpoint computed. `request` is the request as computed (defaults filled). Give `columns` for a
    table, or `data` for any other payload (JSON only)."""

    request: dict[str, Any]
    columns: list[Column] | None = None
    data: Any = None
    location: dict[str, Any] | None = None
    locations: list[dict[str, Any]] | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    etag: str | None = None  # from `etag_for`, when the answer can be revalidated
    filename: str = "agweather"  # a CSV download's name, without the extension
    formats: tuple[str, ...] | None = None  # offered; default json and csv for a table, json otherwise
    timings: dict[str, float] = field(default_factory=dict)  # name → ms, for Server-Timing beside the total
    units: str | None = None  # the unit system, when the request gave it outside the query (a POSTed body)
    render: Callable[[str, dict[str, Any]], bytes] | None = None  # a binary format's file, from (format, meta)
    binary_units: dict[str, str] = field(default_factory=dict)  # meta.units for a binary answer


# --- Units and rounding ------------------------------------------------------------------------------------------


def unit_overrides(request: HttpRequest) -> dict[str, str]:
    """Parameters named for a catalog variable, each a unit for it: a symbol (`mm`, `degF`), its label (`°F`), or a
    system (`us`, `metric`). Checked against the variable's dimension."""
    found: dict[str, str] = {}
    for name, value in request.GET.items():
        try:
            v = find_variable(name)
        except KeyError:
            continue
        symbol = match_unit(v.unit, value)
        if symbol is None:
            raise ApiError(
                "bad_unit", f"We can't show {name} in {value!r}. Choose one of these units: {units_like(v.unit)}.", name
            )
        found[name] = symbol
    return found


def match_unit(stored: str, given: str) -> str | None:
    """The unit symbol `given` names for a variable stored in `stored`: a symbol (`mm`, `degF`), its label (`°F`)
    or a system (`us`, `metric`), of the same dimension; None if it names none."""
    if given in SYSTEMS:
        return agunits.display_unit(stored, SYSTEMS[given])
    dimension = agunits.unit(stored).dimension
    return next(
        (
            u.symbol
            for u in agunits.UNITS.values()
            if u.dimension == dimension and given.lower() in (u.symbol.lower(), u.label.lower())
        ),
        None,
    )


def units_like(stored: str) -> str:
    """The unit symbols a variable stored in `stored` can be given or shown in, for a message."""
    dimension = agunits.unit(stored).dimension
    return ", ".join(u.symbol for u in agunits.UNITS.values() if u.dimension == dimension)


def shown_unit(column: Column, system: agunits.System, overrides: dict[str, str]) -> str:
    """The unit a number column is shown in: an override for its variable or a prefix of its name, else the system's."""
    assert column.unit is not None
    key = column.variable or column.name
    for name, symbol in overrides.items():
        named = key == name or key.startswith(name + "_") or column.name.startswith(name + "_")
        if named and agunits.unit(symbol).dimension == agunits.unit(column.unit).dimension:
            return symbol
    return agunits.display_unit(column.unit, system)


def digits_for(step: float, stored: str, shown: str) -> int:
    """Decimals that show a stored step in another unit: 0.1 °C is 0.18 °F (1 decimal), 0.1 mm 0.004 in (3)."""
    source, target = agunits.unit(stored), agunits.unit(shown)
    step_shown = abs(step * source.factor / target.factor)
    return max(0, math.ceil(round(-math.log10(step_shown), 6)))


@dataclass(kw_only=True)
class _Prepared:
    name: str
    values: list[Any]
    label: str | None = None  # the unit shown, for number columns
    numbers: np.ndarray | None = None  # converted, unrounded, for the summary
    digits: int = 0
    totalled: bool = False
    summarize: bool = False


def _prepare(column: Column, system: agunits.System, overrides: dict[str, str]) -> _Prepared:
    if column.unit is None:
        return _Prepared(name=column.name, values=[_plain(v) for v in column.values])
    shown = shown_unit(column, system, overrides)
    numbers = agunits.convert(np.asarray(column.values, dtype=float), column.unit, shown)
    digits = digits_for(column.step, column.unit, shown) if column.step else 4
    rounded = np.round(numbers, digits).tolist()
    values = [None if v != v else (int(v) if digits == 0 else v) for v in rounded]  # NaN != NaN
    unit = agunits.unit(shown)
    return _Prepared(
        name=column.name,
        values=values,
        label=unit.label,
        numbers=numbers,
        digits=digits,
        totalled=unit.dimension in TOTALLED if column.total is None else column.total,
        summarize=column.summarize,
    )


def _plain(value: Any) -> Any:
    """A value as JSON has it: dates ISO, UTC times with Z, NaN null, numpy scalars as Python's."""
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and value != value:
        return None
    return value


def _stats(prepared: list[_Prepared]) -> tuple[dict[str, int], dict[str, dict[str, Any]]]:
    missing: dict[str, int] = {}
    stats: dict[str, dict[str, Any]] = {}
    for p in prepared:
        if not p.summarize or p.numbers is None:
            continue
        known = p.numbers[np.isfinite(p.numbers)]
        missing[p.name] = int(p.numbers.size - known.size)
        if not known.size:
            continue

        def r(x: float, digits: int = p.digits) -> float | int:
            return round(float(x)) if digits == 0 else round(float(x), digits)

        stats[p.name] = {"min": r(known.min()), "max": r(known.max()), "mean": r(known.mean(), p.digits + 1)}
        if p.totalled:
            stats[p.name]["total"] = r(known.sum())
    return missing, stats


# --- Responses ---------------------------------------------------------------------------------------------------


def respond(request: HttpRequest, result: Result) -> HttpResponse:
    """The response for a result, in the format asked for, with its headers."""
    formats = result.formats or (("json", "csv") if result.columns is not None else ("json",))
    fmt = _format(request, formats)
    params = request.GET
    system = SYSTEMS.get(result.units or params.get("units", "us"), "imperial")
    overrides = unit_overrides(request)
    meta: dict[str, Any] = {"request": result.request}
    if result.location is not None:
        meta["location"] = result.location
    if result.locations is not None:
        meta["locations"] = result.locations

    orient = params.get("orient", "columns")
    if fmt in BINARY:
        meta["units"] = result.binary_units
        meta["summary"] = result.summary
        prepared = []
    elif result.columns is not None:
        prepared = [_prepare(c, system, overrides) for c in result.columns]
        table = _table(prepared, orient)
        meta["units"] = table["units"]
        meta["summary"] = {**result.summary, **table["summary"]}
    else:
        prepared = []
        meta["units"] = {}
        meta["summary"] = result.summary
    meta["sources"] = result.sources
    meta["warnings"] = result.warnings
    now = datetime.now(UTC)
    meta["attribution"] = attribution(now.year)
    meta["api_version"] = API_VERSION
    meta["generated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    data: Any = result.data if result.columns is None else table["data"]

    elapsed = _elapsed_ms(request)
    meta["compute_ms"] = round(elapsed)
    if fmt in BINARY:
        assert result.render is not None, f"{fmt} offered without a renderer"
        media, extension = BINARY[fmt]
        response = HttpResponse(result.render(fmt, meta), content_type=media)
        response["Content-Disposition"] = f'attachment; filename="{_safe(result.filename)}{extension}"'
    elif fmt == "csv":
        if result.columns is None:
            raise ApiError(
                "format_unavailable",
                "This request's answer comes only as JSON. Leave out format=csv, or give format=json.",
                "format",
            )
        body = _csv(meta, prepared, with_meta=params.get("headers", "true").lower() not in ("false", "0", "no"))
        response = HttpResponse(body, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{_safe(result.filename)}.csv"'
    else:
        response = HttpResponse(_json({"meta": meta, "data": data}), content_type="application/json")
    timings = [f"{_safe(name)};dur={ms:.1f}" for name, ms in result.timings.items()]
    response["Server-Timing"] = ", ".join([*timings, f"total;dur={elapsed:.1f}"])
    _cache_headers(response, result.etag)
    if not params.get("format") and len(formats) > 1:
        patch_vary_headers(response, ("Accept",))  # the format came from it
    return response


def table(
    request: HttpRequest, columns: list[Column], summary: dict[str, Any] | None = None, units: str | None = None
) -> dict[str, Any]:
    """One table as a nested answer holds it (`GET /models/run`'s per-model `meta` and `data`): `units`, `summary`
    (with `missing` and `stats`) and `data`, in the request's units (or `units`) and orientation, as `respond`
    makes them."""
    params = request.GET
    system = SYSTEMS.get(units or params.get("units", "us"), "imperial")
    prepared = [_prepare(c, system, unit_overrides(request)) for c in columns]
    found = _table(prepared, params.get("orient", "columns"))
    return {"units": found["units"], "summary": {**(summary or {}), **found["summary"]}, "data": found["data"]}


def _table(prepared: list[_Prepared], orient: str) -> dict[str, Any]:
    lengths = {len(p.values) for p in prepared}
    if len(lengths) > 1:
        raise ValueError(f"columns of different lengths: { {p.name: len(p.values) for p in prepared} }")
    missing, stats = _stats(prepared)
    if orient == "records":
        names = [p.name for p in prepared]
        data: Any = [dict(zip(names, row, strict=True)) for row in zip(*(p.values for p in prepared), strict=True)]
    else:
        data = {p.name: p.values for p in prepared}
    return {
        "units": {p.name: p.label for p in prepared if p.label is not None},
        "summary": {"missing": missing, "stats": stats},
        "data": data,
    }


def etag_for(request: HttpRequest, computed: dict[str, Any], data_stamp: str | None) -> str:
    """The answer's ETag, known before computing it: the code's version, the request as sent (output options and unit
    overrides included) and as computed (defaults such as today's date filled), and `data_stamp`, which changes
    whenever the data read can have (`agdata.series.last_written`). Without `format=`, the `Accept` header picks the
    format, so it's part of the key: a JSON and a CSV answer to the same query are different representations."""
    sent = sorted((key, request.GET.getlist(key)) for key in request.GET)
    accept = None if request.GET.get("format") else request.headers.get("Accept", "")
    key = json.dumps([CODE_VERSION, request.path, sent, accept, computed, data_stamp], default=str, sort_keys=True)
    return '"' + hashlib.sha256(key.encode()).hexdigest()[:32] + '"'


def not_modified(request: HttpRequest, etag: str) -> HttpResponse | None:
    """A 304 if the client holds this answer already (`If-None-Match`), else None: call it before computing."""
    held = [tag.strip() for tag in request.headers.get("If-None-Match", "").split(",")]
    if etag not in held and "*" not in held:
        return None
    response = HttpResponse(status=304)
    _cache_headers(response, etag)
    return response


def error_response(request: HttpRequest, errors: list[dict[str, Any]], status: int) -> HttpResponse:
    """`{meta, errors}`: the request as sent (it couldn't be normalized), and what's wrong with it."""
    now = datetime.now(UTC)
    meta = {
        "request": {key: request.GET.get(key) for key in request.GET},
        "api_version": API_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "compute_ms": round(_elapsed_ms(request)),
    }
    response = HttpResponse(_json({"meta": meta, "errors": errors}), content_type="application/json", status=status)
    response["Cache-Control"] = "no-store"
    return response


def requested_format(request: HttpRequest, offered: tuple[str, ...]) -> str:
    """The format a request asks for among those offered (`format=`, then `Accept`), for an endpoint that builds
    its answer differently per format (a grid's long table, or its file)."""
    return _format(request, offered)


def output_units(request: HttpRequest) -> tuple[agunits.System, dict[str, str]]:
    """The request's unit system and per-variable overrides, as `respond` applies them."""
    return SYSTEMS.get(request.GET.get("units", "us"), "imperial"), unit_overrides(request)


def _format(request: HttpRequest, offered: tuple[str, ...]) -> str:
    asked = request.GET.get("format")
    if asked:
        asked = asked.lower()
        if asked not in offered:
            raise ApiError(
                "format_unavailable",
                f"This request's answer doesn't come as {asked}. Choose one of these formats: {', '.join(offered)}.",
                "format",
            )
        return asked
    accept = request.headers.get("Accept", "")
    for part in accept.split(","):
        media = part.split(";")[0].strip().lower()
        for fmt in offered:
            if media in _MEDIA.get(fmt, ()):
                return fmt
    return offered[0]


_MEDIA = {
    "json": ("application/json",),
    "csv": ("text/csv",),
    "netcdf": ("application/x-netcdf", "application/netcdf"),
    "geotiff": ("image/tiff", "image/geotiff"),
}
BINARY = {"netcdf": ("application/x-netcdf", ".nc"), "geotiff": ("image/tiff", ".tif")}  # media type, extension


def _csv(meta: dict[str, Any], prepared: list[_Prepared], with_meta: bool) -> str:
    out = io.StringIO()
    if with_meta:
        for key, value in meta.items():
            text = (
                value
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=_plain)
            )
            out.write(f"# {key}: {text}\n")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([p.name for p in prepared])
    for row in zip(*(p.values for p in prepared), strict=True):
        writer.writerow(["" if v is None else ("true" if v is True else "false" if v is False else v) for v in row])
    return out.getvalue()


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"), default=_plain)


def _cache_headers(response: HttpResponse, etag: str | None) -> None:
    if etag is not None:
        response["ETag"] = etag
    response["Cache-Control"] = "public, no-cache"


def _elapsed_ms(request: HttpRequest) -> float:
    started = getattr(request, "api_started", None)
    return 0.0 if started is None else (time.perf_counter() - started) * 1000


def _safe(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text)
