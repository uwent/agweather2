from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import forecast, series
from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.cumulative import update_days
from agdata.daily import days_from_hours
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore
from agdata.timezones import GRID_ZONE

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
    assert days.zone == GRID_ZONE  # the grid's days by default (D74)
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
        elif model_id == "red-crown-rot":  # the typical planting's R1 comes after July 20: not started
            assert result.reason == "R1 isn't reached in the series"
        else:
            assert result.reason is None, (model_id, result.reason)

    # Degree days from a biofix inside the stored days: the forecast's warmer days add more
    dd = series.model_at_point(
        world, lat, lon, "degree-days", date(2025, 7, 5), date(2025, 7, 20), biofix=date(2025, 7, 2), now=NOW
    )
    daily = dd.outputs["dd"]
    assert np.isfinite(daily).all() and daily[8] > daily[0] + 10


def test_models_read_their_days_once_and_match_running_alone(world, monkeypatch):
    from agdata.grid import NDFD
    from agmodels.registry import all_models

    lat, lon = (float(v) for v in NDFD.latlon(*CELL))
    start, end = date(2025, 7, 5), date(2025, 7, 20)
    runs = [series.RunSpec(model_id=model_id) for model_id in sorted(all_models())]
    runs.append(series.RunSpec(model_id="degree-days", biofix=date(2025, 7, 2)))  # a biofix before the others' days
    runs.append(series.RunSpec(model_id="frogeye-leaf-spot", planting=date(2025, 7, 3)))  # gated, its own planting
    alone = [
        series.model_at_point(
            world,
            lat,
            lon,
            run.model_id,
            start,
            end,
            biofix=run.biofix,
            planting=run.planting,
            options=dict(run.options),
            now=NOW,
        )
        for run in runs
    ]
    real, reads = series.point_days, []

    def counted(*args, **kwargs):
        reads.append(args[3:5])
        return real(*args, **kwargs)

    monkeypatch.setattr(series, "point_days", counted)
    together = series.models_at_point(world, lat, lon, runs, start, end, now=NOW)
    assert len(reads) == 1
    for one, shared in zip(alone, together, strict=True):
        assert (shared.model_id, shared.dates, shared.kinds) == (one.model_id, one.dates, one.kinds)
        assert (shared.biofix, shared.reason) == (one.biofix, one.reason), one.model_id
        assert shared.outputs.keys() == one.outputs.keys()
        for name, values in one.outputs.items():
            np.testing.assert_array_equal(shared.outputs[name], values, err_msg=f"{one.model_id} {name}")
        for left, right in ((shared.level, one.level), (shared.susceptibility, one.susceptibility)):
            assert (left is None) == (right is None)
            if left is not None:
                np.testing.assert_array_equal(left, right)
        assert shared.estimated.keys() == one.estimated.keys() and shared.missing.keys() == one.missing.keys()


def test_a_slice_starts_inside_the_series(world):
    days = series.point_days(world, *CELL, date(2025, 7, 3), date(2025, 7, 6), ["air_temperature_max"], now=NOW)
    part = series.sliced(days, date(2025, 7, 5), ["air_temperature_max"])
    assert part.dates == [date(2025, 7, 5), date(2025, 7, 6)] and part.kinds == days.kinds[2:]
    with pytest.raises(ValueError, match="before the series"):
        series.sliced(days, date(2025, 7, 2), ["air_temperature_max"])


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
    assert days.zone == GRID_ZONE
    assert days.kinds == [None, None]
    assert np.isnan(days.values["air_temperature_max"]).all() and np.isnan(days.totals["dd_sine_50"]).all()


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


# --- Range reads for maps (Phase 5 E) ------------------------------------------------------------------------------


def test_a_range_of_map_days_matches_each_day_read_alone(world, fx_module):
    window = fx_module.window
    first, last = date(2025, 7, 8), date(2025, 7, 20)
    found = series.grid_days(world, DAILY, "air_temperature_max", first, last, window, now=NOW)
    for k, day in enumerate(found.steps):
        values, kind = series.grid_day(world, "air_temperature_max", day, window, now=NOW)
        assert found.kinds[k] == kind, day
        np.testing.assert_array_equal(found.values[k], values)
    assert found.kinds[:2] == ["observed", "observed"] and found.kinds[2] == "partial"
    assert found.run_from == 2 and not found.stale.any()
    assert "urma" in found.sources and "nbm" in found.sources


def test_map_kinds_alone_read_nothing(world, fx_module):
    found = series.grid_days(
        world, DAILY, "air_temperature_max", date(2025, 7, 8), date(2025, 7, 12), fx_module.window, now=NOW, read=False
    )
    assert np.isnan(found.values).all() and found.kinds[:3] == ["observed", "observed", "partial"]


def test_a_range_of_running_totals_switches_to_the_run(world, fx_module):
    found = series.grid_days(
        world, CUMULATIVE, "dd_sine_50", date(2025, 7, 8), date(2025, 7, 14), fx_module.window, now=NOW
    )
    for k, day in enumerate(found.steps):
        total, kind = series.grid_total(world, "dd_sine_50", day, fx_module.window, now=NOW)
        assert found.kinds[k] == kind
        np.testing.assert_array_equal(found.values[k], total)


def test_map_hours_match_a_point_hour_by_hour(world, fx_module):
    start, end = CYCLE - 3 * HOUR, CYCLE + 6 * HOUR
    found = series.grid_hours(world, "air_temperature", start, end, fx_module.window, now=NOW)
    frame = series.point_hours(world, *CELL, start, end, ["air_temperature"], now=NOW)
    y, x = fx_module.window.local(*CELL)
    np.testing.assert_allclose(found.values[:, y, x], frame.values["air_temperature"], rtol=1e-6)
    assert found.kinds == frame.kinds
    assert found.kinds[0] == "observed" and found.kinds[-1] == "forecast"


def test_a_stale_daily_variable_is_flagged(world, fx_module, monkeypatch):
    newer = replace(DAILY_VARIABLES["air_temperature_max"], version=DAILY_VARIABLES["air_temperature_max"].version + 1)
    monkeypatch.setitem(DAILY_VARIABLES, "air_temperature_max", newer)
    found = series.grid_days(
        world, DAILY, "air_temperature_max", date(2025, 7, 8), date(2025, 7, 9), fx_module.window, now=NOW
    )
    assert found.stale.all()


def test_days_from_hours_are_the_rollups_days(world, fx_module):
    store = GridStore.open(world, DAILY, 2025, DAILY_VARIABLES.values())
    computed = days_from_hours(world, fx_module.window, date(2025, 7, 5), date(2025, 7, 6))
    for name in ("air_temperature_max", "precipitation_sum", "hours_rh_over_90"):
        t = store.index_of(date(2025, 7, 5))
        np.testing.assert_allclose(computed[name], store.read_steps(name, t, t + 2), atol=store_step(name))


def store_step(name: str) -> float:
    return DAILY_VARIABLES[name].scale / 2 + 1e-6


def test_the_stamp_takes_a_range_from_january_first(tmp_path, fx):
    fx.archive(tmp_path, datetime(2024, 12, 20, tzinfo=UTC), datetime(2025, 1, 10, tzinfo=UTC))
    now = datetime(2025, 1, 11, tzinfo=UTC)
    stamp = series.last_written(tmp_path, date(2025, 1, 1), date(2025, 1, 5), totals=["dd_sine_50"], now=now)
    assert not stamp.startswith("None")
    daily = series.last_written(
        tmp_path, date(2025, 1, 1), date(2025, 1, 5), daily=["air_temperature_max"], hourly=[], now=now
    )
    assert not daily.startswith("None") and daily != stamp


def test_a_grid_day_closes_with_its_last_reading_at_06z():
    assert series.last_closed_day(datetime(2026, 7, 2, 6, tzinfo=UTC)) == date(2026, 7, 1)
    assert series.last_closed_day(datetime(2026, 7, 2, 5, tzinfo=UTC)) == date(2026, 6, 30)
