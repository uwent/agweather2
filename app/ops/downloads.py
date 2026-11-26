"""Yearly NetCDF downloads of the daily variables (Phase 5 H2, D69, D71), served as static files.

One file per daily variable and year, `DATA_DIR/downloads/daily/{year}/{name}_{year}.nc`, with the year's days
through the last one rolled up: a past year whole, the current year to date. The values are the daily store's int16
copied as stored, declared as CF `scale_factor`, `add_offset` and `_FillValue` (lossless, 20-35% smaller than
float32; terra, xarray, GDAL and Panoply unpack them), written a month at a time whatever the box's size. Each file
holds one gridded variable on the native grid (`x`, `y` and the CF `grid_mapping`, as `api.gridfiles` writes it), so
GDAL opens it as one raster. The cells' latitude and longitude and their time zones (which set their days) are in
one `daily/grid.nc` beside the years (D71): with 2-D `lat` and `lon` in each file, GDAL saw three subdatasets, and
terra on Windows opened a file given by an absolute path (`D:/…`, the drive's colon in the subdataset name) with
the HDF5 driver, so without its CRS or its scale (Ben, 2026-11-05).

What's offered is the explicit list `OFFERED` (track 7, 2026-11-26): the daily weather layers, soil moisture
(D110), the day and night precipitation, the hours wet, the degree hours over 65 °F and the daily water balance
(computed from precipitation and ET0 as it's built, `agdata.computed`). Every other daily variable is a model's
working input or an estimate's working copy, listed in `NOT_OFFERED` with why; a test fails on a daily variable in
neither. A file whose variable is no longer offered (dropped, or renamed out of the catalog) is deleted with its
index entry (`prune`) before each build.

`index.json` beside them lists each file with the store's write stamp it was built from (`GridStore.written`). A file
is rebuilt when its store has been written since, the current year's at most weekly (`CURRENT_EVERY`), and any built
in another layout (`FORMAT`), by `manage.py downloads` and the weekly `build_downloads` job. Reads only the daily
stores, so it takes no write lock: a store written during a build has a new stamp and is rebuilt next time.
"""

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import h5netcdf
import numpy as np

from agdata import coverage
from agdata.catalog import DAILY_STATISTICS, DAILY_VARIABLES, FILL, Variable
from agdata.computed import DAILY_COMPUTED, Computed
from agdata.grid import NDFD, Window
from agdata.pastyears import years_on_disk
from agdata.store import DAILY, GridStore
from agdata.timezones import window_timezones
from api.envelope import attribution
from api.gridfiles import axis_attrs, cell_degrees, cf_lambert

FOLDER = "downloads"
# The files' layout; a file built in another is rebuilt. 1: int16 with lat/lon; 2: float32 with lat/lon; 3: int16,
# one variable, lat/lon in grid.nc (D71); 4: the comment no longer calls the days local (they're CST, D74)
FORMAT = 4
GRID_FILE = "daily/grid.nc"
CURRENT_EVERY = timedelta(days=7)  # the current year's files: rebuilt at most this often
BLOCK_DAYS = 31  # days read and written at a time
CF_STATS = {"min": "minimum", "max": "maximum", "mean": "mean", "sum": "sum"}
EPOCH = date(1970, 1, 1)


# The yearly files offered, in the order `/data` lists them. Daily stored variables, and computed ones
# (`agdata.computed.DAILY_COMPUTED`), which `build` computes from their inputs.
OFFERED: tuple[str, ...] = (
    "air_temperature_min",
    "air_temperature_max",
    "air_temperature_mean",
    "air_temperature_min_overnight",
    "dew_point_min",
    "dew_point_max",
    "dew_point_mean",
    "dew_point_depression_min",
    "dew_point_depression_mean",
    "dew_point_depression_max",
    "relative_humidity_min",
    "relative_humidity_max",
    "relative_humidity_mean",
    "wind_speed_mean",
    "wind_speed_max",
    "wind_gust_max",
    "surface_pressure_mean",
    "cloud_cover_mean",
    "precipitation_sum",
    "precipitation_7am_to_7pm",
    "precipitation_8pm_to_6am",
    "shortwave_radiation_sum",
    "et0_sum",
    "water_balance",
    "soil_temperature_4cm_min",
    "soil_temperature_4cm_max",
    "soil_temperature_4cm_mean",
    "soil_temperature_10cm_min",
    "soil_temperature_10cm_max",
    "soil_temperature_10cm_mean",
    "soil_temperature_30cm_min",
    "soil_temperature_30cm_max",
    "soil_temperature_30cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "soil_moisture_28_to_100cm_mean",
    "snow_depth_max",
    "snow_depth_mean",
    "hours_temperature_over_20c",
    "hours_temperature_over_30c",
    "hours_rh_under_70",
    "hours_rh_over_80",
    "hours_rh_over_90",
    "hours_rh_over_90_temperature_over_70f",
    "hours_rh_over_80_from_6pm",
    "hours_rh_over_90_from_6pm",
    "hours_rh_over_80_night",
    "hours_rh_over_90_night",
    "hours_rh_over_90_7pm_to_6am",
    "temperature_mean_rh_over_80_from_6pm",
    "temperature_mean_rh_over_90_from_6pm",
    "hours_wet",
    "hours_soil_4cm_below_27f",
    "hours_soil_10cm_below_27f",
    "hours_soil_8in_below_27f",
    "degree_hours_over_65f",
    "chill_hours",
    "utah_chill_units",
    "thi_min",
    "thi_mean",
    "thi_max",
    "hours_thi_over_68",
    "hours_thi_over_72",
    "cci_max",
)

# The daily variables not offered, and why
NOT_OFFERED: dict[str, str] = {
    "et0_sum_estimate": "a gap fill's working copy of ET0: et0_sum holds the values",
    "scab_infection": "apple scab's working input (D96): its map shows the result",
    "scab_wet_hours": "apple scab's working input (D96)",
    "scab_wet_temperature": "apple scab's working input (D96)",
    "scab_period_truncated": "apple scab's working flag (D96)",
    "temperature_mean_rain_7am_to_7pm": "a disease model's working input, meaningful only beside its rain",
    "cougarblight_risk_values": "fire blight's working input: its map shows the result",
}


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
    names = variables or list(OFFERED)
    stored = sorted({n for name in names for n in _inputs(name)})
    found = []
    for year in years_on_disk(data_dir, DAILY):
        store = GridStore.open(data_dir, DAILY, year, [DAILY_VARIABLES[n] for n in stored], add_missing=False)
        for name in names:
            written, has = _written(store, name)
            if written is None or not has.any():
                continue  # nothing rolled up, as `build` judges it (2024's ET0 estimate: no day needed one)
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


def _inputs(name: str) -> tuple[str, ...]:
    """The stored daily variables a file is made from: itself, or a computed variable's inputs."""
    return DAILY_COMPUTED[name].inputs if name in DAILY_COMPUTED else (name,)


def _variable(name: str) -> Variable:
    return DAILY_COMPUTED[name].variable if name in DAILY_COMPUTED else DAILY_VARIABLES[name]


def _written(store: GridStore, name: str) -> tuple[float | None, np.ndarray]:
    """The write stamp a file of `name` is built from (a computed variable's newest input's; None if an input was
    never written) and the days it has (a computed variable's: those every input has)."""
    stamps = [store.written(n) for n in _inputs(name)]
    has = np.logical_and.reduce([store.has_data(n) for n in _inputs(name)])
    known = [stamp for stamp in stamps if stamp is not None]
    return (max(known) if len(known) == len(stamps) else None), has


def prune(data_dir: Path, dry_run: bool = False) -> list[Entry]:
    """Delete the files whose variable isn't offered (`OFFERED`) and drop them from the index; the entries removed.
    With `dry_run`, only say which."""
    entries = read_index(data_dir)
    gone = [e for e in entries if e.variable not in OFFERED]
    if gone and not dry_run:
        for e in gone:
            (folder(data_dir) / e.path).unlink(missing_ok=True)
        write_index(data_dir, [e for e in entries if e.variable in OFFERED])
    return gone


def build(data_dir: Path, name: str, year: int, now: datetime) -> Entry | None:
    """Write one variable's year (None if the store has no days of it) and return its index entry."""
    store = GridStore.open(data_dir, DAILY, year, [DAILY_VARIABLES[n] for n in _inputs(name)])
    written, has = _written(store, name)
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
    """Remove the files no longer offered (`prune`), then build every file `wanted` lists, updating the index after
    each; the entries built."""
    prune(data_dir)
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
    if years and (built or not (folder(data_dir) / GRID_FILE).exists()):
        write_grid(data_dir, GridStore.open(data_dir, DAILY, years[-1], []), now)
        (folder(data_dir) / "daily" / "time_zones.nc").unlink(
            missing_ok=True
        )  # its predecessor (time zones only), before D71
    if progress is not None:
        progress(len(todo), len(todo), "")
    return built


def write_grid(data_dir: Path, store: GridStore, now: datetime) -> Path:
    """`daily/grid.nc`: each cell's latitude and longitude (its center) and local time zone, on the same grid as
    every year's files, for plotting without a projection library (D71). Every file's days are CST (D74); the zone
    is for showing a cell's hours on its own clock."""
    window = coverage.extent(store.window)
    zones, zone_index = window_timezones(window)
    jj, ii = np.arange(window.j0, window.j1), np.arange(window.i0, window.i1)
    lat, lon = NDFD.latlon(*np.meshgrid(jj, ii, indexing="ij"))
    path = folder(data_dir) / GRID_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".nc.tmp")
    with h5netcdf.File(temporary, "w") as f:
        _grid(f, window)
        f.attrs.update(
            _attrs("The grid of AgWeather's yearly files: each cell's latitude, longitude and time zone", now)
        )
        for key, values in (("lat", lat), ("lon", lon)):
            var = f.create_variable(
                key, ("y", "x"), np.float32, data=values.astype(np.float32), compression="gzip", shuffle=True
            )
            var.attrs.update(cell_degrees("latitude" if key == "lat" else "longitude"))
        tz = f.create_variable("time_zone", ("y", "x"), np.int8, data=zone_index.astype(np.int8), compression="gzip")
        tz.attrs.update(
            {
                "long_name": "the cell's local time zone (each day in these files runs midnight to midnight CST)",
                "flag_values": np.arange(len(zones), dtype=np.int8),
                "flag_meanings": " ".join(zones),
                "grid_mapping": "lambert_conformal_conic",
            }
        )
    os.replace(temporary, path)
    return path


def _grid(f: h5netcdf.File, window: Window) -> None:
    """The native grid's projected coordinates over `window` and its projection (`api.gridfiles`)."""
    ny, nx = window.shape
    jj, ii = np.arange(window.j0, window.j1), np.arange(window.i0, window.i1)
    x0, y0 = NDFD.origin
    f.dimensions.update({"y": ny, "x": nx})
    x = f.create_variable("x", ("x",), np.float64, data=x0 + ii * NDFD.dx)
    x.attrs.update(axis_attrs("X", "projection_x_coordinate", "x on the Lambert grid", "m"))
    y = f.create_variable("y", ("y",), np.float64, data=y0 + jj * NDFD.dx)
    y.attrs.update(axis_attrs("Y", "projection_y_coordinate", "y on the Lambert grid", "m"))
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
        "days": "Each day runs midnight to midnight Central Standard Time all year (06:00 to 06:00 UTC).",
    }


def _write(path: Path, store: GridStore, name: str, n: int, first: date, now: datetime) -> None:
    v = _variable(name)
    computed = DAILY_COMPUTED.get(name)
    window = coverage.extent(store.window)  # the covered cells' rectangle, without a coverage window's margin (D107)
    ny, nx = window.shape
    statistic = DAILY_STATISTICS[name].stat if name in DAILY_STATISTICS else None  # hour counts aren't statistics
    if computed is not None and computed.adds_up:
        statistic = "sum"  # the water balance: a day's precipitation less its ET0, both totals
    with h5netcdf.File(path, "w") as f:
        f.dimensions = {"time": n}
        _grid(f, window)
        f.attrs.update(
            {
                **_attrs(f"{v.long_name}, {first.year}", now),
                "comment": "Each cell's latitude, longitude and time zone are in grid.nc beside the yearly folders. Missing values are left missing, never set to zero.",
            }
        )
        time = f.create_variable("time", ("time",), np.int32, data=np.arange(n, dtype=np.int32) + _days(first))
        time.attrs.update(
            {"standard_name": "time", "axis": "T", "units": "days since 1970-01-01", "calendar": "standard"}
        )
        data = f.create_variable(
            name,
            ("time", "y", "x"),
            np.int16,
            fillvalue=np.int16(FILL),
            chunks=(1, ny, nx),
            compression="gzip",
            compression_opts=6,
            shuffle=True,
        )
        data.attrs.update(
            {
                "long_name": v.long_name,
                "units": v.unit,
                "scale_factor": np.float32(v.scale),  # readers unpack to its type: float32 halves a year in memory
                "add_offset": np.float32(v.offset),
                "valid_min": _packed(v.valid_min, v.scale, v.offset),
                "valid_max": _packed(v.valid_max, v.scale, v.offset),
                "grid_mapping": "lambert_conformal_conic",
            }
        )
        if statistic is not None:
            data.attrs["cell_methods"] = f"time: {CF_STATS[statistic]}"
        for start in range(0, n, BLOCK_DAYS):
            stop = min(start + BLOCK_DAYS, n)
            data[start:stop] = _packed_days(store, name, computed, v, start, stop, window)


def _packed_days(
    store: GridStore, name: str, computed: Computed | None, v: Variable, start: int, stop: int, window: Window
) -> np.ndarray:
    """Days start..stop-1 packed as the file holds them: a stored variable's int16 as stored, a computed one's
    value from its inputs packed by its own scale and offset (missing wherever an input is)."""
    if computed is None:
        return store.read_packed(name, start, stop, window=window)
    inputs = {n: store.read_steps(n, start, stop, window=window) for n in computed.inputs}
    return v.encode(np.clip(computed.compute(inputs), v.valid_min, v.valid_max))


def _packed(value: float, scale: float, offset: float) -> np.int16:
    """A value in the stored unit as the file packs it, within int16's range (FILL itself means missing)."""
    return np.int16(np.clip(round((value - offset) / scale), int(FILL) + 1, np.iinfo(np.int16).max))


def _days(day: date) -> int:
    return (day - EPOCH).days
