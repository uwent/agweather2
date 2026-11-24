"""Where the service keeps gridded data: a coverage mask on its window (D105).

A service box (`grid.BOXES`) is a rectangle of the grid, and every cell of its window is covered. A coverage preset
(`PRESETS`, launch's `upper_midwest`) is a mask built from state boundaries (`scripts/make_coverage_mask.py`): its
window is the mask's bounding rectangle, which the stores take, and only the mask's cells are covered. Stores over
that window keep the cells outside the mask missing (`outside`, applied by `GridStore.write`), so zarr writes no
chunk that lies wholly outside it; points outside it go to Open-Meteo, as points outside a box always have.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np

from agdata.grid import NDFD, Window

DATA = Path(__file__).parent / "data"
PRESETS = {"upper_midwest": DATA / "coverage-upper_midwest.npz"}


@dataclass(frozen=True, kw_only=True)
class Coverage:
    """A service area: its window and, over it, the covered cells (y, x)."""

    window: Window
    mask: np.ndarray

    def contains(self, j: int, i: int) -> bool:
        return self.window.contains(j, i) and bool(self.mask[j - self.window.j0, i - self.window.i0])

    def over(self, window: Window) -> np.ndarray:
        """The covered cells of any window, (y, x): False outside this one's."""
        out = np.zeros(window.shape, dtype=bool)
        j0, j1 = max(window.j0, self.window.j0), min(window.j1, self.window.j1)
        i0, i1 = max(window.i0, self.window.i0), min(window.i1, self.window.i1)
        if j0 < j1 and i0 < i1:
            out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = self.mask[
                j0 - self.window.j0 : j1 - self.window.j0, i0 - self.window.i0 : i1 - self.window.i0
            ]
        return out


@cache
def preset(name: str) -> Coverage:
    """A coverage preset's mask, read once."""
    with np.load(PRESETS[name]) as f:
        j0, j1, i0, i1 = (int(v) for v in f["window"])
        window = Window(j0=j0, j1=j1, i0=i0, i1=i1)
        mask = np.unpackbits(f["packed"])[: window.size].reshape(window.shape).astype(bool)
    mask.flags.writeable = False
    return Coverage(window=window, mask=mask)


@cache
def of(spec: str) -> Coverage:
    """The coverage `SERVICE_BOX` names: a preset's mask, or a box's whole window."""
    from agdata.grid import parse_box

    name = spec.strip().lower()
    if name in PRESETS:
        return preset(name)
    window = NDFD.window_for(parse_box(spec))
    mask = np.ones(window.shape, dtype=bool)
    mask.flags.writeable = False
    return Coverage(window=window, mask=mask)


@cache
def outside(window: Window) -> np.ndarray | None:
    """For a store over a coverage preset's window, its cells outside the mask (y, x), which it keeps missing; None
    for any other window (a box's, a test's), whose cells are all kept."""
    for name in PRESETS:
        found = preset(name)
        if found.window == window:
            out = ~found.mask
            out.flags.writeable = False
            return out
    return None


def parts(window: Window, size: int) -> list[Window]:
    """`window` in squares of `size` cells from its corner (smaller at the north and east edges), in row order: the
    way a job divides a store's window into work (`agdata.blocks`). Over a coverage preset's window (`outside`), a
    square with no covered cell is left out; any other window is divided whole. The cells left out are missing
    anyway (`GridStore.write`)."""
    excluded = outside(window)
    out = []
    for j in range(window.j0, window.j1, size):
        for i in range(window.i0, window.i1, size):
            block = Window(j0=j, j1=min(j + size, window.j1), i0=i, i1=min(i + size, window.i1))
            if (
                excluded is None
                or not excluded[
                    block.j0 - window.j0 : block.j1 - window.j0, block.i0 - window.i0 : block.i1 - window.i0
                ].all()
            ):
                out.append(block)
    return out


def covered(window: Window, part: Window) -> np.ndarray:
    """Which cells of `part` (y, x), inside a store's `window`, the store keeps: all of them but over a coverage
    preset's window, where the mask's."""
    excluded = outside(window)
    if excluded is None:
        return np.ones(part.shape, dtype=bool)
    return ~excluded[part.j0 - window.j0 : part.j1 - window.j0, part.i0 - window.i0 : part.i1 - window.i0]
