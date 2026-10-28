"""Regridding fields from another grid (HRRR's 3 km Lambert) to a window of the NDFD grid.

Bilinear interpolation at each NDFD cell center, with weights computed once per (source grid, window) and
cached. A cell whose four source neighbors include a missing value, or that falls outside the source grid,
is NaN.
"""

from dataclasses import dataclass
from functools import cache

import numpy as np

from agdata.grid import NDFD, LambertGrid, Window


@dataclass(frozen=True)
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
def bilinear_weights(source: LambertGrid, window: Window) -> BilinearWeights:
    lat, lon = NDFD.window_latlon(window)
    fj, fi = source.fractional_index(lat, lon)
    inside = (fj >= 0) & (fi >= 0) & (fj <= source.ny - 1) & (fi <= source.nx - 1)
    j0 = np.clip(np.floor(fj).astype(int), 0, source.ny - 2)
    i0 = np.clip(np.floor(fi).astype(int), 0, source.nx - 2)
    return BilinearWeights(j0=j0, i0=i0, dj=fj - j0, di=fi - i0, inside=inside)


def regrid(values: np.ndarray, source: LambertGrid, window: Window) -> np.ndarray:
    if values.shape != (source.ny, source.nx):
        raise ValueError(f"expected a {source.name} field of {(source.ny, source.nx)}, got {values.shape}")
    return bilinear_weights(source, window).apply(values)
