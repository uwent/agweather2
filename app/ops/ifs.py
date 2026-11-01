"""IFS's soil temperature and snow depth (D52, PLAN.md Phase 4 I): the archive's provisional hours after ERA5-Land's
last, and the forecast's.

Each new IFS run on Open-Meteo's open data is read once over the box, from the hour after ERA5-Land's last (at most
`LOOKBACK_DAYS` back) to the run's end: the past hours go into the archive marked `ifs` (never over ERA5-Land's, which
replaces them when it arrives), and every hour is kept in `ifs/latest.zarr`, where the forecast builds take their
soil and snow. The read takes minutes, so it runs outside the write lock.

IFS's soil is shifted to meet ERA5-Land's at the seam (`agdata.soil_seam`, Q23): each cell by the difference in
ERA5-Land's last hour, faded with the hours since. `ifs/latest.zarr` keeps the shifted hours with each cell's offset
(`{variable}_seam_offset`) and the seam's hour, so the raw values can be recovered. When ERA5-Land moves on, the same
run is read again against the new seam.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import zarr

from agdata import soil_seam
from agdata.grid import service_window
from agdata.ingest import SOIL, era5land_through, open_or_create_hourly, write_soil
from agdata.sources import era5land, ifs
from ops.era5land import land_mask, roll_up
from ops.locks import write_lock

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 14  # the provisional hours reach back at most this far (ERA5-Land is ~5 days behind)
HOUR = timedelta(hours=1)

Lock = Callable[[], AbstractContextManager[None]]


def seam_hour(data_dir: Path, box: str, now: datetime) -> datetime | None:
    """ERA5-Land's last hour in the archive, if it's within the last LOOKBACK_DAYS (else there's no seam to meet)."""
    window = service_window(box)
    floor = _floor(now)
    for year in (now.year, now.year - 1):
        through = era5land_through(open_or_create_hourly(data_dir, year, window))
        if through is not None:
            return through if through + HOUR >= floor else None
    return None


def _floor(now: datetime) -> datetime:
    return (now - timedelta(days=LOOKBACK_DAYS)).astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def last_read(data_dir: Path) -> tuple[str | None, str | None]:
    """The run and the seam the kept read was made against."""
    try:
        attrs = zarr.open_group(ifs.latest_path(data_dir), mode="r").attrs
    except FileNotFoundError:
        return None, None
    seam = attrs.get("seam")
    return str(attrs["run"]), str(seam) if seam is not None else None


def seam_offsets(data_dir: Path, window, seam: datetime, at_seam: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """ERA5-Land − IFS in the seam's hour, per cell (y, x), for each soil variable; NaN where either is missing."""
    store = open_or_create_hourly(data_dir, seam.year, window)
    t = store.index_of(seam)
    return {name: store.read_steps(name, t, t + 1)[0] - at_seam[name] for name in soil_seam.VARIABLES}


def apply_seam(hours: era5land.Hours, seam: datetime, offsets: dict[str, np.ndarray]) -> era5land.Hours:
    """The hours after the seam, their soil shifted by the offsets faded with the lead (`soil_seam.shift`)."""
    keep = [n for n, t in enumerate(hours.times) if t > seam]
    lead = np.array([(hours.times[n] - seam) / HOUR for n in keep])
    values = {}
    for name, v in hours.values.items():
        v = v[keep[0] :] if keep else v[:0]
        values[name] = soil_seam.shift(v, offsets[name], lead, name) if name in offsets else v
    return era5land.Hours(times=[hours.times[n] for n in keep], values=values)


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
    with lock():
        seam = seam_hour(data_dir, box, now)
    if last_read(data_dir) == (run.isoformat(), seam.isoformat() if seam else None):
        return False
    window = service_window(box)
    if key is None and not any((Path(data_dir) / "static").glob("era5land_land_*.npz")):
        logger.warning("IFS skipped: no land mask yet and no COPERNICUS_API_KEY to fetch one")
        return False
    land = land_mask(data_dir, window, key or "")
    end = ifs.run_end(info)
    if seam is not None:
        hours = ifs.read(seam, end, window, land, opener)  # from the seam's hour, to measure the step there
        with lock():
            offsets = seam_offsets(
                data_dir, window, seam, {name: hours.values[name][0] for name in soil_seam.VARIABLES}
            )
        hours = apply_seam(hours, seam, offsets)
        first = seam + HOUR
    else:
        first, offsets = _floor(now), {}
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
        ifs.save_latest(path, hours, run, seam=seam, offsets=offsets)
    covered = np.isfinite(hours.values[SOIL[0]]).any(axis=(1, 2))
    step = {
        name.removeprefix("soil_temperature_"): float(np.nanmean(o)) if np.isfinite(o).any() else float("nan")
        for name, o in offsets.items()
    }
    logger.info(
        "IFS %s: %d hours from %s (%d provisional), %d with values; seam %s, mean ERA5-Land − IFS %s",
        run,
        len(hours.times),
        first,
        len(past),
        int(covered.sum()),
        seam,
        {k: round(v, 2) for k, v in step.items()} or "none",
    )
    return True
