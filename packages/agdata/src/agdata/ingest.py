"""Ingest: fetch hours from the sources, QC them, derive RH and ET0, and write them to the hourly store.

One call handles a block of consecutive hours in one year (a backfill does a month at a time; the hourly job a
few hours). Each hour comes from URMA, or RTMA where URMA hasn't published it yet; precip from RTMA before URMA's
hourly precip begins (D23); shortwave and soil temperature from HRRR. Hours are range-checked and packed to int16
as they arrive, so a month of the window fits in memory; spikes are removed per variable over the whole block,
then RH and ET0 are derived. Gaps stay gaps (D25): estimates belong to the running totals. Every variable
records each hour's source.
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
from agdata.qc import check_range, remove_spikes
from agdata.sources import hrrr
from agdata.sources.rtma import RTMA
from agdata.sources.urma import URMA
from agdata.store import HOURLY, GridStore
from agmodels.weather import et0_hourly_series, relative_humidity_percent

logger = logging.getLogger(__name__)

ATTEMPTS = 3
RETRY_SECONDS = 5.0
HOUR = timedelta(hours=1)

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
    report = BlockReport(start, hours, {}, {}, {})
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

    # Spikes, over the block, for measured variables
    decoded: dict[str, np.ndarray] = {}
    for variable in HOURLY_VARIABLES:
        if variable.derived:
            continue
        values = variable.decode(packed[variable.name]).astype(np.float32)  # halves the block's memory
        if variable.spike_c is not None:
            # The stored hours on either side let the block's first and last hours be checked too
            padded = np.concatenate(
                [_stored_hour(store, start - HOUR, variable), values, _stored_hour(store, times[-1] + HOUR, variable)]
            )
            padded, report.spikes[variable.name] = remove_spikes(padded, variable.spike_c)
            values = padded[1:-1].astype(np.float32)
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


def refetch_precipitation(
    store: GridStore, start: datetime, hours: int, workers: int = 8, session_factory=requests.Session
) -> int:
    """Fetches only hourly precip again (URMA, else RTMA) for `hours` from `start` and writes it at the catalog's
    precision; hours neither has keep what they had. Returns the hours written. Precip files are small (about
    250 KB an hour), so this is cheap next to a full ingest."""
    variable = store.variables["precipitation"]
    t0 = store.index_of(start)
    values = store.read_steps("precipitation", t0, t0 + hours)
    sources = store.sources("precipitation")[t0 : t0 + hours]

    def one(n: int) -> None:
        session = _session(session_factory)
        when = start + n * HOUR
        for attempt in range(1, ATTEMPTS + 1):
            try:
                for source in (URMA, RTMA):
                    found = source.fetch_precip(when, store.window, session)
                    if found is not None:
                        values[n] = check_range(variable, found)[0]
                        sources[n] = source.name
                        return
                return
            except Exception as error:  # transient network errors; the hour keeps what it had after the last
                if attempt == ATTEMPTS:
                    logger.warning("refetching precip for %s failed %d times: %r", when, ATTEMPTS, error)
                    return
                time.sleep(RETRY_SECONDS * attempt)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, range(hours)))
    store.write(start, {"precipitation": values}, source=None)
    store.set_sources("precipitation", start, sources)
    return sum(1 for s in sources if s)


def stale_hours(
    data_dir: Path, window: Window, start: datetime, stop: datetime, urma_published: Callable[[datetime], bool]
) -> list[datetime]:
    """Hours ending in start..stop (exclusive) to fetch again: those without an analysis, precip or HRRR
    shortwave yet, and RTMA hours whose URMA has since been published (asked only for those)."""
    out = []
    by_year: dict[int, dict[str, list[str | None]]] = {}
    t = start
    while t < stop:
        if t.year not in by_year:
            store = open_or_create_hourly(data_dir, t.year, window)
            names = ("air_temperature", "precipitation", "shortwave_radiation")
            by_year[t.year] = {name: store.sources(name) for name in names}
        sources = by_year[t.year]
        n = int((t - datetime(t.year, 1, 1, tzinfo=UTC)) / HOUR)
        analysis = sources["air_temperature"][n]
        if None in (analysis, sources["precipitation"][n], sources["shortwave_radiation"][n]) or (
            analysis == "rtma" and urma_published(t)
        ):
            out.append(t)
        t += HOUR
    return out


def hour_runs(hours: list[datetime]) -> list[tuple[datetime, int]]:
    """Consecutive hours as (first, count) runs, each within one year (as `ingest_block` needs)."""
    runs: list[tuple[datetime, int]] = []
    for t in sorted(hours):
        if runs:
            first, n = runs[-1]
            if first + n * HOUR == t and t.year == first.year:
                runs[-1] = (first, n + 1)
                continue
        runs.append((t, 1))
    return runs


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


def _stored_hour(store: GridStore, when: datetime, variable: Variable) -> np.ndarray:
    """One stored hour beside a block, (1, y, x); NaN outside the store's year or where nothing is stored."""
    try:
        index = store.index_of(when)
    except IndexError:
        return np.full((1, *store.window.shape), np.nan, dtype=np.float32)
    return store.read_steps(variable.name, index, index + 1).astype(np.float32)


def _session(factory: Callable[[], requests.Session]) -> requests.Session:
    local = _session.__dict__.setdefault("local", threading.local())
    if not hasattr(local, "session"):
        local.session = factory()
    return local.session
