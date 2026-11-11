"""gridMET's daily grids over a box, kept as received in data/gridmet/<var>/<year>.nc (PLAN.md Phase 6 D2, D82).

uv run python scripts/download_gridmet.py --start 2016 --end 2025 [--box wisconsin] [--vars tmmx,tmmn,pr]

From the University of Idaho's THREDDS subsetting service (one request per variable and year, one at a time). The
service gives netCDF-3 only (int16 with a scale and offset, day × latitude north to south × longitude, 1/24°,
days since 1900-01-01); reading it needs SciPy (`uv run --with scipy`), which the project doesn't depend on, so this
script only downloads. A file already there is skipped; `--force` fetches it again. Phase 6 D3 replaces this with
the store's adapter.
"""

import argparse
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "agdata" / "src"))

from agdata.grid import BOXES  # noqa: E402
from agdata.progress import Reporter  # noqa: E402

URL = "http://thredds.northwestknowledge.net:8080/thredds/ncss/agg_met_{var}_1979_CurrentYear_CONUS.nc"
VARS = ["tmmx", "tmmn", "pr", "rmax", "rmin", "vs", "srad", "pet", "sph"]
MARGIN = 0.25  # degrees past the box on each side, for regridding at its edge
HEADERS = {"User-Agent": "agweather-gridmet-download"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument(
        "--box", default="wisconsin", choices=sorted(name for name, b in BOXES.items() if b is not None)
    )
    parser.add_argument("--vars", default=",".join(VARS))
    parser.add_argument("--out", default=str(REPO / "data" / "gridmet"))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    box = BOXES[args.box]
    if box is None:
        parser.error("--box must be a bounded box, not the whole grid")
    names = [v.strip() for v in args.vars.split(",") if v.strip()]
    jobs = [(var, year) for year in range(args.start, args.end + 1) for var in names]
    report.step(f"gridMET {', '.join(names)}, {args.start}–{args.end}, over {args.box}, to {args.out}")
    fetched = 0
    for k, (var, year) in enumerate(jobs):
        path = Path(args.out) / var / f"{year}.nc"
        if path.exists() and not args.force:
            report.progress("files", k + 1, len(jobs))
            continue
        params = {
            "var": "all",
            "north": box.north + MARGIN,
            "south": box.south - MARGIN,
            "west": box.west - MARGIN,
            "east": box.east + MARGIN,
            "time_start": f"{year}-01-01T00:00:00Z",
            "time_end": f"{year}-12-31T00:00:00Z",
            "accept": "netcdf",
        }
        report.detail(f"{var} {year} ==> GET {URL.format(var=var)}")
        try:
            started = time.monotonic()
            response = requests.get(URL.format(var=var), params=params, headers=HEADERS, timeout=600)
            response.raise_for_status()
            if not response.content.startswith(b"CDF"):
                raise ValueError(f"not a netCDF file: {response.content[:80]!r}")
            path.parent.mkdir(parents=True, exist_ok=True)
            part = path.with_suffix(".part")
            part.write_bytes(response.content)
            part.rename(path)
            fetched += 1
            report.detail(f"{var} {year}: {len(response.content) / 1e6:.1f} MB in {time.monotonic() - started:.1f} s")
        except (requests.RequestException, ValueError) as error:
            report.fail(f"{var} {year}", error)
        report.progress("files", k + 1, len(jobs))
    return 0 if report.finish(f"fetched {fetched} of {len(jobs)} files") else 1


if __name__ == "__main__":
    sys.exit(main())
