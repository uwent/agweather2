"""Writes the small GRIB fixtures for test_sources.py from real URMA files (needs the network).

uv run python packages/agdata/tests/fixtures/make_grib_fixtures.py

- urma_tmp_small.grb2: a real URMA 2 m temperature message cut down to 40 x 50 cells at NDFD (900, 1400),
  re-encoded by eccodes, with one cell missing (bitmap)
- urma_2016_tmp_head.bin: the first 2 KB of a 2016 (no .idx) TMP message, for the header scanner
- urma_wexp.idx: a real .idx
"""

import warnings
from pathlib import Path

import numpy as np
import requests

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="ecCodes .* or higher is recommended")
    import eccodes

from agdata.grid import NDFD
from agdata.sources.grib import RemoteGrib

HERE = Path(__file__).parent
session = requests.Session()

wexp = RemoteGrib(
    "https://noaa-urma-pds.s3.amazonaws.com/urma2p5.20250715/urma2p5.t18z.2dvaranl_ndfd.grb2_wexp", session
)
(HERE / "urma_wexp.idx").write_text(session.get(wexp.url + ".idx", timeout=60).text)

ref = next(r for r in wexp.index() if r.key == ("TMP", "2 m above ground"))
message = wexp._read_range(ref.offset, ref.offset + ref.length - 1)  # pyright: ignore[reportOptionalOperand]
handle = eccodes.codes_new_from_message(message)
full = eccodes.codes_get_values(handle).reshape(NDFD.ny, NDFD.nx)
j0, i0, ny, nx = 900, 1400, 40, 50
lat, lon = NDFD.latlon(j0, i0)
eccodes.codes_set(handle, "Nx", nx)
eccodes.codes_set(handle, "Ny", ny)
eccodes.codes_set(handle, "latitudeOfFirstGridPointInDegrees", float(lat))
eccodes.codes_set(handle, "longitudeOfFirstGridPointInDegrees", float(lon) % 360)
values = full[j0 : j0 + ny, i0 : i0 + nx].copy()
values[0, 0] = 9999.0
eccodes.codes_set(handle, "bitmapPresent", 1)
eccodes.codes_set(handle, "missingValue", 9999.0)
eccodes.codes_set_values(handle, values.ravel())
(HERE / "urma_tmp_small.grb2").write_bytes(eccodes.codes_get_message(handle))
np.save(HERE / "urma_tmp_small_expected.npy", np.where(values == 9999.0, np.nan, values))
eccodes.codes_release(handle)

old = RemoteGrib("https://noaa-urma-pds.s3.amazonaws.com/urma2p5.20160701/urma2p5.t18z.2dvaranl_ndfd.grb2_ext", session)
ref = next(r for r in old.index() if r.key == ("TMP", "2 m above ground"))
(HERE / "urma_2016_tmp_head.bin").write_bytes(old._read_range(ref.offset, ref.offset + 2047))
print("wrote fixtures:", sorted(p.name for p in HERE.iterdir() if p.suffix in {".grb2", ".bin", ".idx", ".npy"}))
