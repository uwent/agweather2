"""ACIS (Applied Climate Information System, https://www.rcc-acis.org/docs_webservices.html): station data from
NOAA's networks (COOP, ASOS, CoCoRaHS). `MultiStnData` gives every station's daily values in a box."""

from datetime import date
from pathlib import Path

import numpy as np

from agdata.clients.http import JsonClient

API = "https://data.rcc-acis.org"
INCH_MM = 25.4


class Acis(JsonClient):
    def __init__(self, cache_dir: Path | str | None = None, **kwargs):
        kwargs.setdefault("timeout_s", 120)
        super().__init__(API, cache_dir=cache_dir, **kwargs)

    def multi_station_daily(
        self, bbox: tuple[float, float, float, float], first: date, last: date, elements: tuple[str, ...]
    ) -> list[dict]:
        """Raw rows ({meta, data}) for every station in `bbox` (west, south, east, north), days first..last."""
        query = {
            "bbox": ",".join(f"{v:.2f}" for v in bbox),
            "sdate": str(first),
            "edate": str(last),
            "elems": [{"name": e} for e in elements],
            "meta": ["name", "ll", "sids"],
        }
        key = f"acis_{'-'.join(elements)}_{first}_{last}.json"
        return self.post("MultiStnData", query, cache_key=key)["data"]

    def precipitation_mm(self, bbox: tuple[float, float, float, float], first: date, last: date) -> list[dict]:
        """Each station's daily precip, mm (trace 0, missing or accumulated NaN): {name, ll, mm}."""
        stations = []
        for row in self.multi_station_daily(bbox, first, last, ("pcpn",)):
            values = [v[0] if isinstance(v, list) else v for v in row["data"]]
            stations.append(
                {
                    "name": row["meta"]["name"],
                    "ll": row["meta"].get("ll"),
                    "mm": np.array([precip_mm(v) for v in values]),
                }
            )
        return stations


def precip_mm(value: str) -> float:
    """An ACIS precip value in mm: "T" (trace) is 0; "M" (missing), "S" and "A" (part of an accumulation) are NaN;
    flags "a"/"b" are dropped."""
    if value == "T":
        return 0.0
    if value in ("M", "S") or value.endswith(("A", "S")):
        return np.nan
    return float(value.rstrip("ab")) * INCH_MM
