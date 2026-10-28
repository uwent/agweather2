"""URMA hourly analyses from NOAA's Open Data bucket on AWS (noaa-urma-pds), for any hour since 2016.

The bucket's files changed over the years (checked 2026-10-27):

- Analysis until 2017-04-30: urma2p5.tHHz.2dvaranl_ndfd.grb2_ext, no .idx, a 2145 x 1597 grid (NDFD columns 200+)
- Analysis from 2017-05-01: urma2p5.tHHz.2dvaranl_ndfd.grb2_wexp, with .idx, the NDFD 2345 x 1597 grid
- Precip until 2017-12-04: 6-hour totals only, pcpurma_g184.YYYYMMDDHH.06h.grb2 (2145 x 1377, columns 200+)
- Precip 2017-12-05 to 2018-11-25: hourly, pcpurma_g184.YYYYMMDDHH.01h.grb2 (2145 x 1377, columns 200+)
- Precip from 2018-11-26: hourly, urma2p5.YYYYMMDDHH.pcp_01h.wexp.grb2 (NDFD)

All are in urma2p5.YYYYMMDD/. Precip files are named by the end of their accumulation. The older grids are
aligned sub-windows of NDFD (`grid.NDFD.offset_of`), so every era lands on the same cells. Values come back in
the catalog's SI units.
"""

from datetime import UTC, date, datetime

import numpy as np
import requests

from agdata.catalog import variable
from agdata.grid import Window
from agdata.sources.grib import Key, RemoteGrib, place
from agdata.units import convert

BUCKET = "https://noaa-urma-pds.s3.amazonaws.com"

WEXP_FROM = date(2017, 5, 1)
HOURLY_PRECIP_FROM = date(2017, 12, 5)
PRECIP_WEXP_FROM = date(2018, 11, 26)

# Analysis fields → (catalog variable, the GRIB unit as a units symbol)
ANALYSIS: dict[Key, tuple[str, str]] = {
    ("TMP", "2 m above ground"): ("air_temperature", "K"),
    ("DPT", "2 m above ground"): ("dew_point", "K"),
    ("WIND", "10 m above ground"): ("wind_speed", "m_s"),
    ("GUST", "10 m above ground"): ("wind_gust", "m_s"),
    ("WDIR", "10 m above ground"): ("wind_direction", "deg"),
    ("PRES", "surface"): ("surface_pressure", "Pa"),
    ("TCDC", "entire atmosphere (considered as a single layer)"): ("cloud_cover", "percent"),
}
PRECIP: Key = ("APCP", "surface")


def analysis_url(when: datetime) -> str:
    day = when.astimezone(UTC)
    suffix = "wexp" if day.date() >= WEXP_FROM else "ext"
    return f"{BUCKET}/urma2p5.{day:%Y%m%d}/urma2p5.t{day:%H}z.2dvaranl_ndfd.grb2_{suffix}"


def precip_url(when: datetime) -> str | None:
    """The hourly precip file for the hour ending at `when`, or None before hourly precip began."""
    end = when.astimezone(UTC)
    if end.date() < HOURLY_PRECIP_FROM:
        return None
    if end.date() < PRECIP_WEXP_FROM:
        return f"{BUCKET}/urma2p5.{end:%Y%m%d}/pcpurma_g184.{end:%Y%m%d%H}.01h.grb2"
    return f"{BUCKET}/urma2p5.{end:%Y%m%d}/urma2p5.{end:%Y%m%d%H}.pcp_01h.wexp.grb2"


def fetch_hour(when: datetime, window: Window, session: requests.Session | None = None) -> dict[str, np.ndarray]:
    """One hour's analysis (and precip, where hourly precip exists) over a window, in stored units.

    A field the file lacks is left out; cells a field doesn't cover are NaN.
    """
    if when.tzinfo is None or when.minute or when.second:
        raise ValueError("pass a timezone-aware time on the hour")
    session = session or requests.Session()
    values: dict[str, np.ndarray] = {}

    analysis = RemoteGrib(analysis_url(when), session)
    for key, field in analysis.fields(ANALYSIS).items():
        name, grib_unit = ANALYSIS[key]
        values[name] = convert(place(field, window), grib_unit, variable(name).unit)

    url = precip_url(when)
    if url:
        precip = RemoteGrib(url, session).fields([PRECIP]).get(PRECIP)
        if precip is not None:
            values["precipitation"] = convert(place(precip, window), "kg_m2", variable("precipitation").unit)
    return values
