"""Yearly NetCDF downloads of the daily variables (PLAN.md Phase 5 H2, D69), served as static files.

One file per daily variable and year, `DATA_DIR/downloads/daily/{year}/{name}_{year}.nc`, with the year's days
through the last one rolled up: a past year whole, the current year to date. The values are plain float32 in the
stored unit, NaN where missing, written a month at a time whatever the box's size. They were first the store's int16
with CF `scale_factor` (lossless and 20-35% smaller), but a viewer Ben opened them in showed the packed integers
(temperatures ×10): not every GIS tool applies `scale_factor`, so a public file mustn't need it (FORMAT 2).
The grid and its projection are `api.gridfiles`' (the same as `/grids` in NetCDF); each cell's time zone, which
sets its days, is in `daily/time_zones.nc`.

`index.json` beside them lists each file with the store's write stamp it was built from (`GridStore.written`). A file
is rebuilt when its store has been written since, and the current year's at most weekly (`CURRENT_EVERY`), by
`manage.py downloads` and the weekly `build_downloads` job. Reads only the daily stores, so it takes no write lock:
a store written during a build has a new stamp and is rebuilt next time.
"""

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import h5netcdf
import numpy as np

from agdata.catalog import DAILY_STATISTICS, DAILY_VARIABLES
from agdata.daily import cell_timezones
from agdata.grid import NDFD
from agdata.pastyears import years_on_disk
from agdata.store import DAILY, GridStore
from api.envelope import attribution
from api.gridfiles import axis_attrs, cell_degrees, cf_lambert

FOLDER = "downloads"
FORMAT = 2  # the files' layout: a file built in another is rebuilt (1: int16 with scale_factor; 2: float32)
CURRENT_EVERY = timedelta(days=7)  # the current year's files: rebuilt at most this often
BLOCK_DAYS = 31  # days read and written at a time
CF_STATS = {"min": "minimum", "max": "maximum", "mean": "mean", "sum": "sum"}
EPOCH = date(1970, 1, 1)


class Stopped(Exception):
    """Raised by a progress callback to stop `build_wanted` between files (the files built so far are indexed)."""


@dataclass(kw_only=True)
class Entry:
    """One file in `index.json`."""

    variable: str
    year: int
    path: str  # under the downloads folder, as served under /downloads/
    bytes: int
    first: str  # the first and last day it holds (ISO)
    last: str
    complete: bool  # holds every day of the year
    written: float  # the store's write stamp it was built from (epoch seconds)
    built_at: str  # ISO, UTC
    format: int = 1  # FORMAT when built (entries from before it existed are 1)


def folder(data_dir: Path) -> Path:
    return data_dir / FOLDER


def read_index(data_dir: Path) -> list[Entry]:
    path = folder(data_dir) / "index.json"
    if not path.exists():
        return []
    return [Entry(**item) for item in json.loads(path.read_text())]


def write_index(data_dir: Path, entries: list[Entry]) -> None:
    path = folder(data_dir) / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    entries = sorted(entries, key=lambda e: (e.variable, e.year))
    temporary.write_text(json.dumps([asdict(e) for e in entries], indent=1))
    os.replace(temporary, path)


def wanted(data_dir: Path, now: datetime, variables: list[str] | None = None) -> list[tuple[str, int, str]]:
    """(variable, year, why) for each file to build: missing, or built from an older write of its store; the current
    year's only if it's also older than CURRENT_EVERY."""
    known = {(e.variable, e.year): e for e in read_index(data_dir)}
    names = variables or list(DAILY_VARIABLES)
    found = []
    for year in years_on_disk(data_dir, DAILY):
        store = GridStore.open(data_dir, DAILY, year, [DAILY_VARIABLES[n] for n in names], add_missing=False)
        for name in names:
            written = store.written(name)
            if written is None:
                continue  # nothing rolled up
            entry = known.get((name, year))
            if entry is None:
                found.append((name, year, "missing"))
            elif entry.format != FORMAT:
                found.append((name, year, f"built in format {entry.format}, now {FORMAT}"))
            elif entry.written != written:
                built = datetime.fromisoformat(entry.built_at)
                if year < now.year or now - built >= CURRENT_EVERY:
                    found.append((name, year, "the store has been written since"))
    return found


def build(data_dir: Path, name: str, year: int, now: datetime) -> Entry | None:
    """Write one variable's year (None if the store has no days of it) and return its index entry."""
    v = DAILY_VARIABLES[name]
    store = GridStore.open(data_dir, DAILY, year, [v])
    written = store.written(name)
    has = store.has_data(name)
    if written is None or not has.any():
        return None
    n = int(np.flatnonzero(has)[-1]) + 1  # through the last day with values
    first = store.time_of(0).date()
    last = first + timedelta(days=n - 1)
    relative = f"daily/{year}/{name}_{year}.nc"
    path = folder(data_dir) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".nc.tmp")
    _write(temporary, store, name, n, first, now)
    os.replace(temporary, path)
    days_in_year = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    return Entry(
        variable=name,
        year=year,
        path=relative,
        bytes=path.stat().st_size,
        first=first.isoformat(),
        last=last.isoformat(),
        complete=n == days_in_year,
        written=written,
        built_at=now.astimezone(UTC).isoformat(timespec="seconds"),
        format=FORMAT,
    )


def build_wanted(
    data_dir: Path,
    now: datetime,
    variables: list[str] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> list[Entry]:
    """Build every file `wanted` lists, updating the index after each; the entries built."""
    todo = wanted(data_dir, now, variables)
    entries = {(e.variable, e.year): e for e in read_index(data_dir)}
    built = []
    for k, (name, year, _) in enumerate(todo):
        if progress is not None:
            progress(k, len(todo), f"{name} {year}")
        entry = build(data_dir, name, year, now)
        if entry is None:
            continue
        entries[(name, year)] = entry
        built.append(entry)
        write_index(data_dir, list(entries.values()))
    years = years_on_disk(data_dir, DAILY)
    if years and (built or not (folder(data_dir) / "daily" / "time_zones.nc").exists()):
        write_time_zones(data_dir, GridStore.open(data_dir, DAILY, years[-1], []), now)
    if progress is not None:
        progress(len(todo), len(todo), "")
    return built


def write_time_zones(data_dir: Path, store: GridStore, now: datetime) -> Path:
    """`daily/time_zones.nc`: each cell's time zone, which sets its days, for every year's files (kept apart from
    them: a second gridded variable in a file makes R's terra read it as one more layer)."""
    zones, zone_index = cell_timezones(store)
    path = folder(data_dir) / "daily" / "time_zones.nc"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".nc.tmp")
    with h5netcdf.File(temporary, "w") as f:
        _grid(f, store)
        f.attrs.update(_attrs("Time zones of the cells, which set their local calendar days", now))
        tz = f.create_variable("time_zone", ("y", "x"), np.int8, data=zone_index.astype(np.int8), compression="gzip")
        tz.attrs.update(
            {
                "long_name": "the cell's time zone",
                "flag_values": np.arange(len(zones), dtype=np.int8),
                "flag_meanings": " ".join(zones),
                "grid_mapping": "lambert_conformal_conic",
            }
        )
    os.replace(temporary, path)
    return path


def _grid(f: h5netcdf.File, store: GridStore) -> None:
    """The native grid's coordinates, the cells' latitude and longitude, and the projection (`api.gridfiles`)."""
    window = store.window
    ny, nx = window.shape
    jj, ii = np.arange(window.j0, window.j1), np.arange(window.i0, window.i1)
    x0, y0 = NDFD.origin
    lat, lon = NDFD.latlon(*np.meshgrid(jj, ii, indexing="ij"))
    f.dimensions.update({"y": ny, "x": nx})
    x = f.create_variable("x", ("x",), np.float64, data=x0 + ii * NDFD.dx)
    x.attrs.update(axis_attrs("X", "projection_x_coordinate", "x on the Lambert grid", "m"))
    y = f.create_variable("y", ("y",), np.float64, data=y0 + jj * NDFD.dx)
    y.attrs.update(axis_attrs("Y", "projection_y_coordinate", "y on the Lambert grid", "m"))
    for key, values in (("lat", lat), ("lon", lon)):
        var = f.create_variable(
            key, ("y", "x"), np.float32, data=values.astype(np.float32), compression="gzip", shuffle=True
        )
        var.attrs.update(cell_degrees("latitude" if key == "lat" else "longitude"))
    mapping = f.create_variable("lambert_conformal_conic", (), np.int32, data=np.int32(0))
    mapping.attrs.update(cf_lambert())


def _attrs(title: str, now: datetime) -> dict[str, str]:
    return {
        "Conventions": "CF-1.8",
        "title": title,
        "institution": "AgWeather, University of Wisconsin–Madison",
        "source": "AgWeather's archive of hourly weather on the National Weather Service's 2.5 km grid",
        "attribution": attribution(now.year),
        "history": f"{now.astimezone(UTC):%Y-%m-%dT%H:%MZ} written by AgWeather",
    }


def _write(path: Path, store: GridStore, name: str, n: int, first: date, now: datetime) -> None:
    v = DAILY_VARIABLES[name]
    ny, nx = store.window.shape
    statistic = DAILY_STATISTICS[name].stat if name in DAILY_STATISTICS else None  # hour counts aren't statistics
    with h5netcdf.File(path, "w") as f:
        f.dimensions = {"time": n}
        _grid(f, store)
        f.attrs.update(
            {
                **_attrs(f"{v.long_name}, {first.year}", now),
                "comment": "Each day is the local calendar day in the cell's time zone (time_zones.nc beside the "
                "yearly folders). Missing values are left missing, never set to zero.",
            }
        )
        time = f.create_variable("time", ("time",), np.int32, data=np.arange(n, dtype=np.int32) + _days(first))
        time.attrs.update(
            {"standard_name": "time", "axis": "T", "units": "days since 1970-01-01", "calendar": "standard"}
        )
        data = f.create_variable(
            name,
            ("time", "y", "x"),
            np.float32,
            fillvalue=np.float32(np.nan),
            chunks=(1, ny, nx),
            compression="gzip",
            compression_opts=6,
        )
        data.attrs.update(
            {
                "long_name": v.long_name,
                "units": v.unit,
                "valid_min": np.float32(v.valid_min),
                "valid_max": np.float32(v.valid_max),
                "grid_mapping": "lambert_conformal_conic",
            }
        )
        if statistic is not None:
            data.attrs["cell_methods"] = f"time: {CF_STATS[statistic]}"
        for start in range(0, n, BLOCK_DAYS):
            stop = min(start + BLOCK_DAYS, n)
            data[start:stop] = store.read_steps(name, start, stop).astype(np.float32)


def _days(day: date) -> int:
    return (day - EPOCH).days
