"""Open-Meteo for points outside the box and before the archive (PLAN.md §7, Phase 4 E; D40, D42, D43).

Ported from WISP 3 (`app/services/weather/open_meteo.rb`, `grid.rb`). Points are snapped to the ECMWF O1280 grid's
cells (~9 km), so every point in a cell shares one series and one cache entry. Checked 2026-10-29 at 36.5° N,
97° W:
- Endpoints by date: `forecast` reaches 7 days back and 16 ahead (D43 keeps 11); `historical-forecast` has
  best_match from 2022 and NBM from some point between mid-2024 and mid-2025 (it had June 2025, not June 2024);
  `archive` (ERA5) the rest, soil included.
- Models (D40): `ncep_nbm_conus` first, `best_match` for what it lacks (pressure always; shortwave past ~2 days;
  hours its run doesn't have), soil from `ecmwf_ifs` (the only one with soil over North America), whose layers are
  0–7, 7–28 and 28–100 cm.
- Values at T are the hour ending T, as ours: precip and shortwave are the preceding hour's sum and mean.
Values are converted to the catalog's variables and units here; RH and ET0 are derived as the archive does them
(from T and Td, and our FAO-56), so a point outside the box agrees with one inside on method.
"""

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import numpy as np
import requests

from agmodels.weather import et0_hourly_series, relative_humidity_percent

HOSTS = {
    "forecast": ("api.open-meteo.com", "/v1/forecast"),
    "historical": ("historical-forecast-api.open-meteo.com", "/v1/forecast"),
    "archive": ("archive-api.open-meteo.com", "/v1/archive"),
}
HISTORICAL_FROM = date(2022, 1, 1)  # historical-forecast's best_match; earlier days come from the archive
RECENT_DAYS = 7  # the forecast endpoint's days back
FORECAST_DAYS = 12  # through the 11 days of D43, whole local days
PRIMARY_MODELS = ("ncep_nbm_conus", "best_match")
SOIL_MODEL = "ecmwf_ifs"
TIMEOUT = 60
HOUR = timedelta(hours=1)

# Open-Meteo variable → (catalog variable, factor to the stored unit)
VARIABLES: dict[str, tuple[str, float]] = {
    "temperature_2m": ("air_temperature", 1.0),
    "dew_point_2m": ("dew_point", 1.0),
    "precipitation": ("precipitation", 1.0),
    "wind_speed_10m": ("wind_speed", 1.0),  # asked for in m/s
    "wind_gusts_10m": ("wind_gust", 1.0),
    "wind_direction_10m": ("wind_direction", 1.0),
    "surface_pressure": ("surface_pressure", 0.1),  # hPa → kPa
    "cloud_cover": ("cloud_cover", 1.0),
    "shortwave_radiation": ("shortwave_radiation", 1.0),
}
SOIL_LAYERS = {  # layer → its middle, cm
    "soil_temperature_0_to_7cm": 3.5,
    "soil_temperature_7_to_28cm": 17.5,
    "soil_temperature_28_to_100cm": 64.0,
}
SOIL_DEPTHS = {"soil_temperature_4cm": 4.0, "soil_temperature_10cm": 10.0, "soil_temperature_30cm": 30.0}


@dataclass(frozen=True, kw_only=True)
class Cell:
    """An O1280 cell: requests are made at its centre."""

    latitude: float
    longitude: float
    ring: int  # 1 = northernmost
    index: int  # along the ring, from longitude 0

    @property
    def key(self) -> str:
        return f"o1280:{self.ring}:{self.index}"


@dataclass(kw_only=True)
class Hours:
    """Hours ending at `start`, `start` + 1 h, … at a cell, in catalog variables and stored units."""

    start: datetime
    values: dict[str, np.ndarray]
    sources: dict[str, str] = field(default_factory=dict)  # the model each variable mostly came from
    elevation_m: float | None = None

    @property
    def count(self) -> int:
        return len(next(iter(self.values.values()))) if self.values else 0


def endpoint_for(day: date, today: date) -> str:
    """Which endpoint serves a day: the forecast's 7 days back and ahead, historical-forecast from 2022, the archive
    before."""
    if day >= today - timedelta(days=RECENT_DAYS):
        return "forecast"
    return "historical" if day >= HISTORICAL_FROM else "archive"


def url(endpoint: str, api_key: str | None) -> str:
    host, path = HOSTS[endpoint]
    return f"https://{'customer-' if api_key else ''}{host}{path}"


def weight(variables: int, days: int) -> float:
    """Calls Open-Meteo counts for one location: more than 10 variables or 2 weeks counts as several."""
    return max(1.0, (variables / 10) * (days / 14))


def fetch(
    endpoint: str,
    cell: Cell,
    first: date,
    last: date,
    session: requests.Session | None = None,
    api_key: str | None = None,
) -> tuple[Hours, float]:
    """The hours ending in UTC days first..last (00Z … 23Z) at a cell from one endpoint, merged across the models
    in order; returns the hours and the calls Open-Meteo counts for them. The forecast endpoint reaches
    RECENT_DAYS back and FORECAST_DAYS ahead (`endpoint_for`)."""
    session = session or requests.Session()
    names = list(VARIABLES)
    start = datetime(first.year, first.month, first.day, tzinfo=UTC)  # the UTC day's hours end 00Z … 23Z
    n = ((last - first).days + 1) * 24
    days = (last - first).days + 1
    requests_made: list[tuple[str | None, list[str]]] = (
        [(None, [*names, *SOIL_LAYERS])]  # ERA5 has everything
        if endpoint == "archive"
        else [*((m, names) for m in PRIMARY_MODELS), (SOIL_MODEL, list(SOIL_LAYERS))]
    )
    merged: dict[str, np.ndarray] = {}
    chosen: dict[str, str] = {}
    elevation, calls = None, 0.0
    for model, variables in requests_made:
        params: dict[str, str | float] = {
            "latitude": round(cell.latitude, 6),
            "longitude": round(cell.longitude, 6),
            "hourly": ",".join(variables),
            "timezone": "GMT",  # dates are UTC days; the point's own zone comes from `agdata.timezones`
            "timeformat": "unixtime",
            "wind_speed_unit": "ms",
        }
        params |= {"start_date": first.isoformat(), "end_date": last.isoformat()}  # the forecast's too, within reach
        if model is not None:
            params["models"] = model
        if api_key:
            params["apikey"] = api_key
        body = _get(session, url(endpoint, api_key), params)
        calls += weight(len(variables), days)
        elevation = elevation if elevation is not None else body.get("elevation")
        times = np.asarray(body["hourly"]["time"], dtype=np.int64)
        for variable in variables:
            series = np.array([np.nan if v is None else v for v in body["hourly"].get(variable, [])], dtype=float)
            placed = _place(times, series, start, n)
            if variable in merged:
                gap = np.isnan(merged[variable]) & np.isfinite(placed)
                merged[variable] = np.where(gap, placed, merged[variable])
            else:
                merged[variable], gap = placed, np.isfinite(placed)
            if variable not in chosen and gap.any():
                chosen[variable] = model or "era5"  # the first model that gave it any hours
    return _to_catalog(merged, chosen, start, cell, elevation), calls


def cell_for(latitude: float, longitude: float) -> Cell:
    """The O1280 cell containing a point (Ben's R client's get_o1280_cells, via WISP 3's Weather::Grid): ring k
    from the nearest pole has 20 + 4(k − 1) evenly spaced points from longitude 0."""
    j = _ring_for(latitude)
    k = min(j, RINGS - j + 1)
    points = 20 + 4 * (k - 1)
    step = 360.0 / points
    i = round((longitude % 360) / step) % points
    centre = i * step
    if centre > 180:
        centre -= 360
    return Cell(latitude=_ring_latitude(j), longitude=centre, ring=j, index=i)


def _get(session: requests.Session, address: str, params: dict) -> dict:
    for attempt in range(3):
        try:
            response = session.get(address, params=params, timeout=TIMEOUT)
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"Open-Meteo {response.status_code}", response=response)
            if response.status_code != 200:
                reason = response.json().get("reason", "") if response.content else ""
                raise ValueError(f"Open-Meteo {response.status_code}: {reason}")
            return response.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def _place(times: np.ndarray, series: np.ndarray, start: datetime, n: int) -> np.ndarray:
    """A response's series onto the hours from `start` (unix times are the hour's end)."""
    out = np.full(n, np.nan)
    k = (times - int(start.timestamp())) // 3600
    inside = (k >= 0) & (k < n)
    out[k[inside]] = series[: len(k)][inside]
    return out


def _to_catalog(merged, chosen, start: datetime, cell: Cell, elevation) -> Hours:
    values: dict[str, np.ndarray] = {}
    sources: dict[str, str] = {}
    for variable, (name, factor) in VARIABLES.items():
        values[name] = merged[variable] * factor
        sources[name] = chosen.get(variable, "")
    middles = np.array(list(SOIL_LAYERS.values()))
    layers = np.stack([merged[v] for v in SOIL_LAYERS])
    for name, depth in SOIL_DEPTHS.items():
        # Between the two layers' middles around the depth (4 cm sits just below the top layer's middle)
        k = int(np.clip(np.searchsorted(middles, depth) - 1, 0, len(middles) - 2))
        w = (depth - middles[k]) / (middles[k + 1] - middles[k])
        values[name] = layers[k] * (1 - w) + layers[k + 1] * w
        sources[name] = chosen.get(list(SOIL_LAYERS)[k], "")
    values["relative_humidity"] = relative_humidity_percent(values["air_temperature"], values["dew_point"])
    times = np.array([(start + k * HOUR).replace(tzinfo=None) for k in range(len(values["air_temperature"]))])
    with np.errstate(invalid="ignore"):
        values["et0"] = et0_hourly_series(
            times.astype("datetime64[s]"),
            cell.latitude,
            cell.longitude,
            values["air_temperature"],
            values["dew_point"],
            values["wind_speed"],
            values["surface_pressure"],
            values["shortwave_radiation"],
        )
    sources["relative_humidity"] = sources["et0"] = "derived"
    return Hours(start=start, values=values, sources=sources, elevation_m=elevation)


# The O1280 grid (ECMWF's octahedral reduced Gaussian grid, N = 1280)
N = 1280
RINGS = 2 * N
_latitudes: dict[int, float] = {}


def _ring_for(latitude: float) -> int:
    guess = max(1, min(RINGS, round((90.0 - latitude) / 180.0 * (RINGS + 0.5) + 0.25)))
    for j in range(max(1, guess - 2), min(RINGS, guess + 2) + 1):
        if _edge(j, j + 1) < latitude <= _edge(j - 1, j):
            return j
    return guess


def _edge(north: int, south: int) -> float:
    if north < 1:
        return 90.0
    if south > RINGS:
        return -90.0
    return (_ring_latitude(north) + _ring_latitude(south)) / 2


def _ring_latitude(j: int) -> float:
    """The j-th largest root of the Legendre polynomial P_2N, by Newton's method from the asymptotic guess."""
    if j not in _latitudes:
        x = math.cos(math.pi * (j - 0.25) / (RINGS + 0.5))
        for _ in range(6):
            p_n, p_prev = _legendre(x)
            x -= p_n / (RINGS * (x * p_n - p_prev) / (x * x - 1))
        _latitudes[j] = math.degrees(math.asin(x))
    return _latitudes[j]


def _legendre(x: float) -> tuple[float, float]:
    p_prev, p_n = 1.0, x
    for k in range(1, RINGS):
        p_prev, p_n = p_n, ((2 * k + 1) * x * p_n - k * p_prev) / (k + 1)
    return p_n, p_prev
