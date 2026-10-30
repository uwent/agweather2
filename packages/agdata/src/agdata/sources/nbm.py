"""NBM (National Blend of Models) forecasts from noaa-nbm-grib2-pds, on the NDFD grid (D2, D38).

Checked 2026-10-29 on the runs of 2026-10-28:
- `blend.YYYYMMDD/HH/core/blend.tHHz.core.fFFF.co.grib2` (+ `.idx`), a run every hour, published ~65 minutes after
  its cycle. The long runs (01, 07, 13, 19z; D38) have a file for every hour to f264 (11 days): every field hourly
  to f036 (f037-f048 lack DSWRF), then every 3 hours on synoptic valid times and, from about f192, every 6 hours;
  the other hours' files hold only 1-hour precip.
- Plain values have nothing after the time field in the `.idx`; their ensemble std dev and probability messages
  share the name, level and time, so they're told apart by what follows (`MessageRef.extra`).
- DSWRF isn't a value for the hour: it fits means over the 1 to 6 hours before the valid time, varying with lead
  (`agdata.interpolate.shortwave_hourly_w_m2` uses it by solar day). There's no surface pressure or soil temperature.
Each message is a whole CONUS field (0.8-1.9 MB), cropped to the window after decoding.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import requests

from agdata.catalog import variable
from agdata.grid import Window
from agdata.sources.grib import Key, MessageRef, RemoteGrib, place
from agdata.units import convert

BUCKET = "https://noaa-nbm-grib2-pds.s3.amazonaws.com"
LONG_CYCLES = (1, 7, 13, 19)  # UTC hours of the runs with hourly precip to the end (D38)
HORIZON_HOURS = 264
PUBLISH_LAG = timedelta(minutes=65)
HOUR = timedelta(hours=1)

# Fields at the valid time (DSWRF: a mean over hours before it) → (catalog variable, the GRIB unit as a units symbol)
FIELDS: dict[Key, tuple[str, str]] = {
    ("TMP", "2 m above ground"): ("air_temperature", "K"),
    ("DPT", "2 m above ground"): ("dew_point", "K"),
    ("WIND", "10 m above ground"): ("wind_speed", "m_s"),
    ("GUST", "10 m above ground"): ("wind_gust", "m_s"),
    ("WDIR", "10 m above ground"): ("wind_direction", "deg"),
    ("TCDC", "surface"): ("cloud_cover", "percent"),
    ("DSWRF", "surface"): ("shortwave_radiation", "W_m2"),
}
PRECIP: Key = ("APCP", "surface")
NAMES = (*(name for name, _ in FIELDS.values()), "precipitation")  # what a run holds


def url(cycle: datetime, lead: int) -> str:
    t = cycle.astimezone(UTC)
    return f"{BUCKET}/blend.{t:%Y%m%d}/{t:%H}/core/blend.t{t:%H}z.core.f{lead:03d}.co.grib2"


def long_cycles_before(now: datetime, count: int = 2) -> list[datetime]:
    """The newest `count` long-run cycles that could be published by `now`, newest first."""
    t = (now.astimezone(UTC) - PUBLISH_LAG).replace(minute=0, second=0, microsecond=0)
    found = []
    while len(found) < count:
        if t.hour in LONG_CYCLES:
            found.append(t)
        t -= HOUR
    return found


def latest_complete_cycle(now: datetime, session: requests.Session | None = None) -> datetime | None:
    """The newest long run whose last file is published (HEAD requests only), or None."""
    session = session or requests.Session()
    for cycle in long_cycles_before(now):
        if RemoteGrib(url(cycle, HORIZON_HOURS), session).exists():
            return cycle
    return None


def wanted(ref: MessageRef, lead: int) -> str | None:
    """The catalog variable a message gives at this lead, if it's one we read: plain values only."""
    if ref.extra:
        return None
    if ref.key in FIELDS and ref.detail == f"{lead} hour fcst":
        return FIELDS[ref.key][0]
    if ref.key == PRECIP and ref.detail == f"{lead - 1}-{lead} hour acc fcst":
        return "precipitation"
    return None


def fetch_step(
    cycle: datetime, lead: int, window: Window, session: requests.Session | None = None
) -> dict[str, np.ndarray]:
    """The fields one forecast file gives for its valid time, on the window, in stored units.

    Precip is the hour ending at the valid time. Raises FileNotFoundError when the file isn't published.
    """
    grib = RemoteGrib(url(cycle, lead), session)
    values: dict[str, np.ndarray] = {}
    for ref, found in grib.iter_fields_where(lambda ref: wanted(ref, lead) is not None):
        name = wanted(ref, lead)
        if name is None or name in values:
            continue
        unit = "kg_m2" if name == "precipitation" else FIELDS[ref.key][1]
        values[name] = convert(place(found, window), unit, variable(name).unit)
    return values


@dataclass(kw_only=True)
class Run:
    """One run's forecast over a window: each variable at every valid hour from cycle + 1 h, NaN where the run
    has no value for that hour (a step between its output times, or a file that failed)."""

    cycle: datetime
    values: dict[str, Any]  # (HORIZON_HOURS, y, x): arrays, or the zarr arrays `fetch_run` wrote to
    failed: list[int] = field(default_factory=list)  # leads whose file couldn't be read

    @property
    def valid_times(self) -> list[datetime]:
        return [self.cycle + (n + 1) * HOUR for n in range(HORIZON_HOURS)]


Step = Callable[[datetime, int, Window, requests.Session], dict[str, np.ndarray]]


def fetch_run(
    cycle: datetime,
    window: Window,
    step: Step = fetch_step,
    workers: int = 8,
    session_factory: Callable[[], requests.Session] = requests.Session,
    attempts: int = 3,
    out: dict[str, Any] | None = None,
) -> Run:
    """Every forecast hour of a long run, read in parallel; a file that fails after retries is left NaN.

    `out` takes the steps instead of arrays in memory: an array per name in NAMES, (HORIZON_HOURS, y, x), that
    threads can write different steps of at once (a zarr array chunked by step does)."""
    values: dict[str, Any] = (
        out
        if out is not None
        else {name: np.full((HORIZON_HOURS, *window.shape), np.nan, dtype=np.float32) for name in NAMES}
    )
    failed: list[int] = []

    def one(lead: int) -> None:
        session = session_factory()
        for attempt in range(1, attempts + 1):
            try:
                for name, field_values in step(cycle, lead, window, session).items():
                    values[name][lead - 1] = field_values
                return
            except (requests.RequestException, ValueError, FileNotFoundError):
                if attempt == attempts:
                    failed.append(lead)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, range(1, HORIZON_HOURS + 1)))
    return Run(cycle=cycle, values=values, failed=sorted(failed))


@dataclass(kw_only=True)
class HourlyRun:
    """A run filled to every hour: values and, per variable, which hours were filled between output steps."""

    cycle: datetime
    values: dict[str, np.ndarray]  # (HORIZON_HOURS, y, x), stored units
    filled: dict[str, np.ndarray]  # (HORIZON_HOURS, y, x) bool

    @property
    def valid_times(self) -> list[datetime]:
        return [self.cycle + (n + 1) * HOUR for n in range(HORIZON_HOURS)]


def to_hourly(run: Run, latitude_deg: np.ndarray, longitude_deg: np.ndarray, pressure_kpa) -> HourlyRun:
    """Fills each variable's hours between the run's output steps (`agdata.interpolate`). Dew point is kept at or
    below temperature; precip comes hourly from the long runs and is never filled (D25)."""
    from agdata import interpolate

    v = run.values
    out: dict[str, np.ndarray] = {}
    filled: dict[str, np.ndarray] = {}
    for name in ("air_temperature", "dew_point"):
        out[name], filled[name] = interpolate.pchip(v[name])
    for name in ("wind_speed", "wind_gust", "cloud_cover"):
        out[name], filled[name] = interpolate.linear(v[name])
    out["wind_direction"], filled["wind_direction"] = interpolate.direction_deg(v["wind_direction"])
    times = np.array([t.replace(tzinfo=None) for t in run.valid_times], dtype="datetime64[s]")
    out["shortwave_radiation"], filled["shortwave_radiation"] = interpolate.shortwave_hourly_w_m2(
        times, v["shortwave_radiation"], latitude_deg, longitude_deg, pressure_kpa
    )
    out["precipitation"] = np.asarray(v["precipitation"], dtype=float)
    filled["precipitation"] = np.zeros(out["precipitation"].shape, dtype=bool)
    with np.errstate(invalid="ignore"):
        out["dew_point"] = np.where(out["dew_point"] > out["air_temperature"], out["air_temperature"], out["dew_point"])
    return HourlyRun(cycle=run.cycle, values=out, filled=filled)
