"""gridMET (Abatzoglou 2013), the 30-year climatology's days before the archive (D82, D84; Phase 6 D3).

gridMET is a daily 1/24° (~4 km) grid over the lower 48 from 1979, PRISM's monthly climate given NLDAS-2's
day-to-day weather, from the University of Idaho's Northwest Knowledge Network. Its day runs 12Z to 12Z, labelled
by its start, so a minimum and a day's rain take in some of our next morning (D2, `docs/validation-climate.md`).

Each variable's year is a whole-CONUS netCDF-4 file (`<var>_<year>.nc`, 60–150 MB), chunked 61 days × 98 × 231
and served with byte ranges, so `fetch` reads only the chunks over the box (Wisconsin's year of one variable:
~20 s) and keeps them as received, cropped: `data_dir/gridmet/<var>/<year>.nc`, the same packed integers, scale,
offset and attributes, rows north to south as gridMET has them. `read` unpacks one into our daily variable's unit,
south to north; `regrid` takes it to the 2.5 km grid by the cubic B-spline (D80). gridMET has no values over the
Great Lakes, so its land points carry the coast rule as ERA5-Land's do (`agdata.coast`): a cell takes its land
neighbours, renormalized, or the nearest land point within 40 km, and on our own water mask nothing.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import fsspec
import h5netcdf
import h5py
import numpy as np

from agdata.coast import KERNEL_OFFSETS, Weights, bspline, finish, land_only
from agdata.grid import NDFD, Box, LatLonGrid, Window

URL = "https://www.northwestknowledge.net/metdata/data/{name}_{year}.nc"
KIND = "gridmet"
STEP = 1 / 24  # degrees
MARGIN = 0.25  # degrees kept past the window's cells: the B-spline's two points (0.08°) past every cell, and some
FIRST_YEAR = 1979
HEADERS = {"User-Agent": "agweather-gridmet"}
BLOCK = 2**20  # bytes a range request reads at least
_KEPT_ATTRS = ("units", "description", "long_name", "standard_name", "scale_factor", "add_offset", "_Unsigned")


def _kelvin(values: np.ndarray) -> np.ndarray:
    return values - 273.15


def _day_mean_to_total(values: np.ndarray) -> np.ndarray:
    return values * 0.0864  # W/m² as a day's mean → MJ/m² over the day


@dataclass(frozen=True, kw_only=True)
class Source:
    """A gridMET variable and the daily variable it stands in for (`agdata.catalog.DAILY_VARIABLES`)."""

    name: str  # gridMET's (the file's prefix)
    daily: str
    convert: Callable[[np.ndarray], np.ndarray] | None = None  # gridMET's unit → the daily variable's


SOURCES = (
    Source(name="tmmx", daily="air_temperature_max", convert=_kelvin),
    Source(name="tmmn", daily="air_temperature_min", convert=_kelvin),
    Source(name="pr", daily="precipitation_sum"),
    Source(name="rmax", daily="relative_humidity_max"),
    Source(name="rmin", daily="relative_humidity_min"),
    Source(name="srad", daily="shortwave_radiation_sum", convert=_day_mean_to_total),
    Source(name="vs", daily="wind_speed_mean"),
    Source(name="pet", daily="et0_sum"),  # ASCE Penman-Monteith, short grass
)
BY_NAME = {s.name: s for s in SOURCES}


def url(name: str, year: int) -> str:
    return URL.format(name=name, year=year)


def path(data_dir: Path, name: str, year: int) -> Path:
    return Path(data_dir) / KIND / name / f"{year}.nc"


def kept(file: Path) -> bool:
    """Whether a file is one `fetch` wrote: netCDF-4 (HDF5). D2's netCDF-3 files from the subsetting service, in
    the same place, are fetched again."""
    try:
        with open(file, "rb") as f:
            return f.read(8) == b"\x89HDF\r\n\x1a\n"
    except FileNotFoundError:
        return False


def _dataset(f: h5py.File, name: str) -> h5py.Dataset:
    found = f[name]
    if not isinstance(found, h5py.Dataset):
        raise ValueError(f"{name} isn't a variable")
    return found


def _array(f: h5py.File, name: str) -> np.ndarray:
    return np.asarray(_dataset(f, name)[()])


def _data_variable(f: h5py.File) -> str:
    found = [k for k, v in f.items() if isinstance(v, h5py.Dataset) and v.ndim == 3]
    if len(found) != 1:
        raise ValueError(f"expected one gridded variable, found {found}")
    return found[0]


def _span(values: np.ndarray, low: float, high: float) -> slice:
    inside = np.flatnonzero((values >= low) & (values <= high))
    if inside.size == 0:
        raise ValueError(f"the file covers none of {low}..{high}")
    return slice(int(inside[0]), int(inside[-1]) + 1)


def _text(value: Any) -> Any:
    return value.decode() if isinstance(value, bytes | np.bytes_) else value


def extent(window: Window, margin: float = MARGIN) -> Box:
    """The latitudes and longitudes a window's cells reach (its edges curve on the Lambert grid), plus `margin`."""
    lat, lon = NDFD.window_latlon(window)
    return Box(
        south=float(np.min(lat)) - margin,
        west=float(np.min(lon)) - margin,
        north=float(np.max(lat)) + margin,
        east=float(np.max(lon)) + margin,
    )


def fetch(source: str, dest: Path, box: Box) -> int:
    """Crops the file at `source` (a URL, or any path fsspec opens) to `box` (`extent`) and writes it to `dest`
    as received (`write`). Returns the bytes written."""
    options = {"block_size": BLOCK, "headers": HEADERS} if source.startswith("http") else {}
    with fsspec.open(source, "rb", **options) as remote, h5py.File(remote, "r") as f:
        name = _data_variable(f)
        data = _dataset(f, name)
        lat, lon, day = _array(f, "lat"), _array(f, "lon"), _array(f, "day")
        if data.shape != (day.size, lat.size, lon.size):
            raise ValueError(f"{name} is {data.shape}, not day × lat × lon {(day.size, lat.size, lon.size)}")
        rows = _span(lat, box.south, box.north)
        cols = _span(lon, box.west, box.east)
        values = np.asarray(data[:, rows, cols])
        fill = data.attrs.get("_FillValue")
        write(
            dest,
            name=name,
            values=values,
            day=day,
            lat=lat[rows],
            lon=lon[cols],
            attrs={k: _text(data.attrs[k]) for k in _KEPT_ATTRS if k in data.attrs},
            fill=None if fill is None else np.asarray(fill).ravel()[0],
            coord_attrs={
                c: {k: _text(v) for k, v in _dataset(f, c).attrs.items() if k in ("units", "long_name", "calendar")}
                for c in ("day", "lat", "lon")
            },
            global_attrs={k: _text(v) for k, v in f.attrs.items() if not k.startswith("_")},
            source=source,
        )
    return dest.stat().st_size


def write(
    dest: Path,
    *,
    name: str,
    values: np.ndarray,
    day: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    attrs: dict[str, Any],
    fill: Any = None,
    coord_attrs: dict[str, dict[str, Any]] | None = None,
    global_attrs: dict[str, Any] | None = None,
    source: str = "",
) -> None:
    """A gridMET-shaped file (netCDF-4, gzip): `name` (day × lat × lon, packed as given, with `attrs`), and the
    `day` (days since 1900-01-01), `lat`, `lon` axes. Written beside `dest` and renamed, so a stopped write leaves
    nothing half-written."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    coord_attrs = coord_attrs or {}
    with h5netcdf.File(part, "w") as out:
        out.dimensions = {"day": day.size, "lat": lat.size, "lon": lon.size}
        for coord, axis in (("day", day), ("lat", lat), ("lon", lon)):
            v = out.create_variable(coord, (coord,), data=axis)
            v.attrs.update(coord_attrs.get(coord, {}))
        v = out.create_variable(
            name,
            ("day", "lat", "lon"),
            data=values,
            compression="gzip",
            compression_opts=4,
            chunks=(min(61, day.size), lat.size, lon.size),
            fillvalue=fill,
        )
        v.attrs.update(attrs)
        out.attrs.update(global_attrs or {})
        out.attrs["agweather_source"] = source
        out.attrs["agweather_fetched"] = datetime.now(UTC).isoformat(timespec="seconds")
    part.rename(dest)


@dataclass(frozen=True, kw_only=True)
class Year:
    """A kept file unpacked: `values` (days, ny, nx) in the daily variable's unit, NaN where missing, rows south to
    north on `grid`."""

    source: Source
    days: list[date]
    values: np.ndarray
    grid: LatLonGrid


def read(file: Path, name: str) -> Year:
    source = BY_NAME[name]
    with h5py.File(file, "r") as f:
        data = _dataset(f, _data_variable(f))
        raw = np.asarray(data[()])
        lat, lon, day = _array(f, "lat"), _array(f, "lon"), _array(f, "day")
        fill = data.attrs.get("_FillValue")
        scale = float(np.asarray(data.attrs.get("scale_factor", 1.0)).ravel()[0])
        offset = float(np.asarray(data.attrs.get("add_offset", 0.0)).ravel()[0])
    values = raw.astype(np.float32) * np.float32(scale) + np.float32(offset)
    if fill is not None:
        values[raw == np.asarray(fill).ravel()[0]] = np.nan
    if source.convert is not None:
        values = source.convert(values)
    if lat[0] > lat[-1]:  # gridMET's rows run north to south
        values, lat = values[:, ::-1], lat[::-1]
    step = float(np.median(np.diff(lat)))
    if abs(step - STEP) > 1e-6 or abs(float(np.median(np.diff(lon))) - STEP) > 1e-6:
        raise ValueError(f"{file}: expected a 1/24° grid")
    grid = LatLonGrid(
        name=f"gridMET {lat.size}×{lon.size}",
        first_lat=round(float(lat[0]), 6),
        first_lon=round(float(lon[0]), 6),
        step=STEP,
        ny=int(lat.size),
        nx=int(lon.size),
    )
    days = [date(1900, 1, 1) + timedelta(days=int(d)) for d in day]
    return Year(source=source, days=days, values=np.ascontiguousarray(values), grid=grid)


_weights: dict[tuple, Weights] = {}


def weights(grid: LatLonGrid, window: Window, land: np.ndarray) -> Weights:
    """Each window cell's 4 × 4 neighbours on `grid` and their cubic B-spline weights, by the coast rule over
    `land` (ny, nx: gridMET's points with values); kept per grid, window and land."""
    key = (grid, window, hash(np.packbits(land).tobytes()))
    if key in _weights:
        return _weights[key]
    is_land = land.ravel()
    lat, lon = NDFD.window_latlon(window)
    fj, fi = grid.fractional_index(lat, lon)
    j0, i0 = np.floor(fj).astype(np.int64), np.floor(fi).astype(np.int64)
    first, last = KERNEL_OFFSETS[0], KERNEL_OFFSETS[-1]
    if j0.min() + first < 0 or i0.min() + first < 0 or j0.max() + last >= grid.ny or i0.max() + last >= grid.nx:
        raise ValueError(f"{grid} doesn't surround {window}")
    wy, wx = bspline(fj - j0), bspline(fi - i0)
    cells, w = [], []
    for a, dj in enumerate(KERNEL_OFFSETS):
        for b, di in enumerate(KERNEL_OFFSETS):
            cells.append((j0 + dj) * grid.nx + (i0 + di))
            w.append(wy[a] * wx[b])
    spline = Weights(cells=np.stack(cells), weights=np.stack(w))
    land_points = np.flatnonzero(is_land)
    point_lat = grid.first_lat + (land_points // grid.nx) * grid.step
    point_lon = grid.first_lon + (land_points % grid.nx) * grid.step
    found, _ = finish(land_only(spline, is_land[spline.cells]), window, land_points, point_lat, point_lon)
    _weights[key] = found
    return found


def regrid(year: Year, window: Window) -> np.ndarray:
    """The year's days on the window (days, ny, nx), float32, NaN where missing. A point with a value on any day
    is land; on a day it's missing, its neighbours' weights are renormalized without it (`Weights.apply`)."""
    land = np.isfinite(year.values).any(axis=0)
    w = weights(year.grid, window, land)
    needed = w.needed
    flat = year.values.reshape(year.values.shape[0], -1)
    return w.apply(np.ascontiguousarray(flat[:, needed].T), needed)


def fetch_with_retries(
    name: str, year: int, dest: Path, box: Box, attempts: int = 4, backoff_s: float = 20.0
) -> tuple[int, float]:
    """`fetch` of gridMET's file with retries on network errors. Returns the bytes kept and the seconds taken."""
    started = time.monotonic()
    for attempt in range(1, attempts + 1):
        try:
            return fetch(url(name, year), dest, box), time.monotonic() - started
        except (OSError, TimeoutError) as error:  # fsspec's HTTP errors are OSErrors (FileNotFoundError on 404)
            if isinstance(error, FileNotFoundError) or attempt == attempts:
                raise
            time.sleep(backoff_s * attempt)
    raise AssertionError("unreachable")
