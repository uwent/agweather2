"""Ingest: fetch hours from the sources, QC them, derive RH and ET0, and write them to the hourly store.

One call handles a block of consecutive hours in one year (a backfill does a month at a time; the hourly job a
few hours). Each hour comes from URMA, or RTMA where URMA hasn't published it yet; precip from RTMA before URMA's
hourly precip begins (D23); shortwave and soil temperature from HRRR. Hours are range-checked and packed to int16
as they arrive, so a month of the window fits in memory; spikes and short gaps are handled per variable over the
whole block, then RH and ET0 are derived. Every variable records each hour's source.
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from agdata.catalog import FILL, VARIABLES, Variable
from agdata.grid import NDFD, Window
from agdata.qc import check_range, fill_short_gaps, remove_spikes
from agdata.sources import hrrr
from agdata.sources.rtma import RTMA
from agdata.sources.urma import URMA
from agdata.store import HOURLY, GridStore
from agmodels.weather import et0_hourly_series, relative_humidity_percent

logger = logging.getLogger(__name__)

ATTEMPTS = 3
RETRY_SECONDS = 5.0

# Every variable of the hourly store, in catalog order
HOURLY_VARIABLES: list[Variable] = list(VARIABLES.values())


@dataclass
class Hour:
    """One hour's fields over the window, in stored units, and which source gave each."""

    values: dict[str, np.ndarray] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)


Fetcher = Callable[[datetime, Window, requests.Session], Hour]


def fetch_hour(when: datetime, window: Window, session: requests.Session) -> Hour:
    """Everything the sources publish for the hour ending at `when` (analysis fields are instantaneous at it)."""
    hour = Hour()
    analysis = None
    for source in (URMA, RTMA):
        try:
            analysis = source.fetch_hour(when, window, session)
        except FileNotFoundError:
            continue
        for name, values in analysis.items():
            hour.values[name] = values
            hour.sources[name] = source.name
        break
    if "precipitation" not in hour.values:
        # URMA has no hourly precip before 2017-12-05, and lags RTMA's (D23)
        precip = RTMA.fetch_precip(when, window, session)
        if precip is not None:
            hour.values["precipitation"] = precip
            hour.sources["precipitation"] = RTMA.name
    for name, values in hrrr.fetch_hour(when, window, session).items():
        hour.values[name] = values
        hour.sources[name] = "hrrr"
    return hour


@dataclass
class BlockReport:
    start: datetime
    hours: int
    missing: dict[str, int]  # hours with no data, per variable
    out_of_range: dict[str, int]  # cells
    spikes: dict[str, int]
    filled: dict[str, int]  # cells interpolated
    failed: list[datetime] = field(default_factory=list)  # hours whose fetch failed after retries


def ingest_block(
    store: GridStore,
    start: datetime,
    hours: int,
    fetch: Fetcher = fetch_hour,
    workers: int = 8,
    session_factory: Callable[[], requests.Session] = requests.Session,
    progress: Callable[[int], None] | None = None,
) -> BlockReport:
    """Fetches, QCs, derives and writes `hours` consecutive hours from `start` (all within the store's year).
    `progress` is called with the number of hours fetched so far as each one finishes."""
    times = [start + timedelta(hours=n) for n in range(hours)]
    store.index_of(times[-1])  # the block must fit in the store's year
    window = store.window
    packed = {v.name: np.full((hours, *window.shape), FILL, dtype=np.int16) for v in HOURLY_VARIABLES}
    sources: dict[str, list[str | None]] = {v.name: [None] * hours for v in HOURLY_VARIABLES}
    report = BlockReport(start, hours, {}, {}, {}, {})
    done = 0
    done_lock = threading.Lock()

    def one(n: int) -> None:
        nonlocal done
        fetch_one(n)
        with done_lock:
            done += 1
            if progress is not None:
                progress(done)

    def fetch_one(n: int) -> None:
        session = _session(session_factory)
        for attempt in range(1, ATTEMPTS + 1):
            try:
                hour = fetch(times[n], window, session)
                break
            except Exception as error:  # network errors are usually transient; the hour stays missing after the last
                if attempt == ATTEMPTS:
                    logger.warning("fetching %s failed %d times: %r", times[n], ATTEMPTS, error)
                    report.failed.append(times[n])
                    return
                time.sleep(RETRY_SECONDS * attempt)
        for name, values in hour.values.items():
            variable = store.variables[name]
            cleaned, bad = check_range(variable, values)
            report.out_of_range[name] = report.out_of_range.get(name, 0) + bad
            packed[name][n] = variable.encode(cleaned)
            sources[name][n] = hour.sources[name]

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, range(hours)))

    # Spikes and short gaps, over the block, for measured variables
    decoded: dict[str, np.ndarray] = {}
    for variable in HOURLY_VARIABLES:
        if variable.derived:
            continue
        values = variable.decode(packed[variable.name]).astype(np.float32)  # halves the block's memory
        if variable.spike_c is not None:
            values, report.spikes[variable.name] = remove_spikes(values, variable.spike_c)
        if variable.fillable:
            values, filled = fill_short_gaps(values)
            report.filled[variable.name] = int(filled.sum())
        report.missing[variable.name] = sum(1 for s in sources[variable.name] if s is None)
        decoded[variable.name] = values

    # Derived variables
    decoded["relative_humidity"] = relative_humidity_percent(decoded["air_temperature"], decoded["dew_point"])
    lat, lon = NDFD.window_latlon(window)
    decoded["et0"] = et0_hourly_series(
        np.array([t.replace(tzinfo=None) for t in times], dtype="datetime64[s]"),
        lat,
        lon,
        decoded["air_temperature"],
        decoded["dew_point"],
        decoded["wind_speed"],
        decoded["surface_pressure"],
        decoded["shortwave_radiation"],
    )
    for name in ("relative_humidity", "et0"):
        sources[name] = ["derived" if np.isfinite(decoded[name][n]).any() else None for n in range(hours)]

    for variable in HOURLY_VARIABLES:
        cleaned, _ = check_range(variable, decoded[variable.name])
        store.write(start, {variable.name: cleaned}, source=None)
        store.set_sources(variable.name, start, sources[variable.name])
    return report


def open_or_create_hourly(data_dir: Path, year: int, window: Window) -> GridStore:
    try:
        store = GridStore.open(data_dir, HOURLY, year, HOURLY_VARIABLES)
    except FileNotFoundError:
        return GridStore.create(data_dir, HOURLY, year, window, HOURLY_VARIABLES)
    if store.window != window:
        raise ValueError(f"{store.path} covers {store.window}, not {window}; widening the box needs a rebuild")
    return store


def blocks(start: datetime, end: datetime, max_days: int = 31) -> list[tuple[datetime, int]]:
    """(block start, hours) between start and end (exclusive): calendar months (UTC), split into pieces of at
    most `max_days` so a block's arrays fit in memory (a month of the Wisconsin window needs about 12 GB in
    float64 at peak; 10 days in float32 about 2.5 GB)."""
    out = []
    t = start
    while t < end:
        next_month = datetime(t.year + (t.month == 12), t.month % 12 + 1, 1, tzinfo=UTC)
        stop = min(next_month, end, t + timedelta(days=max_days))
        out.append((t, int((stop - t) / timedelta(hours=1))))
        t = stop
    return out


def _session(factory: Callable[[], requests.Session]) -> requests.Session:
    local = _session.__dict__.setdefault("local", threading.local())
    if not hasattr(local, "session"):
        local.session = factory()
    return local.session
