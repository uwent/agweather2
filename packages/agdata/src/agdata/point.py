"""Daily values at one point from its hourly series, by the same definitions as the grid rollup (`agdata.daily`).

A point outside the box (Open-Meteo) or a point read from the hourly store goes through here, so its days match
the daily store's cell for cell: the same local-day and 8 pm-day bounds, the same statistics and completeness
rule (D25), the same features. The ET0 estimate across gaps is left out; it belongs to the running totals.
"""

from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

import numpy as np

from agdata.catalog import DAILY_STATISTICS, VARIABLES
from agdata.daily import daily_statistic
from agdata.timezones import day_bounds, from_8pm_bounds
from agmodels import features
from agmodels.weather import relative_humidity_percent

HOUR = timedelta(hours=1)


def daily_at_point(
    first_hour: datetime, hours: Mapping[str, np.ndarray], zone: str, first: date, last: date
) -> dict[str, np.ndarray]:
    """Every daily variable for local days first..last (inclusive) at a point in `zone`.

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

    def humid(begin: datetime, end: datetime) -> dict[str, np.ndarray]:
        temperature = segment("air_temperature", begin, end)
        dew_point = segment("dew_point", begin, end)
        return {
            "temperature": temperature,
            "dew_point": dew_point,
            "rh": relative_humidity_percent(temperature, dew_point),
        }

    out: dict[str, list[np.ndarray]] = {}
    for day in days:
        begin, end = day_bounds(day, zone)
        values: dict[str, np.ndarray] = {
            s.variable.name: daily_statistic(segment(s.hourly, begin, end), s) for s in DAILY_STATISTICS.values()
        }
        h = humid(begin, end)
        values |= features.calendar_features(h["temperature"], h["rh"], h["dew_point"])
        values |= features.soil_features(
            segment("soil_temperature_4cm", begin, end),
            segment("soil_temperature_10cm", begin, end),
            segment("soil_temperature_30cm", begin, end),
        )
        begin, end = from_8pm_bounds(day, zone)
        h = humid(begin, end)
        local_hour = np.array([(begin + n * HOUR).astimezone(tz).hour for n in range(len(h["rh"]))])
        values |= features.from_8pm_features(h["temperature"], h["rh"], features.is_night(local_hour))
        for name, value in values.items():
            out.setdefault(name, []).append(np.broadcast_to(np.asarray(value, dtype=float), rest))
    return {name: np.array(series) for name, series in out.items()}


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
    return {name: tuple(sources) for name, sources in needs.items()}
