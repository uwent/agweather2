"""Typical planting dates for a point: its county's where published, else its state's (D34).

`data/planting_dates.csv` is built once by `scripts/build_planting_dates.py` from two static sources: Deines et al.
(2023), the median over 2000–2020 of the days by which 10, 50 and 90% of each Corn Belt county's corn and soybean
area was planted (12 states, from Landsat); and USDA NASS's Usual Planting and Harvesting Dates (2010, from 1990–2009
crop progress), by state, the middle of the "most active" range (15–85% planted) and its ends. There are no live
sources (D34). A crop growth model's default biofix is the typical date where it has one (its topic id is the crop
here), and the user can always set their own.
"""

import csv
from dataclasses import dataclass
from functools import cache

from agdata.places import DATA, county_at

CROPS = ("corn", "soybean", "spring-wheat", "winter-wheat")
SOURCES = {  # by a row's level
    "county": "Deines, J. M. et al. (2023), Remote Sensing of Environment 291, 113551 "
    "(https://doi.org/10.1016/j.rse.2023.113551; data CC BY 4.0, https://doi.org/10.5281/zenodo.7790257): "
    "median over 2000–2020",
    "state": "USDA NASS (2010), Usual Planting and Harvesting Dates for U.S. Field Crops, Agricultural Handbook 628: "
    "1990–2009 crop progress",
}


@dataclass(frozen=True)
class PlantingDate:
    crop: str
    early: str  # MM-DD: Deines's 10% planted, NASS's start of most active (15%)
    typical: str  # 50% planted, or the middle of NASS's most active range
    late: str  # 90%, or the end of most active (85%); winter wheat's can fall in January
    level: str  # "county" or "state"
    area: str  # county FIPS code or state abbreviation

    @property
    def source(self) -> str:
        return SOURCES[self.level]


@cache
def _table() -> dict[tuple[str, str], PlantingDate]:
    with (DATA / "planting_dates.csv").open() as f:
        return {
            (r["crop"], r["area"]): PlantingDate(r["crop"], r["early"], r["typical"], r["late"], r["level"], r["area"])
            for r in csv.DictReader(f)
        }


def typical_planting(crop: str, latitude: float, longitude: float) -> PlantingDate | None:
    """The typical planting date for `crop` at a point, or None outside the lower 48 or where neither source has it."""
    if crop not in CROPS:
        raise ValueError(f"no planting dates for {crop!r}; known crops are {', '.join(CROPS)}")
    county = county_at(latitude, longitude)
    if county is None:
        return None
    table = _table()
    return table.get((crop, county.geoid)) or table.get((crop, county.state))
