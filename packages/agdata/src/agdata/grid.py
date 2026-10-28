"""The NDFD 2.5 km CONUS grid, the service box, and cells within them.

Every gridded store and source shares one grid (PLAN.md D2): the NDFD CONUS 2.5 km Lambert conformal grid
that URMA, RTMA and NBM use since May 2017 (2345 x 1597 cells, the "wexp" grid). Older URMA files and the
2017-2018 precip files cover aligned sub-windows of it; `NDFD.offset_of` finds where a source grid sits.

Indices are (j, i): j counts rows south to north, i counts columns west to east, both from the grid's
southwest corner. A `Window` is a half-open block of cells, and a store holds one window (the service box).
"""

import re
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from pyproj import CRS, Transformer


@dataclass(frozen=True)
class Box:
    """A latitude/longitude bounding box in degrees (west and east negative in the western hemisphere)."""

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self):
        if not (-90 <= self.south < self.north <= 90 and -180 <= self.west < self.east <= 180):
            raise ValueError(f"not a valid box: {self}")


# Service-box presets (PLAN.md D20). Wisconsin's state lines with a margin, including Lake Michigan's
# Wisconsin waters; the Upper Midwest from ND/SD/NE/KS to OH; CONUS is the whole grid.
BOXES: dict[str, Box | None] = {
    "wisconsin": Box(south=42.4, west=-93.0, north=47.4, east=-86.2),
    "upper_midwest": Box(south=35.0, west=-100.0, north=50.0, east=-75.0),
    "conus": None,
}


@dataclass(frozen=True)
class Window:
    """A half-open block of grid cells: rows j0..j1-1 and columns i0..i1-1."""

    j0: int
    j1: int
    i0: int
    i1: int

    @property
    def shape(self) -> tuple[int, int]:
        return (self.j1 - self.j0, self.i1 - self.i0)

    @property
    def slices(self) -> tuple[slice, slice]:
        return (slice(self.j0, self.j1), slice(self.i0, self.i1))

    @property
    def size(self) -> int:
        return self.shape[0] * self.shape[1]

    def contains(self, j: int, i: int) -> bool:
        return self.j0 <= j < self.j1 and self.i0 <= i < self.i1

    def local(self, j: int, i: int) -> tuple[int, int]:
        """Grid indices → indices within this window."""
        if not self.contains(j, i):
            raise IndexError(f"cell ({j}, {i}) is outside {self}")
        return (j - self.j0, i - self.i0)


@dataclass(frozen=True)
class LambertGrid:
    """A Lambert conformal grid on a sphere, located by its first (southwest) point."""

    name: str
    proj4: str
    nx: int
    ny: int
    dx: float  # meters, the same in y
    first_lat: float
    first_lon: float

    @cached_property
    def crs(self) -> CRS:
        return CRS.from_proj4(self.proj4)

    @cached_property
    def _to_xy(self) -> Transformer:
        return Transformer.from_crs("EPSG:4326", self.crs, always_xy=True)

    @cached_property
    def _to_lonlat(self) -> Transformer:
        return Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)

    @cached_property
    def origin(self) -> tuple[float, float]:
        """Projected (x, y) of cell (0, 0)."""
        x, y = self._to_xy.transform(_lon180(self.first_lon), self.first_lat)
        return (float(x), float(y))

    @property
    def window(self) -> Window:
        return Window(0, self.ny, 0, self.nx)

    def fractional_index(self, lat, lon) -> tuple[np.ndarray, np.ndarray]:
        """Latitude/longitude → fractional (j, i); cell centers fall on whole numbers."""
        x, y = self._to_xy.transform(_lon180(np.asarray(lon, dtype=float)), np.asarray(lat, dtype=float))
        x0, y0 = self.origin
        return ((np.asarray(y) - y0) / self.dx, (np.asarray(x) - x0) / self.dx)

    def cell_of(self, lat: float, lon: float) -> tuple[int, int] | None:
        """The (j, i) of the cell containing a point, or None outside the grid."""
        fj, fi = self.fractional_index(lat, lon)
        j, i = int(np.round(fj)), int(np.round(fi))
        return (j, i) if self.window.contains(j, i) else None

    def latlon(self, j, i) -> tuple[np.ndarray, np.ndarray]:
        """Cell centers (j, i) → (latitude, longitude)."""
        x0, y0 = self.origin
        x = x0 + np.asarray(i, dtype=float) * self.dx
        y = y0 + np.asarray(j, dtype=float) * self.dx
        lon, lat = self._to_lonlat.transform(x, y)
        return (np.asarray(lat), np.asarray(lon))

    def window_latlon(self, window: Window) -> tuple[np.ndarray, np.ndarray]:
        """2-D latitude and longitude arrays of a window's cell centers."""
        jj, ii = np.mgrid[window.j0 : window.j1, window.i0 : window.i1]
        return self.latlon(jj, ii)

    def window_for(self, box: Box | None) -> Window:
        """The smallest window covering a box (its edges are curved on this projection), or the whole grid."""
        if box is None:
            return self.window
        n = 200
        lats = np.concatenate(
            [
                np.full(n, box.south),
                np.full(n, box.north),
                np.linspace(box.south, box.north, n),
                np.linspace(box.south, box.north, n),
            ]
        )
        lons = np.concatenate(
            [
                np.linspace(box.west, box.east, n),
                np.linspace(box.west, box.east, n),
                np.full(n, box.west),
                np.full(n, box.east),
            ]
        )
        fj, fi = self.fractional_index(lats, lons)
        j0, j1 = int(np.floor(fj.min())), int(np.ceil(fj.max())) + 1
        i0, i1 = int(np.floor(fi.min())), int(np.ceil(fi.max())) + 1
        window = Window(max(j0, 0), min(j1, self.ny), max(i0, 0), min(i1, self.nx))
        if window.j0 >= window.j1 or window.i0 >= window.i1:
            raise ValueError(f"{box} is outside the {self.name} grid")
        return window

    def offset_of(self, first_lat: float, first_lon: float, tolerance: float = 0.01) -> tuple[int, int]:
        """Where another grid with this projection and spacing starts, as whole (j, i) on this grid."""
        fj, fi = self.fractional_index(first_lat, first_lon)
        j, i = round(float(fj)), round(float(fi))
        if abs(float(fj) - j) > tolerance or abs(float(fi) - i) > tolerance:
            raise ValueError(f"a grid starting at ({first_lat}, {first_lon}) isn't aligned with {self.name}")
        return (j, i)


def _lon180(lon):
    """Longitudes in GRIB are 0-360; pyproj and everything else here use -180-180."""
    return (np.asarray(lon) + 180) % 360 - 180


# From the GRIB2 grid definition of URMA's wexp files (2017-05-01 on); the same grid as NBM and RTMA
NDFD = LambertGrid(
    name="NDFD CONUS 2.5 km",
    proj4="+proj=lcc +lon_0=265 +lat_0=25 +lat_1=25 +lat_2=25 +R=6371200 +units=m +no_defs",
    nx=2345,
    ny=1597,
    dx=2539.703,
    first_lat=19.228976,
    first_lon=233.723448,
)

_BOX_SPEC = re.compile(r"^\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*$")


def parse_box(spec: str) -> Box | None:
    """A preset name (`wisconsin`, `upper_midwest`, `conus`) or `south,west,north,east` → a Box.

    None means the whole grid.
    """
    name = spec.strip().lower()
    if name in BOXES:
        return BOXES[name]
    match = _BOX_SPEC.match(spec)
    if not match:
        raise ValueError(f"unknown service box {spec!r}: use one of {', '.join(BOXES)} or south,west,north,east")
    south, west, north, east = (float(value) for value in match.groups())
    return Box(south=south, west=west, north=north, east=east)


def service_window(spec: str) -> Window:
    return NDFD.window_for(parse_box(spec))
