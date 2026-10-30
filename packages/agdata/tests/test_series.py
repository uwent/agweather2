from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import forecast, series

HOUR = timedelta(hours=1)
CYCLE = datetime(2025, 7, 10, 13, tzinfo=UTC)
OBSERVED_UNTIL = CYCLE + 2 * HOUR  # 15Z: 10 am CDT
NOW = CYCLE + 3 * HOUR
CELL = (900, 1401)  # (j, i)


@pytest.fixture(scope="module")
def world(tmp_path_factory, fx_module):
    path = tmp_path_factory.mktemp("series")
    fx_module.archive(path, datetime(2025, 7, 1, tzinfo=UTC), OBSERVED_UNTIL)
    run = forecast.write_run(path, fx_module.window, fx_module.nbm_run(CYCLE), pressure_kpa=98.0)
    forecast.publish(path, run)
    return path


def test_hours_switch_to_the_forecast_after_the_last_observed_hour(world):
    frame = series.point_hours(world, *CELL, CYCLE, CYCLE + 5 * HOUR, ["air_temperature", "et0"], now=NOW)
    assert frame.kinds == ["observed"] * 3 + ["forecast"] * 3
    assert frame.sources["air_temperature"] == ["urma"] * 3 + ["nbm"] * 3
    assert frame.sources["et0"][3:] == ["derived"] * 3
    t = frame.values["air_temperature"]
    assert t[2] == pytest.approx(15 + 6 * np.sin(2 * np.pi * (15 - 15) / 24), abs=0.05)  # the archive's 15 °C
    assert t[3] == pytest.approx(25 + 6 * np.sin(2 * np.pi * (16 - 15) / 24), abs=0.05)  # the run's 25 °C
    assert frame.forecast.cycle == CYCLE


def test_days_observed_partial_forecast(world):
    days = series.point_days(
        world, *CELL, date(2025, 7, 8), date(2025, 7, 23), ["air_temperature_max"], totals=["dd_sine_50"], now=NOW
    )
    assert days.zone == "America/Chicago"
    assert days.kinds[:2] == ["observed", "observed"]
    assert days.kinds[2] == "partial"  # July 10: observed to 10 am, then forecast
    assert days.kinds[3:13] == ["forecast"] * 10
    assert days.kinds[14:] == [None, None]  # past the run's last hour (July 21 13Z)
    tmax = days.values["air_temperature_max"]
    assert tmax[1] == pytest.approx(21.0) and tmax[2] == pytest.approx(31.0) and tmax[5] == pytest.approx(31.0)
    dd = days.totals["dd_sine_50"]
    assert np.all(np.diff(dd[:13]) > 0) and dd[4] - dd[3] > dd[1] - dd[0]  # forecast days are warmer


def test_without_a_fresh_run_the_series_ends_with_the_archive(world):
    later = NOW + timedelta(hours=13)
    days = series.point_days(world, *CELL, date(2025, 7, 9), date(2025, 7, 12), ["air_temperature_max"], now=later)
    assert days.forecast.path is None and days.forecast.reason == "stale"
    assert days.kinds == ["observed", None, None, None]
    assert np.isnan(days.values["air_temperature_max"][1:]).all()
    frame = series.point_hours(world, *CELL, CYCLE, CYCLE + 4 * HOUR, ["air_temperature"], now=later)
    assert frame.kinds == ["observed"] * 3 + [None, None]


def test_map_days_by_kind(world, fx_module):
    window = fx_module.window
    values, kind = series.grid_day(world, "air_temperature_max", date(2025, 7, 9), window, now=NOW)
    assert kind == "observed" and values == pytest.approx(np.full(window.shape, 21.0))
    values, kind = series.grid_day(world, "air_temperature_max", date(2025, 7, 10), window, now=NOW)
    assert kind == "partial" and values == pytest.approx(np.full(window.shape, 31.0))
    _, kind = series.grid_day(world, "air_temperature_max", date(2025, 7, 15), window, now=NOW)
    assert kind == "forecast"
    total, kind = series.grid_total(world, "dd_sine_50", date(2025, 7, 15), window, now=NOW)
    assert kind == "forecast" and np.isfinite(total).all()
