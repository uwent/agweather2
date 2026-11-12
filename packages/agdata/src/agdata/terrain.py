"""Open water and terrain per grid cell, from NHDPlus V2.1 (PLAN.md Phase 6 D6, Q39).

URMA's analysis cools inland water cells to a different degree from year to year, and the wave-height mask
(`agdata.coast.water`) knows only the Great Lakes and the ocean. This module gives every cell of the service window
its share of open water, from the National Hydrography Dataset's lakes, reservoirs and wide rivers as NHDPlus V2.1
distributes them (EPA and USGS, 1:100,000), and its elevation from the 30 m National Elevation Dataset snapshot
that comes with them.

**Water share** is exact: the area of the cell (a 2.5 km square on the grid's Lambert projection) covered by water
polygons, over the cell's area, worked out a row of cells at a time (the polygons clipped to the row and merged, so
a lake on a river counts once, then intersected with each cell). It's kept as a whole percent, rounded down, so a
cell is 100 only if it's all water: a cell that touches land is never a water cell (Ben, 2026-11-11). Open water is
lakes and ponds (not intermittent ones), reservoirs, estuaries, the Great Lakes, and the rivers and canals NHD draws
as areas; wetlands, inundation areas and intermittent lakes aren't.

NHD's Great Lakes have holes: Lake Superior's polygon leaves out rectangles of open lake (off Ontonagon, and north
of 47° N east of 87° W), gaps in its tiling. `fill_holes` fills them from the wave-height mask: a cell the mask
calls water that NHD gives none of, and the cells along such a hole's edge, become water, 100% where every
neighbour is water by the mask too, else 99% (water for a summary, never a cell "all water" that might touch land).

The polygons are projected with the same lat/lon → grid transform that finds a point's cell (`NDFD.cell_of`), so a
lake's cells are the cells a point on it falls in.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import shapely

from agdata.grid import NDFD, Box, Window

SOURCE = "https://dmap-data-commons-ow.s3.amazonaws.com/NHDPlusV21/Data"
KIND = "nhdplus"
# NHD's feature types (FTYPE) that are open water, and codes (FCODE) of theirs left out: intermittent lakes
OPEN_WATER = frozenset({"LakePond", "Reservoir", "Estuary", "StreamRiver", "CanalDitch", "SeaOcean", "Lock Chamber"})
NOT_OPEN = frozenset({39001})
WATER_LAYERS = ("NHDWaterbody", "NHDArea")
Progress = Callable[[int, int], None]


@dataclass(frozen=True, kw_only=True)
class Subregion:
    """One of a unit's elevation rasters (NHDPlus's raster processing units)."""

    id: str  # "07b"
    file: str  # the archive's name under the unit's folder
    box: Box  # its extent, roughly (lat/lon), to pick the ones a window needs


@dataclass(frozen=True, kw_only=True)
class Unit:
    """An NHDPlus V2.1 vector processing unit: its hydrography snapshot and elevation subregions."""

    id: str  # "07"
    folder: str  # under SOURCE: "NHDPlusMS/NHDPlus07"
    snapshot: str  # the NHDSnapshot archive's name
    box: Box  # its extent, roughly
    subregions: tuple[Subregion, ...]


# The units around the Upper Midwest. A subregion's box is its raster's extent (lat/lon, rounded out), measured from
# the files: its name says little (04a is Lake Ontario, 04b Lake Superior, 04d Lake Michigan). Add a unit's row
# (from the listing at SOURCE, its boxes measured the same way) when the service box reaches it.
UNITS: tuple[Unit, ...] = (
    Unit(
        id="04",
        folder="NHDPlusGL",
        snapshot="NHDPlusV21_GL_04_NHDSnapshot_08.7z",
        box=Box(south=39.8, west=-93.4, north=48.6, east=-72.2),
        subregions=(
            Subregion(
                id="04a",
                file="NHDPlusV21_GL_04_04a_NEDSnapshot_03.7z",
                box=Box(south=40.5, west=-81.7, north=46.5, east=-72.2),
            ),
            Subregion(
                id="04b",
                file="NHDPlusV21_GL_04_04b_NEDSnapshot_03.7z",
                box=Box(south=45.9, west=-93.4, north=48.6, east=-88.9),
            ),
            Subregion(
                id="04c",
                file="NHDPlusV21_GL_04_04c_NEDSnapshot_03.7z",
                box=Box(south=39.8, west=-86.4, north=47.6, east=-78.8),
            ),
            Subregion(
                id="04d",
                file="NHDPlusV21_GL_04_04d_NEDSnapshot_03.7z",
                box=Box(south=40.7, west=-91.0, north=48.0, east=-82.7),
            ),
        ),
    ),
    Unit(
        id="07",
        folder="NHDPlusMS/NHDPlus07",
        snapshot="NHDPlusV21_MS_07_NHDSnapshot_08.7z",
        box=Box(south=36.2, west=-97.8, north=48.2, east=-84.6),
        subregions=(
            Subregion(
                id="07a",
                file="NHDPlusV21_MS_07_07a_NEDSnapshot_01.7z",
                box=Box(south=36.2, west=-93.3, north=43.8, east=-84.6),
            ),
            Subregion(
                id="07b",
                file="NHDPlusV21_MS_07_07b_NEDSnapshot_01.7z",
                box=Box(south=39.8, west=-96.4, north=46.7, east=-87.1),
            ),
            Subregion(
                id="07c",
                file="NHDPlusV21_MS_07_07c_NEDSnapshot_01.7z",
                box=Box(south=42.8, west=-97.8, north=48.2, east=-88.6),
            ),
        ),
    ),
    Unit(
        id="09",
        folder="NHDPlusSR",
        snapshot="NHDPlusV21_SR_09_NHDSnapshot_07.7z",
        box=Box(south=44.2, west=-109.5, north=53.3, east=-88.8),
        subregions=(
            Subregion(
                id="09a",
                file="NHDPlusV21_SR_09_09a_NEDSnapshot_01.7z",
                box=Box(south=44.2, west=-109.5, north=53.3, east=-88.8),
            ),
        ),
    ),
)


def folder(data_dir: Path) -> Path:
    return Path(data_dir) / KIND


def url(unit: Unit, file: str) -> str:
    return f"{SOURCE}/{unit.folder}/{file}"


def window_box(window: Window, margin: float = 0.1) -> Box:
    """The window's lat/lon extent, `margin` degrees wider."""
    lat, lon = NDFD.window_latlon(window)
    return Box(
        south=float(lat.min()) - margin,
        west=float(lon.min()) - margin,
        north=float(lat.max()) + margin,
        east=float(lon.max()) + margin,
    )


def _overlaps(a: Box, b: Box) -> bool:
    return a.south < b.north and b.south < a.north and a.west < b.east and b.west < a.east


def units_for(window: Window) -> list[Unit]:
    box = window_box(window)
    return [u for u in UNITS if _overlaps(u.box, box)]


def subregions_for(window: Window) -> list[tuple[Unit, Subregion]]:
    box = window_box(window)
    return [(u, s) for u in units_for(window) for s in u.subregions if _overlaps(s.box, box)]


# --- Water ---------------------------------------------------------------------------------------------------


def read_water(shapefiles: Iterable[Path], box: Box) -> list[shapely.Geometry]:
    """The open-water polygons in `box` (lat/lon, as NHD gives them), valid, on the grid's projection."""
    import shapefile  # pyshp

    found: list[shapely.Geometry] = []
    for path in shapefiles:
        reader = shapefile.Reader(str(path))
        names = [f[0] for f in reader.fields[1:]]
        ftype, fcode = names.index("FTYPE"), names.index("FCODE")
        for shape_record in reader.iterShapeRecords():
            record, shape = shape_record.record, shape_record.shape
            if record is None or shape is None:
                continue
            if record[ftype] not in OPEN_WATER or record[fcode] in NOT_OPEN:
                continue
            west, south, east, north = shape.bbox
            if not _overlaps(Box(south=south, west=west, north=north, east=east), box):
                continue
            found.append(shapely.geometry.shape(cast(dict[str, Any], shape.__geo_interface__)))
    if not found:
        return []
    geoms = shapely.make_valid(project(np.asarray(found, dtype=object)))
    return [g for g in geoms if not g.is_empty]


def project(geoms: np.ndarray) -> np.ndarray:
    """Lat/lon geometries onto the grid's projection (meters), as `NDFD.cell_of` places points."""
    to_xy = NDFD._to_xy

    def onto(coords: np.ndarray) -> np.ndarray:
        x, y = to_xy.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geoms, onto)


def cell_edges(window: Window) -> tuple[np.ndarray, np.ndarray]:
    """The projected x of each column's west edge and y of each row's south edge, plus the far edge (n + 1 each)."""
    x0, y0 = NDFD.origin
    xs = x0 + (np.arange(window.i0, window.i1 + 1) - 0.5) * NDFD.dx
    ys = y0 + (np.arange(window.j0, window.j1 + 1) - 0.5) * NDFD.dx
    return xs, ys


def water_share(polygons: list[shapely.Geometry], window: Window, progress: Progress | None = None) -> np.ndarray:
    """Each cell's share of open water, a whole percent rounded down (uint8, (y, x)): 100 only where the cell is
    all water."""
    out = np.zeros(window.shape, dtype=np.uint8)
    if not polygons:
        return out
    geoms = np.asarray(polygons, dtype=object)
    tree = shapely.STRtree(geoms)
    xs, ys = cell_edges(window)
    cell_area = NDFD.dx**2
    for r in range(window.shape[0]):
        strip = shapely.box(xs[0], ys[r], xs[-1], ys[r + 1])
        hits = tree.query(strip, predicate="intersects")
        if len(hits):
            piece = shapely.union_all(shapely.intersection(geoms[hits], strip))
            cells = shapely.box(xs[:-1], ys[r], xs[1:], ys[r + 1])
            area = shapely.area(shapely.intersection(cells, piece))
            # rounded down, so 100 is a cell all water (1e-6: what floating point leaves of a whole cell)
            out[r] = np.clip(np.floor(area / cell_area * 100 + 1e-6), 0, 100).astype(np.uint8)
        if progress is not None:
            progress(r + 1, window.shape[0])
    return out


def _neighbourhood(mask: np.ndarray, every: bool) -> np.ndarray:
    """Whether every (or any) cell of each cell's 3 × 3 neighbourhood is true; outside the window counts as
    true for `every`, false for any."""
    padded = np.pad(mask, 1, constant_values=every)
    ny, nx = mask.shape
    shifted = [padded[1 + dy : 1 + dy + ny, 1 + dx : 1 + dx + nx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    return np.all(shifted, axis=0) if every else np.any(shifted, axis=0)


def fill_holes(share: np.ndarray, wave_water: np.ndarray) -> tuple[np.ndarray, int]:
    """`share` with the holes in NHD's Great Lakes filled from the wave-height mask (`coast.water`), and how many
    cells changed: cells the mask calls water that NHD gives no water, and the cells beside them NHD covers only in
    part, become 100 where their whole neighbourhood is water by the mask, else 99."""
    hole = wave_water & (share == 0)
    edge = wave_water & _neighbourhood(hole, every=False) & (share < 100) & ~hole
    filled = hole | edge
    out = share.copy()
    out[filled] = np.where(_neighbourhood(wave_water, every=True)[filled], 100, 99)
    return out, int(filled.sum())


# --- Elevation ------------------------------------------------------------------------------------------------

SUB = 80  # fine cells a side per grid cell (31.7 m): the DEM kept for points, and each cell's statistics
BLOCK = 32  # grid cells a side per block of the build (2,560 fine cells: ~26 MB as float32)
CHUNK = 1280  # fine cells a side per chunk of the kept DEM (16 grid cells)
DEM_SCALE = 0.1  # the kept DEM is int16 decimeters: up to 3,276 m, enough short of the Rockies
MIN_COVER = 0.05  # of a cell's fine cells with an elevation, for its statistics: NED has none over the Great
# Lakes, so a shore or island cell's statistics are its land's


def fine_transform(window: Window):
    """The fine grid's affine transform over the window: north up, `SUB` fine cells per grid cell, on the grid's
    projection, so fine cell (r, c) lies in grid cell (j1 - 1 - r // SUB, i0 + c // SUB)."""
    from affine import Affine

    xs, ys = cell_edges(window)
    res = NDFD.dx / SUB
    return Affine(res, 0.0, float(xs[0]), 0.0, -res, float(ys[-1]))


def _warped(paths: list[Path], window: Window):
    """Each elevation raster warped onto the window's fine grid (bilinear, meters as float32, NaN off the data)."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    crs = CRS.from_proj4(NDFD.proj4)
    height, width = window.shape[0] * SUB, window.shape[1] * SUB
    sources, vrts = [], []
    for p in paths:
        src = rasterio.open(p)
        sources.append(src)
        vrts.append(
            WarpedVRT(
                src,
                crs=crs,
                transform=fine_transform(window),
                width=width,
                height=height,
                resampling=Resampling.bilinear,
                dtype="float32",
                nodata=np.nan,
            )
        )
    return sources, vrts


def dem_block(vrts: list, window: Window, block: Window) -> np.ndarray:
    """The fine DEM over `block` (a window inside `window`), meters, rows south to north, NaN where none of the
    rasters has a value."""
    from rasterio.windows import Window as RasterWindow

    rows = (window.j1 - block.j1) * SUB  # the fine grid is north up
    cols = (block.i0 - window.i0) * SUB
    asked = RasterWindow.from_slices((rows, rows + block.shape[0] * SUB), (cols, cols + block.shape[1] * SUB))
    found = np.full((block.shape[0] * SUB, block.shape[1] * SUB), np.nan, dtype=np.float32)
    for vrt in vrts:
        values = vrt.read(1, window=asked).astype(np.float32) / 100.0  # centimeters
        found = np.where(np.isnan(found), values, found)
    return found[::-1]


def cell_stats(fine: np.ndarray) -> dict[str, np.ndarray]:
    """Each grid cell's mean, minimum, maximum and standard deviation of its fine cells that have an elevation
    (meters), NaN where fewer than `MIN_COVER` of them do."""
    ny, nx = fine.shape[0] // SUB, fine.shape[1] // SUB
    cells = fine.reshape(ny, SUB, nx, SUB).transpose(0, 2, 1, 3).reshape(ny, nx, SUB * SUB)
    enough = np.isfinite(cells).mean(axis=2) >= MIN_COVER
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # a cell with no elevation at all
        stats = {
            "elevation_mean": np.nanmean(cells, axis=2),
            "elevation_min": np.nanmin(cells, axis=2),
            "elevation_max": np.nanmax(cells, axis=2),
            "elevation_std": np.nanstd(cells, axis=2),
        }
    return {k: np.where(enough, v, np.nan).astype(np.float32) for k, v in stats.items()}


def blocks(window: Window, size: int = BLOCK) -> list[Window]:
    return [
        Window(j0=j, j1=min(j + size, window.j1), i0=i, i1=min(i + size, window.i1))
        for j in range(window.j0, window.j1, size)
        for i in range(window.i0, window.i1, size)
    ]


# --- The store --------------------------------------------------------------------------------------------------

VERSION = 1  # bump when what's built changes, and `manage.py terrain` builds it again
STORE = "terrain.zarr"
CELL_ARRAYS = ("water_share", "elevation_mean", "elevation_min", "elevation_max", "elevation_std")


def path(data_dir: Path) -> Path:
    return Path(data_dir) / STORE


def archives_for(window: Window) -> list[tuple[Unit, str]]:
    """The archives a window needs: each unit's hydrography snapshot and the elevation subregions it touches."""
    found = [(u, u.snapshot) for u in units_for(window)]
    return found + [(u, s.file) for u, s in subregions_for(window)]


def archive_path(data_dir: Path, file: str) -> Path:
    return folder(data_dir) / file


def missing_archives(data_dir: Path, window: Window) -> list[tuple[Unit, str]]:
    return [(u, f) for u, f in archives_for(window) if not archive_path(data_dir, f).exists()]


def fetch(unit: Unit, file: str, dest: Path, timeout_s: float = 60.0) -> int:
    """Downloads one archive to `dest` (through a .part file, renamed once whole); returns its size in bytes."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    with requests.get(url(unit, file), stream=True, timeout=timeout_s) as response:
        response.raise_for_status()
        with open(part, "wb") as out:
            for chunk in response.iter_content(chunk_size=1 << 20):
                out.write(chunk)
    part.rename(dest)
    return dest.stat().st_size


def _is_snapshot(file: str) -> bool:
    """A hydrography snapshot's archive (else an elevation subregion's)."""
    return "NHDSnapshot" in file


def extracted(data_dir: Path) -> Path:
    return folder(data_dir) / "extracted"


def extract(data_dir: Path, file: str) -> list[Path]:
    """Unpacks what's used from an archive (the water layers' shapefiles, or the elevation grid) beside it, once;
    returns the shapefiles, or the elevation grid's folder."""
    import py7zr

    out = extracted(data_dir)
    marker = out / f"{file}.done"
    with py7zr.SevenZipFile(archive_path(data_dir, file)) as z:
        names = z.getnames()
        if _is_snapshot(file):
            wanted = [n for n in names if any(f"/{layer}." in n for layer in WATER_LAYERS)]
        else:
            wanted = [n for n in names if "/elev_cm/" in n or n.endswith("/elev_cm") or "/info/" in n]
        if not marker.exists():
            z.extract(path=out, targets=wanted)
            marker.write_text("\n".join(wanted))
    if _is_snapshot(file):
        return sorted(out / n for n in wanted if n.endswith(".shp"))
    return sorted({(out / n).parent for n in wanted if "/elev_cm/" in n})


def status(data_dir: Path, window: Window) -> str | None:
    """Why the store needs building, or None if it's current."""
    import zarr
    from zarr.errors import GroupNotFoundError

    try:
        attrs = dict(zarr.open_group(path(data_dir), mode="r").attrs)
    except (FileNotFoundError, GroupNotFoundError):
        return "missing"
    if not attrs.get("complete"):
        return "incomplete"
    if attrs.get("version") != VERSION:
        return "out of date: the code changed"
    if attrs.get("window") != _window_attrs(window):
        return "out of date: the service box changed"
    if attrs.get("archives") != [f for _, f in archives_for(window)]:
        return "out of date: the source files changed"
    return None


def _window_attrs(window: Window) -> dict[str, int]:
    return {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1}


def build(
    data_dir: Path,
    window: Window,
    wave_water: np.ndarray,
    report: Callable[[str], None] = lambda _: None,
    progress: Callable[[str, int, int], None] | None = None,
    stopping: Callable[[], bool] = lambda: False,
) -> bool:
    """Builds `terrain.zarr` over the window from the kept archives (`archives_for`; fetched beforehand), beside
    its path and renamed into place. `wave_water` is `coast.water(window)`, for the holes in NHD's Great Lakes.
    Returns False if stopped (the current store stays)."""
    import zarr
    from zarr.codecs.numcodecs import PCodec

    from agdata.climatestore import _swap

    shapefiles: list[Path] = []
    rasters: list[Path] = []
    for _, file in archives_for(window):
        report(f"unpacking {file}")
        (shapefiles if _is_snapshot(file) else rasters).extend(extract(data_dir, file))
    report(f"reading water from {len(shapefiles)} shapefiles")
    polygons = read_water(shapefiles, window_box(window))
    report(f"water share from {len(polygons):,} polygons")
    share = water_share(polygons, window, None if progress is None else lambda d, t: progress("water", d, t))
    share, filled = fill_holes(share, wave_water)
    report(f"{filled} cells filled from the wave-height mask (holes in NHD's Great Lakes)")

    target = path(data_dir)
    building = target.with_name(target.name + ".part")
    if building.exists():
        import shutil

        shutil.rmtree(building)
    group = zarr.open_group(building, mode="w")
    dem = group.create_array(
        "dem",
        shape=(window.shape[0] * SUB, window.shape[1] * SUB),
        chunks=(CHUNK, CHUNK),
        dtype="int16",
        fill_value=np.iinfo(np.int16).min,
        serializer=PCodec(level=8),
    )
    dem.attrs.update({"scale": DEM_SCALE, "units": "m", "sub": SUB})
    stats = {name: np.full(window.shape, np.nan, dtype=np.float32) for name in CELL_ARRAYS[1:]}
    sources, vrts = _warped(rasters, window)
    try:
        todo = blocks(window)
        for k, block in enumerate(todo):
            if stopping():
                import shutil

                shutil.rmtree(building)
                return False
            fine = dem_block(vrts, window, block)
            rows = slice((block.j0 - window.j0) * SUB, (block.j1 - window.j0) * SUB)
            cols = slice((block.i0 - window.i0) * SUB, (block.i1 - window.i0) * SUB)
            packed = np.round(fine / DEM_SCALE)
            dem[rows, cols] = np.where(np.isfinite(packed), packed, np.iinfo(np.int16).min).astype(np.int16)
            y, x = slice(block.j0 - window.j0, block.j1 - window.j0), slice(block.i0 - window.i0, block.i1 - window.i0)
            for name, values in cell_stats(fine).items():
                stats[name][y, x] = values
            if progress is not None:
                progress("elevation", k + 1, len(todo))
    finally:
        for v in vrts:
            v.close()
        for s in sources:
            s.close()
    group.create_array("water_share", data=share, chunks=window.shape)
    for name, values in stats.items():
        group.create_array(name, data=values, chunks=window.shape)
    group.attrs.update(
        {
            "version": VERSION,
            "window": _window_attrs(window),
            "archives": [f for _, f in archives_for(window)],
            "filled_from_wave_height": filled,
            "complete": True,
        }
    )
    _swap(building, target)
    return True


class NotBuilt(RuntimeError):
    """A request needs the terrain store, and it isn't built."""


# --- Reading ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Terrain:
    """The store's per-cell arrays over its window, read once (a few MB at the launch box)."""

    window: Window
    cells: dict[str, np.ndarray]
    stamp: float  # when the store was built (its metadata's mtime): a cache key for what's derived from it

    def inside(self, window: Window) -> np.ndarray:
        """True for `window`'s cells inside the store's window, (y, x)."""
        j, i = np.arange(window.j0, window.j1), np.arange(window.i0, window.i1)
        rows = (j >= self.window.j0) & (j < self.window.j1)
        cols = (i >= self.window.i0) & (i < self.window.i1)
        return rows[:, None] & cols[None, :]

    def crop(self, name: str, window: Window) -> np.ndarray:
        """A per-cell array over `window`, NaN (or 0 for water share) outside the store's window."""
        values = self.cells[name]
        fill = 0 if name == "water_share" else np.nan
        out = np.full(window.shape, fill, dtype=values.dtype)
        j0, j1 = max(window.j0, self.window.j0), min(window.j1, self.window.j1)
        i0, i1 = max(window.i0, self.window.i0), min(window.i1, self.window.i1)
        if j0 < j1 and i0 < i1:
            out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = values[
                j0 - self.window.j0 : j1 - self.window.j0, i0 - self.window.i0 : i1 - self.window.i0
            ]
        return out


_loaded: dict[Path, tuple[float, Terrain]] = {}


def load(data_dir: Path) -> Terrain | None:
    """The built store's per-cell arrays, or None if there's none; read again when the store is rebuilt."""
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
    cells = {name: np.asarray(group[name][...]) for name in CELL_ARRAYS}  # type: ignore[index]
    w: dict[str, int] = dict(attrs["window"])  # type: ignore[arg-type]
    found = Terrain(window=Window(j0=w["j0"], j1=w["j1"], i0=w["i0"], i1=w["i1"]), cells=cells, stamp=stamp)
    _loaded[target] = (stamp, found)
    return found


def point_elevation(data_dir: Path, lat: float, lon: float) -> float | None:
    """The elevation (m) at a point from the kept 31.7 m DEM, or None outside it or where it has none."""
    import zarr

    found = load(data_dir)
    if found is None:
        return None
    fj, fi = NDFD.fractional_index(lat, lon)
    w = found.window
    r = int(np.floor((float(fj) - w.j0 + 0.5) * SUB))
    c = int(np.floor((float(fi) - w.i0 + 0.5) * SUB))
    if not (0 <= r < w.shape[0] * SUB and 0 <= c < w.shape[1] * SUB):
        return None
    dem = zarr.open_array(path(data_dir) / "dem", mode="r")
    value = int(dem[r, c])  # type: ignore[index]
    return None if value == np.iinfo(np.int16).min else value * DEM_SCALE
