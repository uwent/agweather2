"""HRRR (noaa-hrrr-bdp-pds): hourly mean shortwave radiation and soil temperature, regridded to NDFD.

Checked 2026-10-27:
- Shortwave (D7): the hour ending at T is run T-1's sub-hourly file `wrfsubhf01`. Recent runs carry four 15-minute
  averages (`DSWRF:surface:0-15 min ave fcst` … `45-60`), whose mean is the hour's mean. 2016's carry only the
  instantaneous values at 15, 30, 45 and 60 min; their mean stands in (it shifts the hour about 7.5 minutes late,
  which doesn't change daily sums). `wrfsfc`'s DSWRF is instantaneous only.
- Soil temperature is in `wrfprs` (not `wrfsfc` or `wrfnat`), TSOIL at 0, 1, 4, 10, 30, 60, 100 cm; the analysis
  (f00) of run T gives the hour T. The potato model's 2 in and 4 in use the 4 and 10 cm levels.
HRRR's grid is a 3 km Lambert conformal grid in its own projection, so fields are interpolated (`agdata.regrid`),
not offset.
"""

import contextlib
from datetime import UTC, datetime, timedelta

import numpy as np
import requests

from agdata.catalog import variable
from agdata.grid import LambertGrid, Window
from agdata.regrid import regrid
from agdata.sources.grib import RemoteGrib
from agdata.units import convert

BUCKET = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"

HRRR_GRID = LambertGrid(
    name="HRRR CONUS 3 km",
    proj4="+proj=lcc +lon_0=262.5 +lat_0=38.5 +lat_1=38.5 +lat_2=38.5 +R=6371229 +units=m +no_defs",
    nx=1799,
    ny=1059,
    dx=3000.0,
    first_lat=21.138123,
    first_lon=237.280472,
)

SOIL_LEVELS = {"soil_temperature_4cm": "0.04-0.04 m below ground", "soil_temperature_10cm": "0.1-0.1 m below ground"}


def subhourly_url(run: datetime) -> str:
    t = run.astimezone(UTC)
    return f"{BUCKET}/hrrr.{t:%Y%m%d}/conus/hrrr.t{t:%H}z.wrfsubhf01.grib2"


def pressure_url(run: datetime) -> str:
    t = run.astimezone(UTC)
    return f"{BUCKET}/hrrr.{t:%Y%m%d}/conus/hrrr.t{t:%H}z.wrfprsf00.grib2"


def fetch_shortwave(hour_end: datetime, window: Window, session: requests.Session | None = None) -> np.ndarray:
    """Mean downward shortwave (W/m²) over the hour ending at `hour_end`, on the window.

    Raises FileNotFoundError when that run's sub-hourly file isn't published.
    """
    grib = RemoteGrib(subhourly_url(hour_end - timedelta(hours=1)), session)
    dswrf = grib.fields_where(lambda ref: ref.key == ("DSWRF", "surface"))
    averages = [field for ref, field in dswrf if " ave " in ref.detail]
    chosen = averages or [field for ref, field in dswrf if ref.detail.endswith("min fcst")]
    if len(chosen) != 4:
        raise ValueError(f"{grib.url}: expected 4 quarter-hour DSWRF fields, found {len(chosen)}")
    mean = np.mean([field.values for field in chosen], axis=0)
    return regrid(mean, HRRR_GRID, window)


def fetch_soil_temperature(
    hour: datetime, window: Window, session: requests.Session | None = None
) -> dict[str, np.ndarray]:
    """Soil temperature (°C) at the catalog's levels at `hour`, on the window."""
    grib = RemoteGrib(pressure_url(hour), session)
    wanted = {("TSOIL", level): name for name, level in SOIL_LEVELS.items()}
    fields = grib.fields(wanted)
    return {
        wanted[key]: convert(regrid(field.values, HRRR_GRID, window), "K", variable(wanted[key]).unit)
        for key, field in fields.items()
    }


def fetch_hour(hour_end: datetime, window: Window, session: requests.Session | None = None) -> dict[str, np.ndarray]:
    """Shortwave and soil temperature for an hour; a product whose file isn't published is left out."""
    if hour_end.tzinfo is None or hour_end.minute or hour_end.second:
        raise ValueError("pass a timezone-aware time on the hour")
    session = session or requests.Session()
    values: dict[str, np.ndarray] = {}
    with contextlib.suppress(FileNotFoundError):
        values["shortwave_radiation"] = fetch_shortwave(hour_end, window, session)
    with contextlib.suppress(FileNotFoundError):
        values.update(fetch_soil_temperature(hour_end, window, session))
    return values
