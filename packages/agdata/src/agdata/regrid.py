"""Regridding fields from another grid (HRRR's 3 km Lambert, ERA5-Land's 0.1° latitude/longitude) to a window of
the NDFD grid.

Bilinear interpolation at each NDFD cell center, with weights computed once per (source grid, window) and
cached. A cell whose four source neighbors include a missing value, or that falls outside the source grid,
is NaN.

The other way, `latlon_index` maps a regular lat/lng grid's points to NDFD cells (`/grids`' `grid=latlon`, D57):
the cell under each point (`nearest`) or the cells whose centers fall within ±res/2 of it (`mean`), cached per
window, box, step and method.
"""

from dataclasses import dataclass
from functools import cache
from typing import Literal

import numpy as np

from agdata.grid import NDFD, LambertGrid, LatLonGrid, Window

SourceGrid = LambertGrid | LatLonGrid


@dataclass(frozen=True, kw_only=True)
class BilinearWeights:
    j0: np.ndarray  # lower-left source row of each target cell
    i0: np.ndarray
    dj: np.ndarray  # fractional offsets within the source cell
    di: np.ndarray
    inside: np.ndarray  # bool: the target cell has four source neighbors

    def apply(self, values: np.ndarray) -> np.ndarray:
        """A source field (source ny, source nx) → the target window."""
        j0, i0 = self.j0, self.i0
        v00, v01 = values[j0, i0], values[j0, i0 + 1]
        v10, v11 = values[j0 + 1, i0], values[j0 + 1, i0 + 1]
        out = (1 - self.dj) * ((1 - self.di) * v00 + self.di * v01) + self.dj * ((1 - self.di) * v10 + self.di * v11)
        return np.where(self.inside, out, np.nan)


@cache
def bilinear_weights(source: SourceGrid, window: Window) -> BilinearWeights:
    lat, lon = NDFD.window_latlon(window)
    fj, fi = source.fractional_index(lat, lon)
    inside = (fj >= 0) & (fi >= 0) & (fj <= source.ny - 1) & (fi <= source.nx - 1)
    j0 = np.clip(np.floor(fj).astype(int), 0, source.ny - 2)
    i0 = np.clip(np.floor(fi).astype(int), 0, source.nx - 2)
    return BilinearWeights(j0=j0, i0=i0, dj=fj - j0, di=fi - i0, inside=inside)


def regrid(values: np.ndarray, source: SourceGrid, window: Window) -> np.ndarray:
    if values.shape != (source.ny, source.nx):
        raise ValueError(f"expected a {source.name} field of {(source.ny, source.nx)}, got {values.shape}")
    return bilinear_weights(source, window).apply(values)


# --- From the NDFD grid to regular latitude/longitude points (D57: `grid=latlon&res=`; Phase 5 G's tiles) ---------

LatLonMethod = Literal["nearest", "mean"]
MIN_LATLON_RES = 0.025  # finer only repeats cells (2.5 km is ~0.03° of latitude)


@dataclass(frozen=True, kw_only=True)
class LatLonIndex:
    """Where each point of a regular lat/lng grid takes its value from in a window. Points sit on multiples of `res`
    (v1's 0.1° grid had 42.4, 42.5, …); rows run south to north, columns west to east.

    `nearest`: the cell under each point (`cell`, a flat index into the window, −1 outside it). `mean`: the mean of
    the cells whose centers fall within ±res/2 of the point (`box`, each window cell's flat point index, −1 for a
    cell in no box), missing cells left out; a point with no cell in its box is missing."""

    lats: np.ndarray  # (ny,)
    lons: np.ndarray  # (nx,)
    method: LatLonMethod
    cell: np.ndarray | None = None  # nearest: (ny * nx,)
    box: np.ndarray | None = None  # mean: (window cells,)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.lats.size, self.lons.size)

    def resample(self, values: np.ndarray) -> np.ndarray:
        """(steps, y, x) over the window → (steps, ny, nx) on the lat/lng points."""
        steps = values.shape[0]
        flat = values.reshape(steps, -1).astype(np.float64)
        n = self.shape[0] * self.shape[1]
        if self.method == "nearest":
            assert self.cell is not None
            out = np.full((steps, n), np.nan)
            inside = self.cell >= 0
            out[:, inside] = flat[:, self.cell[inside]]
            return out.reshape(steps, *self.shape)
        assert self.box is not None
        used = self.box >= 0
        boxes = self.box[used]
        out = np.full((steps, n), np.nan)
        for k in range(steps):
            v = flat[k, used]
            known = np.isfinite(v)
            total = np.bincount(boxes[known], weights=v[known], minlength=n)
            count = np.bincount(boxes[known], minlength=n)
            with np.errstate(invalid="ignore", divide="ignore"):
                out[k] = np.where(count > 0, total / count, np.nan)
        return out.reshape(steps, *self.shape)


@cache
def latlon_index(
    window: Window, south: float, west: float, north: float, east: float, res: float, method: LatLonMethod
) -> LatLonIndex:
    """The lat/lng points on multiples of `res` within south..north, west..east, and where each takes its value from
    in `window`. Cached per argument set: measured over Wisconsin, ~2 ms to build at 0.1°, ~80 ms at 0.01°."""
    if res < MIN_LATLON_RES:
        raise ValueError(f"res {res} is finer than {MIN_LATLON_RES}°")
    # Rounding to the step's decimals keeps 42.4 from being 42.400000000000006
    digits = max(0, -int(np.floor(np.log10(res)))) + 3
    lats = np.round(np.arange(np.ceil(south / res - 1e-9), np.floor(north / res + 1e-9) + 1) * res, digits)
    lons = np.round(np.arange(np.ceil(west / res - 1e-9), np.floor(east / res + 1e-9) + 1) * res, digits)
    if method == "nearest":
        lat2, lon2 = np.meshgrid(lats, lons, indexing="ij")
        fj, fi = NDFD.fractional_index(lat2.ravel(), lon2.ravel())
        j, i = np.rint(fj).astype(int) - window.j0, np.rint(fi).astype(int) - window.i0
        inside = (j >= 0) & (j < window.shape[0]) & (i >= 0) & (i < window.shape[1])
        cell = np.where(inside, j * window.shape[1] + i, -1)
        return LatLonIndex(lats=lats, lons=lons, method=method, cell=cell)
    cell_lat, cell_lon = NDFD.window_latlon(window)
    r = np.rint((cell_lat.ravel() - lats[0]) / res).astype(int) if lats.size else np.zeros(window.size, dtype=int)
    c = np.rint((cell_lon.ravel() - lons[0]) / res).astype(int) if lons.size else np.zeros(window.size, dtype=int)
    inside = (r >= 0) & (r < lats.size) & (c >= 0) & (c < lons.size)
    box = np.where(inside, r * lons.size + c, -1)
    return LatLonIndex(lats=lats, lons=lons, method=method, box=box)
