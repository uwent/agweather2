"""ERA5-Land from the Copernicus Climate Data Store: soil temperature and snow depth for the archive (D52).

ECMWF's land reanalysis on a 0.1° latitude/longitude grid, hourly, about 5 days behind real time. Its soil layers
are 0–7, 7–28 and 28–100 cm (`soil_temperature_level_1` … `_3`, GRIB `stl1` … `stl3`, K), taken to the catalog's
4, 10 and 30 cm as Open-Meteo's IFS layers are (`openmeteo.soil_at_depths`); snow depth is `snow_depth` (`sde`, m
of snow, not water). Against 80 Wisconet stations it matched their soil best of HRRR, IFS and ERA5-Land
(docs/validation-soil.md).

Checked 2026-10-31 (`reanalysis-era5-land`, GRIB, `download_format: unarchived`):
- Soil comes as GRIB1 and snow depth as GRIB2, both `regular_ll` scanning north to south; snow depth's longitudes
  are 0–360 and it's stamped as the previous day's 00Z plus a step, so hours are keyed by validity time.
- Water has values, not gaps: over Lake Michigan the three layers carry one temperature (the lake's). ERA5-Land's
  land-sea mask (`land_sea_mask`, a land fraction, lakes 0; time-invariant, and the CDS returns it for the whole
  globe whatever the area) marks land at 0.5 or more. Before regridding, water is set missing and then each missing
  cell beside land takes the mean of its land neighbours (`COAST_PASSES` cells out), so NDFD's shore cells get land
  values and open water stays missing.
- Requests queue at the CDS; a few hours over a small box came back in 24 s, a month over a state takes longer.
  The API is `https://cds.climate.copernicus.eu/api` with the account's key (`COPERNICUS_API_KEY`).
"""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.grid import NDFD, LatLonGrid, Window
from agdata.regrid import regrid
from agdata.sources.grib import eccodes
from agdata.sources.openmeteo import soil_at_depths
from agdata.units import convert

API = "https://cds.climate.copernicus.eu/api"
DATASET = "reanalysis-era5-land"
STEP = 0.1  # degrees
AREA_MARGIN = 0.2  # degrees requested beyond the window, so every cell has four neighbours
COAST_PASSES = 1
LAYERS = {  # GRIB short name → Open-Meteo's layer name (the same layers as IFS)
    "stl1": "soil_temperature_0_to_7cm",
    "stl2": "soil_temperature_7_to_28cm",
    "stl3": "soil_temperature_28_to_100cm",
}
REQUEST_VARIABLES = {
    "stl1": "soil_temperature_level_1",
    "stl2": "soil_temperature_level_2",
    "stl3": "soil_temperature_level_3",
    "sde": "snow_depth",
}


@dataclass(kw_only=True)
class Hours:
    """Hours at `times` on a window, by catalog variable: (hours, ny, nx), in stored units."""

    times: list[datetime]
    values: dict[str, np.ndarray]


def area(window: Window) -> list[float]:
    """The CDS `area` ([north, west, south, east], on the 0.1° grid) covering a window with a margin."""
    lat, lon = NDFD.window_latlon(window)
    north = math.ceil((float(lat.max()) + AREA_MARGIN) / STEP) * STEP
    south = math.floor((float(lat.min()) - AREA_MARGIN) / STEP) * STEP
    west = math.floor((float(lon.min()) - AREA_MARGIN) / STEP) * STEP
    east = math.ceil((float(lon.max()) + AREA_MARGIN) / STEP) * STEP
    return [round(north, 1), round(west, 1), round(south, 1), round(east, 1)]


def request(first: date, last: date, window: Window) -> dict:
    """A CDS request for every hour of days first..last (one calendar month at most: CDS crosses the lists)."""
    if (first.year, first.month) != (last.year, last.month) or last < first:
        raise ValueError(f"a request covers days within one month, not {first}..{last}")
    return {
        "variable": list(REQUEST_VARIABLES.values()),
        "year": f"{first.year}",
        "month": f"{first.month:02d}",
        "day": [f"{d:02d}" for d in range(first.day, last.day + 1)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": area(window),
        "data_format": "grib",
        "download_format": "unarchived",
    }


def retrieve(first: date, last: date, window: Window, path: Path, key: str) -> Path:
    """Downloads days first..last over the window to `path` (blocks while the request queues)."""
    import cdsapi  # only the ingest job needs it

    client = cdsapi.Client(url=API, key=key, quiet=True, progress=False)
    client.retrieve(DATASET, request(first, last, window), str(path))
    return path


@dataclass(frozen=True, kw_only=True)
class LandMask:
    """ERA5-Land's land fraction on (part of) its grid, south to north."""

    grid: LatLonGrid
    fraction: np.ndarray

    def on(self, grid: LatLonGrid) -> np.ndarray:
        """Land (fraction ≥ 0.5) on another part of the grid, as a bool (ny, nx)."""
        j0 = round((grid.first_lat - self.grid.first_lat) / STEP)
        i0 = round((grid.first_lon - self.grid.first_lon) / STEP)
        if j0 < 0 or i0 < 0 or j0 + grid.ny > self.grid.ny or i0 + grid.nx > self.grid.nx:
            raise ValueError(f"the land mask ({self.grid}) doesn't cover {grid}")
        return self.fraction[j0 : j0 + grid.ny, i0 : i0 + grid.nx] >= 0.5

    def crop(self, window: Window) -> "LandMask":
        """The part covering a window's request area (what a deployment keeps)."""
        north, west, south, east = area(window)
        grid = LatLonGrid(
            name=self.grid.name,
            first_lat=south,
            first_lon=west,
            step=STEP,
            ny=round((north - south) / STEP) + 1,
            nx=round((east - west) / STEP) + 1,
        )
        return LandMask(grid=grid, fraction=self.fraction[self.on_slices(grid)])

    def on_slices(self, grid: LatLonGrid) -> tuple[slice, slice]:
        j0 = round((grid.first_lat - self.grid.first_lat) / STEP)
        i0 = round((grid.first_lon - self.grid.first_lon) / STEP)
        return slice(j0, j0 + grid.ny), slice(i0, i0 + grid.nx)

    def save(self, path: Path) -> None:
        g = self.grid
        np.savez_compressed(
            path, fraction=self.fraction.astype(np.float32), first=np.array([g.first_lat, g.first_lon]), name=g.name
        )

    @classmethod
    def load(cls, path: Path) -> "LandMask":
        with np.load(path) as f:
            fraction = f["fraction"].astype(np.float64)
            first_lat, first_lon = (float(x) for x in f["first"])
            name = str(f["name"])
        grid = LatLonGrid(
            name=name, first_lat=first_lat, first_lon=first_lon, step=STEP, ny=fraction.shape[0], nx=fraction.shape[1]
        )
        return cls(grid=grid, fraction=fraction)


def retrieve_land_mask(path: Path, key: str) -> Path:
    """Downloads ERA5-Land's land-sea mask (the whole globe, 19 MB of GRIB) to `path`."""
    import cdsapi

    client = cdsapi.Client(url=API, key=key, quiet=True, progress=False)
    client.retrieve(
        DATASET,
        {
            "variable": ["land_sea_mask"],
            "year": "2025",
            "month": "01",
            "day": ["01"],
            "time": ["00:00"],
            "data_format": "grib",
            "download_format": "unarchived",
        },
        str(path),
    )
    return path


def read_land_mask(path: Path) -> LandMask:
    """The land-sea mask GRIB → a LandMask; a global grid is rolled to start at -180° so boxes don't wrap."""
    with open(path, "rb") as f:
        handle = eccodes.codes_grib_new_from_file(f)
        if handle is None:
            raise ValueError(f"{path} has no messages")
        try:
            values, grid = _values(handle)
        finally:
            eccodes.codes_release(handle)
    if round(grid.nx * STEP) == 360:
        shift = round((grid.first_lon + 180) / STEP) % grid.nx
        values = np.roll(values, shift, axis=1)
        grid = LatLonGrid(name=grid.name, first_lat=grid.first_lat, first_lon=-180.0, step=STEP, ny=grid.ny, nx=grid.nx)
    return LandMask(grid=grid, fraction=values)


def read(path: Path, window: Window, land: LandMask) -> Hours:
    """A downloaded file's hours on the window: the catalog's soil depths (°C) and `snow_depth` (cm), each only
    from ERA5-Land's land cells."""
    fields: dict[datetime, dict[str, np.ndarray]] = defaultdict(dict)
    grid: LatLonGrid | None = None
    with open(path, "rb") as f:
        while (handle := eccodes.codes_grib_new_from_file(f)) is not None:
            try:
                name = eccodes.codes_get_string(handle, "shortName")
                if name not in REQUEST_VARIABLES:
                    continue
                when = valid_time(handle)
                values, message_grid = _values(handle)
            finally:
                eccodes.codes_release(handle)
            if grid is not None and message_grid != grid:
                raise ValueError(f"{path}: messages on different grids ({grid} and {message_grid})")
            grid = message_grid
            fields[when][name] = values
    times = sorted(fields)
    if grid is None:
        return Hours(times=[], values={})
    missing = {when: set(REQUEST_VARIABLES) - set(fields[when]) for when in times if len(fields[when]) < 4}
    if missing:
        raise ValueError(f"{path}: hours missing variables: {missing}")
    is_land = land.on(grid)
    out: dict[str, list[np.ndarray]] = defaultdict(list)
    for when in times:
        on_window = {
            name: regrid(fill_coast(np.where(is_land, values, np.nan)), grid, window)
            for name, values in fields[when].items()
        }
        layers = {LAYERS[name]: convert(on_window[name], "K", "degC") for name in LAYERS}
        for catalog_name, (value, _) in soil_at_depths(layers).items():
            out[catalog_name].append(value)
        out["snow_depth"].append(no_negative_snow(on_window["sde"]) * 100)  # m → cm
    return Hours(times=times, values={name: np.stack(v) for name, v in out.items()})


def valid_time(handle) -> datetime:
    day = eccodes.codes_get_long(handle, "validityDate")
    hhmm = eccodes.codes_get_long(handle, "validityTime")
    return datetime(day // 10000, day // 100 % 100, day % 100, hhmm // 100, tzinfo=UTC)


def _values(handle) -> tuple[np.ndarray, LatLonGrid]:
    """A message's values south to north, west to east, NaN where missing, and its grid."""
    if eccodes.codes_get_string(handle, "gridType") != "regular_ll":
        raise ValueError("expected a regular latitude/longitude grid")
    nx, ny = eccodes.codes_get_long(handle, "Ni"), eccodes.codes_get_long(handle, "Nj")
    values = np.asarray(eccodes.codes_get_double_array(handle, "values"), dtype=np.float64)
    if eccodes.codes_get_long(handle, "bitmapPresent"):
        values[values == eccodes.codes_get_double(handle, "missingValue")] = np.nan
    values = values.reshape(ny, nx)
    first_lat = eccodes.codes_get_double(handle, "latitudeOfFirstGridPointInDegrees")
    last_lat = eccodes.codes_get_double(handle, "latitudeOfLastGridPointInDegrees")
    if not eccodes.codes_get_long(handle, "jScansPositively"):
        values = values[::-1]
    first_lon = (eccodes.codes_get_double(handle, "longitudeOfFirstGridPointInDegrees") + 180) % 360 - 180
    grid = LatLonGrid(
        name="ERA5-Land 0.1°",
        first_lat=round(min(first_lat, last_lat), 4),
        first_lon=round(first_lon, 4),
        step=STEP,
        ny=int(ny),
        nx=int(nx),
    )
    return values, grid


def fill_coast(values: np.ndarray, passes: int = COAST_PASSES) -> np.ndarray:
    """Missing (sea) cells beside land take the mean of their land neighbours, `passes` cells out from shore."""
    out = values.copy()
    for _ in range(passes):
        missing = np.isnan(out)
        if not missing.any():
            break
        padded = np.pad(out, 1, constant_values=np.nan)
        neighbours = np.stack(
            [
                padded[1 + dj : 1 + dj + out.shape[0], 1 + di : 1 + di + out.shape[1]]
                for dj in (-1, 0, 1)
                for di in (-1, 0, 1)
                if dj or di
            ]
        )
        count = np.isfinite(neighbours).sum(axis=0)
        with np.errstate(invalid="ignore"):
            mean = np.nansum(neighbours, axis=0) / count
        out = np.where(missing & (count > 0), mean, out)
    return out


def days_of(first: date, last: date) -> list[tuple[date, date]]:
    """first..last split into calendar months, one request each."""
    spans = []
    day = first
    while day <= last:
        month_end = (day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        spans.append((day, min(month_end, last)))
        day = month_end + timedelta(days=1)
    return spans


def no_negative_snow(metres: np.ndarray) -> np.ndarray:
    """Snow depth with packing's tiny negatives (−1e-7 m and the like, on snow-free ground) set to 0, so QC's range
    doesn't drop a whole snow-free day; NaN stays NaN."""
    return np.where(metres < 0, 0.0, metres)
