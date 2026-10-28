"""Build `agdata/data/counties.npz`: the county at every point of a 0.025° grid over the lower 48 (D34).

From the Census Bureau's 2024 cartographic boundary file at 1:500,000 (cb_2024_us_county_500k), downloaded once
into `tmp/planting-dates/`. Each grid point gets the county whose polygon contains it (0 for none: sea, lakes,
Canada, Mexico); `agdata.places` looks points up by index arithmetic, so the app needs no geometry library. The grid
spacing (about 2.8 km north–south, 2 km east–west) puts points within about 1.5 km of a boundary at risk of the
neighbouring county, which is fine for typical planting dates and state region masks.

Run (shapely and pyshp only for the build):
    uv run --with shapely --with pyshp python scripts/build_counties.py
"""

import csv
import io
import zipfile
from pathlib import Path

import numpy as np
import requests
import shapefile  # pyshp
import shapely

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tmp" / "planting-dates"
URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"
OUT = ROOT / "packages" / "agdata" / "src" / "agdata" / "data"
SOUTH, NORTH, WEST, EAST, STEP = 24.4, 49.5, -124.8, -66.9, 0.025
LOWER_48_EXCLUDED = {"02", "15", "60", "66", "69", "72", "78"}  # AK, HI and the territories


def main() -> None:
    archive = CACHE / "cb_county_500k.zip"
    if not archive.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(requests.get(URL, timeout=300).content)
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
    for index, (_, geom) in enumerate(records, start=1):
        west, south, east, north = geom.bounds
        j = np.flatnonzero((lats >= south) & (lats <= north))
        i = np.flatnonzero((lons >= west) & (lons <= east))
        if not j.size or not i.size:
            continue
        lon, lat = np.meshgrid(lons[i], lats[j])
        inside = shapely.contains_xy(geom, lon, lat)
        block = grid[j[0] : j[-1] + 1, i[0] : i[-1] + 1]
        block[inside] = index

    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "counties.npz", county=grid, south=SOUTH, west=WEST, step=STEP)
    with (OUT / "counties.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "geoid", "name", "state"])
        for index, (rec, _) in enumerate(records, start=1):
            writer.writerow([index, rec["GEOID"], rec["NAMELSAD"], rec["STUSPS"]])
    print(f"{len(records)} counties; {np.count_nonzero(grid)} of {grid.size} grid points in a county")


if __name__ == "__main__":
    main()
