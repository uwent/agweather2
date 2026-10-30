"""The correction of HRRR's shortwave against ground pyranometers (D48).

HRRR's hourly mean shortwave reads ~18% high against 80 Wisconet stations (docs/validation-pyranometers.md), and
more under cloud: about 1.10 in clear sky, 1.54 overcast. Each hour is scaled by a factor that depends on its
clearness (HRRR's value over the FAO-56 clear-sky Rso, `agdata.gaps`), from a table fitted on one year of Wisconet
and tested on the next (`scripts/fit_shortwave_correction.py`, docs/validation-shortwave-correction.md).

The archive keeps HRRR's raw value (`shortwave_radiation_hrrr`) and derives `shortwave_radiation` from it, so a
refit only bumps the version and re-derives (`correct_archive`). The table was fitted in Wisconsin; check it
against other networks before trusting it elsewhere.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from agdata.catalog import VARIABLES
from agdata.gaps import clear_sky_shortwave_w_m2
from agdata.grid import NDFD, Window
from agdata.store import HOURLY, GridStore
from agmodels.weather import et0_hourly_series

TABLE_PATH = Path(__file__).parent / "data" / "shortwave_correction.json"
RAW = "shortwave_radiation_hrrr"
FALLBACK_PRESSURE_KPA = 97.0  # Rso barely depends on it; used where an hour has no pressure
BLOCK_HOURS = 48  # ~200 MB of float64 per block over Wisconsin
HOUR = timedelta(hours=1)


def _table() -> dict:
    return json.loads(TABLE_PATH.read_text())


TABLE = _table()
VERSION: int = TABLE["version"]


def correct_w_m2(hour_end, latitude_deg, longitude_deg, raw_w_m2, pressure_kpa) -> np.ndarray:
    """HRRR hourly means (time on axis 0) scaled by the factor for each hour's clearness. Dark hours stay 0, and
    NaN stays NaN."""
    raw = np.asarray(raw_w_m2, dtype=float)
    pressure = np.where(np.isfinite(pressure_kpa), pressure_kpa, FALLBACK_PRESSURE_KPA)
    rso = clear_sky_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, pressure)
    with np.errstate(invalid="ignore", divide="ignore"):
        clearness = np.where(rso > 1, raw / np.where(rso > 1, rso, 1), 0.0)
    factor = np.interp(clearness, TABLE["clearness"], TABLE["factor"])
    return np.where(np.isfinite(raw), np.maximum(raw * factor, 0.0), np.nan)


def correct_archive(data_dir: Path, window: Window, log=print) -> list[int]:
    """Moves stored raw HRRR into `shortwave_radiation_hrrr` where a store predates it, then re-derives the
    corrected shortwave and ET0 from it wherever the store's shortwave is from another version. Returns the years
    changed (their days and running totals need rolling up again). Safe to rerun: the raw copy happens only while
    the store's shortwave is still the uncorrected version 1, and the rest derives from raw."""
    changed = []
    for path in sorted((data_dir / HOURLY.kind).glob("*.zarr")):
        year = int(path.stem)
        store = GridStore.open(data_dir, HOURLY, year, VARIABLES.values(), add_missing=True)
        if "shortwave_radiation" not in store.stale:
            continue
        stored: Any = store._array("shortwave_radiation").attrs.get("version", 1)
        stored_version = int(stored)
        first = datetime(year, 1, 1, tzinfo=UTC)
        steps = len(store.sources("shortwave_radiation"))
        if stored_version == 1:
            log(f"hourly/{year}: keeping raw HRRR shortwave")
            _copy_raw(store, first, steps)
        log(f"hourly/{year}: correcting shortwave and re-deriving ET0 (correction version {VERSION})")
        _derive(store, window, first, steps)
        store.mark_current(["shortwave_radiation"])
        changed.append(year)
    return changed


def _copy_raw(store: GridStore, first: datetime, steps: int) -> None:
    sources = store.sources("shortwave_radiation")
    raw_sources = store.sources(RAW)
    for t0 in range(0, steps, BLOCK_HOURS):
        t1 = min(steps, t0 + BLOCK_HOURS)
        todo = [k for k in range(t0, t1) if raw_sources[k] is None and sources[k] is not None]
        if not todo:
            continue
        values = store.read_steps("shortwave_radiation", t0, t1)
        store.write(first + t0 * HOUR, {RAW: values}, source=None)
        store.set_sources(RAW, first + t0 * HOUR, sources[t0:t1])


def _derive(store: GridStore, window: Window, first: datetime, steps: int) -> None:
    raw_sources = store.sources(RAW)
    lat, lon = NDFD.window_latlon(window)
    for t0 in range(0, steps, BLOCK_HOURS):
        t1 = min(steps, t0 + BLOCK_HOURS)
        if not any(raw_sources[t0:t1]):
            continue
        times = np.array([(first + k * HOUR).replace(tzinfo=None) for k in range(t0, t1)], dtype="datetime64[s]")
        read = {
            n: store.read_steps(n, t0, t1)
            for n in (RAW, "surface_pressure", "air_temperature", "dew_point", "wind_speed")
        }
        shortwave = correct_w_m2(times, lat, lon, read[RAW], read["surface_pressure"])
        with np.errstate(invalid="ignore"):
            et0 = et0_hourly_series(
                times,
                lat,
                lon,
                read["air_temperature"],
                read["dew_point"],
                read["wind_speed"],
                read["surface_pressure"],
                shortwave,
            )
        start = first + t0 * HOUR
        store.write(start, {"shortwave_radiation": shortwave, "et0": et0}, source=None)
        store.set_sources("shortwave_radiation", start, raw_sources[t0:t1])
        store.set_sources("et0", start, ["derived" if np.isfinite(et0[k]).any() else None for k in range(t1 - t0)])
