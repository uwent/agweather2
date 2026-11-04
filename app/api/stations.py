"""Weather sent with a model run (docs/api.md, "Running models on your own weather"; D58): a station's hourly and/or
daily values, checked and turned into the daily series a model reads, by the same rollup as the archive's.

- **Shape:** JSON `{"hourly": {"time": [...], name: [...]}, "daily": {"date": [...], name: [...]}}`, or a CSV body
  whose first column is `time` (hourly) or `date` (daily) and whose others are catalog names. Hourly times are
  ISO with `Z` or an offset, each value for the hour ending then; daily dates are the location's local days.
- **Units:** the request's system (`units=us|metric`), with per-variable overrides (`input_units`, or a parameter
  named for the variable as on GETs); converted to the catalog's stored units.
- **QC as at ingest** (`agdata.qc.run_qc`): out-of-range values and spikes become missing, short gaps in the hours
  are filled; counted in warnings.
- **Humidity:** a station sending RH without dew point gets dew point from RH and temperature (Magnus, inverting
  `agmodels.weather.relative_humidity_percent`), and one sending dew point without RH gets RH, each with a warning.
  Its "RH ≥ 90%" hours count at 90%: D50's 88% is for gridded RH, and a station is what the 90% was measured on.
- **Rollup:** hours through `agdata.point.daily_at_point` in the location's zone (a day needs 20 hours for a min,
  mean or max and every hour for a count or sum, D25); daily values sent directly win over ones made from hours.

Nothing sent is stored."""

import csv
import io
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from agdata import units as agunits
from agdata.catalog import DAILY_VARIABLES, VARIABLES, Variable
from agdata.point import daily_at_point, hourly_sources
from agdata.qc import check_range, run_qc
from agmodels.weather import dew_point_from_rh_c, relative_humidity_percent
from api.envelope import SYSTEMS
from api.errors import ApiError

HOUR = timedelta(hours=1)
MAX_HOURS = 2 * 8784  # about two years of hours per request
MAX_DAYS = 3660
STATION_RH_90 = 90.0
HOURLY = {name: v for name, v in VARIABLES.items() if name != "shortwave_radiation_hrrr"}  # what a station can send
DAILY = {name: v for name, v in DAILY_VARIABLES.items() if name != "et0_sum_estimate"}


@dataclass(kw_only=True)
class Station:
    """What was sent, in stored units: hours from `first_hour`, and daily values by local date."""

    first_hour: datetime | None = None
    hourly: dict[str, np.ndarray] = field(default_factory=dict)
    days: list[date] = field(default_factory=list)
    daily: dict[str, np.ndarray] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def local_days(self, zone: str) -> tuple[date, date] | None:
        """The first and last local day with anything sent."""
        found: list[date] = list(self.days)
        if self.first_hour is not None and self.hourly:
            n = len(next(iter(self.hourly.values())))
            tz = ZoneInfo(zone)
            # an hour ending at local midnight belongs to the day before
            found += [(self.first_hour - HOUR / 2).astimezone(tz).date()]
            found += [(self.first_hour + (n - 1) * HOUR - HOUR / 2).astimezone(tz).date()]
        return (min(found), max(found)) if found else None

    def available(self) -> set[str]:
        """The daily variables this can make: sent daily, or rolled up from hourly variables all sent."""
        sent = {name for name, values in self.hourly.items() if np.isfinite(values).any()}
        made = {name for name, sources in hourly_sources().items() if sources and set(sources) <= sent}
        return made | {name for name, values in self.daily.items() if np.isfinite(values).any()}

    def daily_series(self, zone: str, first: date, last: date, names: list[str]) -> dict[str, np.ndarray]:
        """Local days first..last of `names` (NaN where nothing was sent): the hours rolled up, then daily values
        sent directly over them."""
        n = (last - first).days + 1
        out = {name: np.full(n, np.nan) for name in names}
        if self.first_hour is not None and self.hourly:
            rolled = daily_at_point(
                self.first_hour, self.hourly, zone, first, last, names=names, rh_90_at=STATION_RH_90
            )
            for name in names:
                if name in rolled:
                    out[name] = np.asarray(rolled[name], dtype=float)
        for name in names:
            if name not in self.daily:
                continue
            for k, day in enumerate(self.days):
                j = (day - first).days
                if 0 <= j < n and np.isfinite(self.daily[name][k]):
                    out[name][j] = self.daily[name][k]
        return out


def parse(body: dict[str, Any], system_name: str, overrides: dict[str, str]) -> Station:
    """A JSON body's `hourly` and `daily` blocks, checked, converted and QC'd."""
    system = SYSTEMS.get(system_name)
    if system is None:
        raise ApiError("invalid", "units must be us or metric", "units")
    station = Station()
    hourly, daily = body.get("hourly"), body.get("daily")
    if not hourly and not daily:
        raise ApiError("missing", "send hourly and/or daily values", "body")
    if hourly:
        _hourly(station, _block(hourly, "hourly", "time"), system, overrides)
    if daily:
        _daily(station, _block(daily, "daily", "date"), system, overrides)
    return station


def parse_csv(text: str) -> dict[str, Any]:
    """A CSV body as the JSON body's `hourly` or `daily` block: its first column `time` or `date`."""
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if r and not r[0].startswith("#")]
    if len(rows) < 2:
        raise ApiError("missing", "the CSV needs a header row and at least one row of values", "body")
    header = [h.strip() for h in rows[0]]
    if header[0] not in ("time", "date"):
        raise ApiError("invalid", "the CSV's first column must be time (hourly) or date (daily)", "body")
    columns: dict[str, list[Any]] = {h: [] for h in header}
    for n, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            raise ApiError("invalid", f"CSV row {n} has {len(row)} values; the header has {len(header)}", "body")
        for h, value in zip(header, row, strict=True):
            columns[h].append(value.strip() or None)
    return {"hourly" if header[0] == "time" else "daily": columns}


def _block(block: Any, kind: str, key: str) -> dict[str, list[Any]]:
    if not isinstance(block, dict) or key not in block:
        raise ApiError("invalid", f"{kind} needs a {key!r} list and a list per variable", kind)
    n = len(block[key])
    for name, values in block.items():
        if not isinstance(values, list) or len(values) != n:
            raise ApiError("invalid", f"{kind}.{name} must be a list as long as {kind}.{key} ({n})", kind)
    return block


def _numbers(values: list[Any], where: str) -> np.ndarray:
    try:
        return np.array([np.nan if v is None or v == "" else float(v) for v in values], dtype=float)
    except (TypeError, ValueError):
        raise ApiError("invalid", f"{where} must hold numbers (or null)", where) from None


def _unit_in(v: Variable, system, overrides: dict[str, str]) -> str:
    """The unit a variable was sent in: an override for it or a prefix of its name, else the system's."""
    dimension = agunits.unit(v.unit).dimension
    for name, given in overrides.items():
        if v.name == name or v.name.startswith(name + "_"):
            if given in SYSTEMS:
                return agunits.display_unit(v.unit, SYSTEMS[given])
            matches = [
                u.symbol
                for u in agunits.UNITS.values()
                if u.dimension == dimension and given.lower() in (u.symbol.lower(), u.label.lower())
            ]
            if not matches:
                raise ApiError("bad_unit", f"{v.name} can't be read in {given!r}", f"input_units.{name}")
            return matches[0]
    return agunits.display_unit(v.unit, system)


def _hourly(station: Station, block: dict[str, list[Any]], system, overrides: dict[str, str]) -> None:
    unknown = sorted(set(block) - {"time"} - set(HOURLY))
    if unknown:
        raise ApiError("unknown_variable", f"{', '.join(unknown)}: not hourly catalog names (GET /variables)", "hourly")
    times = []
    for k, text in enumerate(block["time"]):
        try:
            when = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        except ValueError:
            raise ApiError("invalid", f"hourly.time[{k}] ({text!r}) isn't an ISO time", "hourly.time") from None
        if when.tzinfo is None:
            raise ApiError(
                "invalid",
                f"hourly.time[{k}] needs Z or an offset (each value is for the hour ending then)",
                "hourly.time",
            )
        if when.minute or when.second:
            raise ApiError("invalid", f"hourly.time[{k}] ({text}) isn't on the hour", "hourly.time")
        times.append(when.astimezone(UTC))
    if not times:
        return
    if len(set(times)) != len(times):
        raise ApiError("invalid", "hourly.time has the same hour more than once", "hourly.time")
    first, last = min(times), max(times)
    n = (last - first) // HOUR + 1
    if n > MAX_HOURS:
        raise ApiError("too_large", f"{n} hours sent; up to {MAX_HOURS} per request", "hourly")
    index = np.array([(t - first) // HOUR for t in times])
    station.first_hour = first
    for name in block:
        if name == "time":
            continue
        v = HOURLY[name]
        values = np.full(n, np.nan)
        values[index] = agunits.convert(_numbers(block[name], f"hourly.{name}"), _unit_in(v, system, overrides), v.unit)
        qc = run_qc(v, values)
        dropped = qc.out_of_range + qc.spikes
        if dropped:
            station.warnings.append(f"{name}: {dropped} hours outside its range or spikes, left missing")
        station.hourly[name] = qc.values
    _humidity(station, n)


def _humidity(station: Station, n: int) -> None:
    h = station.hourly
    t = h.get("air_temperature")
    if t is None:
        return
    if "relative_humidity" in h and "dew_point" not in h:
        h["dew_point"] = np.asarray(dew_point_from_rh_c(t, h["relative_humidity"]), dtype=float)
        station.warnings.append("dew_point computed from relative_humidity and air_temperature")
    elif "dew_point" in h and "relative_humidity" not in h:
        h["relative_humidity"] = np.asarray(relative_humidity_percent(t, h["dew_point"]), dtype=float)
        station.warnings.append("relative_humidity computed from dew_point and air_temperature")


def _daily(station: Station, block: dict[str, list[Any]], system, overrides: dict[str, str]) -> None:
    unknown = sorted(set(block) - {"date"} - set(DAILY))
    if unknown:
        raise ApiError("unknown_variable", f"{', '.join(unknown)}: not daily catalog names (GET /variables)", "daily")
    days = []
    for k, text in enumerate(block["date"]):
        try:
            days.append(date.fromisoformat(str(text)))
        except ValueError:
            raise ApiError("invalid", f"daily.date[{k}] ({text!r}) isn't a date (YYYY-MM-DD)", "daily.date") from None
    if len(set(days)) != len(days):
        raise ApiError("invalid", "daily.date has the same day more than once", "daily.date")
    if days and (max(days) - min(days)).days + 1 > MAX_DAYS:
        raise ApiError("too_large", f"up to {MAX_DAYS} days per request", "daily")
    station.days = days
    for name in block:
        if name == "date":
            continue
        v = DAILY[name]
        values = agunits.convert(_numbers(block[name], f"daily.{name}"), _unit_in(v, system, overrides), v.unit)
        cleaned, bad = check_range(v, values)
        if bad:
            station.warnings.append(f"{name}: {bad} days outside its range, left missing")
        station.daily[name] = cleaned
