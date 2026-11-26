"""Typical potato planting dates on the grid: days before and after the normal last hard spring freeze around each
cell (replaces D64's interim rule, the dates of the nearest of Veg Path's places within 40 km).

Potato growers plant once the ground can be worked and late enough that the crop, which emerges two to four weeks
later, comes up after the spring's hard freezes. UW Vegetable Pathology's newsletters give early, mid and late
planting dates at seven Wisconsin potato areas each season (`docs/validation/data/vegpath-potato-planting/`, 2020–2026);
a place's dates follow its usual spring, not the year's (a rule on the year's own weather was ~10 days off, one on the
place's normal ~6). So the dates are climatological: each cell's early, mid and late planting are `OFFSETS` days from
the median last spring freeze at 28 °F over the 30-year normal (`agdata.normals`' `last30` `freeze_28/spring_p50`,
D85) averaged over the land within 50 km, center-weighted (`agdata.springfreeze`, D127), the medians at Veg Path's 120
plantings (`scripts/fit_potato_planting.py`). The cell's own freeze date (D126) picked up frost pockets, a cell or a
few two or three weeks later than the farms around them, which speckled the blight maps; whether a place plants early
or late is a trait of its area.

Held out by place, the rule comes within 6.8 days of Veg Path's dates on average (6.7 on the cell's own freeze). The
normal soil degree days above 0 °C from January 1 that the first fit used (2026-11-03) came within 6.2 in Wisconsin,
but put planting in February in Kentucky and southern Illinois, and Ohio's three weeks before Michigan's and
Minnesota's, where NASS's usual dates put them within days: winter warmth adds up where the ground doesn't freeze. The
same rule on air temperature did the same. The freeze dates keep the states' order NASS gives
(`docs/validation/models/potato-stages.md`, "Typical planting dates").

The dates are read from the stored normal on request (the area's map, computed once per build of the normals), so
points and maps give the same date for a cell (`agdata.planting`); a cell without the normal (outside the coverage, or
before `last30` is built) has none.
"""

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np

from agdata import climatology, normals, regions, springfreeze
from agdata.grid import Window

PERIOD = "last30"
# The median last spring freeze at 28 °F, averaged over the area (`agdata.springfreeze`)
FREEZE = springfreeze.SPRING_28
# Days from the freeze to each tier's planting: medians of Veg Path's dates less the freeze at their places
OFFSETS = {"early": -6, "mid": 7, "late": 28}


def slots(data_dir: Path, tier: str, window: Window) -> np.ndarray:
    """A tier's planting over `window` as calendar slots (`climatology.slot`: a leap year's day of year from 0),
    float (y, x), NaN where there's none. Cached per build of the normals."""
    return _slots(Path(data_dir), tier, window, _stamp(data_dir))


def _stamp(data_dir: Path) -> str | None:
    """The normals' build and the open-water mask's (`springfreeze` leaves water out), or None without normals."""
    found = normals.stamp(data_dir, PERIOD)
    return None if found is None else f"{found}:{regions._water_stamp()}"


@lru_cache(maxsize=48)
def _slots(data_dir: Path, tier: str, window: Window, stamp: str | None) -> np.ndarray:
    out = _computed(data_dir, tier, window, stamp)
    out.flags.writeable = False
    return out


def _computed(data_dir: Path, tier: str, window: Window, stamp: str | None) -> np.ndarray:
    if stamp is None:
        return np.full(window.shape, np.nan)
    return np.round(springfreeze.within(data_dir, FREEZE, window, period=PERIOD)) + OFFSETS[tier]


def slot_text(slot: float) -> str:
    """A calendar slot as MM-DD."""
    return (date(climatology.LEAP, 1, 1) + timedelta(days=int(slot))).strftime("%m-%d")


def at(data_dir: Path, j: int, i: int) -> dict[str, str] | None:
    """Each tier's planting at a cell as MM-DD, or None where the normal has none."""
    cell, stamp = Window(j0=j, j1=j + 1, i0=i, i1=i + 1), _stamp(data_dir)
    found = {tier: float(_computed(Path(data_dir), tier, cell, stamp)[0, 0]) for tier in OFFSETS}
    return None if any(np.isnan(v) for v in found.values()) else {t: slot_text(v) for t, v in found.items()}
