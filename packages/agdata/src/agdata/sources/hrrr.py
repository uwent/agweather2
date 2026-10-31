"""HRRR (noaa-hrrr-bdp-pds): hourly mean shortwave radiation, regridded to NDFD.

Checked 2026-10-27:
- Shortwave (D7): the hour ending at T is run T-1's sub-hourly file `wrfsubhf01`. Recent runs carry four 15-minute
  averages (`DSWRF:surface:0-15 min ave fcst` … `45-60`), whose mean is the hour's mean. 2016's carry only the
  instantaneous values at 15, 30, 45 and 60 min; their mean stands in (it shifts the hour about 7.5 minutes late,
  which doesn't change daily sums). `wrfsfc`'s DSWRF is instantaneous only.
- Soil temperature (TSOIL in `wrfprs`) was read here until D52: under its own snow HRRR's shallow soil swings
  with the air (docs/validation-soil.md), so soil and snow now come from ERA5-Land and IFS.
HRRR's grid is a 3 km Lambert conformal grid in its own projection, so fields are interpolated (`agdata.regrid`),
not offset.
"""

import contextlib
from datetime import UTC, datetime, timedelta

import numpy as np
import requests

from agdata.grid import LambertGrid, Window
from agdata.regrid import regrid
from agdata.sources.grib import RemoteGrib

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


def subhourly_url(run: datetime) -> str:
    t = run.astimezone(UTC)
    return f"{BUCKET}/hrrr.{t:%Y%m%d}/conus/hrrr.t{t:%H}z.wrfsubhf01.grib2"


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


def fetch_hour(hour_end: datetime, window: Window, session: requests.Session | None = None) -> dict[str, np.ndarray]:
    """Shortwave for an hour; left out when its file isn't published."""
    if hour_end.tzinfo is None or hour_end.minute or hour_end.second:
        raise ValueError("pass a timezone-aware time on the hour")
    session = session or requests.Session()
    values: dict[str, np.ndarray] = {}
    with contextlib.suppress(FileNotFoundError):
        values["shortwave_radiation"] = fetch_shortwave(hour_end, window, session)
    return values
