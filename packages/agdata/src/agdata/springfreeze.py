"""Area-wide normal freeze dates on the grid: a cell's stored freeze date averaged over the land around it (D127).

A cell's own median last spring freeze (`agdata.normals`' `freeze_<F>/spring_p50`) is a 2.5 km cell's, and the
coldest of those, in low ground, on sand or by a bog, freeze two or three weeks later than the farms a few miles off:
the frost pockets that left a speckle of late dates on maps that read it cell by cell (potato's planting, D126).
Whether a place's spring is early or late is a trait of the area, so these read the normal as a weighted mean over
the cells within `RADIUS_KM`: a Gaussian with σ = `RADIUS_KM` / 2 cut off at the radius, the weighting of
`agdata.areas`' `center` (Ben, 2026-11-26: "an area-wide average, about 50 km, center-weighted").

The mean is a normalized convolution: cells without a value (past the coverage, before a period reaches them) are
left out and the weights of the rest renormalized, so the coverage's edge and the coast don't pull a cell's date
toward nothing. Open water (`agdata.regions.water`: the terrain store's lakes, else the Great Lakes) is left out too,
as `areas`' `land_only` and the place normals (`normals.land_mean`) leave it: the dates are for crops and insects on
land, and a lake's air follows its water. In `last30` the Great Lakes have no freeze dates at all, and Wisconsin's
inland lakes' last 28 °F freeze comes a median 1.5 days before the land's within 10 km, so it
matters little here, but nothing a lake gives should move a field's date. A cell is missing where its own normal is (nothing is made up past the normals' area) or where
no land cell within the radius has a value; a lake cell takes the land around it.

The whole store's map is computed once per build of the normals (and of the terrain store) and cut to each request,
so a point reads exactly its map cell's value. Potato's planting (`agdata.potatoplanting`) reads the 28 °F spring
date; insects' seasons may read these too.
"""

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from agdata import normals, regions
from agdata.grid import NDFD, Window

PERIOD = "last30"
RADIUS_KM = 50.0  # the area a cell's freeze date is averaged over
SIGMA_KM = RADIUS_KM / 2  # `agdata.areas`' center weighting
SPRING_28 = "freeze_28/spring_p50"  # the median last spring freeze at 28 °F, as a calendar slot (`climatology.slot`)
SPRING_32 = "freeze_32/spring_p50"


def kernel() -> np.ndarray:
    """The weights by cell offset, (2r + 1, 2r + 1), centered: exp(−d² / 2σ²) within RADIUS_KM, 0 past it, by the
    grid's spacing (Lambert's scale varies by about 1% over the launch area)."""
    km = NDFD.dx / 1000
    reach = math.floor(RADIUS_KM / km)
    offsets = np.arange(-reach, reach + 1) * km
    d2 = offsets[:, None] ** 2 + offsets[None, :] ** 2
    return np.where(d2 <= RADIUS_KM**2, np.exp(-d2 / (2 * SIGMA_KM**2)), 0.0)


def smooth(values: np.ndarray, land: np.ndarray) -> np.ndarray:
    """Each cell's weighted mean (`kernel`) of `values` over the land cells (`land`) with a value; NaN where the cell's
    own value is missing or no such cell is within reach. (y, x) both."""
    k = kernel()
    use = land & np.isfinite(values)
    num = _convolve(np.where(use, values, 0.0), k)
    den = _convolve(use.astype(np.float64), k)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    return np.where(np.isfinite(values) & (den > 1e-9), out, np.nan)


def _convolve(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """`a` convolved with the (odd, symmetric) `k`, zero past `a`'s edges, the same shape as `a` (by FFT)."""
    r = k.shape[0] // 2
    shape = (a.shape[0] + 2 * r, a.shape[1] + 2 * r)
    full = np.fft.irfft2(np.fft.rfft2(a, shape) * np.fft.rfft2(k, shape), shape)
    return full[r : r + a.shape[0], r : r + a.shape[1]]


def within(data_dir: Path, name: str, window: Window, period: str = PERIOD) -> np.ndarray:
    """The area-wide `name` (a single freeze map, such as SPRING_28) over `window` as calendar slots, float (y, x),
    NaN where missing (past the normals' area, or everywhere if the period isn't built)."""
    whole = _whole(Path(data_dir), name, period, normals.stamp(data_dir, period), regions._water_stamp())
    out = np.full(window.shape, np.nan)
    if whole is None:
        return out
    values, w = whole
    j0, j1 = max(window.j0, w.j0), min(window.j1, w.j1)
    i0, i1 = max(window.i0, w.i0), min(window.i1, w.i1)
    if j0 < j1 and i0 < i1:
        out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = values[
            j0 - w.j0 : j1 - w.j0, i0 - w.i0 : i1 - w.i0
        ]
    return out


def at(data_dir: Path, name: str, j: int, i: int, period: str = PERIOD) -> float:
    """The area-wide `name` at a cell (`within` over one cell)."""
    return float(within(data_dir, name, Window(j0=j, j1=j + 1, i0=i, i1=i + 1), period=period)[0, 0])


@lru_cache(maxsize=8)
def _whole(
    data_dir: Path, name: str, period: str, stamp: str | None, water_stamp: float | None
) -> tuple[np.ndarray, Window] | None:
    """The smoothed map over the store's whole window, read-only, and that window; None if the period isn't built.
    Keyed by the stamps, so a rebuilt store (or terrain store) is read again."""
    attrs = normals.info(data_dir, period)
    if stamp is None or attrs is None:
        return None
    w = Window(**attrs["window"])
    raw = normals.read_within(data_dir, period, name, None, w)
    out = smooth(raw, ~regions.water(w))
    out.flags.writeable = False
    return out, w
