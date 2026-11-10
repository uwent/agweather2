"""Daily values at one point from its hourly series, by the same definitions as the grid rollup (`agdata.daily`).

A point outside the box (Open-Meteo) or a point read from the hourly store goes through here, so its days match
the daily store's cell for cell when given the grid's zone (and a point's own days with its zone, `day_basis=local`):
the same windows (`agdata.timezones`), the same statistics and completeness
rule (D25), the same features. The ET0 estimate across gaps is left out; it belongs to the running totals.
"""

from collections.abc import Collection, Mapping
from datetime import UTC, date, datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

import numpy as np

from agdata.catalog import DAILY_STATISTICS, DAILY_VARIABLES, VARIABLES
from agdata.computed import DAILY_COMPUTED, expand
from agdata.daily import daily_statistic, feature_groups
from agdata.timezones import day_bounds, evening_bounds, overnight_bounds
from agmodels import features
from agmodels.weather import relative_humidity_percent

HOUR = timedelta(hours=1)


_FEATURE_GROUP = feature_groups()


def daily_at_point(
    first_hour: datetime,
    hours: Mapping[str, np.ndarray],
    zone: str,
    first: date,
    last: date,
    names: Collection[str] | None = None,
    rh_90_at: float | None = None,
) -> dict[str, np.ndarray]:
    """Every stored daily variable (or those in `names`, and any others computed with them; a computed one
    (`agdata.computed`) from its inputs, which come back too) for days first..last (inclusive) at a point, by
    `zone`'s clock (the grid's, `timezones.GRID_ZONE`, or the point's own). `rh_90_at`: the RH that "≥ 90%" hours
    are counted at (default D50's gridded 88%; a station's own hours, 90).

    `hours` holds hourly catalog variables, each a series of hours ending at `first_hour`, `first_hour` + 1 h, …
    in stored units. Hours outside a series, and variables not given, count as missing. A series may carry more
    axes after time (several points in the same zone); each day's values then have those axes too.
    """
    rest = np.shape(next(iter(hours.values())))[1:] if hours else ()
    if first_hour.tzinfo is None or first_hour.minute or first_hour.second:
        raise ValueError("pass a timezone-aware first hour on the hour")
    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    tz = ZoneInfo(zone)

    def segment(name: str, begin: datetime, end: datetime) -> np.ndarray:
        """Hours ending begin..end (inclusive), NaN where the series doesn't reach."""
        n = (end - begin) // HOUR + 1
        out = np.full((n, *rest), np.nan)
        values = hours.get(name)
        if values is None:
            return out
        k0 = (begin - first_hour) // HOUR
        lo, hi = max(k0, 0), min(k0 + n, len(values))
        if hi > lo:
            out[lo - k0 : hi - k0] = np.asarray(values[lo:hi], dtype=float)
        return out

    wanted = set(DAILY_VARIABLES) if names is None else set(expand(names, DAILY_COMPUTED))
    statistics = [s for s in DAILY_STATISTICS.values() if s.variable.name in wanted]
    groups = {group for name in wanted if (group := _FEATURE_GROUP.get(name)) is not None}
    out: dict[str, np.ndarray] = {}

    def put(k0: int, k1: int, values: Mapping[str, np.ndarray]) -> None:
        for name, value in values.items():
            if name not in out:
                out[name] = np.full((len(days), *rest), np.nan)
            out[name][k0:k1] = np.broadcast_to(np.asarray(value, dtype=float), (k1 - k0, *rest))

    def stacked(name: str, begin: datetime, length: int, count: int) -> np.ndarray:
        """`count` windows of `length` hours from `begin`, one after another, as (hours, windows, *rest)."""
        hours_read = segment(name, begin, begin + (length * count - 1) * HOUR)
        return np.swapaxes(hours_read.reshape(count, length, *rest), 0, 1)

    def runs(bounds) -> list[tuple[int, int, datetime, int]]:
        """The days as runs (first, past the last, first window's start, hours a window) whose windows (`bounds(day)`)
        follow each other with the same length and clock offset, so each run's hours reshape to (hours, days): every
        grid day is one run; a point's own days break at the changes to and from daylight saving."""
        spans = [bounds(day) for day in days]
        offsets = [begin.astimezone(tz).utcoffset() for begin, _ in spans]
        found, k0 = [], 0
        while k0 < len(days):
            begin, end = spans[k0]
            length = (end - begin) // HOUR + 1
            k1 = k0 + 1
            while (
                k1 < len(days)
                and spans[k1][0] == spans[k1 - 1][1] + HOUR
                and (spans[k1][1] - spans[k1][0]) // HOUR + 1 == length
                and offsets[k1] == offsets[k0]
            ):
                k1 += 1
            found.append((k0, k1, begin, length))
            k0 = k1
        return found

    def humid(begin: datetime, length: int, count: int) -> dict[str, np.ndarray]:
        temperature = stacked("air_temperature", begin, length, count)
        dew_point = stacked("dew_point", begin, length, count)
        return {
            "temperature": temperature,
            "dew_point": dew_point,
            "rh": relative_humidity_percent(temperature, dew_point),
        }

    for k0, k1, begin, length in runs(lambda day: day_bounds(day, zone)):
        count = k1 - k0
        values: dict[str, np.ndarray] = {
            s.variable.name: daily_statistic(stacked(s.hourly, begin, length, count), s) for s in statistics
        }
        if "calendar" in groups:
            h = humid(begin, length, count)
            values |= features.calendar_features(h["temperature"], h["rh"], h["dew_point"], rh_90_at=rh_90_at)
        if "soil" in groups:
            values |= features.soil_features(
                stacked("soil_temperature_4cm", begin, length, count),
                stacked("soil_temperature_10cm", begin, length, count),
                stacked("soil_temperature_30cm", begin, length, count),
            )
        if "chill" in groups:
            values |= features.chill_features(stacked("air_temperature", begin, length, count))
        if "livestock" in groups:
            h = humid(begin, length, count)
            values |= features.livestock_features(
                h["temperature"],
                h["rh"],
                stacked("wind_speed", begin, length, count),
                stacked("shortwave_radiation", begin, length, count),
            )
        put(k0, k1, values)
    if "evening" in groups:
        for k0, k1, begin, length in runs(lambda day: evening_bounds(day, zone)):
            h = humid(begin, length, k1 - k0)
            local_hour = np.array([(begin + n * HOUR).astimezone(tz).hour for n in range(length)])
            put(k0, k1, features.evening_features(h["temperature"], h["rh"], local_hour, rh_90_at=rh_90_at))
    if "overnight" in groups:
        for k0, k1, begin, length in runs(lambda day: overnight_bounds(day, zone)):
            put(k0, k1, features.overnight_features(stacked("air_temperature", begin, length, k1 - k0)))
    for name in names or ():
        c = DAILY_COMPUTED.get(name)
        if c is not None and all(each in out for each in c.inputs):
            out[name] = c.compute(out)
    return out


# A day's hours that give every daily variable a value: humid (RH ≈ 97%, so the humid-hour means exist) and frozen
# soil (so the soil-hour counts aren't all zero by construction); anything else at 1 above its QC minimum
_PROBE = {
    "air_temperature": 20.0,
    "dew_point": 19.5,
    "relative_humidity": 97.0,
    "soil_temperature_4cm": -5.0,
    "soil_temperature_10cm": -5.0,
    "soil_temperature_30cm": -5.0,
}


@cache
def hourly_sources() -> dict[str, tuple[str, ...]]:
    """For each daily variable `daily_at_point` makes, the hourly variables it's made from (in catalog order): found
    by rolling up one probe day with every hourly variable, then with each left out in turn, and seeing which daily
    values go missing. So the table always says what the rollup does (`GET /models/{id}`'s `derivable_from_hourly`,
    and which station variables a POSTed run needs, D58)."""
    day, first_hour, n = date(2025, 7, 15), datetime(2025, 7, 14, tzinfo=UTC), 72  # the day, with a day either side

    def roll_up(left_out: str | None) -> dict[str, np.ndarray]:
        hours = {
            name: np.full(n, _PROBE.get(name, (v.valid_min if np.isfinite(v.valid_min) else 0.0) + 1))
            for name, v in VARIABLES.items()
            if name != left_out
        }
        return daily_at_point(first_hour, hours, "America/Chicago", day, day)

    whole = roll_up(None)
    unmade = [name for name, value in whole.items() if np.isnan(value).all()]
    if unmade:
        raise RuntimeError(f"the probe day leaves {', '.join(unmade)} missing; adjust _PROBE")
    needs: dict[str, list[str]] = {name: [] for name in whole}
    for hourly in VARIABLES:
        for name, value in roll_up(hourly).items():
            if np.isnan(value).all():
                needs[name].append(hourly)
    for c in DAILY_COMPUTED.values():  # a computed variable needs what its inputs need
        wanted = {hourly for each in c.inputs for hourly in needs[each]}
        needs[c.name] = [hourly for hourly in VARIABLES if hourly in wanted]
    return {name: tuple(sources) for name, sources in needs.items()}
