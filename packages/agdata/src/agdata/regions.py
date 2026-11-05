"""States and counties as masks on the grid (`region=` on maps; PLAN.md Phase 5 E), from the county grid
`agdata.places` already holds, so no geometry library or new boundary file is needed.

Each cell takes the county under its center (a cell just over a line, or on a shore within about 10 km, takes the
nearest county, as a point does); open water further out is in no county and so in no region. A state is its
counties. A region is given as a state's name (`wisconsin`, `new-york`), its postal code (`WI`), or a county's
five-digit FIPS code (`55025`, Dane County).
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np

from agdata.grid import NDFD, Window
from agdata.places import counties, county_ids

STATES = {
    "AL": "Alabama", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}  # fmt: skip
_BY_NAME = {name.lower().replace(" ", "-"): code for code, name in STATES.items()}


@dataclass(frozen=True, kw_only=True)
class Region:
    id: str  # canonical: `wisconsin`, or a county's FIPS code
    name: str  # "Wisconsin", "Dane County, WI"
    county_ids: frozenset[int]  # ids in the county grid (`agdata.places.counties()`)


def find(spec: str) -> Region | None:
    """A region by state name, postal code or county FIPS code (case and spaces don't matter); None if unknown."""
    text = spec.strip()
    if text.isdigit() and len(text) == 5:
        for k, county in enumerate(counties()):
            if county is not None and county.geoid == text:
                return Region(id=text, name=f"{county.name}, {county.state}", county_ids=frozenset({k}))
        return None
    code = text.upper() if text.upper() in STATES else _BY_NAME.get(text.lower().replace(" ", "-").replace("_", "-"))
    if code is None:
        return None
    ids = frozenset(k for k, c in enumerate(counties()) if c is not None and c.state == code)
    return Region(id=STATES[code].lower().replace(" ", "-"), name=STATES[code], county_ids=ids)


@cache
def cell_counties(window: Window) -> np.ndarray:
    """Each cell's county id over the window (0 for none), (y, x). Cached: ~0.1–0.5 s for a state-sized box."""
    lat, lon = NDFD.window_latlon(window)
    return county_ids(lat, lon)


LAND_FRACTION = 0.5  # ERA5-Land's threshold for land (D52)


@cache
def land(data_dir: Path, window: Window) -> np.ndarray:
    """True for the window's cells on land, (y, x): in a county, and where the archive keeps ERA5-Land's land-sea
    mask (`data_dir/static`, D52), at least half land there (bilinear from its 0.1° cells). The county grid alone
    gives shore cells within ~10 km of a county to it, whose air is the lake's; the mask leaves them out. Cached."""
    found = cell_counties(window) > 0
    from agdata.regrid import regrid
    from agdata.sources.era5land import LandMask

    for path in sorted((data_dir / "static").glob("era5land_land_*.npz")):
        mask = LandMask.load(path)
        with np.errstate(invalid="ignore"):
            fraction = regrid(mask.fraction, mask.grid, window)
        found &= ~(np.isfinite(fraction) & (fraction < LAND_FRACTION))
    return found


def mask(region: Region, window: Window) -> np.ndarray:
    """True for the window's cells in the region, (y, x)."""
    return np.isin(cell_counties(window), list(region.county_ids))
