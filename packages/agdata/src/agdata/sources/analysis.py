"""NDFD-grid hourly analyses (URMA and RTMA) from NOAA's Open Data buckets: shared reading for both.

Both products publish the same fields on the same grids, under names that changed the same way in 2017
(`_ext` files on a 2145-column grid, then `_wexp` on the full NDFD grid); `urma` and `rtma` describe each
product's files. Where a date sits near a change, the expected file is tried first, then the other naming.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

import numpy as np
import requests

from agdata.catalog import variable
from agdata.grid import Window
from agdata.sources.grib import Key, RemoteGrib, place
from agdata.units import convert

# Analysis fields → (catalog variable, the GRIB unit as a units symbol)
FIELDS: dict[Key, tuple[str, str]] = {
    ("TMP", "2 m above ground"): ("air_temperature", "K"),
    ("DPT", "2 m above ground"): ("dew_point", "K"),
    ("WIND", "10 m above ground"): ("wind_speed", "m_s"),
    ("GUST", "10 m above ground"): ("wind_gust", "m_s"),
    ("WDIR", "10 m above ground"): ("wind_direction", "deg"),
    ("PRES", "surface"): ("surface_pressure", "Pa"),
    ("TCDC", "entire atmosphere (considered as a single layer)"): ("cloud_cover", "percent"),
}
PRECIP: Key = ("APCP", "surface")


@dataclass(frozen=True)
class AnalysisSource:
    name: str  # store source name: urma, rtma
    bucket: str
    prefix: str  # urma2p5, rtma2p5
    wexp_from: date  # first day of the full NDFD grid's files
    precip_urls: Callable[[datetime], list[str]]  # candidate hourly precip files for the hour ending at a time

    def analysis_urls(self, when: datetime) -> list[str]:
        t = when.astimezone(UTC)
        base = f"{self.bucket}/{self.prefix}.{t:%Y%m%d}/{self.prefix}.t{t:%H}z.2dvaranl_ndfd.grb2_"
        first, second = ("wexp", "ext") if t.date() >= self.wexp_from else ("ext", "wexp")
        return [base + first, base + second]

    def fetch_hour(
        self, when: datetime, window: Window, session: requests.Session | None = None, precip: bool = True
    ) -> dict[str, np.ndarray]:
        """One hour's analysis (and hourly precip, where it exists) over a window, in stored units.

        Raises FileNotFoundError when the hour's analysis isn't published (yet). A field a file lacks is left
        out; cells a field doesn't cover are NaN.
        """
        if when.tzinfo is None or when.minute or when.second:
            raise ValueError("pass a timezone-aware time on the hour")
        session = session or requests.Session()
        values: dict[str, np.ndarray] = {}

        fields = _first_existing(self.analysis_urls(when), FIELDS, session)
        if fields is None:
            raise FileNotFoundError(f"no {self.name} analysis for {when:%Y-%m-%d %H}Z")
        for key, field in fields.items():
            name, grib_unit = FIELDS[key]
            values[name] = convert(place(field, window), grib_unit, variable(name).unit)

        if precip:
            found = _first_existing(self.precip_urls(when), [PRECIP], session)
            if found and PRECIP in found:
                rain = convert(place(found[PRECIP], window), "kg_m2", variable("precipitation").unit)
                values["precipitation"] = rain
        return values


def _first_existing(urls: list[str], keys, session: requests.Session):
    for url in urls:
        try:
            return RemoteGrib(url, session).fields(keys)
        except FileNotFoundError:
            continue
    return None
