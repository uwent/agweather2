"""Cropland per grid cell, from USDA NASS's Cropland Data Layer (Phase 6 step 6, D116).

The Cropland Data Layer (CDL) classes every 30 m pixel of the lower 48 by what was grown there each year, from
satellite imagery trained on FSA's field records. This module turns the five newest years (2021–2025 at first, rolled
forward each February when NASS publishes a year) into a few numbers per 2.5 km cell, kept in `data/cropland.zarr`:

- `observed`: the share of the cell's pixels the CDL has a class for, averaged over the years (0 over Canada and
  the Great Lakes' open water beyond the US line; clouds and no data don't count);
- `<crop>_mean`: the share of the observed pixels in that crop, over the years: the average area planted;
- `<crop>_any`: the share of the pixels observed in any year that were in that crop in at least one: the land the
  crop rotates through ("where it's grown");
- `cultivated`: the share of the pixels observed in any year that NASS's Cultivated Layer rule calls cultivated:
  in a cultivated class in at least two of the years, or in the newest (Boryan, Yang and Di 2012; the class list is
  NASS's for its 2025 Cultivated Layer: hay other than alfalfa, sod, switchgrass and grassland aren't cultivated).

A crop is an `agmodels.croplist` id (D93); `CODES` maps each to its CDL classes. Double-crop classes count for both
crops (241, corn and soybean, for each), and a group is the union of its members' classes at the pixel, never a sum,
so a pixel in winter wheat then soybean counts once toward wheat. A crop with no CDL class (snap bean, table beet,
spinach, kale, collards, horseradish, oak) has no arrays. Every share is NaN where `observed` is under half.

**Pixels to cells.** Each pixel counts once, in the NDFD cell that holds its centre, found the way `NDFD.cell_of`
finds a point's: Albers (EPSG:5070) → latitude and longitude → the grid's Lambert projection, worked out exactly on a
lattice every 16 pixels and interpolated bilinearly between (the error is far under a metre). A 2.5 km cell holds
about 7,000 pixels. No resampling or warping: the years are read on their own 30 m lattice, which the build checks
they share (`check_aligned`), so a pixel's five years are the same ground.

**Files.** NASS's national 30 m zips (`<year>_30m_cdls.zip`, 1.6–2.0 GB each) are kept as received in `data/cdl/`.
A build unpacks only each year's `.tif` (1.9–3.3 GB; never the `.tif.ovr` pyramid) into `data/cdl/extracted/`
and the command deletes them after. The store is small (a uint16 array a statistic over the coverage's extent, in
hundredths of a percent) and isn't part of the weather archive, so it's written without the write lock, beside its
path and renamed into place, as `agdata.terrain`'s.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import warnings
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache, partial
from pathlib import Path

import numpy as np

from agdata.grid import NDFD, Window

SOURCE = "https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/Release/datasets"
KIND = "cdl"
YEARS = (2021, 2022, 2023, 2024, 2025)  # the five newest; `manage.py cropland --years` rolls them forward
PIXEL = 30.0  # meters
ALBERS = "EPSG:5070"  # CONUS Albers on NAD83, as every CDL year is
NO_DATA = frozenset({0, 81})  # background (outside the US) and clouds/no data
MIN_OBSERVED = 0.5  # of a cell's pixels with a class, averaged over the years, for its shares
VERSION = 1  # bump when what's built changes, and `manage.py cropland` builds it again
STORE = "cropland.zarr"
BLOCK = 64  # grid cells a side per block of the build: ~5,500 pixels a side, ~30 MB a year as uint8
LATTICE_STEP = 16  # pixels between exact projections of pixel centres; bilinear between
MISSING = np.iinfo(np.uint16).max
SCALE = 10_000  # stored as hundredths of a percent

# Each croplist id (D93) with CDL classes, and the classes it takes. Double crops (26, 225–241, 254) count for both
# crops; durum (22) is spring wheat's; caneberries (55) are raspberry's and blackberry's alike. A group (`wheat`,
# `cole-crops`) takes its members' classes (`codes`). Codes from NASS's CDL legend (2025 metadata).
CODES: dict[str, frozenset[int]] = {
    "corn": frozenset({1, 225, 226, 228, 237, 241}),
    "soybean": frozenset({5, 26, 239, 240, 241, 254}),
    "spring-wheat": frozenset({22, 23, 230, 234}),
    "winter-wheat": frozenset({24, 26, 225, 236, 238}),
    "barley": frozenset({21, 233, 235, 237, 254}),
    "sorghum": frozenset({4, 234, 235, 236}),
    "sunflower": frozenset({6}),
    "sugarbeet": frozenset({41}),
    "dry-bean": frozenset({42}),
    "cotton": frozenset({2, 232, 238, 239}),
    "alfalfa": frozenset({36}),
    "rye": frozenset({27}),
    "asparagus": frozenset({207}),
    "carrot": frozenset({206}),
    "celery": frozenset({245}),
    "cabbage": frozenset({243}),
    "broccoli": frozenset({214}),
    "cauliflower": frozenset({244}),
    "cucumber": frozenset({50}),
    "eggplant": frozenset({248}),
    "lettuce": frozenset({227, 230, 231, 232, 233}),
    "melon": frozenset({48, 209, 213, 231}),  # watermelon, cantaloupe, honeydew
    "onion": frozenset({49}),
    "pea": frozenset({53}),
    "pepper": frozenset({216}),
    "potato": frozenset({43}),
    "pumpkin": frozenset({229}),
    "squash": frozenset({222}),
    "sweet-corn": frozenset({12}),
    "tomato": frozenset({54}),
    "apple": frozenset({68}),
    "blackberry": frozenset({55}),
    "raspberry": frozenset({55}),
    "cherry": frozenset({66}),
    "pecan": frozenset({74}),
    "hops": frozenset({56}),
    "mint": frozenset({14}),
}
# Croplist ids the CDL has no class for (so no arrays): not a guess from a broader class
NO_CLASS = frozenset({"snap-bean", "beet", "spinach", "kale", "collards", "brussels-sprouts", "horseradish", "oak"})

# NASS's cultivated classes for its Cultivated Layer (2025 metadata): every crop class but other hay (37), sod and
# grass seed (59) and switchgrass (60), with fallow and idle cropland (61) and the tree crops
CULTIVATED = frozenset(
    {*range(1, 7), *range(10, 15), *range(21, 37), 38, 39, *range(41, 59), 61, *range(66, 73), *range(74, 78)}
    | {*range(204, 251), 254}
)
STATS = ("mean", "any")


def codes(crop_id: str) -> frozenset[int]:
    """A crop's CDL classes: its own, or a group's members' together (empty if the CDL has none)."""
    from agmodels import croplist

    crop = croplist.crop(crop_id)
    if crop.members:
        return frozenset().union(*(codes(m) for m in crop.members))
    return CODES.get(crop_id, frozenset())


@cache
def crop_ids() -> tuple[str, ...]:
    """The croplist ids with CDL classes, groups among them, in croplist's order."""
    from agmodels import croplist

    return tuple(c for c in croplist.CROPS if codes(c))


def array_name(crop_id: str, stat: str) -> str:
    return f"{crop_id}_{stat}"


def cell_arrays() -> tuple[str, ...]:
    return ("observed", "cultivated", *(array_name(c, s) for c in crop_ids() for s in STATS))


def codes_hash() -> str:
    """A hash of the class tables, so a change to them makes the store out of date."""
    table = {c: sorted(codes(c)) for c in crop_ids()} | {"_cultivated": sorted(CULTIVATED)}
    return hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest()[:16]


# --- Files ------------------------------------------------------------------------------------------------------


def folder(data_dir: Path) -> Path:
    return Path(data_dir) / KIND


def zip_name(year: int) -> str:
    return f"{year}_30m_cdls.zip"


def url(year: int) -> str:
    return f"{SOURCE}/{zip_name(year)}"


def zip_path(data_dir: Path, year: int) -> Path:
    return folder(data_dir) / zip_name(year)


def missing_years(data_dir: Path, years: Iterable[int]) -> list[int]:
    """The years whose zip isn't kept yet."""
    return [y for y in years if not zip_path(data_dir, y).exists()]


def fetch(
    year: int, dest: Path, progress: Callable[[int, int], None] | None = None, timeout_s: float = 60.0, tries: int = 5
) -> int:
    """Downloads a year's zip to `dest` through a .part file, resuming one left by an earlier try (an HTTP range)
    and checking the length the server gave; renamed once whole. A dropped connection or a server error (5xx) is
    tried again, up to `tries` in all, after a wait. Returns its size in bytes."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    total: int | None = None
    for attempt in range(tries):
        have = part.stat().st_size if part.exists() else 0
        if total is not None and have == total:
            break
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with requests.get(url(year), headers=headers, stream=True, timeout=timeout_s) as response:
                if have and response.status_code == 416:  # nothing past what's kept: it's whole
                    total = have
                    break
                response.raise_for_status()
                if have and response.status_code != 206:  # the server sent it all again
                    have = 0
                total = have + int(response.headers["Content-Length"])
                with open(part, "ab" if have else "wb") as out:
                    done = have
                    for chunk in response.iter_content(chunk_size=1 << 20):
                        out.write(chunk)
                        done += len(chunk)
                        if progress is not None:
                            progress(done, total)
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
            if attempt == tries - 1:
                raise
            _wait_before_retry(attempt)
            continue
        except requests.HTTPError as error:  # NASS's server answers 500 now and then; a retry gets the file
            if error.response is None or error.response.status_code < 500 or attempt == tries - 1:
                raise
            _wait_before_retry(attempt)
            continue
        if part.stat().st_size == total:
            break
    size = part.stat().st_size if part.exists() else 0
    if total is None or size != total:
        raise OSError(f"{dest.name}: got {size:,} bytes of {total if total is not None else '?'}; rerun to resume")
    part.rename(dest)
    return size


RETRY_WAIT_S = 10.0


def _wait_before_retry(attempt: int) -> None:
    import time

    time.sleep(RETRY_WAIT_S * (attempt + 1))


def extracted(data_dir: Path) -> Path:
    return folder(data_dir) / "extracted"


def _tif_member(z: zipfile.ZipFile) -> zipfile.ZipInfo:
    """The zip's raster: the one `.tif` (beside a `.tif.ovr` pyramid, world file, metadata and tables)."""
    found = [i for i in z.infolist() if i.filename.lower().endswith(".tif")]
    if len(found) != 1:
        raise ValueError(f"expected one .tif in the zip, found {[i.filename for i in found]}")
    return found[0]


def extract(data_dir: Path, year: int, progress: Callable[[int, int], None] | None = None) -> Path:
    """Unpacks a year's `.tif` from its zip into `extracted/` (once: kept while its size matches); returns it."""
    with zipfile.ZipFile(zip_path(data_dir, year)) as z:
        member = _tif_member(z)
        out = extracted(data_dir) / f"{year}_30m_cdls.tif"
        if out.exists() and out.stat().st_size == member.file_size:
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_name(out.name + ".part")
        with z.open(member) as src, open(part, "wb") as dst:
            done = 0
            while chunk := src.read(1 << 24):
                dst.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, member.file_size)
        part.rename(out)
    return out


def delete_extracted(data_dir: Path) -> int:
    """Deletes the unpacked rasters (the zips stay); returns the bytes freed."""
    found = extracted(data_dir)
    if not found.exists():
        return 0
    freed = sum(p.stat().st_size for p in found.rglob("*") if p.is_file())
    shutil.rmtree(found)
    return freed


# --- The years' lattice -----------------------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Raster:
    """A year's raster: where it is, and its extent on the 30 m lattice (its west and north edges, Albers m)."""

    year: int
    path: str
    west: float
    north: float
    width: int
    height: int


class Misaligned(ValueError):
    """The years' pixels aren't on one 30 m lattice, so a pixel's years wouldn't be the same ground."""


def open_rasters(paths: dict[int, Path]) -> list[Raster]:
    """Each year's raster, checked: Albers, 30 m pixels, north up, one band."""
    import rasterio
    from rasterio.crs import CRS

    albers = CRS.from_string(ALBERS)
    found = []
    for year, p in sorted(paths.items()):
        with rasterio.open(p) as src:
            t = src.transform
            # NASS's files carry the Albers definition by parameters: compare what it means, not its name
            if src.crs is None or (not src.crs.equals(albers) and src.crs.to_proj4() != albers.to_proj4()):
                raise ValueError(f"{year}: expected {ALBERS}, found {src.crs}")
            if abs(t.a - PIXEL) > 1e-6 or abs(t.e + PIXEL) > 1e-6 or t.b or t.d:
                raise ValueError(f"{year}: expected 30 m pixels, north up; found {tuple(t)[:6]}")
            found.append(
                Raster(year=year, path=str(p), west=float(t.c), north=float(t.f), width=src.width, height=src.height)
            )
    return found


def check_aligned(rasters: list[Raster]) -> None:
    """Raises `Misaligned` unless every year's pixel edges fall on the first year's 30 m lattice."""
    first = rasters[0]
    off = []
    for r in rasters[1:]:
        dx, dy = (r.west - first.west) / PIXEL, (first.north - r.north) / PIXEL
        if abs(dx - round(dx)) > 1e-6 or abs(dy - round(dy)) > 1e-6:
            off.append(f"{r.year} ({r.west:.3f}, {r.north:.3f})")
    if off:
        raise Misaligned(
            f"not on {first.year}'s 30 m lattice (west, north edge {first.west:.3f}, {first.north:.3f}): {', '.join(off)}"
        )


# --- Counting a block -------------------------------------------------------------------------------------------


def _albers_to_grid():
    """Albers (x, y) → the grid's fractional (j, i): through latitude and longitude, as `NDFD.cell_of` places a
    point."""
    from pyproj import Transformer

    to_lonlat = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)
    x0, y0 = NDFD.origin

    def onto(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        lon, lat = to_lonlat.transform(x, y)
        gx, gy = NDFD._to_xy.transform(lon, lat)
        return (np.asarray(gy) - y0) / NDFD.dx, (np.asarray(gx) - x0) / NDFD.dx

    return onto


def pixel_window(block: Window, west: float, north: float) -> tuple[int, int, int, int]:
    """The rows and columns (r0, r1, c0, c1, on the lattice whose corner is `west`, `north`) of every pixel whose
    centre may lie in `block`'s cells: the cells' outline projected to Albers, two pixels wider."""
    from pyproj import Transformer

    x0, y0 = NDFD.origin
    n = 64
    js = np.concatenate([np.full(n, block.j0), np.full(n, block.j1), np.linspace(block.j0, block.j1, n)])
    js = np.concatenate([js, np.linspace(block.j0, block.j1, n)]) - 0.5
    is_ = np.concatenate([np.linspace(block.i0, block.i1, n), np.linspace(block.i0, block.i1, n)])
    is_ = np.concatenate([is_, np.full(n, block.i0), np.full(n, block.i1)]) - 0.5
    lon, lat = NDFD._to_lonlat.transform(x0 + is_ * NDFD.dx, y0 + js * NDFD.dx)
    ax, ay = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True).transform(lon, lat)
    c0, c1 = int(np.floor((np.min(ax) - west) / PIXEL)) - 2, int(np.ceil((np.max(ax) - west) / PIXEL)) + 2
    r0, r1 = int(np.floor((north - np.max(ay)) / PIXEL)) - 2, int(np.ceil((north - np.min(ay)) / PIXEL)) + 2
    return r0, r1, c0, c1


def _read(raster: Raster, rows: tuple[int, int], cols: tuple[int, int], west: float, north: float) -> np.ndarray:
    """A raster's classes over the lattice's rows and columns, 0 (background) off its extent."""
    import rasterio
    from rasterio.windows import Window as RasterWindow

    # the lattice's row r and column c are the raster's row r + dr and column c + dc (2025's extent is wider)
    dr, dc = round((raster.north - north) / PIXEL), round((west - raster.west) / PIXEL)
    r0, r1, c0, c1 = rows[0] + dr, rows[1] + dr, cols[0] + dc, cols[1] + dc
    out = np.zeros((rows[1] - rows[0], cols[1] - cols[0]), dtype=np.uint8)
    rr0, rr1, cc0, cc1 = max(r0, 0), min(r1, raster.height), max(c0, 0), min(c1, raster.width)
    if rr0 >= rr1 or cc0 >= cc1:
        return out
    with rasterio.open(raster.path) as src:
        values = src.read(1, window=RasterWindow.from_slices((rr0, rr1), (cc0, cc1)))
    out[rr0 - r0 : rr1 - r0, cc0 - c0 : cc1 - c0] = values
    return out


def _lerp(coarse: np.ndarray, positions: np.ndarray, axis: int) -> np.ndarray:
    """Linear interpolation along `axis` of values given every LATTICE_STEP positions from 0."""
    k = np.minimum(positions // LATTICE_STEP, coarse.shape[axis] - 2)
    t = (positions - k * LATTICE_STEP) / LATTICE_STEP
    a, b = np.take(coarse, k, axis=axis), np.take(coarse, k + 1, axis=axis)
    shape = [1] * coarse.ndim
    shape[axis] = len(positions)
    t = t.reshape(shape)
    return a * (1 - t) + b * t


@dataclass(frozen=True, kw_only=True)
class Tables:
    """Lookup tables from a class to what it counts toward, built once per process."""

    crops: np.ndarray  # (256, crops) uint8: whether class c is in crop k
    bits: np.ndarray  # (256,) uint64: crop k's bit set for its classes
    observed: np.ndarray  # (256,) bool
    cultivated: np.ndarray  # (256,) bool


@cache
def tables() -> Tables:
    ids = crop_ids()
    if len(ids) > 62:
        raise ValueError("more crops than a 64-bit mask holds beside its two flags")
    crops = np.zeros((256, len(ids)), dtype=np.uint8)
    bits = np.zeros(256, dtype=np.uint64)
    for k, crop_id in enumerate(ids):
        for c in codes(crop_id):
            crops[c, k] = 1
            bits[c] |= np.uint64(1) << np.uint64(k)
    observed = np.ones(256, dtype=bool)
    observed[list(NO_DATA)] = False
    cultivated = np.zeros(256, dtype=bool)
    cultivated[list(CULTIVATED)] = True
    return Tables(crops=crops, bits=bits, observed=observed, cultivated=cultivated)


OBSERVED_BIT = np.uint64(1) << np.uint64(62)
CULTIVATED_BIT = np.uint64(1) << np.uint64(63)
STRIP = 256  # pixel rows counted at a time


def count_block(*, rasters: tuple[Raster, ...], block: Window) -> dict[str, np.ndarray]:
    """A block's counts per cell (y, x): `pixels` (centres in the cell), `classes` (year, y, x, 256: pixels of each
    class each year), and `any` (y, x, crops + 2: pixels in each crop in any year, then observed in any year, then
    cultivated by NASS's rule). The rasters must share a lattice (`check_aligned`)."""
    t = tables()
    first = rasters[0]
    west, north = first.west, first.north
    r0, r1, c0, c1 = pixel_window(block, west, north)
    height, width = r1 - r0, c1 - c0
    years = np.stack([_read(r, (r0, r1), (c0, c1), west, north) for r in rasters])  # (years, rows, cols)

    # Each pixel centre's fractional (j, i), exact every LATTICE_STEP pixels and bilinear between
    coarse_rows = np.arange(0, height + LATTICE_STEP, LATTICE_STEP)
    coarse_cols = np.arange(0, width + LATTICE_STEP, LATTICE_STEP)
    cx = west + (c0 + coarse_cols + 0.5) * PIXEL
    cy = north - (r0 + coarse_rows + 0.5) * PIXEL
    fj, fi = _albers_to_grid()(*np.meshgrid(cx, cy))
    cols = np.arange(width)
    fj_cols, fi_cols = _lerp(fj, cols, axis=1), _lerp(fi, cols, axis=1)  # (coarse rows, cols)

    ny, nx = block.shape
    ncell = ny * nx
    nyears = len(rasters)
    nbits = t.crops.shape[1] + 2
    classes = np.zeros((nyears, ncell * 256), dtype=np.int64)
    pixels = np.zeros(ncell, dtype=np.int64)
    anyof = np.zeros((ncell, nbits), dtype=np.int64)
    bit_index = np.uint64(1) << np.arange(nbits, dtype=np.uint64)
    bit_index[-2:] = (OBSERVED_BIT, CULTIVATED_BIT)
    for s in range(0, height, STRIP):
        rows = np.arange(s, min(s + STRIP, height))
        j = np.floor(_lerp(fj_cols, rows, axis=0) + 0.5).astype(np.int64)
        i = np.floor(_lerp(fi_cols, rows, axis=0) + 0.5).astype(np.int64)
        inside = (j >= block.j0) & (j < block.j1) & (i >= block.i0) & (i < block.i1)
        cell = ((j - block.j0) * nx + (i - block.i0))[inside]
        if not len(cell):
            continue
        pixels += np.bincount(cell, minlength=ncell)
        strip = years[:, rows[0] : rows[-1] + 1][:, inside]  # (years, pixels)
        for y in range(nyears):
            classes[y] += np.bincount(cell * 256 + strip[y], minlength=ncell * 256)
        mask = np.bitwise_or.reduce(t.bits[strip], axis=0)
        mask[t.observed[strip].any(axis=0)] |= OBSERVED_BIT
        cultivated = t.cultivated[strip]
        mask[(cultivated.sum(axis=0) >= 2) | cultivated[-1]] |= CULTIVATED_BIT
        kinds, which = np.unique(mask, return_inverse=True)
        per_kind = np.bincount(cell * len(kinds) + which.ravel(), minlength=ncell * len(kinds)).reshape(ncell, -1)
        has = ((kinds[:, None] & bit_index[None, :]) != 0).astype(np.int64)  # (kinds, bits)
        anyof += per_kind @ has
    return {
        "pixels": pixels.reshape(ny, nx),
        "classes": classes.reshape(nyears, ny, nx, 256),
        "any": anyof.reshape(ny, nx, nbits),
    }


def block_shares(counts: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """A block's statistics (float32 shares, 0–1, NaN where under `MIN_OBSERVED` is observed) from its counts."""
    t = tables()
    pixels, classes, anyof = counts["pixels"], counts["classes"], counts["any"]
    observed_years = (classes * t.observed).sum(axis=-1)  # (years, y, x)
    with np.errstate(invalid="ignore", divide="ignore"):
        observed = np.mean(observed_years / pixels, axis=0)
        enough = observed >= MIN_OBSERVED
        pixel_years = classes.sum(axis=0) @ t.crops.astype(np.int64)  # (y, x, crops): pixel-years in each crop
        mean = pixel_years / observed_years.sum(axis=0)[..., None]
        seen = anyof[..., -2]
        anyshare = anyof[..., :-2] / seen[..., None]
        cultivated = anyof[..., -1] / seen
    out = {"observed": np.where(pixels > 0, observed, np.nan).astype(np.float32)}
    out["cultivated"] = np.where(enough, cultivated, np.nan).astype(np.float32)
    for k, crop_id in enumerate(crop_ids()):
        out[array_name(crop_id, "mean")] = np.where(enough, mean[..., k], np.nan).astype(np.float32)
        out[array_name(crop_id, "any")] = np.where(enough, anyshare[..., k], np.nan).astype(np.float32)
    return out


def block_task(*, rasters: tuple[Raster, ...], block: Window) -> dict[str, np.ndarray]:
    """A pool task: a block's statistics, packed (`pack`)."""
    return {name: pack(v) for name, v in block_shares(count_block(rasters=rasters, block=block)).items()}


def pack(share: np.ndarray) -> np.ndarray:
    """Shares (0–1, NaN missing) as uint16 hundredths of a percent, MISSING for NaN."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.where(np.isfinite(share), np.round(np.clip(share, 0, 1) * SCALE), MISSING).astype(np.uint16)


def unpack(packed: np.ndarray) -> np.ndarray:
    return np.where(packed == MISSING, np.nan, packed / SCALE).astype(np.float32)


# --- The store --------------------------------------------------------------------------------------------------


def path(data_dir: Path) -> Path:
    return Path(data_dir) / STORE


def _window_attrs(window: Window) -> dict[str, int]:
    return {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1}


def stored_years(data_dir: Path) -> tuple[int, ...] | None:
    """The years the built store counts, or None if there's none."""
    attrs = _attrs(data_dir)
    return None if attrs is None or not attrs.get("complete") else tuple(attrs.get("years", ()))  # type: ignore[arg-type]


def _attrs(data_dir: Path) -> dict | None:
    import zarr
    from zarr.errors import GroupNotFoundError

    try:
        return dict(zarr.open_group(path(data_dir), mode="r").attrs)
    except (FileNotFoundError, GroupNotFoundError):
        return None


def status(data_dir: Path, window: Window, years: Iterable[int]) -> str | None:
    """Why the store needs building over `window` from `years`, or None if it's current."""
    attrs = _attrs(data_dir)
    if attrs is None:
        return "missing"
    if not attrs.get("complete"):
        return "incomplete"
    if attrs.get("version") != VERSION:
        return "out of date: the code changed"
    if attrs.get("codes") != codes_hash():
        return "out of date: the crops' classes changed"
    if attrs.get("window") != _window_attrs(window):
        return "out of date: the service box changed"
    if list(attrs.get("years", [])) != sorted(years):
        return f"out of date: built from {attrs.get('years')}"
    return None


def blocks_for(window: Window, covered: np.ndarray) -> list[Window]:
    """The window's squares of BLOCK cells from its corner that hold a covered cell (`covered` (y, x) over it),
    largest first."""
    out = []
    for j in range(window.j0, window.j1, BLOCK):
        for i in range(window.i0, window.i1, BLOCK):
            block = Window(j0=j, j1=min(j + BLOCK, window.j1), i0=i, i1=min(i + BLOCK, window.i1))
            if covered[j - window.j0 : block.j1 - window.j0, i - window.i0 : block.i1 - window.i0].any():
                out.append(block)
    return sorted(out, key=lambda b: -b.size)


def build(
    data_dir: Path,
    window: Window,
    covered: np.ndarray,
    paths: dict[int, Path],
    report: Callable[[str], None] = lambda _: None,
    progress: Callable[[int, int], None] | None = None,
    stopping: Callable[[], bool] = lambda: False,
) -> dict | None:
    """Builds `cropland.zarr` over `window` from each year's unpacked raster (`paths`, from `extract`), its cells
    outside `covered` (y, x) missing, beside its path and renamed into place. Blocks run in `agdata.blocks`' pool.
    Returns the store's summary attributes, or None if stopped (the current store stays)."""
    import zarr

    from agdata import blocks as pool
    from agdata.climatestore import _swap

    rasters = open_rasters(paths)
    check_aligned(rasters)
    report(f"{len(rasters)} years on one 30 m lattice: {', '.join(str(r.year) for r in rasters)}")
    names = cell_arrays()
    found = {name: np.full(window.shape, MISSING, dtype=np.uint16) for name in names}
    todo = blocks_for(window, covered)
    report(f"{len(todo)} blocks of up to {BLOCK} × {BLOCK} cells, {pool.workers()} at a time")

    def handle(key, result: dict[str, np.ndarray]) -> None:
        block: Window = key
        y, x = slice(block.j0 - window.j0, block.j1 - window.j0), slice(block.i0 - window.i0, block.i1 - window.i0)
        for name, values in result.items():
            found[name][y, x] = values

    chains = [[(block, partial(block_task, rasters=tuple(rasters), block=block))] for block in todo]
    if not pool.run(chains, handle=handle, stop=stopping, progress=progress):
        return None
    for values in found.values():
        values[~covered] = MISSING

    target = path(data_dir)
    building = target.with_name(target.name + ".part")
    if building.exists():
        shutil.rmtree(building)
    group = zarr.open_group(building, mode="w")
    for name, values in found.items():
        group.create_array(name, data=values, chunks=window.shape, fill_value=MISSING)
    observed = unpack(found["observed"])
    summary = {
        "covered_cells": int(covered.sum()),
        "observed_cells": int((observed >= MIN_OBSERVED).sum()),
        "cultivated_share": round(float(np.nanmean(unpack(found["cultivated"]))), 4),
    }
    group.attrs.update(
        {
            "version": VERSION,
            "years": sorted(paths),
            "window": _window_attrs(window),
            "files": [zip_name(y) for y in sorted(paths)],
            "codes": codes_hash(),
            "scale": SCALE,
            "missing": int(MISSING),
            "source": "USDA NASS Cropland Data Layer",
            "summary": summary,
            "complete": True,
        }
    )
    _swap(building, target)
    return summary


# --- Reading ----------------------------------------------------------------------------------------------------


class NotBuilt(RuntimeError):
    """A request needs the cropland store, and it isn't built."""


@dataclass(frozen=True, kw_only=True)
class Cropland:
    """The store's per-cell arrays over its window (packed, as stored), read once (~100 MB at the launch box)."""

    window: Window
    years: tuple[int, ...]
    cells: dict[str, np.ndarray]
    stamp: float  # when the store was built (its metadata's mtime): a cache key for what's derived from it

    def share(self, crop_id: str | None, stat: str, window: Window) -> np.ndarray:
        """A share (0–1, float32 (y, x)) over `window`, NaN where it's missing and outside the store's window.
        `crop_id` None with `stat` "observed" or "cultivated" gives those; else a crop's `stat` ("mean", "any")."""
        name = stat if crop_id is None else array_name(crop_id, stat)
        if name not in self.cells:
            raise KeyError(f"no cropland array {name!r}")
        values = self.cells[name]
        out = np.full(window.shape, MISSING, dtype=np.uint16)
        j0, j1 = max(window.j0, self.window.j0), min(window.j1, self.window.j1)
        i0, i1 = max(window.i0, self.window.i0), min(window.i1, self.window.i1)
        if j0 < j1 and i0 < i1:
            out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = values[
                j0 - self.window.j0 : j1 - self.window.j0, i0 - self.window.i0 : i1 - self.window.i0
            ]
        return unpack(out)


_loaded: dict[Path, tuple[float, Cropland]] = {}


def load(data_dir: Path) -> Cropland | None:
    """The built store's arrays, or None if there's none; read again when the store is rebuilt."""
    import zarr

    target = path(data_dir)
    marker = target / "zarr.json"
    if not marker.exists():
        return None
    stamp = marker.stat().st_mtime
    kept = _loaded.get(target)
    if kept is not None and kept[0] == stamp:
        return kept[1]
    group = zarr.open_group(target, mode="r")
    attrs = dict(group.attrs)
    if not attrs.get("complete"):
        return None
    cells = {name: np.asarray(group[name][...]) for name in group.array_keys()}  # type: ignore[index]
    w: dict[str, int] = dict(attrs["window"])  # type: ignore[arg-type]
    found = Cropland(
        window=Window(j0=w["j0"], j1=w["j1"], i0=w["i0"], i1=w["i1"]),
        years=tuple(attrs["years"]),  # type: ignore[arg-type]
        cells=cells,
        stamp=stamp,
    )
    _loaded[target] = (stamp, found)
    return found
