"""Writers that bypass `GridStore.write` keep cells outside the coverage missing themselves (CLAUDE.md, D105)."""

from datetime import date

import numpy as np

from agdata import coverage, croptiers, seasonmaps
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import Window
from agdata.store import INGREDIENTS, GridStore

WINDOW = Window(j0=900, j1=904, i0=1400, i1=1404)


def _store(tmp_path, monkeypatch) -> GridStore:
    outside = np.zeros(WINDOW.shape, dtype=bool)
    outside[:, :2] = True  # the west half isn't covered
    monkeypatch.setattr(coverage, "outside", lambda window: outside if window == WINDOW else None)
    return GridStore.create(tmp_path, INGREDIENTS, 2025, WINDOW, [DAILY_VARIABLES["air_temperature_min"]])


def test_a_seasons_biofix_is_missing_outside_the_coverage(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    seasonmaps._write_biofix(store, "apple-scab", WINDOW, np.full(WINDOW.shape, np.inf, dtype=np.float32))
    found = seasonmaps.biofix(tmp_path, "apple-scab", 2025, WINDOW)
    assert np.isnan(found[:, :2]).all() and np.isinf(found[:, 2:]).all()


def test_a_crops_stage_days_are_missing_outside_the_coverage(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    values = np.full((3, *WINDOW.shape), np.inf, dtype=np.float32)
    croptiers._write_reached(store, "soybean-stages", "mid", WINDOW, values, date(2025, 7, 1))
    found = croptiers.reached(tmp_path, "soybean-stages", "mid", 2025, WINDOW)
    assert found is not None
    assert np.isnan(found[0][:, :, :2]).all() and np.isinf(found[0][:, :, 2:]).all()
