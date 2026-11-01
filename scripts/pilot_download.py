"""Phase 1 D pilot, step 1: download URMA hours over a box into packed .npz files (one per hour).

uv run python scripts/pilot_download.py --start 2025-07-01 --end 2025-08-01 --box wisconsin --workers 8
Resumable: hours already downloaded are skipped. Timings go to <out>/download.log (one JSON line per hour).
Add --quiet to print only warnings, failures and the summary.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from agdata.grid import service_window
from agdata.progress import Reporter
from agdata.sources.urma import URMA
from pilot_encoding import pilot_variable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="exclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default="data/pilot/raw")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    try:
        start = datetime.fromisoformat(args.start).replace(tzinfo=UTC)
        end = datetime.fromisoformat(args.end).replace(tzinfo=UTC)
    except ValueError as error:
        parser.error(f"--start and --end must be ISO dates or datetimes: {error}")
    if start > end:
        parser.error("--start must not be after --end")

    window = service_window(args.box)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    hours = [start + timedelta(hours=n) for n in range(int((end - start) / timedelta(hours=1)))]
    todo = [h for h in hours if not (out / f"{h:%Y%m%d%H}.npz").exists()]
    report.step(
        f"{len(hours)} hours from {start:%Y-%m-%d %H}Z to {end:%Y-%m-%d %H}Z, {len(todo)} to download "
        f"({args.workers} workers), window {window.shape}, writing {out}/<YYYYMMDDHH>.npz and download.log"
    )

    sessions: dict[int, requests.Session] = {}

    def fetch(when: datetime):
        import threading

        session = sessions.setdefault(threading.get_ident(), requests.Session())
        began = time.time()
        values = URMA.fetch_hour(when, window, session)
        fetched = time.time() - began
        packed = {name: pilot_variable(name).encode(array) for name, array in values.items()}
        final = out / f"{when:%Y%m%d%H}.npz"
        part = out / f"{when:%Y%m%d%H}.part.npz"  # a later run treats a present .npz as done
        np.savez(part, **packed)
        os.replace(part, final)
        return when, fetched, sorted(values)

    failed = 0
    with ThreadPoolExecutor(args.workers) as pool, open(out / "download.log", "a") as log:
        futures = [pool.submit(fetch, h) for h in todo]
        for n, future in enumerate(as_completed(futures), 1):
            try:
                when, seconds, names = future.result()
                log.write(
                    json.dumps({"hour": when.isoformat(), "seconds": round(seconds, 2), "variables": names}) + "\n"
                )
            except Exception as error:  # keep going; a rerun retries the missing hours
                failed += 1
                log.write(json.dumps({"error": repr(error)}) + "\n")
                report.fail(f"hour {n} of {len(todo)}", error)
            log.flush()
            report.progress("hours", n, len(todo))
    if not report.finish(f"{len(todo) - failed} of {len(todo)} hours downloaded into {out}"):
        sys.exit(1)


if __name__ == "__main__":
    main()
