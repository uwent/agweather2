"""Builds `agdata/data/water.npz`: open water on the NDFD 2.5 km grid, for the coast of soil temperature and snow
depth (D79, `agdata.coast`).

URMA analyzes significant wave height (`HTSGW`) over the ocean and the Great Lakes only, so a cell with a value is
water. Ice can leave a wave height missing, so the mask is the union of a few ice-free analyses. Inland lakes have no
wave height and count as land, as ERA5-Land's coarser grid mostly treats them too.

    uv run python scripts/make_water_mask.py
"""

import io
import sys
import urllib.request
from pathlib import Path

import numpy as np

from agdata.grid import NDFD
from agdata.progress import Reporter
from agdata.sources.grib import eccodes

OUT = Path(__file__).resolve().parents[1] / "packages/agdata/src/agdata/data/water.npz"
BUCKET = "https://noaa-urma-pds.s3.amazonaws.com"
DAYS = ("20260801", "20260915", "20261005")  # ice-free on the Great Lakes


def wave_height_present(day: str, report: Reporter) -> np.ndarray:
    """Where one analysis (12Z) has a wave height, (ny, nx) south to north."""
    url = f"{BUCKET}/urma2p5.{day}/urma2p5.t12z.2dvaranl_ndfd.grb2_wexp"
    lines = urllib.request.urlopen(f"{url}.idx").read().decode().splitlines()
    k = next(k for k, line in enumerate(lines) if ":HTSGW:" in line)
    start, end = int(lines[k].split(":")[1]), int(lines[k + 1].split(":")[1]) - 1
    report.detail(f"{day} 12Z ==> GET {url} bytes {start}-{end}")
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    data = urllib.request.urlopen(request).read()
    handle = eccodes.codes_new_from_message(data)
    try:
        if eccodes.codes_get_long(handle, "scanningMode") != 64:
            raise ValueError(f"{day}: expected scanning mode 64 (rows south to north)")
        nx, ny = eccodes.codes_get_long(handle, "Nx"), eccodes.codes_get_long(handle, "Ny")
        values = np.asarray(eccodes.codes_get_double_array(handle, "values"))
        missing = eccodes.codes_get_double(handle, "missingValue")
    finally:
        eccodes.codes_release(handle)
    if (ny, nx) != (NDFD.ny, NDFD.nx):
        raise ValueError(f"{day}: a {ny} x {nx} grid, not NDFD's {NDFD.ny} x {NDFD.nx}")
    return (values != missing).reshape(ny, nx)


def main() -> int:
    report = Reporter()
    report.step(f"Water mask from URMA wave height on {len(DAYS)} ice-free days")
    water = np.zeros((NDFD.ny, NDFD.nx), dtype=bool)
    for day in DAYS:
        found = wave_height_present(day, report)
        report.detail(f"{day}: {found.mean():.1%} of the grid is water")
        water |= found
    buffer = io.BytesIO()
    np.savez_compressed(buffer, packed=np.packbits(water), shape=np.array(water.shape), days=np.array(DAYS))
    OUT.write_bytes(buffer.getvalue())
    return 0 if report.finish(f"{water.mean():.1%} water; wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)") else 1


if __name__ == "__main__":
    sys.exit(main())
