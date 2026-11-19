"""URMA's hourly temperature and dew point at a lattice of cells over the whole NDFD grid, for fitting Open-Meteo's
humidity map against URMA region by region (D100's follow-up: the map was fitted in Wisconsin only, and in Oklahoma it
made spring 2–4 times too humid; URMA is the archive's source and covers the country, so the map can target it
everywhere).

Every message is a whole CONUS field (~5 MB), so an hour costs two reads (TMP and DPT, 2 m) whatever the sample; only
the lattice's cells are kept: every `--step`th row and column (20: about 50 km apart, ~9,400 cells) plus the cells of
the points in `EXTRA` (the five Oklahoma Mesonet stations of `tmp/pecan-check/`). One file a day,
`data/urma-sample/<year>/<YYYYMMDD>.npz` (`air_temperature` and `dew_point`, °C, hours × cells, float32; hours
01Z…24Z, each the hour ending then, as the archive stamps them), and the cells in `data/urma-sample/cells.npz`. Days
already written are skipped, so a stopped run picks up where it left off.

    uv run python scripts/fetch_urma_sample.py --start 2025-01-01 --end 2025-12-31 --workers 8

`--quiet` prints only warnings, failures and the summary; the exit status is nonzero if any hour failed.
"""

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from agdata.grid import NDFD
from agdata.progress import Reporter
from agdata.sources.analysis import _first_existing
from agdata.sources.grib import place
from agdata.sources.urma import URMA

OUT = Path(__file__).resolve().parents[1] / "data" / "urma-sample"
KEYS = {"air_temperature": ("TMP", "2 m above ground"), "dew_point": ("DPT", "2 m above ground")}
EXTRA = {  # Oklahoma Mesonet stations of the pecan check (tmp/pecan-check/stations.csv)
    "OKMU": (35.5815, -95.9148),
    "BURN": (33.8937, -97.2692),
    "DURA": (33.9171, -96.3204),
    "EUFA": (35.3004, -95.6578),
    "SHAW": (35.3647, -96.9484),
}
HOUR = timedelta(hours=1)
_sessions = threading.local()


def lattice(step: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Grid indices (j, i) of the sample: every `step`th row and column from step // 2, then the EXTRA points' cells."""
    jj, ii = np.meshgrid(np.arange(step // 2, NDFD.ny, step), np.arange(step // 2, NDFD.nx, step), indexing="ij")
    j, i = list(jj.ravel()), list(ii.ravel())
    names = [""] * len(j)
    for name, (lat, lon) in EXTRA.items():
        cell = NDFD.cell_of(lat, lon)
        assert cell is not None, name
        cj, ci = cell
        j.append(cj)
        i.append(ci)
        names.append(name)
    return np.array(j), np.array(i), names


def fetch_hour(when: datetime, j: np.ndarray, i: np.ndarray) -> dict[str, np.ndarray]:
    """The hour's TMP and DPT (°C) at the sample's cells; FileNotFoundError if the hour isn't published."""
    session = getattr(_sessions, "session", None)
    if session is None:
        session = _sessions.session = requests.Session()
    fields = _first_existing(URMA.analysis_urls(when), list(KEYS.values()), session)
    if fields is None:
        raise FileNotFoundError(f"no URMA analysis for {when:%Y-%m-%d %H}Z")
    window = NDFD.window
    out = {}
    for name, key in KEYS.items():
        values = place(fields[key], window) if key in fields else np.full(window.shape, np.nan)
        out[name] = (values[j, i] - 273.15).astype(np.float32)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="first day, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="last day, YYYY-MM-DD")
    parser.add_argument("--step", type=int, default=20, help="keep every Nth row and column (20: about 50 km)")
    parser.add_argument("--workers", type=int, default=8, help="hours read at once")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last:
        parser.error("--start must not be after --end")

    j, i, names = lattice(args.step)
    lat, lon = NDFD.latlon(j, i)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT / "cells.npz", j=j, i=i, latitude=lat, longitude=lon, name=np.array(names), step=args.step)
    days = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    todo = [d for d in days if not (OUT / str(d.year) / f"{d:%Y%m%d}.npz").exists()]
    with report.activate():
        report.step(
            f"URMA TMP and DPT at {len(j):,} cells (every {args.step}th row and column, and {len(EXTRA)} station cells), {first} to {last}: {len(todo)} of {len(days)} days to fetch, {args.workers} at once, into {OUT}"
        )
        done_days = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for d in todo:
                start = datetime(d.year, d.month, d.day, tzinfo=UTC)
                hours = [start + (k + 1) * HOUR for k in range(24)]  # hours ending 01Z … 24Z
                found = {name: np.full((24, len(j)), np.nan, dtype=np.float32) for name in KEYS}
                failed = 0
                futures = {pool.submit(fetch_hour, when, j, i): k for k, when in enumerate(hours)}
                for future in as_completed(futures):
                    k = futures[future]
                    try:
                        values = future.result()
                    except Exception as error:  # a missing or unreadable hour stays NaN
                        failed += 1
                        report.fail(f"{hours[k]:%Y-%m-%d %H}Z", error)
                        continue
                    for name in KEYS:
                        found[name][k] = values[name]
                path = OUT / str(d.year) / f"{d:%Y%m%d}.npz"
                path.parent.mkdir(parents=True, exist_ok=True)
                if failed < 24:
                    np.savez_compressed(path, **found)
                report.detail(
                    f"{d}: {24 - failed} hours" + (f", {failed} failed" if failed else "") + f" → {path.name}"
                )
                done_days += 1
                report.progress("days", done_days, len(todo))
        ok = report.finish(f"{done_days} days written to {OUT}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
