"""ECMWF IFS HRES soil temperature, soil moisture and snow depth on the grid, from Open-Meteo's open data (D52, Q22, D53).

Open-Meteo keeps IFS on its native O1280 grid (~9 km) at `s3://openmeteo/data/ecmwf_ifs/<variable>/chunk_<k>.om`:
each file is (1, 6 599 680 cells, 504 hours), chunk k starting k × 504 hours after 1970-01-01 00Z, values at each
hour instantaneous (as ours, the hour ending then). Past hours are each run's first hours, so one read gives the
provisional days after ERA5-Land's last and the forecast. Read with `omfiles` (GPL-2.0-only), which is the optional
`agdata[ifs]` extra and imported only here (D53).

Files are chunked 6 cells × 504 hours, so a read over the launch box is thousands of small range requests per file
(~7,300, 1.5 KB each): one after another that was ~11 minutes a file and ~3 hours a read. `read_points` reads every
file at once through `omfiles.OmFileReaderAsync` (`S3Chunks`), a ring per read, with REQUESTS_AT_ONCE requests in
flight over all of them, each bounded in time and tries, each pinned to the version of the file it opened (`_Pinned`),
and the whole read to READ_DEADLINE: ~1.5 minutes over the launch box (2026-11-25).

Checked 2026-10-31 against Open-Meteo's API (`models=ecmwf_ifs`) at a cell in northern Wisconsin: chunk 988's
deep soil matched for 360 hours within 0.03 °C (the API adjusts for elevation). The files hold hours past the
newest run's end (older runs' long leads and stale values), so reads stop at `run_end`: a 00Z or 12Z run reaches
240 hours, a 06Z or 18Z run 144, and after one of those the 00Z or 12Z run 6 hours before it still reaches 234
hours past the newer one (`static/meta.json` gives the newest run).

Cells: ring k from the nearer pole holds 20 + 4(k − 1) points from longitude 0 (`openmeteo.cell_for`). Each NDFD
cell takes the cubic B-spline over four points on each of the four rings around it (`coast.bspline`, as ERA5-Land),
by the coast rule (`agdata.coast`, D79): neighbours over water (ERA5-Land's land mask, `era5land.LandMask`) get no
weight, as IFS's lake points carry the lake's temperature; a cell with none on land takes the nearest land point
within 40 km; our water is missing.
"""

import asyncio
import errno
import inspect
import json
import logging
import shutil
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import zarr

from agdata import coverage, soil_seam
from agdata.coast import KERNEL_OFFSETS, Weights, bspline, finish, land_only, padded
from agdata.grid import NDFD, Window
from agdata.ingest import SOIL, SOIL_MOISTURE
from agdata.sources import era5land
from agdata.sources.openmeteo import RINGS, SOIL_LAYERS, _ring_latitude, soil_at_depths

logger = logging.getLogger(__name__)

BUCKET = "openmeteo/data/ecmwf_ifs"
CHUNK_HOURS = 504
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)
VARIABLES = (*SOIL_LAYERS, "snow_depth", *SOIL_MOISTURE)  # the bucket's moisture layers are named as the catalog's
LONG_RUN_HOURS = 240  # 00Z and 12Z
SHORT_RUN_HOURS = 144  # 06Z and 18Z
READ_ATTEMPTS = 4  # a chunk's file being replaced mid-read is retried this many times in all
READ_DEADLINE = (
    20 * 60
)  # s (a read takes ~1.5 min): a read still going after this is abandoned (the job fails; the next run tries again)
RINGS_AT_ONCE = 32  # ring reads in flight per chunk file (each is a few dozen range requests)
REQUESTS_AT_ONCE = (
    64  # range requests in flight to S3 over the whole read (launch box, 2026-11-25: 32 → 153 s, 64 → 80 s, 128 → 54 s)
)
REQUEST_TIMEOUT = 60  # s: one range request's whole time, botocore's own retries included
REQUEST_ATTEMPTS = 3  # a range request that times out or fails in transit is sent this many times in all
REQUEST_BACKOFF = 1.0  # s, times the attempt: the wait before a range request is sent again

Opener = Callable[
    [str, int], Any
]  # (variable, chunk) → a reader (or a coroutine giving one): `read_array` (sync or async) or indexing, [0, cells, hours]


def ring_points(j: int) -> int:
    k = min(j, RINGS - j + 1)
    return 20 + 4 * (k - 1)


@cache
def ring_offsets() -> np.ndarray:
    """The flat index of each ring's first point, by ring (index 0 unused)."""
    counts = np.array([0] + [ring_points(j) for j in range(1, RINGS + 1)], dtype=np.int64)
    return np.cumsum(counts) - counts


@cache
def weights_for(window: Window) -> Weights:
    """Cubic B-spline weights on the rings, before the land mask: four points along each of the four rings around a
    cell, the rings' weights by the cell's place between the two nearest (their spacing is nearly even)."""
    lat, lon = NDFD.window_latlon(window)
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float) % 360
    first = max(1, int((90 - lat.max()) / 180 * RINGS) - 3)
    last = min(RINGS, int((90 - lat.min()) / 180 * RINGS) + 4)
    rings = np.arange(first, last + 1)
    ring_lat = np.array([_ring_latitude(int(j)) for j in rings])  # decreasing
    north = rings[np.searchsorted(-ring_lat, -lat, side="right") - 1]  # the ring at or north of each cell
    if (north + KERNEL_OFFSETS[0] < first).any() or (north + KERNEL_OFFSETS[-1] > last).any():
        raise ValueError(f"the rings searched don't surround {window}")
    lat_n = ring_lat[north - first]
    lat_s = ring_lat[north + 1 - first]
    wy = bspline((lat_n - lat) / (lat_n - lat_s))
    offsets = ring_offsets()
    cells, weights = [], []
    for a, dj in enumerate(KERNEL_OFFSETS):
        ring = north + dj
        points = np.vectorize(ring_points)(ring)
        position = lon / (360.0 / points)
        i0 = np.floor(position).astype(np.int64)
        wx = bspline(position - i0)
        for b, di in enumerate(KERNEL_OFFSETS):
            cells.append(offsets[ring] + (i0 + di) % points)
            weights.append(wy[a] * wx[b])
    return Weights(cells=np.stack(cells), weights=np.stack(weights))


def cell_latlon(cells: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Flat O1280 indices → their (latitude, longitude -180–180)."""
    offsets = ring_offsets()
    ring = np.searchsorted(offsets, cells, side="right") - 1
    index = cells - offsets[ring]
    points = np.vectorize(ring_points)(ring)
    lat = np.vectorize(_ring_latitude)(ring)
    lon = (index * 360.0 / points + 180) % 360 - 180
    return lat, lon


def land_weights(weights: Weights, land: era5land.LandMask) -> Weights:
    """Zero weight for neighbours whose nearest ERA5-Land cell is water."""
    return land_only(weights, _is_land(weights.cells, land))


def _is_land(cells: np.ndarray, land: era5land.LandMask) -> np.ndarray:
    lat, lon = cell_latlon(cells)
    g = land.grid
    j = np.clip(np.round((lat - g.first_lat) / g.step).astype(int), 0, g.ny - 1)
    i = np.clip(np.round((lon - g.first_lon) / g.step).astype(int), 0, g.nx - 1)
    return land.fraction[j, i] >= 0.5


_coast: dict[tuple, Weights] = {}


def coast_weights(window: Window, land: era5land.LandMask) -> Weights:
    """The window's weights by the coast rule (`agdata.coast`, D79): land neighbours only, the nearest land point
    within 40 km where none is, nothing on water. Kept per window and mask."""
    key = (window, land.grid, hash(land.fraction.tobytes()))
    part = coverage.extent(window)
    if key not in _coast and part != window:  # over a coverage's window, its extent only
        _coast[key] = padded(coast_weights(part, land), part, window)
    if key not in _coast:
        spline = weights_for(window)
        points = np.unique(spline.cells)
        land_points = points[_is_land(points, land)]
        lat, lon = cell_latlon(land_points)
        _coast[key] = finish(land_weights(spline, land), window, land_points, lat, lon)[0]
    return _coast[key]


def chunk_span(first: datetime, last: datetime) -> list[tuple[int, int, int, int]]:
    """(chunk, first step in it, step after the last in it, offset of that first step from `first`) covering
    the hours first..last."""
    a = int((first - EPOCH) / HOUR)
    b = int((last - EPOCH) / HOUR) + 1
    out = []
    for chunk in range(a // CHUNK_HOURS, (b - 1) // CHUNK_HOURS + 1):
        lo = max(a, chunk * CHUNK_HOURS)
        hi = min(b, (chunk + 1) * CHUNK_HOURS)
        out.append((chunk, lo - chunk * CHUNK_HOURS, hi - chunk * CHUNK_HOURS, lo - a))
    return out


def run_end(meta: dict) -> datetime:
    """The last hour the newest runs reach (`static/meta.json`'s `last_run_initialisation_time`)."""
    newest = datetime.fromtimestamp(meta["last_run_initialisation_time"], UTC)
    if newest.hour % 12 == 0:
        return newest + LONG_RUN_HOURS * HOUR
    return max(newest + SHORT_RUN_HOURS * HOUR, newest - 6 * HOUR + LONG_RUN_HOURS * HOUR)


class ReadTimedOut(TimeoutError):
    """A read that passed its deadline (READ_DEADLINE): it's abandoned, and the next run of the job tries again."""


async def _slice(reader, key: tuple) -> np.ndarray:
    """reader[key] from an async reader (`read_array`, a coroutine) or a plain one (indexing, as the tests' fakes)."""
    read_array = getattr(reader, "read_array", None)
    out = read_array(key) if read_array is not None else reader[key]
    if inspect.isawaitable(out):
        out = await out
    return np.asarray(out, dtype=np.float32)


def _first_leaf(error: BaseException) -> BaseException:
    while isinstance(error, BaseExceptionGroup):
        error = error.exceptions[0]
    return error


async def _read_cells(
    reader, needed: np.ndarray, rings: np.ndarray, t0: int, t1: int, rings_at_once: int
) -> np.ndarray:
    """The `needed` flat cells' steps t0..t1 from one file, a read per ring (each ring's cells are contiguous), up to
    `rings_at_once` of them in flight; the first to fail cancels the rest, and its error is raised."""
    out = np.empty((len(needed), t1 - t0), dtype=np.float32)
    gate = asyncio.Semaphore(rings_at_once)

    async def ring_read(rows: np.ndarray) -> None:
        lo, hi = int(needed[rows[0]]), int(needed[rows[-1]])
        async with gate:
            block = await _slice(reader=reader, key=(0, slice(lo, hi + 1), slice(t0, t1)))
        out[rows] = block[needed[rows] - lo]

    try:
        async with asyncio.TaskGroup() as group:
            for ring in np.unique(rings):
                group.create_task(ring_read(np.flatnonzero(rings == ring)))
    except BaseExceptionGroup as errors:
        raise _first_leaf(errors) from errors
    return out


async def _read_chunk(
    open_chunk: Opener,
    variable: str,
    chunk: int,
    span: tuple[np.ndarray, np.ndarray, int, int],
    retry_wait: float,
    rings_at_once: int,
    deadline: float,
) -> np.ndarray:
    """One chunk file's cells and steps (`span`: the cells, their rings, the first step and the one after the last).
    Open-Meteo rewrites a chunk's file in place as runs come in, so a read that finds its file replaced (or can't
    decode it) opens the chunk again and rereads it, `retry_wait` seconds later, up to READ_ATTEMPTS times; never past
    the read's deadline (`time.monotonic()`)."""
    needed, rings, t0, t1 = span
    for attempt in range(1, READ_ATTEMPTS + 1):
        try:
            reader = open_chunk(variable, chunk)
            if inspect.isawaitable(reader):
                reader = await reader
            return await _read_cells(
                reader=reader, needed=needed, rings=rings, t0=t0, t1=t1, rings_at_once=rings_at_once
            )
        except RuntimeError as error:  # omfiles wraps I/O errors, `FileExpired` among them, in its own
            if attempt == READ_ATTEMPTS:
                raise
            if time.monotonic() + retry_wait >= deadline:
                raise ReadTimedOut(
                    f"IFS {variable} chunk {chunk} unreadable and no time left to retry: {error}"
                ) from error
            logger.warning(
                "IFS %s chunk %d unreadable (attempt %d of %d), retrying in %gs: %s",
                variable,
                chunk,
                attempt,
                READ_ATTEMPTS,
                retry_wait,
                error,
            )
        await asyncio.sleep(retry_wait)
    raise AssertionError("unreachable")


@dataclass(kw_only=True)
class Read:
    """A read's values on IFS's own points (small: ~100 MB a variable over the launch box), from which the window's
    hours are made a slice at a time (`hours`), since every hour of a run over the window at once is several GB."""

    times: list[datetime]
    weights: Weights
    needed: np.ndarray
    raw: dict[str, np.ndarray]  # variable → (points, hours)

    def hours(self, start: int = 0, stop: int | None = None) -> era5land.Hours:
        """Hours start..stop-1 on the window: the catalog's soil depths (°C), `snow_depth` (cm) and soil moisture
        layers (m³/m³)."""
        stop = len(self.times) if stop is None else stop
        on_window = {name: self.weights.apply(values[:, start:stop], self.needed) for name, values in self.raw.items()}
        layers = {name: on_window[name] for name in SOIL_LAYERS}
        out = {name: value for name, (value, _) in soil_at_depths(layers).items()}
        out["snow_depth"] = era5land.no_negative_snow(on_window["snow_depth"]) * 100  # m → cm
        out |= {name: on_window[name] for name in SOIL_MOISTURE if name in on_window}
        return era5land.Hours(times=self.times[start:stop], values=out)


def read_points(
    first: datetime,
    last: datetime,
    window: Window,
    land: era5land.LandMask,
    open_chunk: Opener,
    retry_wait: float = 60,
    deadline: float | None = None,
    rings_at_once: int = RINGS_AT_ONCE,
) -> Read:
    """IFS's hours first..last at the points the window's cells take (`Read.hours` puts them on the window).

    Every variable's chunks are read at once, each a read per ring with up to `rings_at_once` rings of a file in
    flight (`S3Chunks` bounds the requests themselves). A chunk whose file is replaced mid-read is read again
    (`_read_chunk`). A read still going after `deadline` seconds (READ_DEADLINE) raises `ReadTimedOut`."""
    weights = coast_weights(window, land)
    needed = weights.needed
    rings = np.searchsorted(ring_offsets(), needed, side="right") - 1
    n = int((last - first) / HOUR) + 1
    seconds = READ_DEADLINE if deadline is None else deadline
    raw = {variable: np.full((len(needed), n), np.nan, dtype=np.float32) for variable in VARIABLES}

    async def read_all() -> None:
        ends = time.monotonic() + seconds

        async def one(variable: str, chunk: int, t0: int, t1: int, at: int) -> None:
            values = await _read_chunk(
                open_chunk=open_chunk,
                variable=variable,
                chunk=chunk,
                span=(needed, rings, t0, t1),
                retry_wait=retry_wait,
                rings_at_once=rings_at_once,
                deadline=ends,
            )
            raw[variable][:, at : at + (t1 - t0)] = values

        try:
            async with asyncio.timeout(seconds):
                async with asyncio.TaskGroup() as group:
                    for variable in VARIABLES:
                        for chunk, t0, t1, at in chunk_span(first, last):
                            group.create_task(one(variable, chunk, t0, t1, at))
        except TimeoutError as error:
            raise ReadTimedOut(
                f"IFS read stopped after {seconds:g} s, its deadline; the next run tries again"
            ) from error
        except BaseExceptionGroup as errors:
            raise _first_leaf(errors) from errors
        finally:
            close = getattr(open_chunk, "aclose", None)
            if close is not None:
                await close()

    _run(read_all())
    return Read(times=[first + k * HOUR for k in range(n)], weights=weights, needed=needed, raw=raw)


def _run(coroutine) -> None:
    """Runs a coroutine to its end from sync code, on a thread of its own if this one already runs an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coroutine)
        return
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, coroutine).result()


def read(
    first: datetime,
    last: datetime,
    window: Window,
    land: era5land.LandMask,
    open_chunk: Opener,
    retry_wait: float = 60,
) -> era5land.Hours:
    """IFS's hours first..last on the window, all at once (`read_points` for a read made a slice at a time)."""
    return read_points(
        first=first, last=last, window=window, land=land, open_chunk=open_chunk, retry_wait=retry_wait
    ).hours()


class _Pinned:
    """What `OmFileReaderAsync.from_fsspec` reads through (`_size`, `_cat_file`), held to the version of the file it
    opened, with the requests bounded in number, time and tries.

    The filesystem's own `_cat_file` reads whatever is there now, so a file replaced partway through a read would mix
    the old file's index with the new one's bytes ("Decoder error: Corrupted data", 2026-11-02). Each range is sent
    with the ETag seen at open (`IfMatch`), and S3's 412 once the file has changed raises `FileExpired` (which omfiles
    wraps in a RuntimeError, and `_read_chunk` then reads the chunk again). A request that takes longer than
    REQUEST_TIMEOUT, or fails in transit, is sent again, REQUEST_ATTEMPTS times in all."""

    def __init__(self, *, fs, path: str, etag: str, size: int, gate: asyncio.Semaphore):
        self.fs, self.path, self.etag, self.size, self.gate = fs, path, etag, size, gate

    async def _size(self, path: str) -> int:
        return self.size

    async def _cat_file(self, path: str, start: int | None = None, end: int | None = None, **kwargs) -> bytes:
        from s3fs.utils import FileExpired  # agdata[ifs]

        start = 0 if start is None else start
        end = self.size if end is None else end
        if end <= start:
            return b""
        try:
            return await _s3_call(
                fs=self.fs,
                gate=self.gate,
                method="get_object",
                path=self.path,
                Range=f"bytes={start}-{end - 1}",
                IfMatch=self.etag,
            )
        except OSError as error:
            if _precondition_failed(error):
                raise FileExpired(filename=self.path, e_tag=self.etag) from error
            raise


async def _s3_call(*, fs, gate: asyncio.Semaphore, method: str, path: str, **kwargs) -> Any:
    """`fs._call_s3(method, …)` on the path (a `get_object`'s body read whole), one of the `gate`'s requests in
    flight, sent again if it takes longer than REQUEST_TIMEOUT or fails in transit, REQUEST_ATTEMPTS times in all."""
    bucket, key, _ = fs.split_path(path)
    async with gate:
        for attempt in range(1, REQUEST_ATTEMPTS + 1):
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    response = await fs._call_s3(method, Bucket=bucket, Key=key, **kwargs)
                    if method != "get_object":
                        return response
                    try:
                        return await response["Body"].read()
                    finally:
                        response["Body"].close()
            except Exception as error:
                if attempt == REQUEST_ATTEMPTS or not _transient(error):
                    raise
                logger.info(
                    "IFS %s %s %s failed (attempt %d of %d), sending again: %r",
                    method,
                    path,
                    kwargs.get("Range", ""),
                    attempt,
                    REQUEST_ATTEMPTS,
                    error,
                )
                await asyncio.sleep(REQUEST_BACKOFF * attempt)
    raise AssertionError("unreachable")


def _precondition_failed(error: Exception) -> bool:
    """S3's 412 as s3fs translates it (as `S3File._fetch_range` reads it)."""
    return isinstance(error, OSError) and error.errno == errno.EINVAL and "pre-condition" in str(error).lower()


def _transient(error: Exception) -> bool:
    """Worth sending again: a timeout, a dropped connection or a server error, not a missing file or a refusal."""
    if isinstance(error, (FileNotFoundError, PermissionError)):
        return False
    if isinstance(error, OSError):  # TimeoutError and s3fs's translations of S3's errors
        return error.errno != errno.EINVAL
    return type(error).__module__.split(".")[0] in ("botocore", "aiobotocore", "aiohttp")


def _s3_config(requests_at_once: int) -> dict:
    """botocore's settings for Open-Meteo's bucket: bounded connects and reads (s3fs's defaults left a read waiting
    20+ minutes on sockets that never connected, 2026-11-24), retries of throttling and server errors, and a
    connection pool as large as the requests in flight."""
    return {
        "connect_timeout": 10,
        "read_timeout": 30,
        "retries": {"max_attempts": 3, "mode": "standard"},
        "max_pool_connections": requests_at_once,
    }


class S3Chunks:
    """Opens Open-Meteo's chunk files on AWS (anonymous) for async reads (`omfiles.OmFileReaderAsync`), each pinned
    to the version it opened (`_Pinned`), with at most `requests_at_once` range requests in flight over all of them.
    The S3 session belongs to the event loop of the read that first opens a file, and `aclose` (called by
    `read_points` at its end) closes it; needs `agdata[ifs]`."""

    def __init__(self, requests_at_once: int = REQUESTS_AT_ONCE, make_fs: Callable[[], Any] | None = None):
        self.requests_at_once = requests_at_once
        self.make_fs = make_fs or self._s3
        self.fs: Any = None
        self.gate: asyncio.Semaphore | None = None

    def _s3(self):
        import s3fs  # agdata[ifs]

        fs = s3fs.S3FileSystem(
            anon=True, asynchronous=True, skip_instance_cache=True, config_kwargs=_s3_config(self.requests_at_once)
        )
        fs.retries = 1  # botocore retries (`_s3_config`) and `_Pinned`'s own; s3fs's wrapper would multiply them
        return fs

    async def __call__(self, variable: str, chunk: int):
        import omfiles  # agdata[ifs]; GPL-2.0-only (D53)

        if self.fs is None:
            self.fs = self.make_fs()
            self.gate = asyncio.Semaphore(self.requests_at_once)
        assert self.gate is not None
        path = f"{BUCKET}/{variable}/chunk_{chunk}.om"
        try:
            head = await _s3_call(fs=self.fs, gate=self.gate, method="head_object", path=path)
        except Exception as error:  # as omfiles reports a failed read, so `_read_chunk` opens the chunk again
            raise RuntimeError(f"IFS {path} couldn't be opened: {error!r}") from error
        pinned = _Pinned(fs=self.fs, path=path, etag=head["ETag"], size=int(head["ContentLength"]), gate=self.gate)
        return await omfiles.OmFileReaderAsync.from_fsspec(pinned, path)

    async def aclose(self) -> None:
        fs, self.fs, self.gate = self.fs, None, None
        creator = getattr(fs, "_s3creator", None)
        if creator is not None:
            await creator.__aexit__(None, None, None)


def s3_opener() -> tuple[Opener, Callable[[], dict]]:
    """Readers of Open-Meteo's files on AWS (anonymous) and of its `static/meta.json`; needs `agdata[ifs]`."""
    import s3fs  # agdata[ifs]

    def meta() -> dict:
        fs = s3fs.S3FileSystem(anon=True, skip_instance_cache=True, config_kwargs=_s3_config(1))
        return json.loads(fs.cat_file(f"{BUCKET}/static/meta.json"))

    return S3Chunks(), meta


def latest_path(data_dir: Path) -> Path:
    """Where the IFS job keeps its newest read (the forecast's soil and snow come from it)."""
    return Path(data_dir) / "ifs" / "latest.zarr"


class LatestWriter:
    """Builds a kept read (`latest_path`) beside the one in place, a slice of hours at a time (`write`), and swaps it
    in whole (`finish`), so a forecast build reading it (`latest_at`) never sees a half-written one. Holds the hours
    (from the first provisional hour to the run's end), the seam they were shifted to meet and each cell's offset there
    (`agdata.soil_seam`; raw = value − offset × weight)."""

    def __init__(
        self,
        path: Path,
        times: list[datetime],
        shape: tuple[int, int],
        run: datetime,
        seam: datetime | None = None,
        offsets: dict[str, np.ndarray] | None = None,
    ):
        """`shape`: the window's (y, x)."""
        if not times:
            raise ValueError("an IFS read with no hours")
        self.path = path
        self.building = path.with_name(path.name + ".part")
        if self.building.exists():
            shutil.rmtree(self.building)  # left by a build that crashed
        self.group = zarr.open_group(self.building, mode="w")
        self.shape = (len(times), *shape)
        for name, offset in (offsets or {}).items():
            self.group.create_array(f"{name}_seam_offset", data=np.asarray(offset, dtype=np.float32))
        self.group.attrs.update(
            {
                "first": times[0].isoformat(),
                "hours": len(times),
                "run": run.isoformat(),
                "seam": seam.isoformat() if seam is not None else None,
                "seam_correction": f"ifs-soil-seam v{soil_seam.table().version}" if offsets else None,
            }
        )

    def write(self, start: int, values: dict[str, np.ndarray]) -> None:
        """Hours start.. of each variable (hours, y, x)."""
        for name, v in values.items():
            if name not in self.group:
                self.group.create_array(
                    name, shape=self.shape, chunks=(24, *self.shape[1:]), dtype="float32", fill_value=np.nan
                )
            self.group[name][start : start + v.shape[0]] = np.asarray(v, dtype=np.float32)  # type: ignore[index]

    def finish(self) -> None:
        old = self.path.with_name(self.path.name + ".old")
        if old.exists():
            shutil.rmtree(old)  # left by a swap that crashed
        if self.path.exists():
            self.path.rename(old)
        self.building.rename(self.path)
        if old.exists():
            shutil.rmtree(old)


def save_latest(
    path: Path,
    hours: era5land.Hours,
    run: datetime,
    seam: datetime | None = None,
    offsets: dict[str, np.ndarray] | None = None,
) -> None:
    """Keeps a read's hours whole (`LatestWriter` for one made a slice at a time)."""
    if not hours.times:
        raise ValueError("an IFS read with no hours")
    shape = next(iter(hours.values.values())).shape[1:]
    writer = LatestWriter(path, hours.times, (shape[0], shape[1]), run, seam=seam, offsets=offsets)
    writer.write(0, hours.values)
    writer.finish()


def latest_at(path: Path, times: list[datetime], window: Window) -> dict[str, np.ndarray]:
    """The kept hours at `times`, (times, y, x) per variable on the window it was read for; NaN for hours it
    doesn't hold (or with no read yet)."""
    out = {name: np.full((len(times), *window.shape), np.nan, dtype=np.float32) for name in SOIL}
    try:
        group = zarr.open_group(path, mode="r")
    except FileNotFoundError:
        return out
    first = datetime.fromisoformat(str(group.attrs["first"]))
    count = int(group.attrs["hours"])  # type: ignore[arg-type]
    index = np.array([int((t - first) / HOUR) for t in times])
    inside = (index >= 0) & (index < count)
    if not inside.any():
        return out
    lo, hi = int(index[inside].min()), int(index[inside].max()) + 1
    for name in SOIL:
        if name not in group:
            continue  # a read kept before the variable was read (soil moisture): missing until the next run
        block = np.asarray(group[name][lo:hi])  # type: ignore[index]
        if block.shape[1:] != window.shape:
            raise ValueError(f"{path} was read for another window")
        out[name][inside] = block[index[inside] - lo]
    return out
