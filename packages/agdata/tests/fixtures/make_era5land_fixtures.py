"""Writes the ERA5-Land fixture for test_era5land.py from the Copernicus CDS (needs the network and
COPERNICUS_API_KEY in the environment or .env).

uv run python packages/agdata/tests/fixtures/make_era5land_fixtures.py

- era5land_milwaukee.grib: 2025-12-16 (snow on the ground), every hour, soil levels 1-3 and snow depth over
  `MILWAUKEE`, a window from the city out over Lake Michigan (so it has shore and open water)
- era5land_milwaukee_lsm.npz: ERA5-Land's land-sea mask cropped to the same request area
"""

import os
import tempfile
from datetime import date
from pathlib import Path

from agdata.grid import NDFD, Window
from agdata.sources import era5land

HERE = Path(__file__).parent
j, i = NDFD.cell_of(43.04, -88.0) or (0, 0)
MILWAUKEE = Window(j0=j - 4, j1=j + 4, i0=i - 4, i1=i + 16)


def key() -> str:
    if value := os.environ.get("COPERNICUS_API_KEY"):
        return value
    for line in Path(".env").read_text().splitlines():
        if line.startswith("COPERNICUS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("COPERNICUS_API_KEY isn't set")


if __name__ == "__main__":
    path = HERE / "era5land_milwaukee.grib"
    era5land.retrieve(date(2025, 12, 16), date(2025, 12, 16), MILWAUKEE, path, key())
    print("wrote", path, path.stat().st_size, "bytes", MILWAUKEE)
    with tempfile.TemporaryDirectory() as tmp:
        lsm = era5land.retrieve_land_mask(Path(tmp) / "lsm.grib", key())
        era5land.read_land_mask(lsm).crop(MILWAUKEE).save(HERE / "era5land_milwaukee_lsm.npz")
    print("wrote", HERE / "era5land_milwaukee_lsm.npz")
