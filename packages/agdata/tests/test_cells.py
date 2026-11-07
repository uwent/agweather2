"""Several cells read at once (`series.cells_days`, `cells_hours`) against each read alone: an archive whose cells
differ (noise per cell, gaps in one), across a year's end, then a forecast run without soil, which each cell fills
from its own source."""

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import forecast, series, testing
from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.cumulative import update_days
from agdata.store import HOURLY, GridStore
from agdata.timezones import GRID_ZONE

HOUR = timedelta(hours=1)
START = datetime(2024, 12, 28, tzinfo=UTC)
CYCLE = datetime(2025, 1, 3, 12, tzinfo=UTC)
NOW = CYCLE + 2 * HOUR
CELLS = [(900, 1400), (901, 1402), (900, 1401), (901, 1400)]
ZONES = [GRID_ZONE, GRID_ZONE, "America/New_York", GRID_ZONE]
NAMES = [name for name in DAILY_VARIABLES if name != "et0_sum_estimate"]


def _noisy(values: dict[str, np.ndarray], rng: np.random.Generator) -> None:
    shape = values["air_temperature"].shape
    values["air_temperature"] += rng.normal(0, 2.0, shape)
    values["dew_point"] = values["air_temperature"] - 1 - np.abs(rng.normal(0, 3.0, shape))
    values["precipitation"] = np.where(rng.random(shape) < 0.2, rng.exponential(1.0, shape), 0.0)


@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    path = tmp_path_factory.mktemp("cells")
    rng = np.random.default_rng(7)
    end = CYCLE + 2 * HOUR
    times = [START + k * HOUR for k in range((end - START) // HOUR + 1)]
    values = testing.weather(times, warm=2.0)
    _noisy(values, rng)
    shape = values["air_temperature"].shape
    values |= {
        "surface_pressure": np.full(shape, 98.0),
        "relative_humidity": np.full(shape, 75.0),
        "et0": np.full(shape, 0.05),
    }
    gaps = rng.random(shape[0]) < 0.1  # hours missing in one cell only, and a block that empties a day
    gaps[60:76] = True
    for v in values.values():
        v[gaps, 1, 2] = np.nan
    for year in (2024, 2025):
        store = GridStore.create(path, HOURLY, year, testing.WINDOW, VARIABLES.values())
        k = [n for n, t in enumerate(times) if t.year == year]
        store.write(times[k[0]], {name: v[k[0] : k[-1] + 1] for name, v in values.items()}, source="urma")
    update_days(path, testing.WINDOW, (START + timedelta(days=1)).date(), (end - timedelta(days=1)).date())
    run = testing.nbm_run(CYCLE, warm=6.0)
    _noisy(run.values, rng)
    forecast.publish(path, forecast.write_run(path, testing.WINDOW, run, pressure_kpa=98.0))
    return path


def _filler(level: float):
    def fill(first_hour, last_hour, names):
        n = (last_hour - first_hour) // HOUR + 1
        return {name: np.full(n, level) for name in names}

    return fill


def test_several_cells_read_at_once_match_each_read_alone(mixed):
    first, last = date(2024, 12, 29), date(2025, 1, 12)
    fills = [_filler(10.0 + c) for c in range(len(CELLS))]
    together = series.cells_days(
        mixed, CELLS, first, last, NAMES, totals=["dd_sine_50"], now=NOW, fill_soil=fills, zones=ZONES
    )
    for c, cell in enumerate(CELLS):
        alone = series.point_days(
            mixed, *cell, first, last, NAMES, totals=["dd_sine_50"], now=NOW, fill_soil=fills[c], zone=ZONES[c]
        )
        found = together[c]
        assert found.dates == alone.dates and found.kinds == alone.kinds and found.zone == ZONES[c]
        assert found.sources == alone.sources and found.corrections == alone.corrections
        assert set(found.values) == set(alone.values)
        for name, values in alone.values.items():
            # equal but for summation order: a mean over several cells adds in another order (~1e-16)
            np.testing.assert_allclose(found.values[name], values, rtol=1e-12, atol=0, err_msg=f"{cell} {name}")
        np.testing.assert_array_equal(found.totals["dd_sine_50"], alone.totals["dd_sine_50"])
    assert {"observed", "partial", "forecast"} <= set(together[0].kinds)
    assert "openmeteo" in together[0].sources  # forecast soil from each cell's own fill
    tmax = [d.values["air_temperature_max"] for d in together]
    assert not np.array_equal(tmax[0], tmax[1], equal_nan=True)  # the cells differ, so a mix-up would show
    assert np.isnan(together[1].values["air_temperature_max"]).any()  # the gappy cell's incomplete days


def test_several_cells_hours_match_each_read_alone(mixed):
    start, end = CYCLE - 30 * HOUR, CYCLE + 30 * HOUR
    names = ["air_temperature", "precipitation", "soil_temperature_10cm"]
    fills = [_filler(10.0 + c) for c in range(len(CELLS))]
    together = series.cells_hours(mixed, CELLS, start, end, names, now=NOW, fill_soil=fills)
    for c, cell in enumerate(CELLS):
        alone = series.point_hours(mixed, *cell, start, end, names, now=NOW, fill_soil=fills[c])
        assert together[c].kinds == alone.kinds and together[c].sources == alone.sources
        for name in names:
            np.testing.assert_array_equal(together[c].values[name], alone.values[name])
    soil = [frame.values["soil_temperature_10cm"] for frame in together]
    assert np.nanmax(soil[0]) == 10.0 and np.nanmax(soil[3]) == 13.0  # each cell's fill stays its own
