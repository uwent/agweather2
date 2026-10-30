from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import forecast
from agdata.catalog import VARIABLES
from agdata.grid import Window
from agdata.sources.nbm import HORIZON_HOURS
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)  # 2 x 3 cells near Madison
HOUR = timedelta(hours=1)


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
    fx.archive(tmp_path, datetime(2025, 6, 1, tzinfo=UTC), datetime(2025, 6, 5, 7, tzinfo=UTC))
    assert forecast.last_observed_hour(tmp_path, datetime(2025, 6, 10, tzinfo=UTC)) == datetime(
        2025, 6, 5, 7, tzinfo=UTC
    )
    assert forecast.last_observed_hour(tmp_path, datetime(2025, 6, 5, 3, tzinfo=UTC)) == datetime(
        2025, 6, 5, 3, tzinfo=UTC
    )
    assert forecast.last_observed_hour(tmp_path, datetime(2025, 7, 1, tzinfo=UTC)) is None  # over two weeks back


def test_building_in_strips_matches_the_whole_window(tmp_path, fx, monkeypatch):
    from agdata.sources import nbm

    cycle = datetime(2025, 7, 10, 13, tzinfo=UTC)
    fx.archive(tmp_path, datetime(2025, 7, 1, tzinfo=UTC), cycle + 2 * HOUR)
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
