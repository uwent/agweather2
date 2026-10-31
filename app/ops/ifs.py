"""IFS's soil temperature and snow depth (D52, PLAN.md Phase 4 I): the archive's provisional hours after ERA5-Land's
last, and the forecast's.

Each new IFS run on Open-Meteo's open data is read once over the box, from the hour after ERA5-Land's last (at most
`LOOKBACK_DAYS` back) to the run's end: the past hours go into the archive marked `ifs` (never over ERA5-Land's, which
replaces them when it arrives), and every hour is kept in `ifs/latest.zarr`, where the forecast builds take their
soil and snow. The read takes minutes, so it runs outside the write lock.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import zarr

from agdata.grid import service_window
from agdata.ingest import SOIL, era5land_through, open_or_create_hourly, write_soil
from agdata.sources import era5land, ifs
from ops.era5land import land_mask, roll_up
from ops.locks import write_lock

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 14  # the provisional hours reach back at most this far (ERA5-Land is ~5 days behind)
HOUR = timedelta(hours=1)

Lock = Callable[[], AbstractContextManager[None]]


def provisional_from(data_dir: Path, box: str, now: datetime) -> datetime:
    """The first hour without ERA5-Land, within the last LOOKBACK_DAYS."""
    window = service_window(box)
    floor = (now - timedelta(days=LOOKBACK_DAYS)).astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    for year in (now.year, now.year - 1):
        through = era5land_through(open_or_create_hourly(data_dir, year, window))
        if through is not None:
            return max(through + HOUR, floor)
    return floor


def last_read_run(data_dir: Path) -> str | None:
    try:
        return str(zarr.open_group(ifs.latest_path(data_dir), mode="r").attrs["run"])
    except FileNotFoundError:
        return None


def refresh_ifs(
    data_dir: Path,
    box: str,
    now: datetime,
    key: str | None,
    opener: ifs.Opener | None = None,
    meta: Callable[[], dict] | None = None,
    lock: Lock | None = None,
) -> bool:
    """Reads the newest IFS run if it hasn't been read, writes its provisional hours and keeps its forecast hours;
    returns whether it did. `key` (the CDS's) is needed only if the land mask hasn't been downloaded yet."""
    if opener is None or meta is None:
        opener, meta = ifs.s3_opener()
    lock = lock or (lambda: write_lock(data_dir))
    info = meta()
    run = datetime.fromtimestamp(info["last_run_initialisation_time"], UTC)
    if last_read_run(data_dir) == run.isoformat():
        return False
    window = service_window(box)
    if key is None and not any((Path(data_dir) / "static").glob("era5land_land_*.npz")):
        logger.warning("IFS skipped: no land mask yet and no COPERNICUS_API_KEY to fetch one")
        return False
    land = land_mask(data_dir, window, key or "")
    with lock():
        first = provisional_from(data_dir, box, now)
    end = ifs.run_end(info)
    hours = ifs.read(first, end, window, land, opener)
    stop = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    past = [n for n, t in enumerate(hours.times) if t <= stop]
    with lock():
        if past:
            observed = era5land.Hours(
                times=hours.times[: past[-1] + 1],
                values={name: values[: past[-1] + 1] for name, values in hours.values.items()},
            )
            for year in sorted({t.year for t in observed.times}):
                write_soil(open_or_create_hourly(data_dir, year, window), observed, "ifs")
            roll_up(data_dir, window, observed.times[0].date(), observed.times[-1].date())
        path = ifs.latest_path(data_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        ifs.save_latest(path, hours, run)
    covered = np.isfinite(hours.values[SOIL[0]]).any(axis=(1, 2))
    logger.info(
        "IFS %s: %d hours from %s (%d provisional), %d with values",
        run,
        len(hours.times),
        first,
        len(past),
        int(covered.sum()),
    )
    return True
