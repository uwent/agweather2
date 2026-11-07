"""The forecast's calibration against the archive (D39, D49), fitted by `scripts/backtest_forecast.py
--fit-calibration` on the 2025 backtest and applied in `forecast.adjust_hours`:

- `max_offset`: NBM's TMAX less the archive's daily max (the warmest top-of-hour value), by season, interpolated
  through the year between mid-season days. Fitted on lead days 1–3 and applied at every lead.
- `night_min`: the hours' warm bias at each night's min (00–12Z) by hours from the cycle to 12Z: interpolation
  between NBM's steps rounds off the coldest hours.
- `rh_map`: quantile maps from the forecast's hourly RH to the archive's, by season, lead and solar hour (D49):
  NBM's blended humidity rarely saturates, so it counts too few humid hours. Each hour's map is blended from the
  neighbouring seasons (by day of year, around the year's end), leads and solar hours, so nothing steps in time
  or across a map. Temperature is kept and the dew point recomputed.

Each table is a small JSON file in `agdata/data`; a missing file leaves its step out.
"""

import json
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from agdata import interpolate
from agmodels.weather import dew_point_from_rh_c, relative_humidity_percent

DATA = Path(__file__).parent / "data"
MAX_OFFSET_PATH = DATA / "nbm_max_offset.json"
NIGHT_MIN_PATH = DATA / "nbm_night_min.json"
RH_MAP_PATH = DATA / "nbm_rh_map.json"
OPENMETEO_RH_MAP_PATH = DATA / "openmeteo_rh_map.json"  # for points from Open-Meteo (D51), one lead group
HOUR = timedelta(hours=1)
NIGHT_END_HOUR = 12  # UTC: NBM's TMIN window, 00–12Z, the night before a Central-time day


@dataclass(kw_only=True, frozen=True)
class Adjustments:
    """Which calibration tables to apply; None leaves a step out."""

    max_offset: dict | None = None
    night_min: dict | None = None
    rh_map: dict | None = None


def fitted() -> Adjustments:
    def read(path: Path) -> dict | None:
        return json.loads(path.read_text()) if path.exists() else None

    return Adjustments(max_offset=read(MAX_OFFSET_PATH), night_min=read(NIGHT_MIN_PATH), rh_map=read(RH_MAP_PATH))


def max_offset_c(valid_times: list[datetime], table: dict) -> np.ndarray:
    """The offset at each valid hour's day of year, linear between the table's days and around the year's end."""
    days = np.array(table["day_of_year"], dtype=float)
    offsets = np.array(table["offset_c"], dtype=float)
    doy = np.array([t.timetuple().tm_yday for t in valid_times], dtype=float)
    return np.interp(doy, np.concatenate([days - 365, days, days + 365]), np.tile(offsets, 3))


def max_targets(valid_times: list[datetime], tmax_c: np.ndarray, table: dict | None) -> np.ndarray:
    """NBM's 12-hour max (at the steps that end a window, NaN elsewhere) less the season's offset."""
    if table is None:
        return tmax_c
    shape = (-1, *([1] * (np.ndim(tmax_c) - 1)))
    return tmax_c - max_offset_c(valid_times, table).reshape(shape)


def night_min_targets(
    cycle: datetime, valid_times: list[datetime], temperature_c: np.ndarray, table: dict
) -> np.ndarray:
    """Each night's target min at its last hour (12Z; NaN elsewhere): the hours' min over the 12 hours ending
    there, less the warm bias for its hours from the cycle (linear between the table's leads, held at its ends)."""
    out = np.full(np.shape(temperature_c), np.nan)
    window = interpolate.WINDOW_HOURS
    for k, valid in enumerate(valid_times):
        if valid.hour != NIGHT_END_HOUR or k < window - 1:
            continue
        bias = np.interp((valid - cycle) // HOUR, table["lead_hours"], table["warm_bias_c"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells
            out[k] = np.nanmin(temperature_c[k - window + 1 : k + 1], axis=0) - bias
    return out


def solar_hour(valid: datetime, longitude_deg) -> np.ndarray:
    """Local solar time at the end of the hour ending `valid` (hours, 0–24), by longitude."""
    return (valid.hour + valid.minute / 60 + np.asarray(longitude_deg, dtype=float) / 15) % 24


def season_index(valid: datetime) -> int:
    """The table's season for a valid time: 0 DJF, 1 MAM, 2 JJA, 3 SON (for fitting)."""
    return (valid.month % 12) // 3


def lead_index(cycle: datetime, valid: datetime, table: dict) -> int:
    """The lead group a valid time falls in (for fitting): groups end at the table's `lead_group_ends`."""
    return int(np.searchsorted(table["lead_group_ends"], (valid - cycle) // HOUR, side="left"))


def _neighbours(x: np.ndarray, centers, period: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """For each `x`, the two table entries around it and their weights, (n, 2) each: linear, held at the ends (an
    end's own entry twice, weights 1 and 0), or around `period`."""
    c = np.asarray(centers, dtype=float)
    x = np.asarray(x, dtype=float)
    if period is not None:
        k = np.searchsorted(c, x % period, side="right") - 1  # -1: before the first, so after the last
        lo, hi = k % len(c), (k + 1) % len(c)
        span = (c[hi] - c[lo]) % period
        span = np.where(span == 0, period, span)
        w = ((x - c[lo]) % period) / span
        return np.stack([lo, hi], axis=1), np.stack([1 - w, w], axis=1)
    if len(c) == 1:
        zero = np.zeros(x.shape, dtype=int)
        return np.stack([zero, zero], axis=1), np.stack([np.ones(x.shape), np.zeros(x.shape)], axis=1)
    k = np.clip(np.searchsorted(c, x, side="right") - 1, 0, len(c) - 2)
    w = np.clip((x - c[k]) / (c[k + 1] - c[k]), 0.0, 1.0)  # held at the ends
    return np.stack([k, k + 1], axis=1), np.stack([1 - w, w], axis=1)


MAP_BLOCK = 2_000_000  # values mapped at once (hours × cells): ~16 MB a temporary


def map_rh(cycle: datetime, valid_times: list[datetime], longitude_deg, rh_percent: np.ndarray, table: dict):
    """Hourly RH (time on axis 0) through the table's maps, each hour's map blended as the module says: between
    the two seasons and the two lead groups around it, and the two solar-hour bins and RH grid points around each
    value. The blend is linear, so each term is looked up and weighted, for many hours at once."""
    maps = np.asarray(table["map"], dtype=float)  # (season, lead, solar hour, RH grid)
    grid = np.asarray(table["rh_grid"], dtype=float)  # 0, 1, …, 100
    out = np.array(rh_percent, dtype=float)
    n = len(valid_times)
    if n == 0:
        return out
    doy = np.array([v.timetuple().tm_yday + v.hour / 24 for v in valid_times])
    lead = np.array([(v - cycle) // HOUR for v in valid_times], dtype=float)
    clock = np.array([v.hour + v.minute / 60 for v in valid_times])
    season, season_w = _neighbours(doy, table["season_day_of_year"], period=365)
    group, group_w = _neighbours(lead, table["lead_hours"])
    lon = np.asarray(longitude_deg, dtype=float)
    cells = max(1, int(np.prod(out.shape[1:])))
    step = max(1, MAP_BLOCK // cells)
    for a in range(0, n, step):
        b = min(a + step, n)
        rh = out[a:b]
        axes = (b - a, *([1] * (rh.ndim - 1)))
        hour = np.broadcast_to((clock[a:b].reshape(axes) + lon / 15) % 24 - 0.5, rh.shape)  # bins centred on h + 0.5
        h0 = np.floor(hour).astype(int) % 24
        wh = hour - np.floor(hour)
        h1 = (h0 + 1) % 24
        x = np.clip(np.nan_to_num(rh), grid[0], grid[-1])
        i0 = np.clip(np.floor(x).astype(int), 0, len(grid) - 2)
        f = x - grid[i0]
        mapped = np.zeros(rh.shape)
        for p in range(2):
            for q in range(2):
                w = (season_w[a:b, p] * group_w[a:b, q]).reshape(axes)
                m = (season[a:b, p].reshape(axes), group[a:b, q].reshape(axes))
                lower = (1 - f) * maps[(*m, h0, i0)] + f * maps[(*m, h0, i0 + 1)]
                upper = (1 - f) * maps[(*m, h1, i0)] + f * maps[(*m, h1, i0 + 1)]
                mapped += w * ((1 - wh) * lower + wh * upper)
        out[a:b] = np.where(np.isfinite(rh), mapped, np.nan)
    return out


def map_humidity(cycle: datetime, valid_times: list[datetime], longitude_deg, temperature_c, dew_point_c, table):
    """The dew point after mapping the hours' RH (`map_rh`), temperature kept."""
    rh = relative_humidity_percent(temperature_c, dew_point_c)
    mapped = map_rh(cycle, valid_times, longitude_deg, rh, table)
    with np.errstate(invalid="ignore"):
        return np.fmin(dew_point_from_rh_c(temperature_c, mapped), temperature_c)
