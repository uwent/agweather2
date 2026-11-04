"""Typical planting dates for a point: its county's where published, else its state's (D34).

`data/planting_dates.csv` is built once by `scripts/build_planting_dates.py` from two static sources: Deines et al.
(2023), the median over 2000–2020 of the days by which 10, 50 and 90% of each Corn Belt county's corn and soybean
area was planted (12 states, from Landsat); and USDA NASS's Usual Planting and Harvesting Dates (2010, from 1990–2009
crop progress), by state, the middle of the "most active" range (15–85% planted) and its ends. There are no live
sources (D34).

Potato comes from `data/potato_planting.csv` (`scripts/build_potato_planting.py`): the early, mid and late planting
dates UW Vegetable Pathology's newsletters give at Wisconsin's potato areas, averaged over 2020–2026. It's interim
(D64): served only within `POTATO_RADIUS_KM` of one of those places, until Phase 6's climatology estimates planting
on the grid. A crop growth model's default biofix is the typical date where it has one (its topic id is the crop
here), and the user can always set their own.
"""

import csv
import math
from dataclasses import dataclass
from functools import cache

from agdata.places import DATA, county_at

CROPS = ("corn", "soybean", "spring-wheat", "winter-wheat", "potato")
POTATO_RADIUS_KM = 40.0
SOURCES = {  # by a row's level
    "county": "Deines, J. M. et al. (2023), Remote Sensing of Environment 291, 113551 "
    "(https://doi.org/10.1016/j.rse.2023.113551; data CC BY 4.0, https://doi.org/10.5281/zenodo.7790257): "
    "median over 2000–2020",
    "location": "UW Vegetable Pathology, Vegetable Crop Updates (vegpath.plantpath.wisc.edu): early, mid and late "
    "planting dates by location in each season's early and late blight table, mean over 2020–2026",
    "state": "USDA NASS (2010), Usual Planting and Harvesting Dates for U.S. Field Crops, Agricultural Handbook 628: "
    "1990–2009 crop progress",
}


@dataclass(frozen=True, kw_only=True)
class PlantingDate:
    crop: str
    early: str  # MM-DD: Deines's 10% planted, NASS's start of most active (15%)
    typical: str  # 50% planted, or the middle of NASS's most active range
    late: str  # 90%, or the end of most active (85%); winter wheat's can fall in January
    level: str  # "county", "state" or "location" (potato: the nearest of Veg Path's places)
    area: str  # county FIPS code, state abbreviation or place name

    @property
    def source(self) -> str:
        return SOURCES[self.level]


@cache
def _table() -> dict[tuple[str, str], PlantingDate]:
    with (DATA / "planting_dates.csv").open() as f:
        return {
            (r["crop"], r["area"]): PlantingDate(
                crop=r["crop"], early=r["early"], typical=r["typical"], late=r["late"], level=r["level"], area=r["area"]
            )
            for r in csv.DictReader(f)
        }


def typical_planting(crop: str, latitude: float, longitude: float) -> PlantingDate | None:
    """The typical planting date for `crop` at a point, or None outside the lower 48 or where neither source has it."""
    if crop not in CROPS:
        raise ValueError(f"no planting dates for {crop!r}; known crops are {', '.join(CROPS)}")
    if crop == "potato":
        return _potato(latitude, longitude)
    county = county_at(latitude, longitude)
    if county is None:
        return None
    table = _table()
    return table.get((crop, county.geoid)) or table.get((crop, county.state))


@cache
def _potato_table() -> tuple[tuple[float, float, PlantingDate], ...]:
    with (DATA / "potato_planting.csv").open() as f:
        return tuple(
            (
                float(r["latitude"]),
                float(r["longitude"]),
                PlantingDate(
                    crop="potato",
                    early=r["early"],
                    typical=r["mid"],
                    late=r["late"],
                    level="location",
                    area=r["location"],
                ),
            )
            for r in csv.DictReader(f)
        )


def _potato(latitude: float, longitude: float) -> PlantingDate | None:
    """The nearest of Veg Path's potato places within `POTATO_RADIUS_KM`, or None."""
    found = min(_potato_table(), key=lambda row: _km(latitude, longitude, row[0], row[1]))
    return found[2] if _km(latitude, longitude, found[0], found[1]) <= POTATO_RADIUS_KM else None


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine, Earth radius 6371 km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))
