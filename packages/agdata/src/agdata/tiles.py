"""Web map tiles of a layer (PLAN.md Phase 5 G): 256-pixel web-mercator tiles from the native grid, with each value
packed into the pixel's color so the browser colors maps itself and reads values under the pointer.

Each pixel takes the grid cell under its center (no averaging at low zooms: a threshold or a risk level doesn't
average, D66's note on maps). `index` is that cell per pixel, cached per tile and window.

A value is a 24-bit count of the layer's steps, with zero at the middle of the range: `value = (R·65536 + G·256 + B)
× step − 2²³ × step`, so any value within ±8,388,608 steps fits (±838,860.8 °F·d at 0.1, ±8,388.608 at an index's
0.001). Code 0 (black, alpha 0) is missing; code 1 (`NONE`) is "none", where a first or last day within bounds
(D78) has values but no such day. It's Mapbox's Terrain-RGB scheme with the layer's own step, which
MapLibre reads as a `raster-dem` source with `encoding: "custom"` (`ENCODING`'s factors, in the layer's stored unit)
for a `color-relief` layer to color on the GPU, or a client decodes from the pixels.
"""

import io
import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

from agdata.grid import NDFD, Window

SIZE = 256
MIN_ZOOM, MAX_ZOOM = 3, 8  # past 8 a pixel is finer than a cell's 2.5 km: a client enlarges zoom 8's tiles
ZERO = 2**23  # the code of a value of zero
TOP = 2**24 - 1
NONE = 1  # a first or last day's "none" (no day within bounds); real values clip to 2 and up


@dataclass(frozen=True, kw_only=True)
class Encoding:
    """How a layer's tiles pack values: value = (R × red + G × green + B × blue) + base, in `unit`."""

    step: float
    unit: str

    @property
    def factors(self) -> dict[str, float]:
        """MapLibre's custom `raster-dem` encoding."""
        return {
            "redFactor": SIZE * SIZE * self.step,
            "greenFactor": SIZE * self.step,
            "blueFactor": self.step,
            "baseShift": -ZERO * self.step,
        }


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """(west, south, east, north) of a tile in degrees."""
    n = 2**z
    west, east = x / n * 360 - 180, (x + 1) / n * 360 - 180
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return west, south, east, north


def tile_of(lon: float, lat: float, z: int) -> tuple[int, int]:
    """The (x, y) of the tile at zoom `z` holding a point."""
    n = 2**z
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return int((lon + 180) / 360 * n), int(y)


@lru_cache(maxsize=256)  # 256 KB each: a few screens of tiles
def index(window: Window, z: int, x: int, y: int) -> np.ndarray | None:
    """Each pixel's cell (a flat index into the window, −1 outside it), (SIZE * SIZE,) by rows from the north-west;
    None if no pixel is in the window. ~5 ms to build."""
    n = 2**z * SIZE
    px = (x * SIZE + np.arange(SIZE) + 0.5) / n
    py = (y * SIZE + np.arange(SIZE) + 0.5) / n
    lon = px * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * py))))
    lat2, lon2 = np.meshgrid(lat, lon, indexing="ij")
    fj, fi = NDFD.fractional_index(lat2.ravel(), lon2.ravel())
    j = np.rint(fj).astype(np.int64) - window.j0
    i = np.rint(fi).astype(np.int64) - window.i0
    inside = (j >= 0) & (j < window.shape[0]) & (i >= 0) & (i < window.shape[1])
    if not inside.any():
        return None
    out = np.where(inside, j * window.shape[1] + i, -1).astype(np.int32)
    out.setflags(write=False)
    return out


def codes(values: np.ndarray, step: float) -> np.ndarray:
    """Values (any shape) as 24-bit codes: 0 where missing, clipped to the range otherwise."""
    with np.errstate(invalid="ignore"):
        scaled = np.rint(values / step) + ZERO
    return np.where(np.isfinite(values), np.clip(scaled, NONE + 1, TOP), 0).astype(np.uint32)


def decode(rgba: np.ndarray, step: float) -> np.ndarray:
    """A tile's pixels (…, 4) back to values (NaN where missing), as a client reads them."""
    code = rgba[..., 0].astype(np.int64) * 65536 + rgba[..., 1].astype(np.int64) * 256 + rgba[..., 2]
    return np.where((rgba[..., 3] > 0) & (code > NONE), (code - ZERO) * step, np.nan)


def pick(values: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """A tile's values (SIZE, SIZE) from a map over the window (y, x) and the tile's `index` (NaN outside)."""
    picked = np.where(cells >= 0, values.ravel()[np.clip(cells, 0, None)], np.nan)
    return picked.reshape(SIZE, SIZE)


def data_tile(values: np.ndarray, cells: np.ndarray, step: float, states: np.ndarray | None = None) -> np.ndarray:
    """A tile's RGBA pixels (SIZE, SIZE, 4) from a map over the window (y, x) and the tile's `index`; `states`
    (y, x; `mapimage.map_png`'s) marks "none" cells with code NONE."""
    code = codes(pick(values, cells).ravel(), step)
    if states is not None:
        code = np.where(pick(states, cells).ravel() == 0, NONE, code).astype(np.uint32)
    rgba = np.empty((cells.size, 4), dtype=np.uint8)
    rgba[:, 0] = code >> 16
    rgba[:, 1] = (code >> 8) & 0xFF
    rgba[:, 2] = code & 0xFF
    rgba[:, 3] = np.where(code > 0, 255, 0)
    return rgba.reshape(SIZE, SIZE, 4)


def png(rgba: np.ndarray) -> bytes:
    """RGBA pixels as a PNG (lossless: a value's bytes must come back exactly)."""
    out = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(out, "PNG", compress_level=6)
    return out.getvalue()


@lru_cache(maxsize=1)
def empty_png() -> bytes:
    """A tile with nothing on it (outside the window)."""
    return png(np.zeros((SIZE, SIZE, 4), dtype=np.uint8))
