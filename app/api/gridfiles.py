"""Grids as files (docs/api.md, "Grids"): NetCDF for xarray and R, GeoTIFF for GIS.

The native grid is NDFD's Lambert conformal on a sphere (`agdata.grid.NDFD`), regular in projected x and y, so both
formats carry it exactly and the reader reprojects: NetCDF with a CF `grid_mapping` (and its WKT), GeoTIFF with
user-defined Lambert GeoKeys (no GDAL here; the keys follow the GeoTIFF 1.1 specification, OGC 19-008r4). Both name
the CRS `CRS_NAME` and describe it the same way: Lambert conformal, one standard parallel at 25° N, central meridian
95° W, scale 1, on NDFD's sphere.

A native-grid NetCDF carries each cell's latitude and longitude as plain 2-D variables `lat` and `lon` (float32,
units `degree`), for plotting without a projection library (`plt.pcolormesh(ds.lon, ds.lat, ds[name][0])`). They
are deliberately not CF auxiliary coordinates: with a `coordinates = "lat lon"` attribute, or CF's `standard_name`
and `degrees_north`/`degrees_east`, GDAL takes them as geolocation arrays in place of the projection, and R's terra
then can't reproject the file (its extent collapses to the projection's origin; terra 1.9.50, GDAL 3.13,
2026-11-04). xarray users who want them as coordinates call `ds.set_coords(["lat", "lon"])` after opening.

Compression: each data variable is chunked a whole map per step and deflated at level 6 (a week over Wisconsin:
1.64 MB raw, 0.36 MB); the lat/lon arrays are shuffled too, which helps their smooth values and not the data's.
A regular lat/lng grid (`grid=latlon`) is plain CF latitude/longitude, or EPSG:4326 in GeoTIFF.

NetCDF is NetCDF-4 (HDF5, through h5netcdf), zlib-compressed. GeoTIFF has one band per step, top row north,
missing as NaN (`GDAL_NODATA`), and each band's date in GDAL's metadata tag, which QGIS and rasterio show.
"""

import io
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import cache
from typing import Any

import numpy as np
import tifffile
import xarray as xr
from pyproj import CRS

from agdata.grid import NDFD, Window

R_EARTH = 6371200.0  # m, NDFD's sphere
LAT_0, LON_0 = 25.0, -95.0  # NDFD's standard parallel and central meridian (265 °E)
CRS_NAME = "NDFD CONUS 2.5 km Lambert conformal (sphere 6371200 m)"


@dataclass(kw_only=True)
class GridFile:
    """What goes in a file: `values` (steps, rows south to north, columns west to east) in `unit`, on a window of the
    native grid every `stride` cells, or on lat/lng points (`lats`, `lons`). `steps` label the bands (dates or UTC
    hours), or None for a statistic over a range (one band). `extra` holds per-cell counts beside a statistic."""

    name: str
    long_name: str
    unit: str
    values: np.ndarray
    steps: list[date] | list[datetime] | None
    window: Window | None = None
    stride: int = 1
    lats: np.ndarray | None = None
    lons: np.ndarray | None = None
    extra: dict[str, np.ndarray] = field(default_factory=dict)
    attrs: dict[str, Any] = field(default_factory=dict)  # meta, written as JSON strings
    cell_methods: str | None = None  # CF: how the values summarize time ("time: maximum")


def netcdf(grid: GridFile) -> bytes:
    data_vars: dict[str, Any] = {}
    coords: dict[str, Any] = {}
    if grid.window is not None:
        jj, ii = _native_indices(grid)
        x0, y0 = NDFD.origin
        coords["x"] = ("x", x0 + ii * NDFD.dx, _axis("X", "projection_x_coordinate", "x on the Lambert grid", "m"))
        coords["y"] = ("y", y0 + jj * NDFD.dx, _axis("Y", "projection_y_coordinate", "y on the Lambert grid", "m"))
        lat, lon = NDFD.latlon(*np.meshgrid(jj, ii, indexing="ij"))
        data_vars["lat"] = (("y", "x"), lat.astype(np.float32), _cell_degrees("latitude"))
        data_vars["lon"] = (("y", "x"), lon.astype(np.float32), _cell_degrees("longitude"))
        data_vars["lambert_conformal_conic"] = ((), np.int32(0), _cf_lambert())
        dims: tuple[str, ...] = ("y", "x")
        mapping = {"grid_mapping": "lambert_conformal_conic"}
    else:
        assert grid.lats is not None and grid.lons is not None
        coords["lat"] = ("lat", grid.lats, _axis("Y", "latitude", "latitude", "degrees_north"))
        coords["lon"] = ("lon", grid.lons, _axis("X", "longitude", "longitude", "degrees_east"))
        dims, mapping = ("lat", "lon"), {}
    attrs = {"long_name": grid.long_name, "units": grid.unit, **mapping}
    if grid.cell_methods:
        attrs["cell_methods"] = grid.cell_methods
    if grid.steps is not None:
        coords["time"] = ("time", _times(grid.steps), {"standard_name": "time", "axis": "T"})
        data_vars[grid.name] = (("time", *dims), grid.values.astype(np.float32), attrs)
    else:
        data_vars[grid.name] = (dims, grid.values[0].astype(np.float32), attrs)
    for name, values in grid.extra.items():
        data_vars[name] = (
            dims,
            values.astype(np.float32),
            {"long_name": name.replace("_", " "), "units": "day", **mapping},
        )
    # Coordinates have no fill value (CF forbids missing coordinates); the data's missing values are NaN
    encoding: dict[str, Any] = {name: {"_FillValue": None} for name in coords}
    shape = tuple(grid.values.shape[1:])
    for name in [grid.name, *grid.extra]:
        chunks = (1, *shape) if name == grid.name and grid.steps is not None else shape
        encoding[name] = {"zlib": True, "complevel": 6, "chunksizes": chunks, "_FillValue": np.float32(np.nan)}
    if grid.window is not None:
        for name in ("lat", "lon"):
            encoding[name] = {"zlib": True, "complevel": 6, "shuffle": True, "_FillValue": None}
    ds = xr.Dataset(data_vars=data_vars, coords=coords)
    ds.attrs = {"Conventions": "CF-1.8", **{k: _attr(v) for k, v in grid.attrs.items()}}
    return bytes(ds.to_netcdf(engine="h5netcdf", encoding=encoding))


def _cell_degrees(what: str) -> dict[str, str]:
    """A plain lat/lon variable's attributes: no `standard_name` or CF units, so GDAL doesn't take it as geolocation."""
    return {
        "long_name": f"{what} of the cell center",
        "units": "degree",
        "comment": "for plotting without a projection library; not CF auxiliary coordinates, so GIS software uses "
        "the grid_mapping (see docs/api.md, Grids)",
    }


def _axis(axis: str, standard_name: str, long_name: str, units: str) -> dict[str, str]:
    return {"axis": axis, "standard_name": standard_name, "long_name": long_name, "units": units}


def geotiff(grid: GridFile) -> bytes:
    bands = list(grid.values) + list(grid.extra.values())
    labels = [_label(s) for s in grid.steps] if grid.steps is not None else ["value"]
    labels += list(grid.extra)
    data = np.stack([np.flipud(b) for b in bands]).astype(np.float32)  # GeoTIFF's first row is the north
    if grid.window is not None:
        jj, ii = _native_indices(grid)
        x0, y0 = NDFD.origin
        size = NDFD.dx * grid.stride
        west = x0 + ii[0] * NDFD.dx - size / 2
        north = y0 + jj[-1] * NDFD.dx + size / 2
        keys, doubles, ascii_params = _lambert_keys()
    else:
        assert grid.lats is not None and grid.lons is not None
        size = float(grid.lons[1] - grid.lons[0]) if grid.lons.size > 1 else float(grid.lats[1] - grid.lats[0])
        west, north = float(grid.lons[0]) - size / 2, float(grid.lats[-1]) + size / 2
        keys, doubles, ascii_params = _wgs84_keys()
    items = "".join(
        f'<Item name="DESCRIPTION" sample="{k}" role="description">{label}</Item>' for k, label in enumerate(labels)
    )
    unit = "".join(f'<Item name="UNITTYPE" sample="{k}" role="unittype">{grid.unit}</Item>' for k in range(len(bands)))
    metadata = f'<GDALMetadata><Item name="NAME">{grid.name}</Item>{items}{unit}</GDALMetadata>'
    extratags = [
        (33550, "d", 3, (size, size, 0.0), True),  # ModelPixelScale
        (33922, "d", 6, (0.0, 0.0, 0.0, west, north, 0.0), True),  # ModelTiepoint: the top-left corner
        (34735, "H", len(keys), tuple(keys), True),  # GeoKeyDirectory
        (34736, "d", len(doubles), tuple(doubles), True),  # GeoDoubleParams
        (34737, "s", 0, ascii_params, True),  # GeoAsciiParams
        (42112, "s", 0, metadata, True),  # GDAL_METADATA
        (42113, "s", 0, "nan", True),  # GDAL_NODATA
    ]
    out = io.BytesIO()
    tifffile.imwrite(
        out,
        data if len(bands) > 1 else data[0],
        photometric="minisblack",
        planarconfig="separate" if len(bands) > 1 else None,
        compression="zlib",
        extratags=extratags,
        metadata=None,
    )
    return out.getvalue()


def _native_indices(grid: GridFile) -> tuple[np.ndarray, np.ndarray]:
    assert grid.window is not None
    w, s = grid.window, grid.stride
    return np.arange(w.j0, w.j1, s), np.arange(w.i0, w.i1, s)


def _cf_lambert() -> dict[str, Any]:
    return {
        "grid_mapping_name": "lambert_conformal_conic",
        "standard_parallel": LAT_0,
        "longitude_of_central_meridian": LON_0,
        "latitude_of_projection_origin": LAT_0,
        "false_easting": 0.0,
        "false_northing": 0.0,
        "earth_radius": R_EARTH,
        "crs_wkt": crs().to_wkt(),
    }


@cache
def crs() -> CRS:
    """NDFD's projection as both files describe it: the grid's own (`NDFD.crs`, a two-parallel Lambert at 265° E with
    both parallels at 25°) is the same projection, written here as the one-parallel form CF and GeoTIFF use, named."""
    sphere = {"name": "NDFD sphere", "radius": R_EARTH}
    return CRS.from_json_dict(
        {
            "$schema": "https://proj.org/schemas/v0.7/projjson.schema.json",
            "type": "ProjectedCRS",
            "name": CRS_NAME,
            "base_crs": {
                "name": "NDFD sphere",
                "datum": {"type": "GeodeticReferenceFrame", "name": "NDFD sphere", "ellipsoid": sphere},
                "coordinate_system": {
                    "subtype": "ellipsoidal",
                    "axis": [
                        {"name": "Longitude", "abbreviation": "lon", "direction": "east", "unit": "degree"},
                        {"name": "Latitude", "abbreviation": "lat", "direction": "north", "unit": "degree"},
                    ],
                },
            },
            "conversion": {
                "name": "NDFD Lambert conformal",
                "method": {"name": "Lambert Conic Conformal (1SP)", "id": {"authority": "EPSG", "code": 9801}},
                "parameters": [
                    {"name": "Latitude of natural origin", "value": LAT_0, "unit": "degree"},
                    {"name": "Longitude of natural origin", "value": LON_0, "unit": "degree"},
                    {"name": "Scale factor at natural origin", "value": 1.0, "unit": "unity"},
                    {"name": "False easting", "value": 0.0, "unit": "metre"},
                    {"name": "False northing", "value": 0.0, "unit": "metre"},
                ],
            },
            "coordinate_system": {
                "subtype": "Cartesian",
                "axis": [
                    {"name": "Easting", "abbreviation": "E", "direction": "east", "unit": "metre"},
                    {"name": "Northing", "abbreviation": "N", "direction": "north", "unit": "metre"},
                ],
            },
        }
    )


def _times(steps: list[date] | list[datetime]) -> np.ndarray:
    if all(isinstance(s, datetime) for s in steps):
        return np.array(
            [np.datetime64(s.astimezone(UTC).replace(tzinfo=None), "s") for s in steps if isinstance(s, datetime)]
        )
    return np.array([np.datetime64(s, "D") for s in steps])


def _label(step: date | datetime) -> str:
    return step.strftime("%Y-%m-%dT%H:%MZ") if isinstance(step, datetime) else step.isoformat()


def _attr(value: Any) -> str | int | float:
    if isinstance(value, str | int | float):
        return value
    return json.dumps(value, default=str, separators=(",", ":"))


# GeoKey ids and codes (GeoTIFF 1.1, OGC 19-008r4)
_USER_DEFINED = 32767


def _directory(shorts: list[tuple[int, int]], doubles: list[tuple[int, float]], texts: list[tuple[int, str]]):
    """The GeoKeyDirectory from keys holding a short, a double or text, sorted by key id."""
    entries: list[tuple[int, int, int, int]] = [(key, 0, 1, value) for key, value in shorts]
    double_values: list[float] = []
    for key, value in doubles:
        entries.append((key, 34736, 1, len(double_values)))
        double_values.append(value)
    ascii_params = ""
    for key, text in texts:
        entries.append((key, 34737, len(text) + 1, len(ascii_params)))
        ascii_params += text + "|"
    entries.sort()
    # Directory version 1, key revision 1.0 (what every reader takes), then each key as (id, location, count, value)
    keys = [1, 1, 0, len(entries)] + [n for entry in entries for n in entry]
    return keys, double_values or [0.0], ascii_params


def _lambert_keys():
    return _directory(
        shorts=[
            (1024, 1),  # GTModelType: projected
            (1025, 1),  # GTRasterType: pixel is area
            (2048, _USER_DEFINED),  # GeodeticCRS
            (2050, _USER_DEFINED),  # GeodeticDatum
            (2051, 8901),  # PrimeMeridian: Greenwich
            (2054, 9102),  # GeogAngularUnits: degree
            (2056, _USER_DEFINED),  # Ellipsoid
            (3072, _USER_DEFINED),  # ProjectedCRS
            (3074, _USER_DEFINED),  # Projection
            (3075, 9),  # ProjMethod: Lambert conformal conic, one standard parallel
            (3076, 9001),  # ProjLinearUnits: metre
        ],
        doubles=[
            (2057, R_EARTH),  # EllipsoidSemiMajorAxis
            (2058, R_EARTH),  # EllipsoidSemiMinorAxis
            (3080, LON_0),  # ProjNatOriginLong
            (3081, LAT_0),  # ProjNatOriginLat
            (3082, 0.0),  # ProjFalseEasting
            (3083, 0.0),  # ProjFalseNorthing
            (3092, 1.0),  # ProjScaleAtNatOrigin
        ],
        texts=[(1026, CRS_NAME), (2049, "NDFD sphere")],
    )


def _wgs84_keys():
    return _directory(
        shorts=[(1024, 2), (1025, 1), (2048, 4326), (2054, 9102)],  # geographic, pixel is area, WGS 84, degree
        doubles=[],
        texts=[(1026, "WGS 84")],
    )
