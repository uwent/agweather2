"""Writes ndfd_points.json: cell centers from a real URMA wexp GRIB message, for test_grid.py.

uv run python packages/agdata/tests/fixtures/make_ndfd_points.py <urma ...2dvaranl_ndfd.grb2_wexp message>
"""

import json
import sys
from pathlib import Path

import eccodes
import numpy as np

with open(sys.argv[1], "rb") as f:
    message = eccodes.codes_grib_new_from_file(f)
    nx, ny = eccodes.codes_get(message, "Nx"), eccodes.codes_get(message, "Ny")
    lats = eccodes.codes_get_array(message, "latitudes").reshape(ny, nx)
    lons = eccodes.codes_get_array(message, "longitudes").reshape(ny, nx)

rng = np.random.default_rng(0)
cells = [(0, 0), (0, nx - 1), (ny - 1, 0), (ny - 1, nx - 1)]
cells += [(int(j), int(i)) for j, i in zip(rng.integers(0, ny, 26), rng.integers(0, nx, 26), strict=True)]
points = [{"j": j, "i": i, "lat": float(lats[j, i]), "lon": float((lons[j, i] + 180) % 360 - 180)} for j, i in cells]
out = Path(__file__).with_name("ndfd_points.json")
out.write_text(json.dumps({"nx": nx, "ny": ny, "points": points}, indent=1) + "\n")
print(f"wrote {len(points)} points to {out}")
