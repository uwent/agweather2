import asyncio
import time
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
    # Soil moisture stays by layer, as read (m³/m³)
    for name in ("soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm"):
        np.testing.assert_allclose(hours.values[name], expected, atol=1e-4)
    assert hours.times == [first + k * ifs.HOUR for k in range(5)]


def test_a_read_put_on_the_window_in_slices_is_the_whole_read():
    first = datetime(2026, 11, 11, 22, tzinfo=UTC)
    read = ifs.read_points(first, first + timedelta(hours=9), WINDOW, all_land(), lambda v, c: LinearField(c))
    whole = read.hours()
    for name, values in whole.values.items():
        sliced = np.concatenate([read.hours(k, min(k + 4, 10)).values[name] for k in range(0, 10, 4)])
        np.testing.assert_array_equal(sliced, values, err_msg=name)
    assert read.hours(4, 8).times == whole.times[4:8]


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


class Replaced(LinearField):
    """A chunk whose file was replaced after it was opened: every read fails, as omfiles reports it."""

    def __getitem__(self, key):
        raise RuntimeError("Decoder error: Python I/O error FileExpired")


def test_a_chunk_replaced_mid_read_is_opened_again_and_reread():
    opened = []

    def open_chunk(variable, chunk):
        opened.append(variable)
        return Replaced(chunk) if opened.count(variable) == 1 else LinearField(chunk)

    hours = ifs.read(START, START, WINDOW, all_land(), open_chunk, retry_wait=0)
    assert sorted(opened) == sorted(v for v in ifs.VARIABLES for _ in range(2))  # read at once, in any order
    assert np.isfinite(hours.values["soil_temperature_10cm"]).all()


def test_a_chunk_that_stays_unreadable_fails_the_read():
    with pytest.raises(RuntimeError, match="FileExpired"):
        ifs.read(START, START, WINDOW, all_land(), lambda v, c: Replaced(c), retry_wait=0)


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


def test_over_a_coverage_only_its_extent_is_read(monkeypatch):
    from agdata import coverage

    whole = ifs.read(START, START, WINDOW, all_land(), lambda v, c: LinearField(c))
    part = Window(j0=901, j1=904, i0=1402, i1=1406)  # standing in for a coverage's extent
    monkeypatch.setattr(coverage, "extent", lambda w: part if w == WINDOW else w)
    ifs._coast.clear()
    read = ifs.read_points(START, START, WINDOW, all_land(), lambda v, c: LinearField(c))
    np.testing.assert_array_equal(read.needed, ifs.coast_weights(part, all_land()).needed)  # only the part's points
    cropped = read.hours().values["soil_temperature_10cm"][0]
    y, x = slice(1, 4), slice(2, 6)
    np.testing.assert_array_equal(cropped[y, x], whole.values["soil_temperature_10cm"][0][y, x])
    outside = np.ones(WINDOW.shape, dtype=bool)
    outside[y, x] = False
    assert np.isnan(cropped[outside]).all()
    ifs._coast.clear()


# Reads through `S3Chunks`: a small real .om file (as Open-Meteo's: (1, cells, hours), chunked 6 cells × the hours)
# served by a fake of s3fs's async filesystem, which answers ranges and IfMatch as S3 does.

CELLS, STEPS = 1200, 24
PATH = f"{ifs.BUCKET}/soil_temperature_0_to_7cm/chunk_988.om"


def om_file(tmp_path, seed: int) -> tuple[bytes, np.ndarray]:
    """A file's bytes and its values as read back (omfiles packs to 0.01, so compare with what it reads)."""
    import omfiles

    path = tmp_path / f"chunk_{seed}.om"
    data = np.random.default_rng(seed).normal(loc=5, size=(1, CELLS, STEPS)).astype(np.float32)
    writer = omfiles.OmFileWriter(str(path))
    writer.close(writer.write_array(data, chunks=[1, 6, STEPS], scale_factor=100))
    return path.read_bytes(), np.asarray(omfiles.OmFileReader(str(path))[0, :, :])


class Body:
    def __init__(self, data: bytes):
        self.data = data

    async def read(self) -> bytes:
        return self.data

    def close(self) -> None:
        pass


class FakeS3:
    """Open-Meteo's bucket as `S3FileSystem(asynchronous=True)._call_s3` answers it: `head_object`, and
    `get_object` of a byte range, refused with S3's 412 (as s3fs translates it) once the file's ETag isn't the one
    sent. `hang` makes the first that many range requests never answer; `replace_after` swaps the file for
    `replacement` after that many."""

    def __init__(self, data: bytes, hang: int = 0, replace_after: int | None = None, replacement: bytes = b""):
        self.data, self.etag = data, '"v1"'
        self.hang, self.replace_after, self.replacement = hang, replace_after, replacement
        self.gets = self.in_flight = self.peak = 0

    def split_path(self, path):
        bucket, key = path.split("/", 1)
        return bucket, key, None

    async def _call_s3(self, method, Bucket, Key, Range=None, IfMatch=None):
        from botocore.exceptions import ClientError
        from s3fs.errors import translate_boto_error

        assert f"{Bucket}/{Key}" == PATH
        if method == "head_object":
            return {"ETag": self.etag, "ContentLength": len(self.data)}
        assert method == "get_object" and Range is not None and IfMatch is not None
        self.gets += 1
        if self.replace_after is not None and self.gets > self.replace_after:
            self.data, self.etag, self.replace_after = self.replacement, '"v2"', None
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(60 if self.gets <= self.hang else 0.001)
            if IfMatch != self.etag:
                message = "At least one of the pre-conditions you specified did not hold"
                error = ClientError({"Error": {"Code": "PreconditionFailed", "Message": message}}, "GetObject")
                raise translate_boto_error(error)
            start, end = (int(x) for x in Range.removeprefix("bytes=").split("-"))
            return {"Body": Body(self.data[start : end + 1])}
        finally:
            self.in_flight -= 1


def cells_and_rings():
    """Some cells, grouped in runs as a window's rings are (each ring's cells contiguous and increasing)."""
    needed = np.sort(np.random.default_rng(0).choice(CELLS, size=400, replace=False))
    return needed, needed // 150


def read_cells(chunks: ifs.S3Chunks, t0: int = 2, t1: int = 20) -> np.ndarray:
    needed, rings = cells_and_rings()

    async def go():
        try:
            reader = await chunks("soil_temperature_0_to_7cm", 988)
            return await ifs._read_cells(reader=reader, needed=needed, rings=rings, t0=t0, t1=t1, rings_at_once=8)
        finally:
            await chunks.aclose()

    return asyncio.run(go())


def test_a_concurrent_read_gives_what_a_read_ring_by_ring_does(tmp_path):
    data, values = om_file(tmp_path, seed=1)
    needed, _ = cells_and_rings()
    s3 = FakeS3(data)
    got = read_cells(ifs.S3Chunks(requests_at_once=5, make_fs=lambda: s3))
    np.testing.assert_array_equal(got, values[needed, 2:20])
    assert 1 < s3.peak <= 5  # requests overlapped, never more than allowed


def test_a_file_replaced_mid_read_fails_the_read_rather_than_mixing_versions(tmp_path):
    data, _ = om_file(tmp_path, seed=1)
    replacement, _ = om_file(tmp_path, seed=2)
    s3 = FakeS3(data, replace_after=3, replacement=replacement)
    with pytest.raises(RuntimeError, match="FileExpired"):
        read_cells(ifs.S3Chunks(make_fs=lambda: s3))


def test_a_chunk_replaced_mid_read_is_read_again_whole_from_the_new_file(tmp_path):
    data, _ = om_file(tmp_path, seed=1)
    replacement, new_values = om_file(tmp_path, seed=2)
    needed, rings = cells_and_rings()
    s3 = FakeS3(data, replace_after=3, replacement=replacement)
    chunks = ifs.S3Chunks(make_fs=lambda: s3)

    async def go():
        try:
            return await ifs._read_chunk(
                open_chunk=chunks,
                variable="soil_temperature_0_to_7cm",
                chunk=988,
                span=(needed, rings, 0, STEPS),
                retry_wait=0,
                rings_at_once=8,
                deadline=time.monotonic() + 60,
            )
        finally:
            await chunks.aclose()

    np.testing.assert_array_equal(asyncio.run(go()), new_values[needed])


def test_a_request_that_never_answers_is_sent_again(tmp_path, monkeypatch):
    monkeypatch.setattr(ifs, "REQUEST_TIMEOUT", 0.05)
    monkeypatch.setattr(ifs, "REQUEST_BACKOFF", 0)
    data, values = om_file(tmp_path, seed=1)
    needed, _ = cells_and_rings()
    s3 = FakeS3(data, hang=2)
    got = read_cells(ifs.S3Chunks(requests_at_once=1, make_fs=lambda: s3))
    np.testing.assert_array_equal(got, values[needed, 2:20])
    s3 = FakeS3(data, hang=10**6)
    with pytest.raises(RuntimeError, match="TimeoutError"):
        read_cells(ifs.S3Chunks(requests_at_once=1, make_fs=lambda: s3))
    assert s3.gets == ifs.REQUEST_ATTEMPTS


class Slow(LinearField):
    """A chunk whose reads take a second each."""

    async def read_array(self, key):
        await asyncio.sleep(1)
        return self[key]


def test_a_read_past_its_deadline_stops_with_a_clear_error():
    closed = []

    class Opener:
        def __call__(self, variable, chunk):
            return Slow(chunk)

        async def aclose(self):
            closed.append(True)

    started = time.monotonic()
    with pytest.raises(ifs.ReadTimedOut, match="deadline"):
        ifs.read_points(START, START, WINDOW, all_land(), Opener(), deadline=0.1)
    assert time.monotonic() - started < 0.9 and closed == [True]


def test_a_chunk_that_fails_with_no_time_left_isnt_retried():
    started = time.monotonic()
    with pytest.raises(ifs.ReadTimedOut, match="no time left"):
        ifs.read_points(START, START, WINDOW, all_land(), lambda v, c: Replaced(c), retry_wait=5, deadline=2)
    assert time.monotonic() - started < 1
