"""Builds a launch-sized archive for profiling (Phase 6 step 7 B): the dev archive's real hours over Wisconsin, tiled
across the launch coverage's window (D105) in a separate data folder.

Real values compress and branch as real data does (pcodec's ratios, the models' data-dependent loops), which made-up
fields don't; seams between tiles don't matter for timing. `GridStore.write` keeps the cells outside the mask missing,
as the real archive will. Only the hourly store is copied: the rest is built by the real commands, which is the jobs'
half of the profile, e.g.

    uv run python scripts/make_profile_archive.py --out tmp/launchbox --first 2025-01-01 --last 2025-07-31
    DATA_DIR=tmp/launchbox SERVICE_BOX=upper_midwest uv run app/manage.py rollup --start 2025-01-01 --end 2025-07-31

Each step's source (URMA, RTMA, HRRR, ERA5-Land) is copied from Wisconsin's store.
"""

import argparse
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import VARIABLES
from agdata.grid import service_window
from agdata.progress import Reporter
from agdata.store import HOURLY, GridStore

ROOT = Path(__file__).resolve().parents[1]
BLOCK_HOURS = 240  # a third of a 720-hour chunk: ~4 GB at peak over the launch window


def tiled(source: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """(steps, sy, sx) repeated across (steps, *shape), from the corner."""
    reps = (1, -(-shape[0] // source.shape[1]), -(-shape[1] // source.shape[2]))
    return np.tile(source, reps)[:, : shape[0], : shape[1]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", type=Path, default=ROOT / "data", help="the dev archive (Wisconsin)")
    parser.add_argument("--out", type=Path, required=True, help="the profile archive's data folder")
    parser.add_argument("--box", default="upper_midwest", help="the service box or coverage to tile across")
    parser.add_argument("--first", type=date.fromisoformat, required=True)
    parser.add_argument("--last", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    if args.first.year != args.last.year:
        parser.error("--first and --last must be in one year")
    report = Reporter()
    year = args.first.year
    target = service_window(args.box)
    source = GridStore.open(args.source, HOURLY, year, [])
    names = sorted(source.group.array_keys())
    names = [n for n in names if n in VARIABLES]
    variables = [VARIABLES[n] for n in names]
    source = GridStore.open(args.source, HOURLY, year, variables)
    report.step(
        f"Tiling {year}'s hours {args.first} to {args.last} of {len(names)} variables from {source.window.shape} over {args.box}'s {target.shape} into {args.out}"
    )
    try:
        out = GridStore.open(args.out, HOURLY, year, variables)
    except FileNotFoundError:
        out = GridStore.create(args.out, HOURLY, year, target, variables)
    if out.window != target:
        report.fail(str(args.out), f"its {year} store covers {out.window}, not {target}")
        return 1
    start = datetime(args.first.year, args.first.month, args.first.day, tzinfo=UTC)
    end = datetime(args.last.year, args.last.month, args.last.day, tzinfo=UTC) + timedelta(days=1)
    t0, t1 = source.index_of(start), source.index_of(end) if end.year == year else source.length
    blocks = [(k, min(k + BLOCK_HOURS, t1)) for k in range(t0, t1, BLOCK_HOURS)]
    total, done = len(blocks) * len(names), 0
    for name in names:
        for a, b in blocks:
            values = tiled(source.read_steps(name, a, b, dtype=np.float32), target.shape)
            out.write(source.time_of(a), {name: values}, source=None)
            out.set_sources(name, source.time_of(a), source.sources(name, a, b))
            done += 1
            report.detail(f"{name} {source.time_of(a):%Y-%m-%d %H}Z–{source.time_of(b - 1):%Y-%m-%d %H}Z")
            report.progress("blocks", done, total)
    out.mark_current(names)
    size = sum(p.stat().st_size for p in out.path.rglob("*") if p.is_file())
    return 0 if report.finish(f"{len(names)} variables, {t1 - t0} hours; the store is {size / 1e9:.1f} GB") else 1


if __name__ == "__main__":
    sys.exit(main())
