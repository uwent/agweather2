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
from datetime import date
from functools import cache
from typing import TYPE_CHECKING

import numpy as np

from agdata.places import DATA, counties, county_at
from agmodels.runner import crop_models

if TYPE_CHECKING:
    from agdata.grid import Window
    from agmodels.spec import ModelSpec

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


TIERS = {"early": "early", "mid": "typical", "late": "late"}  # map and request words → `PlantingDate` fields


def planting_crop(spec: "ModelSpec") -> tuple[str, str] | None:
    """(the crop model a planting date runs, its crop in `agdata.planting`), or None if the model takes no planting:
    a disease's gating or anchoring crop model, or a crop model itself when its biofix is the planting."""
    crops = crop_models(spec)
    if crops:
        return crops[0], crops[0].removesuffix("-stages")
    if spec.group == "crop" and spec.biofix is not None and spec.biofix.label.lower().startswith("planting"):
        return spec.id, spec.topics[0]
    return None


def planting_map(crop: str, tier: str, window: "Window", season: int) -> np.ndarray:
    """Each cell's typical planting date for `crop` at `tier` (early, mid, late) in `season`, as date ordinals
    (float, NaN where there's none): its county's, else its state's; potato's from the nearest Veg Path place within
    POTATO_RADIUS_KM. A date before the early one falls in the next year (winter wheat's late, in January), as at a
    point (`api.runs`)."""
    days = _tier_days(crop, tier, window)
    out = np.full(window.shape, np.nan)
    for (month, day, next_year), cells in days.items():
        out[cells] = date(season + next_year, month, day).toordinal()
    return out


@cache
def _tier_days(crop: str, tier: str, window: "Window") -> dict[tuple[int, int, int], np.ndarray]:
    """(month, day, years after the season) → the cells planted then (boolean masks); cached per window."""
    if crop not in CROPS:
        raise ValueError(f"no planting dates for {crop!r}; known crops are {', '.join(CROPS)}")
    if tier not in TIERS:
        raise ValueError(f"tier is early, mid or late, not {tier!r}")
    from agdata.grid import NDFD
    from agdata.regions import cell_counties

    found: dict[int, PlantingDate | None] = {}
    if crop == "potato":
        lat, lon = NDFD.window_latlon(window)
        index = np.zeros(window.shape, dtype=int)
        best = np.full(window.shape, np.inf)
        rows = _potato_table()
        for k, (plat, plon, row) in enumerate(rows, start=1):
            km = _km_grid(lat, lon, plat, plon)
            closer = (km < best) & (km <= POTATO_RADIUS_KM)
            index[closer], best[closer] = k, km[closer]
            found[k] = row
        keys = index
    else:
        keys = cell_counties(window)
        table, names = _table(), counties()
        for k in np.unique(keys).tolist():
            county = names[k] if k else None
            found[k] = None if county is None else table.get((crop, county.geoid)) or table.get((crop, county.state))
    out: dict[tuple[int, int, int], np.ndarray] = {}
    for k, row in found.items():
        if row is None:
            continue
        month, day = (int(p) for p in getattr(row, TIERS[tier]).split("-"))
        early = tuple(int(p) for p in row.early.split("-"))
        when = (month, day, 1 if (month, day) < early else 0)
        cells = keys == k
        out[when] = out[when] | cells if when in out else cells
    return out


def _km_grid(lat: np.ndarray, lon: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    p1, p2 = np.radians(lat), math.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * math.cos(p2) * np.sin(np.radians(lon2 - lon) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))
