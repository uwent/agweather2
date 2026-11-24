"""The launch coverage mask (`agdata.coverage`, D105): its cells at known places, boxes covering their whole window,
and a store over the mask's window keeping the cells outside it missing, without writing their chunks."""

from datetime import date

import numpy as np
import pytest

from agdata import coverage
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD, Window, service_window
from agdata.store import DAILY, GridStore

UM = coverage.preset("upper_midwest")


@pytest.mark.parametrize(
    ("place", "lat", "lng", "covered"),
    [
        ("Madison", 43.07, -89.40, True),
        ("Bismarck", 46.81, -100.78, True),
        ("Paducah", 37.08, -88.60, True),
        ("Columbus", 39.96, -83.00, True),
        ("Windsor, Ontario", 42.31, -83.04, True),  # within 50 km of Michigan
        ("Thunder Bay, Ontario", 48.38, -89.25, True),
        ("Lake Superior", 47.70, -87.50, True),
        ("Lake Erie", 42.20, -81.20, True),
        ("Toronto", 43.65, -79.38, False),
        ("Lake Ontario", 43.60, -77.80, False),
        ("Winnipeg", 49.90, -97.14, False),
        ("Denver", 39.74, -104.99, False),
        ("Nashville", 36.16, -86.78, False),
        ("Tulsa", 36.15, -95.99, False),
    ],
)
def test_the_mask_covers_the_states_their_buffer_and_the_great_lakes(place, lat, lng, covered):
    cell = NDFD.cell_of(lat, lng)
    assert cell is not None
    assert UM.contains(*cell) is covered, place


def test_the_window_is_the_masks_bounding_rectangle_on_the_block_lattice():
    """D107: the window is the mask's extent rounded out to the grid-wide lattice of 256-cell blocks."""
    assert service_window("upper_midwest") == UM.window
    w, e = UM.window, UM.extent
    assert all(v % coverage.LATTICE == 0 for v in (w.j0, w.j1, w.i0, w.i1))
    assert w == coverage.on_lattice(e)
    assert (
        w.j0 <= e.j0 < w.j0 + 256
        and w.j1 - 256 < e.j1 <= w.j1
        and w.i0 <= e.i0 < w.i0 + 256
        and w.i1 - 256 < e.i1 <= w.i1
    )
    inside = UM.over(e)
    assert inside[0].any() and inside[-1].any() and inside[:, 0].any() and inside[:, -1].any()
    assert inside.sum() == UM.mask.sum()
    assert coverage.extent(w) == e
    assert 400_000 < UM.mask.sum() < 500_000  # D105: about 447,000 cells
    wi = service_window("wisconsin")
    assert UM.over(wi).all()  # Wisconsin's box is inside the coverage
    assert coverage.of("wisconsin").mask.all() and coverage.of("wisconsin").window == wi
    assert coverage.extent(wi) == wi  # a box's window is all covered


def test_on_lattice_rounds_out_and_stops_at_the_grids_edges():
    assert coverage.on_lattice(Window(j0=256, j1=512, i0=0, i1=256)) == Window(j0=256, j1=512, i0=0, i1=256)
    assert coverage.on_lattice(Window(j0=300, j1=301, i0=10, i1=600)) == Window(j0=256, j1=512, i0=0, i1=768)
    ny, nx = NDFD.window.shape
    assert coverage.on_lattice(Window(j0=ny - 5, j1=ny, i0=nx - 5, i1=nx)) == Window(
        j0=ny // 256 * 256, j1=ny, i0=nx // 256 * 256, i1=nx
    )


def test_only_a_coverage_presets_window_masks_its_stores():
    assert coverage.outside(UM.window) is not None
    assert coverage.outside(service_window("wisconsin")) is None
    assert coverage.outside(Window(j0=900, j1=910, i0=1400, i1=1410)) is None


def test_a_store_over_the_coverage_keeps_cells_outside_it_missing_and_their_chunks_unwritten(tmp_path):
    variable = DAILY_VARIABLES["air_temperature_max"]
    store = GridStore.create(tmp_path, DAILY, 2025, UM.window, [variable], chunks=(1, 64, 64))
    day = date(2025, 7, 1)
    store.write(day, {variable.name: np.full(UM.window.shape, 25.0)}, source="urma")
    got = store.read_block(variable.name, store.index_of(day))
    assert np.isnan(got[~UM.mask]).all() and np.allclose(got[UM.mask], 25.0)
    # a sub-window across the mask's edge: the same rule
    row = next(r for r in range(UM.mask.shape[0]) if UM.mask[r].any() and np.argmax(UM.mask[r]) >= 20)
    edge = int(np.argmax(UM.mask[row]))  # the mask's western edge on that row
    sub = Window(
        j0=UM.window.j0 + row, j1=UM.window.j0 + row + 40, i0=UM.window.i0 + edge - 20, i1=UM.window.i0 + edge + 20
    )
    store.write(date(2025, 7, 2), {variable.name: np.full(sub.shape, 20.0)}, source="urma", window=sub)
    part = store.read_block(variable.name, store.index_of(date(2025, 7, 2)), window=sub)
    inside = UM.over(sub)
    assert inside.any() and not inside.all()
    assert np.isnan(part[~inside]).all() and np.allclose(part[inside], 20.0)
    # chunks wholly outside the mask aren't stored
    ny, nx = UM.window.shape
    blocks = [(a, b) for a in range(0, ny, 64) for b in range(0, nx, 64)]
    empty = sum(not UM.mask[a : a + 64, b : b + 64].any() for a, b in blocks)
    assert empty > 0
    stored = [p for p in (store.path / variable.name / "c").rglob("*") if p.is_file()]
    written = np.zeros(UM.window.shape, dtype=bool)  # July 2's covered cells
    written[sub.j0 - UM.window.j0 : sub.j1 - UM.window.j0, sub.i0 - UM.window.i0 : sub.i1 - UM.window.i0] = inside
    touched = sum(written[a : a + 64, b : b + 64].any() for a, b in blocks)
    assert touched > 0
    assert len(stored) == len(blocks) - empty + touched  # July 1's covered chunks, and July 2's


def test_work_over_the_coverage_skips_blocks_outside_it():
    """`coverage.parts`: squares from the window's corner, every covered cell in exactly one; squares with none are
    left out, and those kept are trimmed to their covered cells in 32-cell steps, so no 32-cell chunk (nor any
    smaller one dividing it) is split between two parts; any other window is divided whole."""
    for size in (16, 256):
        found = coverage.parts(UM.window, size)
        seen = np.zeros(UM.window.shape, dtype=int)
        for p in found:
            seen[p.j0 - UM.window.j0 : p.j1 - UM.window.j0, p.i0 - UM.window.i0 : p.i1 - UM.window.i0] += 1
            assert UM.over(p).any()
            sj, si = p.j0 - (p.j0 - UM.window.j0) % size, p.i0 - (p.i0 - UM.window.i0) % size  # its square's corner
            assert p.j1 <= sj + size and p.i1 <= si + size  # inside one square
            step = min(size, coverage.TRIM)
            assert (p.j0 - sj) % step == 0 and (p.i0 - si) % step == 0
            assert (p.j1 - sj) % step == 0 or p.j1 == min(sj + size, UM.window.j1)
            assert (p.i1 - si) % step == 0 or p.i1 == min(si + size, UM.window.i1)
        assert (seen[UM.mask] == 1).all() and seen.max() == 1
    trimmed = coverage.parts(UM.window, 256)
    assert sum(p.size for p in trimmed) <= UM.extent.size  # no more work than the extent, for all the margin
    assert len(coverage.parts(UM.window, 16)) < -(-UM.window.shape[0] // 16) * -(-UM.window.shape[1] // 16)
    wi = service_window("wisconsin")
    whole = coverage.parts(wi, 100)
    assert [(p.j0, p.j1, p.i0, p.i1) for p in whole] == [
        (wi.j0 + a, min(wi.j0 + a + 100, wi.j1), wi.i0 + b, min(wi.i0 + b + 100, wi.i1))
        for a in range(0, wi.shape[0], 100)
        for b in range(0, wi.shape[1], 100)
    ]
    assert coverage.covered(wi, whole[0]).all()
    corner = coverage.parts(UM.window, 256)[0]
    assert (coverage.covered(UM.window, corner) == UM.over(corner)).all()
