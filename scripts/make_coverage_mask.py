"""Builds `agdata/data/coverage-upper_midwest.npz`: the launch coverage (D105) as a mask on the NDFD 2.5 km grid.

The cells whose centers lie within BUFFER_KM of the 12 Midwest states and Kentucky (the Census Bureau's 2023
cartographic boundaries, buffered on an equal-area projection so 50 km is 50 km on the ground), and the Great Lakes
that buffer reaches (the wave-height water, `agdata.coast.water`, connected to it: Superior, Michigan, Huron and
Erie, not Ontario), so lake maps aren't cut into bands, and any cell the mask encloses (gaps in the wave-height
water). The file keeps the mask over its bounding window, which is
the window the stores take.

    uv run python scripts/make_coverage_mask.py
"""

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pyproj
import shapefile
import shapely

from agdata.coast import water
from agdata.grid import NDFD, Window
from agdata.progress import Reporter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packages/agdata/src/agdata/data/coverage-upper_midwest.npz"
STATES_ZIP = ROOT / "data/census/cb_2023_us_state_5m.zip"
STATES = ("ND", "SD", "NE", "KS", "MN", "IA", "MO", "WI", "IL", "IN", "MI", "OH", "KY")
BUFFER_KM = 50.0
EQUAL_AREA = "EPSG:5070"  # CONUS Albers: distances near true across the region


def read_states(report: Reporter) -> shapely.Geometry:
    """The states' union on EQUAL_AREA, buffered by BUFFER_KM."""
    with zipfile.ZipFile(STATES_ZIP) as z:
        stem = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
        reader = shapefile.Reader(
            shp=io.BytesIO(z.read(f"{stem}.shp")),
            shx=io.BytesIO(z.read(f"{stem}.shx")),
            dbf=io.BytesIO(z.read(f"{stem}.dbf")),
        )
        field = [f[0] for f in reader.fields[1:]].index("STUSPS")
        shapes = {r.record[field]: shapely.geometry.shape(r.shape.__geo_interface__) for r in reader.iterShapeRecords()}
    missing = set(STATES) - set(shapes)
    if missing:
        raise ValueError(f"{STATES_ZIP.name} has no {', '.join(sorted(missing))}")
    to_area = pyproj.Transformer.from_crs("EPSG:4326", EQUAL_AREA, always_xy=True)
    union = shapely.union_all([shapes[s] for s in STATES])
    report.detail(f"{len(STATES)} states from {STATES_ZIP.name}, buffered {BUFFER_KM:g} km on {EQUAL_AREA}")
    projected = shapely.transform(union, lambda xy: np.column_stack(to_area.transform(xy[:, 0], xy[:, 1])))
    return projected.buffer(BUFFER_KM * 1000)


def connected_water(seed: np.ndarray, is_water: np.ndarray) -> np.ndarray:
    """The `is_water` cells connected (4-neighbours) to `seed`'s."""
    found = seed & is_water
    while True:
        grown = found.copy()
        grown[1:] |= found[:-1]
        grown[:-1] |= found[1:]
        grown[:, 1:] |= found[:, :-1]
        grown[:, :-1] |= found[:, 1:]
        grown &= is_water
        if (grown == found).all():
            return found
        found = grown


def main() -> int:
    report = Reporter()
    report.step(f"Coverage mask: {', '.join(STATES)} with a {BUFFER_KM:g} km buffer, and the Great Lakes it reaches")
    area = read_states(report)
    full = NDFD.window
    lat, lon = NDFD.window_latlon(full)
    to_area = pyproj.Transformer.from_crs("EPSG:4326", EQUAL_AREA, always_xy=True)
    x, y = to_area.transform(np.asarray(lon), np.asarray(lat))
    shapely.prepare(area)
    states = shapely.contains_xy(area, x, y)
    report.detail(f"{states.sum():,} cells within the buffered states")
    lakes = connected_water(states, water(full))
    report.detail(f"{(lakes & ~states).sum():,} more cells of the Great Lakes connected to them")
    mask = states | lakes
    outer = np.zeros_like(mask)
    outer[[0, -1], :] = outer[:, [0, -1]] = True
    holes = ~mask & ~connected_water(outer, ~mask)  # cells the mask encloses (gaps in the wave-height water)
    report.detail(f"{holes.sum():,} cells enclosed by the mask filled")
    mask |= holes
    rows, cols = np.nonzero(mask)
    window = Window(j0=int(rows.min()), j1=int(rows.max()) + 1, i0=int(cols.min()), i1=int(cols.max()) + 1)
    inside = mask[window.slices]
    buffer = io.BytesIO()
    np.savez_compressed(
        buffer,
        packed=np.packbits(inside),
        window=np.array([window.j0, window.j1, window.i0, window.i1]),
        states=np.array(STATES),
        buffer_km=np.array(BUFFER_KM),
        source=np.array(STATES_ZIP.name),
    )
    OUT.write_bytes(buffer.getvalue())
    done = f"{inside.sum():,} cells in a window of {window.shape[0]} × {window.shape[1]} ({inside.mean():.0%}); wrote {OUT.name} ({OUT.stat().st_size / 1e3:.0f} kB)"
    return 0 if report.finish(done) else 1


if __name__ == "__main__":
    sys.exit(main())
