"""The correction of HRRR's shortwave against ground pyranometers (D48).

HRRR's hourly mean shortwave reads ~18% high against 80 Wisconet stations (docs/validation-pyranometers.md), and
more under cloud: about 1.10 in clear sky, 1.54 overcast. Each hour is scaled by a factor that depends on its
clearness (HRRR's value over the FAO-56 clear-sky Rso, `agdata.gaps`), from a table fitted on one year of Wisconet
and tested on the next (`scripts/fit_shortwave_correction.py`, docs/validation-shortwave-correction.md).

The archive keeps HRRR's raw value (`shortwave_radiation_hrrr`) and derives `shortwave_radiation` from it, so a
refit only bumps the version and re-derives (`correct_archive`). The table was fitted in Wisconsin; check it
against other networks before trusting it elsewhere.

NBM's forecast shortwave has its own tables (`correct_nbm_w_m2`), by lead day and the day's clearness, fitted on
the 2025 backtest against the corrected archive (`scripts/backtest_forecast.py --fit-shortwave`). They're mostly
calibration rather than bias: as skill falls with lead, a forecast very dark or very clear day is on average less
so, and the tables move it toward what was observed (test runs' day-5 MAE 4.2 → 3.1 MJ/m²).
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
NBM_TABLE_PATH = Path(__file__).parent / "data" / "nbm_shortwave_correction.json"
OPENMETEO_TABLE_PATH = Path(__file__).parent / "data" / "openmeteo_shortwave_correction.json"
RAW = "shortwave_radiation_hrrr"
BLOCK_HOURS = 48  # ~200 MB of float64 per block over Wisconsin
HOUR = timedelta(hours=1)


def _table() -> dict:
    return json.loads(TABLE_PATH.read_text())


TABLE = _table()
VERSION: int = TABLE["version"]
NBM_TABLE = json.loads(NBM_TABLE_PATH.read_text())
OPENMETEO_TABLE = json.loads(OPENMETEO_TABLE_PATH.read_text())  # D51, for points (`sources.openmeteo.correct`)


def correct_w_m2(hour_end, latitude_deg, longitude_deg, raw_w_m2, pressure_kpa, table: dict | None = None):
    """Hourly mean shortwave (time on axis 0) scaled by the factor for each hour's clearness: HRRR's by `TABLE`
    (D48) unless another source's table is given. Dark hours stay 0, and NaN stays NaN."""
    table = TABLE if table is None else table
    raw = np.asarray(raw_w_m2, dtype=float)
    rso = clear_sky_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, pressure_kpa)
    with np.errstate(invalid="ignore", divide="ignore"):
        clearness = np.where(rso > 1, raw / np.where(rso > 1, rso, 1), 0.0)
    factor = np.interp(clearness, table["clearness"], table["factor"])
    return np.where(np.isfinite(raw), np.maximum(raw * factor, 0.0), np.nan)


def lead_days(hour_end, longitude_deg, cycle: datetime) -> np.ndarray:
    """Each hour's lead in days: the whole days from the cycle to its solar day's noon, rounded (the 13z run's
    today is 0 and tomorrow 1; the 01z run's today is 1). Time on axis 0."""
    times = np.asarray(hour_end, dtype="datetime64[s]")
    extra = (1,) * np.ndim(longitude_deg)
    hours = (times.astype("int64") / 3600.0).reshape(-1, *extra)
    noon = (np.floor((hours - 0.5 + np.asarray(longitude_deg) / 15) / 24) + 0.5) * 24 - np.asarray(longitude_deg) / 15
    return np.rint((noon - cycle.timestamp() / 3600.0) / 24).astype(int)


def correct_nbm_w_m2(hour_end, latitude_deg, longitude_deg, hourly_w_m2, pressure_kpa, cycle: datetime) -> np.ndarray:
    """A forecast's hourly shortwave (from NBM's DSWRF by solar day, `agdata.interpolate`) scaled by the factor for
    its lead and its hour's clearness, which is its solar day's. Day 0 takes day 1's table; past the last, the
    last's."""
    sw = np.asarray(hourly_w_m2, dtype=float)
    rso = clear_sky_shortwave_w_m2(hour_end, latitude_deg, longitude_deg, pressure_kpa)
    with np.errstate(invalid="ignore", divide="ignore"):
        clearness = np.where(rso > 1, sw / np.where(rso > 1, rso, 1), 0.0)
    lead = np.broadcast_to(lead_days(hour_end, longitude_deg, cycle), sw.shape)
    factor = np.ones(sw.shape)
    groups = NBM_TABLE["lead_days"]
    for g, table in enumerate(NBM_TABLE["factor"]):
        first, last = min(groups[g]), max(groups[g])
        here = (lead >= (0 if g == 0 else first)) & (lead <= (10**6 if g == len(groups) - 1 else last))
        factor = np.where(here, np.interp(clearness, NBM_TABLE["clearness"], table), factor)
    return np.where(np.isfinite(sw), np.maximum(sw * factor, 0.0), np.nan)


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
