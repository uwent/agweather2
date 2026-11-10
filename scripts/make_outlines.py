"""Builds `agdata/data/outlines.npz`: state and county outlines for static maps (PLAN.md Phase 5 G3, D60).

From the Census Bureau's cartographic boundary files, 1:5,000,000 (public domain): the lower 48 and DC, each ring
as lat/lng vertices. Static maps project them onto the grid when drawing (`agdata.mapimage`).

The files are kept in `data/census/` (download them there if they're missing):

    curl -L --output-dir data/census -O https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_5m.zip
    curl -L --output-dir data/census -O https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_5m.zip
    uv run --with pyshp python scripts/make_outlines.py data/census/cb_2023_us_state_5m.zip \
        data/census/cb_2023_us_county_5m.zip
"""

import itertools
import sys
from pathlib import Path

import numpy as np
import shapefile  # pyshp

OUT = Path(__file__).resolve().parents[1] / "packages/agdata/src/agdata/data/outlines.npz"
OUTSIDE = {"02", "15", "60", "66", "69", "72", "78"}  # Alaska, Hawaii and the territories


def rings(path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(lat, lon, starts): every ring's vertices, concatenated, and where each ring starts."""
    lats, lons, starts = [], [], []
    n = 0
    with shapefile.Reader(path) as reader:
        for record, shape in zip(reader.iterRecords(fields=["STATEFP"]), reader.iterShapes(), strict=True):
            if record["STATEFP"] in OUTSIDE:
                continue
            bounds = [*shape.parts, len(shape.points)]
            for a, b in itertools.pairwise(bounds):
                points = np.array(shape.points[a:b])
                starts.append(n)
                lons.append(points[:, 0])
                lats.append(points[:, 1])
                n += b - a
    return np.concatenate(lats), np.concatenate(lons), np.array(starts, dtype=np.int32)


def main(states: str, counties: str) -> None:
    found = {}
    for kind, path in (("states", states), ("counties", counties)):
        lat, lon, starts = rings(path)
        found |= {
            f"{kind}_lat": lat.astype(np.float32),
            f"{kind}_lon": lon.astype(np.float32),
            f"{kind}_starts": starts,
        }
        print(f"{kind}: {starts.size:,} rings, {lat.size:,} vertices")
    np.savez_compressed(OUT, **found)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main(*sys.argv[1:3])
