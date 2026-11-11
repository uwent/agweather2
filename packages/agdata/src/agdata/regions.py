"""States and counties as masks on the grid (`region=` on maps; PLAN.md Phase 5 E), from the county grid
`agdata.places` already holds, so no geometry library or new boundary file is needed.

Each cell takes the county under its center (a cell just over a line, or on a shore within about 10 km, takes the
nearest county, as a point does); open water further out is in no county and so in no region. A state is its
counties. A region is given as a state's name (`wisconsin`, `new-york`), its postal code (`WI`), a county's
five-digit FIPS code (`55025`, Dane County), or a county's name with its state (`Dane, WI`, `Dane County, Wisconsin`,
`dane-wi`, `st-croix-wi`).
"""

import re
from dataclasses import dataclass
from functools import cache

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
    """A region by state name, postal code, county FIPS code, or county name with its state (case, spaces and
    punctuation don't matter); None if unknown."""
    text = spec.strip()
    if text.isdigit() and len(text) == 5:
        for k, county in enumerate(counties()):
            if county is not None and county.geoid == text:
                return _county_region(k)
        return None
    code = _state_code(text)
    if code is None:
        k = _county_by_name(text)
        return None if k is None else _county_region(k)
    ids = frozenset(k for k, c in enumerate(counties()) if c is not None and c.state == code)
    return Region(id=STATES[code].lower().replace(" ", "-"), name=STATES[code], county_ids=ids)


def _county_region(k: int) -> Region:
    county = counties()[k]
    assert county is not None
    return Region(id=county.geoid, name=f"{county.name}, {county.state}", county_ids=frozenset({k}))


def _slug(text: str) -> str:
    """Lowercase words joined by hyphens, without punctuation; "Saint" as "st" (`St. Croix`, `Saint Croix`)."""
    words = re.sub(r"[^a-z0-9]+", " ", text.lower().replace("'", "")).split()
    return "-".join("st" if w == "saint" else w for w in words)


def _state_code(text: str) -> str | None:
    code = text.strip().upper()
    return code if code in STATES else _BY_NAME.get(_slug(text))


# A county's name ends in one of these; the name without it is accepted too where that's unambiguous in its state
_SUFFIXES = ("city-and-borough", "census-area", "municipality", "borough", "parish", "county", "city")


@cache
def _county_names() -> dict[tuple[str, str], int | None]:
    """(state code, name slug) → county id, by full name and by name without its suffix; None where two counties of
    a state share the shorter form (Baltimore County and Baltimore city), so only the full name finds them."""
    full: dict[tuple[str, str], int] = {}
    short: dict[tuple[str, str], list[int]] = {}
    for k, county in enumerate(counties()):
        if county is None:
            continue
        slug = _slug(county.name)
        full[(county.state, slug)] = k
        for suffix in _SUFFIXES:
            if slug.endswith("-" + suffix):
                short.setdefault((county.state, slug[: -len(suffix) - 1]), []).append(k)
                break
    found: dict[tuple[str, str], int | None] = {key: ks[0] if len(ks) == 1 else None for key, ks in short.items()}
    found.update(full)
    return found


def _county_by_name(text: str) -> int | None:
    """A county id from "Name, State" or a slug ending in the state (`dane-wi`, `dane-county-wisconsin`)."""
    if "," in text:
        name, state = text.rsplit(",", 1)
        code = _state_code(state)
        return None if code is None else _county_names().get((code, _slug(name)))
    slug = _slug(text)
    for code, state in STATES.items():
        for tail in (code.lower(), _slug(state)):
            if slug.endswith("-" + tail):
                found = _county_names().get((code, slug[: -len(tail) - 1]))
                if found is not None:
                    return found
    return None


@cache
def cell_counties(window: Window) -> np.ndarray:
    """Each cell's county id over the window (0 for none), (y, x). Cached: ~0.1–0.5 s for a state-sized box."""
    lat, lon = NDFD.window_latlon(window)
    return county_ids(lat, lon)


def land(window: Window) -> np.ndarray:
    """True for the window's cells on land, (y, x): in a county and not open water, the same cells summaries count
    (`summary_counties`). Model maps keep only these (a crop's disease over the Great Lakes means nothing). Until
    2026-11-10 they went by ERA5-Land's land fraction (at least half land), which also dropped shore cells our
    water mask (`coast.water`, from URMA's wave height) calls land, so shore counties' summaries came up short."""
    return summary_counties(window) > 0


@cache
def summary_counties(window: Window) -> np.ndarray:
    """Each cell's county as summaries count it (0 for none), (y, x): `cell_counties` less open water
    (`agdata.coast.water`, the Great Lakes and the ocean), so a shore county's lake cells, which the county grid
    gives it within ~10 km, don't count. Inland lakes count as land. Cached; don't write to it."""
    from agdata.coast import water

    found = cell_counties(window).copy()
    found[water(window)] = 0
    found.flags.writeable = False
    return found


def mask(region: Region, window: Window) -> np.ndarray:
    """True for the window's cells in the region, (y, x)."""
    return np.isin(cell_counties(window), list(region.county_ids))


# --- Summaries by county or state (PLAN.md Phase 6 C5) ----------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Area:
    """A county or state as a summary's row gives it."""

    fips: str  # a county's five digits, a state's two
    name: str  # "Dane County", "Wisconsin"
    state: str  # postal code
    land_m2: int  # the Census Bureau's land area
    cells: int  # its cells on the whole 2.5 km grid, as `summary_counties` counts them


@cache
def areas(by: str) -> tuple[Area | None, ...]:
    """Every county (`by="county"`, indexed as the county grid) or state (`"state"`, by postal code), with index 0
    for none: the labels `area_labels` gives cells."""
    if by == "county":
        return (
            None,
            *(
                Area(fips=c.geoid, name=c.name, state=c.state, land_m2=c.land_m2, cells=c.cells)
                for c in counties()
                if c is not None
            ),
        )
    found: dict[str, list] = {}
    for c in counties():
        if c is not None:
            found.setdefault(c.state, []).append(c)
    return (
        None,
        *(
            Area(
                fips=found[code][0].geoid[:2],
                name=STATES[code],
                state=code,
                land_m2=sum(c.land_m2 for c in found[code]),
                cells=sum(c.cells for c in found[code]),
            )
            for code in sorted(found, key=lambda code: found[code][0].geoid)
        ),
    )


@cache
def _state_of_county() -> np.ndarray:
    """Each county id's index in `areas("state")` (0 for none)."""
    index = {a.state: k for k, a in enumerate(areas("state")) if a is not None}
    return np.array([0, *(index[c.state] for c in counties() if c is not None)], dtype=np.int32)


def area_labels(by: str, window: Window) -> np.ndarray:
    """Each cell's index into `areas(by)` (0 for none: open water, outside the lower 48), (y, x)."""
    ids = summary_counties(window)
    return ids.astype(np.int32) if by == "county" else _state_of_county()[ids]


def area_indices(region: Region, by: str) -> list[int]:
    """The indices into `areas(by)` that make up `region`: its counties, or its state (a county's own state)."""
    if by == "county":
        return sorted(region.county_ids)
    return sorted({int(_state_of_county()[k]) for k in region.county_ids})


@dataclass(kw_only=True)
class AreaStats:
    """Statistics over each area's cells with a value, indexed as `areas(by)`: NaN where an area has none."""

    with_data: np.ndarray  # cells with a value (or, with `present`, with an answer)
    none: np.ndarray  # cells with an answer of none (`present` but no value): a first frost not yet come
    mean: np.ndarray
    min: np.ndarray
    max: np.ndarray
    levels: np.ndarray | None  # (areas, levels): cells at each level, for a map of levels


def area_stats(
    values: np.ndarray, labels: np.ndarray, n: int, levels: int | None = None, present: np.ndarray | None = None
) -> AreaStats:
    """`values` (y, x) over each label's cells (`labels`, 0 for none; `n` labels in all), missing cells left out.
    The mean isn't weighted by cell area: the 2.5 km grid's cells differ by under 2% across a state. With `levels`,
    values are level indices (0 to levels − 1), counted per level too. `present` marks the cells with data where
    that isn't the same as having a value (a first day within bounds: found, or none in the range)."""
    in_area = labels > 0
    kept = np.isfinite(values) & in_area
    label, v = labels[kept], values[kept]
    counted = np.bincount(label, minlength=n)
    with_data = counted if present is None else np.bincount(labels[present & in_area], minlength=n)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.bincount(label, weights=v, minlength=n) / counted
    low, high = np.full(n, np.inf), np.full(n, -np.inf)
    np.minimum.at(low, label, v)
    np.maximum.at(high, label, v)
    empty = counted == 0
    low[empty] = high[empty] = mean[empty] = np.nan
    per_level = None
    if levels is not None:
        index = np.clip(np.rint(v).astype(np.int64), 0, levels - 1)
        per_level = np.bincount(label * levels + index, minlength=n * levels).reshape(n, levels)
    return AreaStats(with_data=with_data, none=with_data - counted, mean=mean, min=low, max=high, levels=per_level)
