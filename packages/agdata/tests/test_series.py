from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import forecast, series
from agdata.catalog import VARIABLES
from agdata.cumulative import update_days
from agdata.store import HOURLY, GridStore

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


def test_forecast_soil_gaps_are_filled_from_another_source(world):
    asked = []

    def fill_soil(first_hour, last_hour, names):
        asked.append((first_hour, last_hour, names))
        n = (last_hour - first_hour) // HOUR + 1
        return {name: np.full(n, 12.0) for name in names}

    last = datetime(2025, 7, 21, 15, tzinfo=UTC)  # two hours past the run's last
    names = ["air_temperature", "soil_temperature_10cm"]
    frame = series.point_hours(world, *CELL, CYCLE, last, names, now=NOW, fill_soil=fill_soil)
    assert asked == [(CYCLE + 3 * HOUR, last - 2 * HOUR, ["soil_temperature_10cm"])]
    soil, sources = frame.values["soil_temperature_10cm"], frame.sources["soil_temperature_10cm"]
    assert np.all(soil[3:-2] == 12.0) and set(sources[3:-2]) == {"openmeteo"}
    assert np.isnan(soil[-2:]).all() and sources[-2:] == [None, None]
    assert np.isnan(soil[:3]).all() and sources[:3] == [None] * 3  # observed gaps stay gaps
    assert set(frame.sources["air_temperature"][3:-2]) == {"nbm"}


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


def test_every_model_runs_at_a_point_through_the_forecast(world, monkeypatch):
    # Models share most of their inputs: read each distinct request from the stores once
    real, answers = series.point_days, {}

    def point_days_once(data_dir, j, i, first, last, names, totals=(), **kwargs):
        key = (first, last, tuple(names), tuple(totals), tuple(kwargs))
        if key not in answers:
            answers[key] = real(data_dir, j, i, first, last, names, totals=totals, **kwargs)
        return answers[key]

    monkeypatch.setattr(series, "point_days", point_days_once)
    from agdata.grid import NDFD
    from agmodels.registry import all_models

    lat, lon = (float(v) for v in NDFD.latlon(*CELL))
    for model_id in sorted(all_models()):
        result = series.model_at_point(world, lat, lon, model_id, date(2025, 7, 5), date(2025, 7, 20), now=NOW)
        assert result.kinds[:5] == ["observed"] * 5 and result.kinds[5] == "partial", model_id
        assert result.kinds[6:] == ["forecast"] * 10, model_id
        region = all_models()[model_id].SPEC.region
        if region and "WI" not in region:  # pecan scab, cotton planting
            assert result.reason == "outside the model's region"
        elif result.biofix is not None and result.biofix > date(2025, 7, 20):  # corn earworm's August 1
            assert result.reason == "biofix after the series"
        else:
            assert result.reason is None, (model_id, result.reason)

    # Degree days from a biofix inside the stored days: the forecast's warmer days add more
    dd = series.model_at_point(
        world, lat, lon, "degree-days", date(2025, 7, 5), date(2025, 7, 20), biofix=date(2025, 7, 2), now=NOW
    )
    daily = dd.outputs["dd"]
    assert np.isfinite(daily).all() and daily[8] > daily[0] + 10


def test_no_published_run_means_no_forecast(tmp_path):
    found = series.current_forecast(tmp_path, NOW)
    assert (found.path, found.reason) == (None, "none")


def test_a_point_off_the_grid_is_refused(world):
    with pytest.raises(ValueError, match="off the grid"):
        series.model_at_point(world, 10.0, -88.0, "degree-days", date(2025, 7, 5), date(2025, 7, 20), now=NOW)


def test_days_in_a_year_without_stores_are_missing(world, tmp_path):
    days = series.point_days(
        world, *CELL, date(2024, 7, 9), date(2024, 7, 10), ["air_temperature_max"], totals=["dd_sine_50"], now=NOW
    )
    assert days.zone == "America/Chicago"  # the cell's own zone, without a daily store to read it from
    assert days.kinds == [None, None]
    assert np.isnan(days.values["air_temperature_max"]).all() and np.isnan(days.totals["dd_sine_50"]).all()
    with pytest.raises(FileNotFoundError, match="no daily store"):
        series.cell_zone(tmp_path, *CELL, years=[2024])


def test_a_day_on_the_map_in_a_year_without_stores_is_missing_not_observed(world, fx_module):
    values, kind = series.grid_day(world, "air_temperature_max", date(2024, 7, 9), fx_module.window, now=NOW)
    assert values.shape == fx_module.window.shape and np.isnan(values).all()
    assert kind is None


def test_the_written_stamp_changes_only_when_the_days_read_are_rewritten(tmp_path, fx):
    fx.archive(tmp_path, datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 20, tzinfo=UTC))
    now = datetime(2025, 7, 21, tzinfo=UTC)

    def stamp(first: date, last: date) -> str:
        return series.last_written(tmp_path, first, last, totals=["dd_sine_50"], now=now)

    early, late = stamp(date(2025, 7, 3), date(2025, 7, 5)), stamp(date(2025, 7, 14), date(2025, 7, 16))
    assert early == stamp(date(2025, 7, 3), date(2025, 7, 5))  # nothing written: the same
    assert early.endswith(":none")  # no forecast run published

    store = GridStore.open(tmp_path, HOURLY, 2025, VARIABLES.values())
    store.write(
        datetime(2025, 7, 15, 12, tzinfo=UTC), {"air_temperature": np.full((1, *fx.window.shape), 20.0)}, "urma"
    )
    assert stamp(date(2025, 7, 3), date(2025, 7, 5)) == early  # a write outside the days read
    assert stamp(date(2025, 7, 14), date(2025, 7, 16)) != late

    late = stamp(date(2025, 7, 14), date(2025, 7, 16))
    update_days(tmp_path, fx.window, date(2025, 7, 15), date(2025, 7, 15))  # the totals from July 15 on
    assert stamp(date(2025, 7, 14), date(2025, 7, 16)) != late
