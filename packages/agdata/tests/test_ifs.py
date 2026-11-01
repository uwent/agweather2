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


def kept_hours(count: int, value: float = 2.0) -> era5land.Hours:
    values = {name: np.full((count, *WINDOW.shape), value + k) for k, name in enumerate(ifs.SOIL)}
    return era5land.Hours(times=[START + k * ifs.HOUR for k in range(count)], values=values)


def test_a_kept_read_comes_back_for_the_hours_it_holds_and_nan_for_the_rest(tmp_path):
    path = ifs.latest_path(tmp_path)
    assert path == tmp_path / "ifs" / "latest.zarr"
    ifs.save_latest(path, kept_hours(5), run=START)
    times = [START + k * ifs.HOUR for k in (-2, 0, 3, 4, 5, 9)]  # two before the read, four in it, two after
    kept = ifs.latest_at(path, times, WINDOW)
    for k, name in enumerate(ifs.SOIL):
        column = kept[name][:, 0, 0]
        np.testing.assert_allclose(column[[1, 2, 3]], [2.0 + k] * 3)
        assert np.isnan(column[[0, 4, 5]]).all()
        assert kept[name].shape == (6, *WINDOW.shape)
    assert np.isnan(ifs.latest_at(path, [START + 10 * ifs.HOUR], WINDOW)[ifs.SOIL[0]]).all()  # wholly outside


def test_no_kept_read_means_no_hours(tmp_path):
    kept = ifs.latest_at(ifs.latest_path(tmp_path), [START], WINDOW)
    assert set(kept) == set(ifs.SOIL) and all(np.isnan(v).all() for v in kept.values())


def test_a_kept_read_is_replaced_whole_and_leaves_nothing_behind(tmp_path):
    path = ifs.latest_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.with_name("latest.zarr.old").mkdir()  # left by a swap that crashed
    ifs.save_latest(path, kept_hours(3, value=1.0), run=START)
    ifs.save_latest(path, kept_hours(3, value=7.0), run=START + 6 * ifs.HOUR, seam=START + ifs.HOUR)
    assert sorted(p.name for p in path.parent.iterdir()) == ["latest.zarr"]
    assert ifs.latest_at(path, [START], WINDOW)[ifs.SOIL[0]][0, 0, 0] == 7.0  # the newer read
    with pytest.raises(ValueError, match="with no hours"):
        ifs.save_latest(path, era5land.Hours(times=[], values={}), run=START)


def test_a_kept_read_remembers_its_seam_and_each_cells_offset(tmp_path):
    import zarr

    path = ifs.latest_path(tmp_path)
    offsets = {name: np.full(WINDOW.shape, 0.5) for name in ifs.SOIL}
    ifs.save_latest(path, kept_hours(2), run=START, seam=START, offsets=offsets)
    attrs = dict(zarr.open_group(path, mode="r").attrs)
    assert attrs["seam"] == START.isoformat() and attrs["hours"] == 2 and attrs["first"] == START.isoformat()
    assert str(attrs["seam_correction"]).startswith("ifs-soil-seam v")
    assert f"{ifs.SOIL[0]}_seam_offset" in zarr.open_group(path, mode="r")
    ifs.save_latest(path, kept_hours(2), run=START)
    assert dict(zarr.open_group(path, mode="r").attrs)["seam_correction"] is None


def test_a_kept_read_for_another_window_is_refused(tmp_path):
    path = ifs.latest_path(tmp_path)
    ifs.save_latest(path, kept_hours(2), run=START)
    with pytest.raises(ValueError, match="another window"):
        ifs.latest_at(path, [START], Window(j0=900, j1=903, i0=1400, i1=1405))
