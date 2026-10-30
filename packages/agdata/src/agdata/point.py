"""Daily values at one point from its hourly series, by the same definitions as the grid rollup (`agdata.daily`).

A point outside the box (Open-Meteo) or a point read from the hourly store goes through here, so its days match
the daily store's cell for cell: the same local-day and 8 pm-day bounds, the same statistics and completeness
rule (D25), the same features. The ET0 estimate across gaps is left out; it belongs to the running totals.
"""

from collections.abc import Mapping
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from agdata.catalog import DAILY_STATISTICS
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
    in stored units. Hours outside a series, and variables not given, count as missing.
    """
    if first_hour.tzinfo is None or first_hour.minute or first_hour.second:
        raise ValueError("pass a timezone-aware first hour on the hour")
    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    tz = ZoneInfo(zone)

    def segment(name: str, begin: datetime, end: datetime) -> np.ndarray:
        """Hours ending begin..end (inclusive), NaN where the series doesn't reach."""
        n = (end - begin) // HOUR + 1
        out = np.full(n, np.nan)
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

    out: dict[str, list[float]] = {}
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
            out.setdefault(name, []).append(float(value))
    return {name: np.array(series) for name, series in out.items()}
