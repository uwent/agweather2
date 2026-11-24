"""Where the service keeps gridded data: a coverage mask on its window (D105).

A service box (`grid.BOXES`) is a rectangle of the grid, and every cell of its window is covered. A coverage preset
(`PRESETS`, launch's `upper_midwest`) is a mask built from state boundaries (`scripts/make_coverage_mask.py`): its
window, which the stores take, is the mask's bounding rectangle rounded out to the grid-wide LATTICE (D107), and only
the mask's cells are covered. Stores over that window keep the cells outside the mask missing (`outside`, applied by
`GridStore.write`), so zarr writes no chunk that lies wholly outside it; points outside it go to Open-Meteo, as points
outside a box always have.

On the lattice, a store's 256-cell chunks and the jobs' blocks (`agdata.blocks`) are the same squares of the grid in
every preset's window: a wider coverage later is a window grown by whole blocks, whose stores keep their chunks (moved,
not rewritten), and the cells it adds are new blocks to backfill. Files for people (the yearly downloads) take the
mask's `extent` instead, so they don't carry the empty margin.
"""

from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path

import numpy as np

from agdata.grid import NDFD, Window

DATA = Path(__file__).parent / "data"
PRESETS = {"upper_midwest": DATA / "coverage-upper_midwest.npz"}
LATTICE = 256  # cells: a preset's window starts and ends on multiples of this from NDFD's corner (the daily chunk)


def on_lattice(window: Window, size: int = LATTICE) -> Window:
    """The smallest window on the grid-wide lattice of `size` cells that holds `window` (clipped at the grid's north
    and east edges, where the last squares are smaller)."""
    ny, nx = NDFD.window.shape
    return Window(
        j0=window.j0 // size * size,
        j1=min(-(-window.j1 // size) * size, ny),
        i0=window.i0 // size * size,
        i1=min(-(-window.i1 // size) * size, nx),
    )


@dataclass(frozen=True, kw_only=True)
class Coverage:
    """A service area: its window and, over it, the covered cells (y, x)."""

    window: Window
    mask: np.ndarray

    def contains(self, j: int, i: int) -> bool:
        return self.window.contains(j, i) and bool(self.mask[j - self.window.j0, i - self.window.i0])

    @cached_property
    def extent(self) -> Window:
        """The mask's bounding rectangle (the window itself if no cell is covered)."""
        rows, cols = np.nonzero(self.mask)
        if not len(rows):
            return self.window
        j0, i0 = self.window.j0, self.window.i0
        return Window(
            j0=j0 + int(rows.min()), j1=j0 + int(rows.max()) + 1, i0=i0 + int(cols.min()), i1=i0 + int(cols.max()) + 1
        )

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


def extent(window: Window) -> Window:
    """The part of a store's `window` that holds covered cells: over a coverage preset's window, the mask's bounding
    rectangle; any other window whole."""
    for name in PRESETS:
        found = preset(name)
        if found.window == window:
            return found.extent
    return window


def parts(window: Window, size: int) -> list[Window]:
    """`window` in squares of `size` cells from its corner (smaller at the north and east edges), in row order: the
    way a job divides a store's window into work (`agdata.blocks`). Over a coverage preset's window (`outside`), a
    square with no covered cell is left out, and each square kept is cropped to its covered cells' bounding rectangle,
    rounded out to whole TRIM-cell steps from the square's corner, so the work skips the window's empty margin while
    every chunk a store has (32 cells or a divisor of it, up to whole squares) still lies in one part. Any other
    window is divided whole. The cells left out are missing anyway (`GridStore.write`)."""
    excluded = outside(window)
    out = []
    for j in range(window.j0, window.j1, size):
        for i in range(window.i0, window.i1, size):
            block = Window(j0=j, j1=min(j + size, window.j1), i0=i, i1=min(i + size, window.i1))
            if excluded is None:
                out.append(block)
                continue
            kept = ~excluded[block.j0 - window.j0 : block.j1 - window.j0, block.i0 - window.i0 : block.i1 - window.i0]
            if kept.any():
                out.append(_trimmed(block, kept))
    return out


TRIM = 32  # cells: the hourly store's chunk, a multiple of every smaller chunk (the past-years copies' 16)


def _trimmed(block: Window, kept: np.ndarray) -> Window:
    """`block` cropped to `kept`'s cells (y, x over it), rounded out to TRIM-cell steps from its corner."""
    rows, cols = np.nonzero(kept.any(axis=1))[0], np.nonzero(kept.any(axis=0))[0]
    return Window(
        j0=block.j0 + int(rows[0]) // TRIM * TRIM,
        j1=min(block.j1, block.j0 + -(-(int(rows[-1]) + 1) // TRIM) * TRIM),
        i0=block.i0 + int(cols[0]) // TRIM * TRIM,
        i1=min(block.i1, block.i0 + -(-(int(cols[-1]) + 1) // TRIM) * TRIM),
    )


def covered(window: Window, part: Window) -> np.ndarray:
    """Which cells of `part` (y, x), inside a store's `window`, the store keeps: all of them but over a coverage
    preset's window, where the mask's."""
    excluded = outside(window)
    if excluded is None:
        return np.ones(part.shape, dtype=bool)
    return ~excluded[part.j0 - window.j0 : part.j1 - window.j0, part.i0 - window.i0 : part.i1 - window.i0]
