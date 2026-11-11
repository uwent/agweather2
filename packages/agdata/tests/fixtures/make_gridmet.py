"""Records gridMET fixtures: 5 days (January 1–5, 2020) of tmmx and pr over a 12 × 14 patch at Lake Michigan's
shore near Sheboygan (some points are the lake, which gridMET leaves as fill), cropped from gridMET's whole-CONUS
2020 files as received (packed integers and their attributes). Reads the box's chunks over the network.

    uv run python packages/agdata/tests/fixtures/make_gridmet.py
"""

from pathlib import Path

import fsspec
import h5py
import numpy as np

from agdata.sources import gridmet

OUT = Path(__file__).parent / "gridmet"
SOUTH, NORTH, WEST, EAST = 43.55, 44.0, -88.05, -87.5
DAYS = 5


def main() -> None:
    for name in ("tmmx", "pr"):
        url = gridmet.url(name, 2020)
        with (
            fsspec.open(url, "rb", block_size=gridmet.BLOCK, headers=gridmet.HEADERS) as remote,
            h5py.File(remote) as f,
        ):
            var = gridmet._data_variable(f)
            data = gridmet._dataset(f, var)
            lat, lon, day = gridmet._array(f, "lat"), gridmet._array(f, "lon"), gridmet._array(f, "day")
            rows = gridmet._span(lat, SOUTH, NORTH)
            cols = gridmet._span(lon, WEST, EAST)
            fill = data.attrs.get("_FillValue")
            gridmet.write(
                OUT / f"{name}_2020.nc",
                name=var,
                values=np.asarray(data[:DAYS, rows, cols]),
                day=day[:DAYS],
                lat=lat[rows],
                lon=lon[cols],
                attrs={k: gridmet._text(data.attrs[k]) for k in gridmet._KEPT_ATTRS if k in data.attrs},
                fill=None if fill is None else np.asarray(fill).ravel()[0],
                coord_attrs={
                    c: {
                        k: gridmet._text(v)
                        for k, v in gridmet._dataset(f, c).attrs.items()
                        if k in ("units", "long_name")
                    }
                    for c in ("day", "lat", "lon")
                },
                source=url,
            )
        print(name, (OUT / f"{name}_2020.nc").stat().st_size, "bytes")


if __name__ == "__main__":
    main()
