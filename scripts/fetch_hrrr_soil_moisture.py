"""HRRR's analysed volumetric soil moisture (`SOILW`, `wrfprs` f00) at Wisconet's stations, every third day at 12Z,
for `scripts/compare_soil_moisture_wisconet.py --hrrr` (Phase 6 step 6). Each station takes the HRRR point nearest
it, at HRRR's levels of 4, 10, 30 and 60 cm. About 1.3 MB a message, so ~1.2 GB over 2025–2026; nothing is kept but
the stations' values.

    uv run python scripts/fetch_hrrr_soil_moisture.py --start 2025-01-01 --end 2026-11-20 \
        --stations tmp/soil-moisture/wisconet/stations.json --out tmp/soil-moisture/hrrr_soilw.npz

Writes an npz of times (Unix seconds), station ids, levels (cm) and values (times, stations, levels; NaN where a
file or message was missing).
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from agdata.progress import Reporter
from agdata.sources.grib import RemoteGrib
from agdata.sources.hrrr import BUCKET, HRRR_GRID

LEVELS = {
    "0.04-0.04 m below ground": 4,
    "0.1-0.1 m below ground": 10,
    "0.3-0.3 m below ground": 30,
    "0.6-0.6 m below ground": 60,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--every", type=int, default=3, help="days between samples")
    parser.add_argument("--stations", required=True, help="Wisconet's stations.json (the client's cache)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    stations = json.loads(Path(args.stations).read_text())
    cells = []
    for s in stations:
        fj, fi = HRRR_GRID.fractional_index(np.array([s["latitude"]]), np.array([s["longitude"]]))
        cells.append((round(float(fj[0])), round(float(fi[0]))))
    first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    times = [
        datetime(first.year, first.month, first.day, 12, tzinfo=UTC) + timedelta(days=k)
        for k in range(0, (last - first).days + 1, args.every)
    ]
    report.step(f"HRRR soil moisture at {len(stations)} stations, {len(times)} hours; writing {args.out}")
    done = 0

    def one(t: datetime) -> np.ndarray:
        nonlocal done
        url = f"{BUCKET}/hrrr.{t:%Y%m%d}/conus/hrrr.t{t:%H}z.wrfprsf00.grib2"
        out = np.full((len(stations), len(LEVELS)), np.nan)
        try:
            grib = RemoteGrib(url, requests.Session())
            for ref, field in grib.fields_where(lambda r: r.key[0] == "SOILW" and r.key[1] in LEVELS):
                k = list(LEVELS).index(ref.key[1])
                for n, (j, i) in enumerate(cells):
                    out[n, k] = field.values[j, i]
        except Exception as error:
            report.fail(f"{t:%Y-%m-%d %HZ}", error)
        done += 1
        report.progress("hours", done, len(times))
        return out

    with ThreadPoolExecutor(6) as pool:
        values = np.stack(list(pool.map(one, times)))
    np.savez(
        args.out,
        times=np.array([int(t.timestamp()) for t in times]),
        stations=np.array([s["station_id"] for s in stations]),
        levels=np.array(list(LEVELS.values())),
        values=values,
    )
    report.step(f"wrote {args.out}")
    if not report.finish(f"{len(times)} hours, {np.isfinite(values).mean():.0%} of values found"):
        sys.exit(1)


if __name__ == "__main__":
    main()
