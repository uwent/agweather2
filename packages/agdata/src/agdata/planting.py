"""Typical planting dates for a point: its county's where published, else its state's (D34).

`data/planting_dates.csv` is built once by `scripts/build_planting_dates.py` from two static sources: Deines et al.
(2023), the median over 2000–2020 of the days by which 10, 50 and 90% of each Corn Belt county's corn and soybean
area was planted (12 states, from Landsat); and USDA NASS's Usual Planting and Harvesting Dates (2010, from 1990–2009
crop progress), by state, the middle of the "most active" range (15–85% planted) and its ends. There are no live
sources (D34).

Potato's are estimated for each grid cell from its normal last spring freeze (`agdata.potatoplanting`), fitted to the
dates UW Vegetable Pathology's newsletters give at Wisconsin's potato areas, 2020–2026: a point's are its cell's and a
map's each cell's own, read from the normals in the data folder the caller passes. A crop growth model's default
biofix is the typical date where it has one (its topic id is the crop here), and the user can always set their own.
"""

import csv
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from agdata.places import DATA, counties, county_at
from agmodels.runner import crop_models

if TYPE_CHECKING:
    from agdata.grid import Window
    from agmodels.spec import ModelSpec

CROPS = ("corn", "soybean", "spring-wheat", "winter-wheat", "potato")
SOURCES = {  # by a row's level
    "county": "Deines, J. M. et al. (2023), Remote Sensing of Environment 291, 113551 (https://doi.org/10.1016/j.rse.2023.113551; data CC BY 4.0, https://doi.org/10.5281/zenodo.7790257): median over 2000–2020",
    "cell": "Estimated for the grid cell from the 30-year normal date of the last spring freeze at 28 °F averaged over the area within about 30 miles (nearer places counting more), by the days before and after it that fit the planting dates in UW Vegetable Pathology's Vegetable Crop Updates (vegpath.plantpath.wisc.edu) at seven Wisconsin potato areas, 2020–2026",
    "state": "USDA NASS (2010), Usual Planting and Harvesting Dates for U.S. Field Crops, Agricultural Handbook 628: 1990–2009 crop progress",
}


@dataclass(frozen=True, kw_only=True)
class PlantingDate:
    crop: str
    early: str  # MM-DD: Deines's 10% planted, NASS's start of most active (15%)
    typical: str  # 50% planted, or the middle of NASS's most active range
    late: str  # 90%, or the end of most active (85%); winter wheat's can fall in January
    level: str  # "county", "state" or "cell" (potato: estimated for the grid cell, `agdata.potatoplanting`)
    area: str  # county FIPS code, state abbreviation, or the cell's grid indices as "j,i"

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


def typical_planting(crop: str, latitude: float, longitude: float, data_dir: Path | None) -> PlantingDate | None:
    """The typical planting date for `crop` at a point, or None outside the lower 48 or where neither source has it
    (potato: where the grid's normals in `data_dir` don't reach, or without one)."""
    if crop not in CROPS:
        raise ValueError(f"no planting dates for {crop!r}; known crops are {', '.join(CROPS)}")
    if crop == "potato":
        return _potato(latitude, longitude, data_dir)
    county = county_at(latitude, longitude)
    if county is None:
        return None
    table = _table()
    return table.get((crop, county.geoid)) or table.get((crop, county.state))


def _potato(latitude: float, longitude: float, data_dir: Path | None) -> PlantingDate | None:
    """The point's cell's estimate (`agdata.potatoplanting`), or None."""
    from agdata import potatoplanting
    from agdata.grid import NDFD

    cell = NDFD.cell_of(latitude, longitude)
    if cell is None or data_dir is None:
        return None
    found = potatoplanting.at(data_dir, *cell)
    if found is None:
        return None
    return PlantingDate(
        crop="potato",
        early=found["early"],
        typical=found["mid"],
        late=found["late"],
        level="cell",
        area=f"{cell[0]},{cell[1]}",
    )


TIERS = {"early": "early", "mid": "typical", "late": "late"}  # map and request words → `PlantingDate` fields


def planting_crop(spec: "ModelSpec") -> tuple[str, str] | None:
    """(the crop model a planting date runs, its crop in `agdata.planting`), or None if the model takes no planting:
    a disease's gating or anchoring crop model, or a crop model itself when its biofix is the planting."""
    crops = crop_models(spec)
    if crops:
        crop = crops[0].removesuffix("-stages")
        # a perennial's stages (apple) count from January 1, not from a planting
        return (crops[0], crop) if crop in CROPS else None
    if spec.group == "crop" and spec.biofix is not None and spec.biofix.label.lower().startswith("planting"):
        return spec.id, spec.topics[0]
    return None


def map_crop(spec: "ModelSpec") -> tuple[str, str] | None:
    """`planting_crop` for a model's map: None for a gate that runs only from a planting date the user gives
    (`Susceptibility.planting_given_only`: wheat scab's map is for all wheat, its gate spring wheat's stages)."""
    gate = spec.susceptible
    if gate is not None and gate.planting_given_only and spec.biofix_stage is None:
        return None
    return planting_crop(spec)


def planting_map(crop: str, tier: str, window: "Window", season: int, data_dir: Path) -> np.ndarray:
    """Each cell's typical planting date for `crop` at `tier` (early, mid, late) in `season`, as date ordinals
    (float, NaN where there's none): its county's, else its state's; potato's its own estimate
    (`agdata.potatoplanting`, from the normals in `data_dir`). A date before the early one falls in the next year
    (winter wheat's late, in January), as at a point (`api.runs`)."""
    if crop not in CROPS:
        raise ValueError(f"no planting dates for {crop!r}; known crops are {', '.join(CROPS)}")
    if tier not in TIERS:
        raise ValueError(f"tier is early, mid or late, not {tier!r}")
    if crop == "potato":
        from agdata import potatoplanting

        return _slot_dates(potatoplanting.slots(data_dir, tier, window), season)
    days = _tier_days(crop, tier, window)
    out = np.full(window.shape, np.nan)
    for (month, day, next_year), cells in days.items():
        out[cells] = date(season + next_year, month, day).toordinal()
    return out


def _slot_dates(slots: np.ndarray, season: int) -> np.ndarray:
    """Calendar slots (`agdata.climatology.slot`) as date ordinals in `season`, NaN where missing (February 29 in a
    year without one is March 1)."""
    from agdata.climatology import LEAP

    out = np.full(slots.shape, np.nan)
    for slot in np.unique(slots[np.isfinite(slots)]).tolist():
        when = date.fromordinal(date(LEAP, 1, 1).toordinal() + int(slot))
        try:
            found = date(season, when.month, when.day)
        except ValueError:  # February 29
            found = date(season, 3, 1)
        out[slots == slot] = found.toordinal()
    return out


@cache
def _tier_days(crop: str, tier: str, window: "Window") -> dict[tuple[int, int, int], np.ndarray]:
    """(month, day, years after the season) → the cells planted then (boolean masks), from the county and state
    table (not potato); cached per window."""
    from agdata.regions import cell_counties

    keys = cell_counties(window)
    table, names = _table(), counties()
    found: dict[int, PlantingDate | None] = {}
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
