"""ECMWF IFS HRES soil temperature and snow depth on the grid, from Open-Meteo's open data (D52, Q22, D53).

Open-Meteo keeps IFS on its native O1280 grid (~9 km) at `s3://openmeteo/data/ecmwf_ifs/<variable>/chunk_<k>.om`:
each file is (1, 6 599 680 cells, 504 hours), chunk k starting k × 504 hours after 1970-01-01 00Z, values at each
hour instantaneous (as ours, the hour ending then). Past hours are each run's first hours, so one read gives the
provisional days after ERA5-Land's last and the forecast. Read with `omfiles` (GPL-2.0-only), which is the optional
`agdata[ifs]` extra and imported only here (D53).

Checked 2026-10-31 against Open-Meteo's API (`models=ecmwf_ifs`) at a cell in northern Wisconsin: chunk 988's
deep soil matched for 360 hours within 0.03 °C (the API adjusts for elevation). The files hold hours past the
newest run's end (older runs' long leads and stale values), so reads stop at `run_end`: a 00Z or 12Z run reaches
240 hours, a 06Z or 18Z run 144, and after one of those the 00Z or 12Z run 6 hours before it still reaches 234
hours past the newer one (`static/meta.json` gives the newest run).

Cells: ring k from the nearer pole holds 20 + 4(k − 1) points from longitude 0 (`openmeteo.cell_for`). Each NDFD
cell interpolates linearly along the two rings around it, then between them; neighbours over water (ERA5-Land's
land mask, `era5land.LandMask`) get no weight, as IFS's lake points carry the lake's temperature.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import zarr

from agdata import soil_seam
from agdata.grid import NDFD, Window
from agdata.ingest import SOIL
from agdata.sources import era5land
from agdata.sources.openmeteo import RINGS, SOIL_LAYERS, _ring_latitude, soil_at_depths

BUCKET = "openmeteo/data/ecmwf_ifs"
CHUNK_HOURS = 504
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)
VARIABLES = (*SOIL_LAYERS, "snow_depth")
LONG_RUN_HOURS = 240  # 00Z and 12Z
SHORT_RUN_HOURS = 144  # 06Z and 18Z

Opener = Callable[[str, int], Any]  # (variable, chunk) → something sliced [0, cells, hours]


def ring_points(j: int) -> int:
    k = min(j, RINGS - j + 1)
    return 20 + 4 * (k - 1)


@cache
def ring_offsets() -> np.ndarray:
    """The flat index of each ring's first point, by ring (index 0 unused)."""
    counts = np.array([0] + [ring_points(j) for j in range(1, RINGS + 1)], dtype=np.int64)
    return np.cumsum(counts) - counts


@dataclass(frozen=True, kw_only=True)
class Weights:
    """Each NDFD cell's four O1280 neighbours (flat indices) and their weights: (4, ny, nx)."""

    cells: np.ndarray
    weights: np.ndarray

    def apply(self, values: np.ndarray, needed: np.ndarray, hours_per_pass: int = 24) -> np.ndarray:
        """Values at the `needed` flat cells, (cells, hours) → (hours, ny, nx); NaN where no neighbour has one."""
        rows = np.searchsorted(needed, self.cells)  # (4, ny, nx)
        out = np.full((values.shape[1], *self.cells.shape[1:]), np.nan, dtype=np.float32)
        for h in range(0, values.shape[1], hours_per_pass):
            v = np.moveaxis(values[rows, h : h + hours_per_pass], -1, 1)  # (4, hours, ny, nx)
            w = np.where(np.isfinite(v), self.weights[:, None], 0.0)
            total = w.sum(axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = (np.where(w > 0, v, 0.0) * w).sum(axis=0) / total
            out[h : h + hours_per_pass] = np.where(total > 0, mean, np.nan)
        return out


@cache
def weights_for(window: Window) -> Weights:
    """Bilinear weights on the rings, before the land mask."""
    lat, lon = NDFD.window_latlon(window)
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float) % 360
    first = max(1, int((90 - lat.max()) / 180 * RINGS) - 3)
    last = min(RINGS, int((90 - lat.min()) / 180 * RINGS) + 4)
    rings = np.arange(first, last + 1)
    ring_lat = np.array([_ring_latitude(int(j)) for j in rings])  # decreasing
    north = rings[np.searchsorted(-ring_lat, -lat, side="right") - 1]  # the ring at or north of each cell
    south = north + 1
    lat_n = ring_lat[north - first]
    lat_s = ring_lat[south - first]
    wy = (lat_n - lat) / (lat_n - lat_s)
    offsets = ring_offsets()
    cells, weights = [], []
    for ring, w_ring in ((north, 1 - wy), (south, wy)):
        points = np.vectorize(ring_points)(ring)
        position = lon / (360.0 / points)
        i0 = np.floor(position).astype(np.int64) % points
        i1 = (i0 + 1) % points
        wx = position - np.floor(position)
        cells += [offsets[ring] + i0, offsets[ring] + i1]
        weights += [w_ring * (1 - wx), w_ring * wx]
    return Weights(cells=np.stack(cells), weights=np.stack(weights))


def cell_latlon(cells: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Flat O1280 indices → their (latitude, longitude -180–180)."""
    offsets = ring_offsets()
    ring = np.searchsorted(offsets, cells, side="right") - 1
    index = cells - offsets[ring]
    points = np.vectorize(ring_points)(ring)
    lat = np.vectorize(_ring_latitude)(ring)
    lon = (index * 360.0 / points + 180) % 360 - 180
    return lat, lon


def land_weights(weights: Weights, land: era5land.LandMask) -> Weights:
    """Zero weight for neighbours whose nearest ERA5-Land cell is water."""
    lat, lon = cell_latlon(weights.cells)
    g = land.grid
    j = np.clip(np.round((lat - g.first_lat) / g.step).astype(int), 0, g.ny - 1)
    i = np.clip(np.round((lon - g.first_lon) / g.step).astype(int), 0, g.nx - 1)
    is_land = land.fraction[j, i] >= 0.5
    return Weights(cells=weights.cells, weights=np.where(is_land, weights.weights, 0.0))


def chunk_span(first: datetime, last: datetime) -> list[tuple[int, int, int, int]]:
    """(chunk, first step in it, step after the last in it, offset of that first step from `first`) covering
    the hours first..last."""
    a = int((first - EPOCH) / HOUR)
    b = int((last - EPOCH) / HOUR) + 1
    out = []
    for chunk in range(a // CHUNK_HOURS, (b - 1) // CHUNK_HOURS + 1):
        lo = max(a, chunk * CHUNK_HOURS)
        hi = min(b, (chunk + 1) * CHUNK_HOURS)
        out.append((chunk, lo - chunk * CHUNK_HOURS, hi - chunk * CHUNK_HOURS, lo - a))
    return out


def run_end(meta: dict) -> datetime:
    """The last hour the newest runs reach (`static/meta.json`'s `last_run_initialisation_time`)."""
    newest = datetime.fromtimestamp(meta["last_run_initialisation_time"], UTC)
    if newest.hour % 12 == 0:
        return newest + LONG_RUN_HOURS * HOUR
    return max(newest + SHORT_RUN_HOURS * HOUR, newest - 6 * HOUR + LONG_RUN_HOURS * HOUR)


def read(
    first: datetime, last: datetime, window: Window, land: era5land.LandMask, open_chunk: Opener
) -> era5land.Hours:
    """IFS's hours first..last on the window: the catalog's soil depths (°C) and `snow_depth` (cm)."""
    weights = land_weights(weights_for(window), land)
    needed = np.unique(weights.cells)
    offsets = ring_offsets()
    rings = np.searchsorted(offsets, needed, side="right") - 1
    n = int((last - first) / HOUR) + 1
    raw: dict[str, np.ndarray] = {}
    for variable in VARIABLES:
        values = np.full((len(needed), n), np.nan, dtype=np.float32)
        for chunk, t0, t1, at in chunk_span(first, last):
            reader = open_chunk(variable, chunk)
            for ring in np.unique(rings):
                rows = np.flatnonzero(rings == ring)
                lo, hi = int(needed[rows[0]]), int(needed[rows[-1]])
                block = np.asarray(reader[0, lo : hi + 1, t0:t1], dtype=np.float32)
                values[rows, at : at + (t1 - t0)] = block[needed[rows] - lo]
        raw[variable] = weights.apply(values, needed)
    layers = {name: raw[name] for name in SOIL_LAYERS}
    out = {name: value for name, (value, _) in soil_at_depths(layers).items()}
    out["snow_depth"] = era5land.no_negative_snow(raw["snow_depth"]) * 100  # m → cm
    return era5land.Hours(times=[first + k * HOUR for k in range(n)], values=out)


def s3_opener() -> tuple[Opener, Callable[[], dict]]:
    """Readers of Open-Meteo's files on AWS (anonymous) and of its `static/meta.json`; needs `agdata[ifs]`."""
    import fsspec  # agdata[ifs]
    import omfiles  # agdata[ifs]; GPL-2.0-only (D53)

    fs = fsspec.filesystem("s3", anon=True)

    @cache
    def open_chunk(variable: str, chunk: int):
        return omfiles.OmFileReader.from_fsspec(fs, f"{BUCKET}/{variable}/chunk_{chunk}.om")

    def meta() -> dict:
        return json.loads(fs.cat(f"{BUCKET}/static/meta.json"))

    return open_chunk, meta


def latest_path(data_dir: Path) -> Path:
    """Where the IFS job keeps its newest read (the forecast's soil and snow come from it)."""
    return Path(data_dir) / "ifs" / "latest.zarr"


def save_latest(
    path: Path,
    hours: era5land.Hours,
    run: datetime,
    seam: datetime | None = None,
    offsets: dict[str, np.ndarray] | None = None,
) -> None:
    """Keeps a read's hours (from the first provisional hour to the run's end) for the forecast builds, with the
    seam they were shifted to meet and each cell's offset there (`agdata.soil_seam`; raw = value − offset × weight)."""
    group = zarr.open_group(path, mode="w")
    for name, values in hours.values.items():
        group.create_array(name, data=np.asarray(values, dtype=np.float32), chunks=(24, *values.shape[1:]))
    for name, offset in (offsets or {}).items():
        group.create_array(f"{name}_seam_offset", data=np.asarray(offset, dtype=np.float32))
    group.attrs.update(
        {
            "first": hours.times[0].isoformat(),
            "hours": len(hours.times),
            "run": run.isoformat(),
            "seam": seam.isoformat() if seam is not None else None,
            "seam_correction": f"ifs-soil-seam v{soil_seam.table().version}" if offsets else None,
        }
    )


def latest_at(path: Path, times: list[datetime], window: Window) -> dict[str, np.ndarray]:
    """The kept hours at `times`, (times, y, x) per variable on the window it was read for; NaN for hours it
    doesn't hold (or with no read yet)."""
    out = {name: np.full((len(times), *window.shape), np.nan, dtype=np.float32) for name in SOIL}
    try:
        group = zarr.open_group(path, mode="r")
    except FileNotFoundError:
        return out
    first = datetime.fromisoformat(str(group.attrs["first"]))
    count = int(group.attrs["hours"])  # type: ignore[arg-type]
    index = np.array([int((t - first) / HOUR) for t in times])
    inside = (index >= 0) & (index < count)
    if not inside.any():
        return out
    lo, hi = int(index[inside].min()), int(index[inside].max()) + 1
    for name in SOIL:
        block = np.asarray(group[name][lo:hi])  # type: ignore[index]
        if block.shape[1:] != window.shape:
            raise ValueError(f"{path} was read for another window")
        out[name][inside] = block[index[inside] - lo]
    return out
