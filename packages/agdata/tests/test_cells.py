"""Several cells read at once (`series.cells_days`, `cells_hours`) against each read alone: an archive whose cells
differ (noise per cell, gaps in one), across a year's end, then a forecast run without soil, which each cell fills
from its own source."""

from datetime import date, timedelta

import numpy as np
import pytest

from agdata import series, testing
from agdata.catalog import DAILY_VARIABLES
from agdata.timezones import GRID_ZONE

HOUR = timedelta(hours=1)
START, CYCLE, NOW = testing.CELLS_START, testing.CELLS_CYCLE, testing.CELLS_NOW
CELLS = [(900, 1400), (901, 1402), (900, 1401), (901, 1400)]
ZONES = [GRID_ZONE, GRID_ZONE, "America/New_York", GRID_ZONE]
NAMES = [name for name in DAILY_VARIABLES if name != "et0_sum_estimate"]


@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    return testing.differing_cells(tmp_path_factory.mktemp("cells"))


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
