"""ERA5-Land as received, a store per year on its own 0.1° grid (D79): `data_dir/era5land/<year>.zarr`.

The hourly store's soil temperature and snow depth are derived from it (`era5land.derive`, the coast rule in
`agdata.coast`), so a change to how they're derived is a rebuild from here (`manage.py era5land --rederive`), not a
download. Every value is kept, water included, in ERA5-Land's units (`stl1`..`stl3` K, `sde` m), float32 with
pcodec (lossless), as the other stores. A year over the launch box is roughly 0.5–1 GB.

Arrays are (hours of the year, ny, nx), rows south to north, a chunk a day; `written` holds when each hour was last
written (Unix seconds, NaN never). The grid is the one the first write brought (the CDS request's area for the
service box) and later writes must match it.
"""

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import zarr
from zarr.codecs.numcodecs import PCodec

from agdata.grid import LatLonGrid
from agdata.sources.era5land import REQUEST_VARIABLES, Native
from agdata.store import steps_in_year

KIND = "era5land"
HOUR = timedelta(hours=1)
CHUNK_HOURS = 24


def path(data_dir: Path, year: int) -> Path:
    return Path(data_dir) / KIND / f"{year}.zarr"


def years(data_dir: Path) -> list[int]:
    folder = Path(data_dir) / KIND
    return sorted(int(p.stem) for p in folder.glob("*.zarr")) if folder.exists() else []


def _grid_attrs(grid: LatLonGrid) -> dict:
    return {
        "name": grid.name,
        "first_lat": grid.first_lat,
        "first_lon": grid.first_lon,
        "step": grid.step,
        "ny": grid.ny,
        "nx": grid.nx,
    }


def _grid(attrs: dict) -> LatLonGrid:
    g = attrs["grid"]
    return LatLonGrid(
        name=g["name"],
        first_lat=g["first_lat"],
        first_lon=g["first_lon"],
        step=g["step"],
        ny=int(g["ny"]),
        nx=int(g["nx"]),
    )


def _open(data_dir: Path, year: int, grid: LatLonGrid) -> zarr.Group:
    where = path(data_dir, year)
    if where.exists():
        group = zarr.open_group(where, mode="r+")
        held = _grid(dict(group.attrs))
        if held != grid:
            raise ValueError(f"{where} holds {held}, not {grid}; a new box needs a new store")
        return group
    where.parent.mkdir(parents=True, exist_ok=True)
    group = zarr.open_group(where, mode="w")
    group.attrs.update({"grid": _grid_attrs(grid), "source": "ERA5-Land (Copernicus CDS), as received", "year": year})
    n = steps_in_year(year, "hour")
    for name in REQUEST_VARIABLES:
        group.create_array(
            name,
            shape=(n, grid.ny, grid.nx),
            chunks=(CHUNK_HOURS, grid.ny, grid.nx),
            dtype="float32",
            fill_value=np.nan,
            serializer=PCodec(level=8),
            compressors=(),
            dimension_names=("time", "y", "x"),
            attributes={"units": "m" if name == "sde" else "K", "long_name": REQUEST_VARIABLES[name]},
        )
    group.create_array("written", shape=(n,), chunks=(n,), dtype="float64", fill_value=np.nan)
    return group


def write(data_dir: Path, native: Native) -> int:
    """Writes a file's hours into the stores of their years; returns the hours written. The caller holds the write
    lock."""
    times = native.times
    written = 0
    for year in sorted({t.year for t in times}):
        group = _open(data_dir, year, native.grid)
        start = datetime(year, 1, 1, tzinfo=UTC)
        rows = [k for k, t in enumerate(times) if t.year == year]
        index = np.array([int((times[k] - start) / HOUR) for k in rows])
        # Runs of consecutive hours, each written as one slice
        breaks = np.flatnonzero(np.diff(index) != 1) + 1
        for run in np.split(np.arange(len(rows)), breaks):
            t0, t1 = int(index[run[0]]), int(index[run[-1]]) + 1
            k0, k1 = rows[run[0]], rows[run[-1]] + 1
            for name in REQUEST_VARIABLES:
                _array(group, name)[t0:t1] = native.values[name][k0:k1]
            _array(group, "written")[t0:t1] = time.time()
        written += len(rows)
    return written


def read(data_dir: Path, first: datetime, last: datetime) -> Native | None:
    """Hours first..last (UTC, within one year) as they were received; None if the year has no store. Hours never
    written are NaN."""
    if first.year != last.year:
        raise ValueError("a read covers one year")
    where = path(data_dir, first.year)
    if not where.exists():
        return None
    group = zarr.open_group(where, mode="r")
    start = datetime(first.year, 1, 1, tzinfo=UTC)
    t0, t1 = int((first - start) / HOUR), int((last - start) / HOUR) + 1
    values = {name: np.asarray(_array(group, name)[t0:t1], dtype=np.float32) for name in REQUEST_VARIABLES}
    times = [first + k * HOUR for k in range(t1 - t0)]
    return Native(times=times, grid=_grid(dict(group.attrs)), values=values)


def written_hours(data_dir: Path, year: int) -> np.ndarray:
    """Which hours of the year the store holds (bool, by hour of the year); all False without a store."""
    where = path(data_dir, year)
    if not where.exists():
        return np.zeros(steps_in_year(year, "hour"), dtype=bool)
    return np.isfinite(np.asarray(_array(zarr.open_group(where, mode="r"), "written")[:]))


def _array(group: zarr.Group, name: str) -> zarr.Array:
    found = group[name]
    assert isinstance(found, zarr.Array)
    return found
