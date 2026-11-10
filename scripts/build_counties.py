"""Build `agdata/data/counties.npz` and `counties.csv`: the county at every point of a 0.025° grid over the lower 48
(D34), and each county's land area and cells on the 2.5 km grid.

From the Census Bureau's 2024 cartographic boundary file at 1:500,000 (cb_2024_us_county_500k), kept in
`data/census/` (downloaded there if it's missing). Each grid point gets the county whose polygon contains it (0 for
none: sea, lakes, Canada, Mexico); `agdata.places` looks points up by index arithmetic, so the app needs no geometry
library. The grid
spacing (about 2.8 km north–south, 2 km east–west) puts points within about 1.5 km of a boundary at risk of the
neighbouring county, which is fine for typical planting dates and state region masks.

`counties.csv` also gives each county's land area (the file's ALAND, in square meters) and its `cells`: the 2.5 km
grid's cells that summaries count as the county (`agdata.regions.summary_counties`, over the whole grid), so a
summary can say what share of a county the area we cover holds.

Run (shapely and pyshp only for the build):
    uv run --with shapely --with pyshp python scripts/build_counties.py [--quiet]

`--quiet` prints only warnings, failures and the summary.
"""

import argparse
import csv
import io
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import requests
import shapefile  # pyshp
import shapely

from agdata.progress import Reporter

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data" / "census"
URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"
OUT = ROOT / "packages" / "agdata" / "src" / "agdata" / "data"
SOUTH, NORTH, WEST, EAST, STEP = 24.4, 49.5, -124.8, -66.9, 0.025
LOWER_48_EXCLUDED = {"02", "15", "60", "66", "69", "72", "78"}  # AK, HI and the territories


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)

    archive = CENSUS / "cb_2024_us_county_500k.zip"
    report.step(f"building the county grid into {OUT} from {archive}")
    if not archive.exists():
        CENSUS.mkdir(parents=True, exist_ok=True)
        report.step(f"downloading {URL}")
        response = requests.get(URL, timeout=300)
        response.raise_for_status()  # never cache an error page as the archive
        part = archive.with_name(archive.name + ".part")
        part.write_bytes(response.content)
        os.replace(part, archive)
    else:
        report.step(f"using the cached {archive}")
    report.step("reading the county shapes")
    with zipfile.ZipFile(archive) as z:
        name = "cb_2024_us_county_500k"
        reader = shapefile.Reader(
            shp=io.BytesIO(z.read(f"{name}.shp")),
            shx=io.BytesIO(z.read(f"{name}.shx")),
            dbf=io.BytesIO(z.read(f"{name}.dbf")),
        )
        records = [
            (r.record.as_dict(), shapely.geometry.shape(r.shape.__geo_interface__)) for r in reader.iterShapeRecords()
        ]
    records = sorted(
        ((rec, geom) for rec, geom in records if rec["STATEFP"] not in LOWER_48_EXCLUDED),
        key=lambda pair: pair[0]["GEOID"],
    )

    lats = SOUTH + STEP * np.arange(round((NORTH - SOUTH) / STEP) + 1)
    lons = WEST + STEP * np.arange(round((EAST - WEST) / STEP) + 1)
    grid = np.zeros((lats.size, lons.size), dtype=np.uint16)
    skipped = 0
    report.step(f"{len(records)} counties over a {lats.size} x {lons.size} grid")
    for index, (_, geom) in enumerate(records, start=1):
        report.progress("counties", index, len(records))
        west, south, east, north = geom.bounds
        j = np.flatnonzero((lats >= south) & (lats <= north))
        i = np.flatnonzero((lons >= west) & (lons <= east))
        if not j.size or not i.size:
            skipped += 1
            continue
        lon, lat = np.meshgrid(lons[i], lats[j])
        inside = shapely.contains_xy(geom, lon, lat)
        block = grid[j[0] : j[-1] + 1, i[0] : i[-1] + 1]
        block[inside] = index

    if skipped:
        report.warn(f"{skipped} counties cover no grid point")
    OUT.mkdir(parents=True, exist_ok=True)
    report.step(f"writing {OUT / 'counties.npz'} (overwriting)")
    np.savez_compressed(OUT / "counties.npz", county=grid, south=SOUTH, west=WEST, step=STEP)
    report.step("counting each county's cells on the 2.5 km grid")
    from agdata import regions  # reads the county grid just written
    from agdata.grid import NDFD

    cells = np.bincount(regions.summary_counties(NDFD.window).ravel(), minlength=len(records) + 1)
    report.step(f"writing {OUT / 'counties.csv'} (overwriting)")
    with (OUT / "counties.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "geoid", "name", "state", "land_m2", "cells"])
        for index, (rec, _) in enumerate(records, start=1):
            writer.writerow([index, rec["GEOID"], rec["NAMELSAD"], rec["STUSPS"], rec["ALAND"], cells[index]])
    if (empty := int(np.count_nonzero(cells[1:] == 0))) > 0:
        report.warn(f"{empty} counties have no cell on the 2.5 km grid")
    if not report.finish(f"{len(records)} counties; {np.count_nonzero(grid)} of {grid.size} grid points in a county"):
        sys.exit(1)


if __name__ == "__main__":
    main()
