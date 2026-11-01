import shutil
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import calibration, forecast
from agdata.catalog import VARIABLES
from agdata.grid import Window
from agdata.sources.nbm import HORIZON_HOURS
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)  # 2 x 3 cells near Madison
HOUR = timedelta(hours=1)


@pytest.fixture(autouse=True)
def no_calibration(monkeypatch):
    """These tests check the stitch and the stores; the calibration is tested in test_nbm."""
    monkeypatch.setattr(forecast, "CALIBRATION", calibration.Adjustments())


CYCLE = datetime(2025, 7, 10, 13, tzinfo=UTC)


@pytest.fixture(scope="module")
def july_archive(tmp_path_factory, fx_module):
    """July 1 through two hours past CYCLE, built once; `copy_of_july_archive` gives a test its own copy."""
    path = tmp_path_factory.mktemp("july")
    fx_module.archive(path, datetime(2025, 7, 1, tzinfo=UTC), CYCLE + 2 * HOUR)
    return path


@pytest.fixture
def copy_of_july_archive(july_archive, tmp_path):
    shutil.copytree(july_archive, tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_a_run_continues_the_archive(tmp_path, fx):
    cycle = datetime(2025, 7, 10, 13, tzinfo=UTC)
    fx.archive(tmp_path, datetime(2025, 6, 25, tzinfo=UTC), cycle + 2 * HOUR)  # RTMA reaches past the cycle
    path = forecast.write_run(tmp_path, WINDOW, fx.nbm_run(cycle), pressure_kpa=98.0)
    info = forecast.run_info(path)
    assert info["last_observed"] == (cycle + 2 * HOUR).isoformat()
    assert info["first_day"] == "2025-07-09"

    hourly = GridStore.open(path, HOURLY, 2025, VARIABLES.values())
    t = hourly.index_of(cycle)
    sources = hourly.sources("air_temperature")
    assert sources[t - 47 : t + 3] == ["urma"] * 50  # 48 hours before the first forecast hour, through observed
    assert sources[t + 3] == "nbm" and sources[t + HORIZON_HOURS] == "nbm"
    assert hourly.sources("relative_humidity")[t + 3] == "derived"
    assert hourly.sources("soil_temperature_4cm")[t + 3] is None  # no soil given

    # A day the archive covers is the archive's; the next mixes; a forecast day is the forecast's
    assert fx.read(path, DAILY, "air_temperature_max", date(2025, 7, 9)).max() == pytest.approx(21.0)
    assert fx.read(path, DAILY, "air_temperature_max", date(2025, 7, 10)).max() == pytest.approx(31.0)
    assert fx.read(path, DAILY, "air_temperature_min", date(2025, 7, 10)).min() == pytest.approx(9.0)
    assert fx.read(path, DAILY, "air_temperature_min", date(2025, 7, 12)).min() == pytest.approx(19.0)

    # Running totals: the archive's through the first day, then the run's days added
    archived = fx.read(tmp_path, CUMULATIVE, "dd_sine_50", date(2025, 7, 9))
    np.testing.assert_allclose(fx.read(path, CUMULATIVE, "dd_sine_50", date(2025, 7, 9)), archived, atol=0.5)
    later = fx.read(path, CUMULATIVE, "dd_sine_50", date(2025, 7, 15)) - fx.read(
        path, CUMULATIVE, "dd_sine_50", date(2025, 7, 14)
    )
    assert later == pytest.approx(np.full(WINDOW.shape, (25 * 1.8 + 32) - 50), abs=0.6)  # a day at 25 °C ± 6
    # No missing days added: the count is still the archive's (January 1 to June 25, before its first rolled day)
    missing = fx.read(tmp_path, CUMULATIVE, "temperature_missing_days", date(2025, 7, 9))
    assert (missing == 176).all()
    np.testing.assert_array_equal(fx.read(path, CUMULATIVE, "temperature_missing_days", date(2025, 7, 15)), missing)


def test_publish_swaps_current_and_keeps_two(tmp_path, fx):
    paths = []
    for cycle in (
        datetime(2025, 7, 9, 19, tzinfo=UTC),
        datetime(2025, 7, 10, 1, tzinfo=UTC),
        datetime(2025, 7, 10, 7, tzinfo=UTC),
    ):
        paths.append(forecast.run_path(tmp_path, cycle))
        paths[-1].mkdir(parents=True)  # publishing doesn't read the run
        forecast.publish(tmp_path, paths[-1])
        assert forecast.current_run(tmp_path) == paths[-1].resolve()
    assert not paths[0].exists() and paths[1].exists() and paths[2].exists()
    assert (tmp_path / "forecast" / "current").is_symlink()


def test_totals_restart_on_january_1(tmp_path, fx):
    cycle = datetime(2025, 12, 30, 13, tzinfo=UTC)
    fx.archive(tmp_path, datetime(2025, 12, 15, tzinfo=UTC), cycle)
    path = forecast.write_run(tmp_path, WINDOW, fx.nbm_run(cycle, warm=10.0), pressure_kpa=98.0)
    jan_1 = fx.read(path, CUMULATIVE, "dd_sine_39p2", date(2026, 1, 1))
    jan_2 = fx.read(path, CUMULATIVE, "dd_sine_39p2", date(2026, 1, 2))
    day = (10 * 1.8 + 32) - 39.2
    np.testing.assert_allclose(jan_1, day, atol=0.6)  # only January 1's degree days
    np.testing.assert_allclose(jan_2 - jan_1, day, atol=0.6)
    assert fx.read(path, CUMULATIVE, "dd_sine_39p2", date(2025, 12, 31)).min() > 10 * day


def test_last_observed_hour(tmp_path, fx):
    start, end = datetime(2025, 6, 1, tzinfo=UTC), datetime(2025, 6, 5, 7, tzinfo=UTC)
    hourly = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())  # hours only: no rollup needed
    n = (end - start) // HOUR + 1
    hourly.write(start, {"air_temperature": np.full((n, *WINDOW.shape), 15.0)}, source="urma")
    assert forecast.last_observed_hour(tmp_path, datetime(2025, 6, 10, tzinfo=UTC)) == end
    assert forecast.last_observed_hour(tmp_path, datetime(2025, 6, 5, 3, tzinfo=UTC)) == datetime(
        2025, 6, 5, 3, tzinfo=UTC
    )
    assert forecast.last_observed_hour(tmp_path, datetime(2025, 7, 1, tzinfo=UTC)) is None  # over two weeks back


def test_building_in_strips_matches_the_whole_window(copy_of_july_archive, fx, monkeypatch):
    from agdata.sources import nbm

    tmp_path, cycle = copy_of_july_archive, CYCLE
    truth = fx.nbm_run(cycle)
    rows = np.arange(WINDOW.shape[0])[:, None]

    def step(cycle, lead, window, session):  # a long run's pattern of steps, a different value per row
        n = lead - 1
        values = {"precipitation": truth.values["precipitation"][n] + rows}
        if lead <= 36 or (lead - 2) % 3 == 0:
            values |= {name: truth.values[name][n] + rows for name in nbm.NAMES if name != "precipitation"}
        return values

    monkeypatch.setattr(forecast, "BAND_CELLS", 3)  # one row per strip
    assert forecast.band_rows(WINDOW) == 1
    built = forecast.build_run(tmp_path, WINDOW, cycle, step=step, workers=4, pressure_kpa=98.0)
    assert not (built / "scratch.zarr").exists()
    stored = {
        name: GridStore.open(built, HOURLY, 2025, VARIABLES.values()).read_steps(name, 0, 8760)
        for name in ("air_temperature", "et0", "shortwave_radiation")
    }
    sources = GridStore.open(built, HOURLY, 2025, VARIABLES.values()).sources("et0")

    # The same run filled whole, in memory
    whole = nbm.fetch_run(cycle, WINDOW, step=step, workers=4)
    from agdata.grid import NDFD

    lat, lon = NDFD.window_latlon(WINDOW)
    other = forecast.write_run(tmp_path / "whole", WINDOW, nbm.to_hourly(whole, lat, lon, 98.0), pressure_kpa=98.0)
    expected = GridStore.open(other, HOURLY, 2025, VARIABLES.values())
    t = expected.index_of(cycle + 3 * HOUR)  # forecast hours (the first copy has no archive under it)
    for name, values in stored.items():
        np.testing.assert_array_equal(values[t:], expected.read_steps(name, t, 8760), err_msg=name)
    assert sources[t:] == expected.sources("et0")[t:]
    assert np.isfinite(stored["air_temperature"][t + 100]).all()


def test_a_run_takes_its_soil_and_snow_from_ifs(copy_of_july_archive, fx):
    from agdata.sources import nbm

    tmp_path, cycle = copy_of_july_archive, CYCLE
    truth = fx.nbm_run(cycle)

    def step(cycle, lead, window, session):
        return {name: truth.values[name][lead - 1] for name in nbm.NAMES}

    asked = []

    def soil(times, window):  # IFS's hours reach 100 hours past the cycle
        asked.append(len(times))
        reach = np.array([(t - cycle) / HOUR <= 100 for t in times])[:, None, None]
        shape = (len(times), *window.shape)
        return {
            name: np.where(reach, np.full(shape, 12.0 if name == "snow_depth" else 3.0), np.nan)
            for name in ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm", "snow_depth")
        }

    built = forecast.build_run(tmp_path, WINDOW, cycle, step=step, workers=4, pressure_kpa=98.0, soil=soil)
    assert asked == [nbm.HORIZON_HOURS]
    store = GridStore.open(built, HOURLY, 2025, VARIABLES.values())
    t = store.index_of(cycle + 3 * HOUR)  # the first forecast hour past the archive's
    np.testing.assert_allclose(store.read_steps("soil_temperature_10cm", t, t + 1), 3.0)
    np.testing.assert_allclose(store.read_steps("snow_depth", t, t + 1), 12.0)
    assert store.sources("soil_temperature_10cm")[t] == "ifs" and store.sources("snow_depth")[t] == "ifs"
    later = store.index_of(cycle + 101 * HOUR)
    assert np.isnan(store.read_steps("soil_temperature_10cm", later, later + 1)).all()  # past IFS's reach: a gap


def write_pressure_days(data_dir, year, first_day, pressures):
    from agdata.daily import open_or_create_daily

    shape = (len(pressures), *WINDOW.shape)
    values = np.broadcast_to(np.asarray(pressures, dtype=float)[:, None, None], shape)
    open_or_create_daily(data_dir, year, WINDOW).write(first_day, {"surface_pressure_mean": values}, source="derived")


def test_the_forecast_borrows_the_archives_recent_mean_pressure(tmp_path, fx):
    write_pressure_days(tmp_path, 2025, date(2025, 6, 1), [98.0, 99.0, np.nan, 100.0])
    mean = forecast.archive_pressure_kpa(tmp_path, WINDOW, date(2025, 6, 5))
    np.testing.assert_allclose(mean, 99.0, atol=0.05)  # the missing day is left out of the mean, not counted as 0
    assert np.isnan(forecast.archive_pressure_kpa(tmp_path, WINDOW, date(2025, 5, 31))).all()  # nothing before June 1


def test_the_pressure_window_reaches_back_into_the_previous_year_when_it_has_a_store(tmp_path, fx):
    write_pressure_days(tmp_path, 2024, date(2024, 12, 30), [96.0, 97.0])
    write_pressure_days(tmp_path, 2025, date(2025, 1, 1), [98.0, 99.0])
    mean = forecast.archive_pressure_kpa(tmp_path, WINDOW, date(2025, 1, 3))
    np.testing.assert_allclose(mean, 97.5, atol=0.05)
    no_archive = forecast.archive_pressure_kpa(tmp_path / "other", WINDOW, date(2025, 1, 3))  # no archive at all
    assert np.isnan(no_archive).all()


def test_a_cell_the_archive_has_no_pressure_for_gets_a_typical_value(tmp_path):
    from agdata.gaps import FALLBACK_PRESSURE_KPA

    first = datetime(2025, 7, 10, 14, tzinfo=UTC)
    given = np.array([[98.0, np.nan, 97.0], [np.nan, np.nan, 99.0]])
    assert forecast._pressure(tmp_path, WINDOW, first, given).tolist() == [
        [98.0, FALLBACK_PRESSURE_KPA, 97.0],
        [FALLBACK_PRESSURE_KPA, FALLBACK_PRESSURE_KPA, 99.0],
    ]
    assert (forecast._pressure(tmp_path, WINDOW, first, None) == FALLBACK_PRESSURE_KPA).all()  # no archive either


def test_publishing_clears_a_pointer_left_by_a_crashed_publish(tmp_path):
    run = forecast.run_path(tmp_path, datetime(2025, 7, 10, 7, tzinfo=UTC))
    run.mkdir(parents=True)
    (tmp_path / "forecast" / "current.tmp").write_text("left by a crash")
    forecast.publish(tmp_path, run)
    assert forecast.current_run(tmp_path) == run.resolve()
    assert not (tmp_path / "forecast" / "current.tmp").exists()


def test_a_rebuilt_cycle_replaces_its_earlier_run_directory(tmp_path):
    cycle = datetime(2025, 7, 10, 7, tzinfo=UTC)
    first = forecast._fresh_run_dir(tmp_path, cycle)
    (first / "stale.txt").write_text("from the earlier attempt")
    again = forecast._fresh_run_dir(tmp_path, cycle)
    assert again == first and list(again.iterdir()) == []
