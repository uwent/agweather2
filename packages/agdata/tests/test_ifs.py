from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from agdata.grid import NDFD, LatLonGrid, Window
from agdata.sources import era5land, ifs
from agdata.sources.openmeteo import cell_for

WINDOW = Window(j0=900, j1=906, i0=1400, i1=1408)  # near Madison
START = datetime(2026, 10, 30, 22, tzinfo=UTC)


class LinearField:
    """A fake chunk: every cell's value is linear in its latitude and longitude, plus the hour."""

    def __init__(self, chunk: int, slope=(0.5, 0.2), water=None):
        self.chunk, self.slope, self.water = chunk, slope, water

    def __getitem__(self, key):
        _, cells, steps = key
        flat = np.arange(cells.start, cells.stop)
        lat, lon = ifs.cell_latlon(flat)
        value = self.slope[0] * lat + self.slope[1] * lon
        if self.water is not None:
            value = np.where(self.water(lat, lon), 99.0, value)
        hours = np.arange(steps.start, steps.stop) + self.chunk * ifs.CHUNK_HOURS
        # As omfiles: the integer index drops the first axis, so a read is (cells, hours)
        return np.broadcast_to(value[:, None] + 1e-6 * hours[None, :], (len(flat), len(hours)))


def all_land() -> era5land.LandMask:
    grid = LatLonGrid(name="land", first_lat=40.0, first_lon=-95.0, step=0.1, ny=100, nx=100)
    return era5land.LandMask(grid=grid, fraction=np.ones((grid.ny, grid.nx)))


def test_flat_indices_find_the_cells_cell_for_names():
    for lat, lon in ((45.5, -89.5), (43.07, -89.4), (30.0, -100.0)):
        c = cell_for(lat, lon)
        flat = ifs.ring_offsets()[c.ring] + c.index
        got_lat, got_lon = ifs.cell_latlon(np.array([flat]))
        assert got_lat[0] == pytest.approx(c.latitude) and got_lon[0] == pytest.approx(c.longitude)
    assert ifs.ring_offsets()[-1] + ifs.ring_points(ifs.RINGS) == 6_599_680  # every cell of an O1280 file


def test_a_field_linear_in_latitude_and_longitude_comes_through_exactly():
    first = datetime(2026, 11, 11, 22, tzinfo=UTC)  # crosses from chunk 988 into 989 at Nov 12 00Z
    last = first + timedelta(hours=4)
    hours = ifs.read(first, last, WINDOW, all_land(), lambda variable, chunk: LinearField(chunk))
    lat, lon = NDFD.window_latlon(WINDOW)
    step = np.array([int((t - ifs.EPOCH) / ifs.HOUR) for t in hours.times])
    expected = 0.5 * lat[None] + 0.2 * lon[None] + 1e-6 * step[:, None, None]
    # Every layer holds the same field, so every depth does too; snow comes out ×100 (m → cm)
    np.testing.assert_allclose(hours.values["soil_temperature_10cm"], expected, atol=1e-4)
    np.testing.assert_allclose(hours.values["snow_depth"], expected * 100, atol=1e-2)
    assert hours.times == [first + k * ifs.HOUR for k in range(5)]


def test_water_neighbours_get_no_weight():
    _, lon = NDFD.window_latlon(WINDOW)
    east = float(np.median(lon))
    land = all_land()
    grid_lon = land.grid.first_lon + land.grid.step * np.arange(land.grid.nx)
    fraction = np.repeat(np.where(grid_lon > east, 0.0, 1.0)[None, :], land.grid.ny, axis=0)
    water = era5land.LandMask(grid=land.grid, fraction=fraction)
    hours = ifs.read(START, START, WINDOW, water, lambda v, c: LinearField(c, water=lambda la, lo: lo > east))
    soil = hours.values["soil_temperature_4cm"][0]
    assert np.nanmax(soil) < 90  # no lake value (99) leaks into a land cell
    assert np.isfinite(soil[lon < east - 0.15]).all()  # well inland: every neighbour is land
    assert np.isnan(soil[lon > east + 0.15]).all()  # well out: no land neighbour


def test_the_run_end_follows_the_newest_long_run():
    at = lambda h: {"last_run_initialisation_time": datetime(2026, 10, 31, h, tzinfo=UTC).timestamp()}  # noqa: E731
    assert ifs.run_end(at(12)) == datetime(2026, 11, 10, 12, tzinfo=UTC)
    assert ifs.run_end(at(6)) == datetime(2026, 11, 10, 0, tzinfo=UTC)  # the 00Z run's 240 hours


def test_chunk_spans():
    first = datetime(2026, 11, 11, 23, tzinfo=UTC)
    spans = ifs.chunk_span(first, first + timedelta(hours=2))
    assert spans == [(988, 503, 504, 0), (989, 0, 2, 1)]
