"""Writers that bypass `GridStore.write` keep cells outside the coverage missing themselves (CLAUDE.md, D105); reads in the block pool add nothing."""

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


def test_a_blocks_daily_read_adds_nothing_to_the_store(tmp_path):
    # Reads in the block pool's workers mustn't add arrays: two workers adding one would race (`agdata.blocks`)
    from agdata import modelmaps
    from agdata.store import DAILY

    GridStore.create(tmp_path, DAILY, 2025, WINDOW, [DAILY_VARIABLES["air_temperature_min"]])
    found = modelmaps._read(tmp_path, None, None, "air_temperature_max", date(2025, 5, 1), 3, WINDOW)
    assert np.isnan(found).all()
    assert not (DAILY.path(tmp_path, 2025) / "air_temperature_max").exists()
    assert modelmaps._store_window(tmp_path, tmp_path, 2025, Window(j0=900, j1=901, i0=1400, i1=1401)) == WINDOW
