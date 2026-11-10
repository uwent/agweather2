"""A point's days rolled up in runs of days (`point.daily_at_point`, 2026-11-06) against the day-by-day rollup it
replaced, kept here as the reference: grid days (one run), a point's own days across both changes of daylight
saving (23- and 25-hour days), gaps, a window the series doesn't reach, and points as a trailing axis."""

from collections.abc import Collection, Mapping
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from agdata.catalog import DAILY_STATISTICS, DAILY_VARIABLES, VARIABLES
from agdata.daily import daily_statistic
from agdata.point import _FEATURE_GROUP, daily_at_point
from agdata.timezones import GRID_ZONE, day_bounds, evening_bounds, overnight_bounds
from agmodels import features
from agmodels.weather import relative_humidity_percent

HOUR = timedelta(hours=1)
NAMES = [name for name in DAILY_VARIABLES if name != "et0_sum_estimate"]


def _daily_at_point_day_by_day(
    first_hour: datetime,
    hours: Mapping[str, np.ndarray],
    zone: str,
    first: date,
    last: date,
    names: Collection[str] | None = None,
    rh_90_at: float | None = None,
) -> dict[str, np.ndarray]:
    """Every daily variable (or those in `names`, and any others computed with them) for days first..last
    (inclusive) at a point, by `zone`'s clock (the grid's, `timezones.GRID_ZONE`, or the point's own). `rh_90_at`: the
    RH that "≥ 90%" hours are counted at (default D50's gridded 88%; a station's own hours, 90).

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

    wanted = set(DAILY_VARIABLES) if names is None else set(names)
    statistics = [s for s in DAILY_STATISTICS.values() if s.variable.name in wanted]
    groups = {group for name in wanted if (group := _FEATURE_GROUP.get(name)) is not None}
    out: dict[str, list[np.ndarray]] = {}
    for day in days:
        begin, end = day_bounds(day, zone)
        values: dict[str, np.ndarray] = {
            s.variable.name: daily_statistic(segment(s.hourly, begin, end), s) for s in statistics
        }
        if "calendar" in groups:
            h = humid(begin, end)
            values |= features.calendar_features(h["temperature"], h["rh"], h["dew_point"], rh_90_at=rh_90_at)
        if "soil" in groups:
            values |= features.soil_features(
                segment("soil_temperature_4cm", begin, end),
                segment("soil_temperature_10cm", begin, end),
                segment("soil_temperature_30cm", begin, end),
            )
        if "chill" in groups:
            values |= features.chill_features(segment("air_temperature", begin, end))
        if "livestock" in groups:
            h = humid(begin, end)
            wind, sun = segment("wind_speed", begin, end), segment("shortwave_radiation", begin, end)
            values |= features.livestock_features(h["temperature"], h["rh"], wind, sun)
        if "evening" in groups:
            begin, end = evening_bounds(day, zone)
            h = humid(begin, end)
            local_hour = np.array([(begin + n * HOUR).astimezone(tz).hour for n in range(len(h["rh"]))])
            values |= features.evening_features(h["temperature"], h["rh"], local_hour, rh_90_at=rh_90_at)
        if "overnight" in groups:
            values |= features.overnight_features(segment("air_temperature", *overnight_bounds(day, zone)))
        for name, value in values.items():
            out.setdefault(name, []).append(np.broadcast_to(np.asarray(value, dtype=float), rest))
    return {name: np.array(series) for name, series in out.items()}


def _hours(n: int, points: int | None, rng: np.random.Generator) -> dict[str, np.ndarray]:
    shape = (n,) if points is None else (n, points)
    hour = np.arange(n).reshape((n,) + (1,) * (len(shape) - 1))
    t = 5 + 10 * np.sin(2 * np.pi * (hour - 15) / 24) + rng.normal(0, 2, shape)
    low = {name: v.valid_min if np.isfinite(v.valid_min) else 0.0 for name, v in VARIABLES.items()}
    hours = {name: rng.uniform(low[name], low[name] + 30, shape) for name in VARIABLES}
    hours |= {"air_temperature": t, "dew_point": t - np.abs(rng.normal(1, 3, shape))}
    hours["soil_temperature_4cm"] = t / 2 - 3
    for v in hours.values():
        v[rng.random(shape) < 0.03] = np.nan  # scattered gaps
    hours["precipitation"][200:230] = np.nan  # a block: a day without a total
    return hours


@pytest.mark.parametrize("zone", [GRID_ZONE, "America/Chicago", "America/New_York"])
@pytest.mark.parametrize("points", [None, 3])
def test_runs_of_days_give_the_day_by_day_rollup(zone, points):
    rng = np.random.default_rng(11)
    first_hour = datetime(2025, 3, 1, tzinfo=UTC)
    n = 24 * 260  # March through mid-November: both changes of daylight saving
    hours = _hours(n, points, rng)
    first, last = date(2025, 2, 27), date(2025, 11, 20)  # before and past the series: missing days at both ends
    found = daily_at_point(first_hour, hours, zone, first, last)
    expected = _daily_at_point_day_by_day(first_hour, hours, zone, first, last)
    assert list(found) == list(expected)
    for name, values in expected.items():
        assert found[name].shape == values.shape, name
        np.testing.assert_allclose(found[name], values, rtol=1e-12, atol=1e-12, err_msg=name)
    assert np.isnan(found["air_temperature_max"][:2]).all()  # the days before the series


def test_some_names_and_a_station_threshold_give_the_day_by_day_rollup():
    rng = np.random.default_rng(5)
    first_hour = datetime(2025, 10, 20, tzinfo=UTC)
    hours = _hours(24 * 20, None, rng)
    names = ["air_temperature_min", "hours_rh_over_90_from_6pm", "air_temperature_min_overnight"]
    args = (first_hour, hours, "America/Chicago", date(2025, 10, 21), date(2025, 11, 7))
    found = daily_at_point(*args, names=names, rh_90_at=90.0)
    expected = _daily_at_point_day_by_day(*args, names=names, rh_90_at=90.0)
    assert list(found) == list(expected)
    for name, values in expected.items():
        np.testing.assert_allclose(found[name], values, rtol=1e-12, atol=1e-12, err_msg=name)
