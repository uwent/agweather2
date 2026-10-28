"""Phase 1 D pilot, step 1: download URMA hours over a box into packed .npz files (one per hour).

uv run python scripts/pilot_download.py --start 2025-07-01 --end 2025-08-01 --box wisconsin --workers 8
Resumable: hours already downloaded are skipped. Timings go to <out>/download.log (one JSON line per hour).
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from agdata.grid import service_window
from agdata.sources import urma
from pilot_encoding import pilot_variable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="exclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default="data/pilot/raw")
    args = parser.parse_args()

    window = service_window(args.box)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    start = datetime.fromisoformat(args.start).replace(tzinfo=UTC)
    end = datetime.fromisoformat(args.end).replace(tzinfo=UTC)
    hours = [start + timedelta(hours=n) for n in range(int((end - start) / timedelta(hours=1)))]
    todo = [h for h in hours if not (out / f"{h:%Y%m%d%H}.npz").exists()]
    print(f"{len(hours)} hours, {len(todo)} to download, window {window.shape}", flush=True)

    sessions: dict[int, requests.Session] = {}

    def fetch(when: datetime):
        import threading

        session = sessions.setdefault(threading.get_ident(), requests.Session())
        began = time.time()
        values = urma.fetch_hour(when, window, session)
        fetched = time.time() - began
        packed = {name: pilot_variable(name).encode(array) for name, array in values.items()}
        np.savez(out / f"{when:%Y%m%d%H}.npz", **packed)
        return when, fetched, sorted(values)

    began = time.time()
    with ThreadPoolExecutor(args.workers) as pool, open(out / "download.log", "a") as log:
        futures = [pool.submit(fetch, h) for h in todo]
        for n, future in enumerate(as_completed(futures), 1):
            try:
                when, seconds, names = future.result()
                log.write(
                    json.dumps({"hour": when.isoformat(), "seconds": round(seconds, 2), "variables": names}) + "\n"
                )
            except Exception as error:  # keep going; a rerun retries the missing hours
                log.write(json.dumps({"error": repr(error)}) + "\n")
            log.flush()
            if n % 24 == 0 or n == len(todo):
                rate = n / (time.time() - began) * 3600
                print(f"{n}/{len(todo)} hours, {rate:.0f} hours per hour of wall time", flush=True)


if __name__ == "__main__":
    main()
