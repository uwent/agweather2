from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from functools import partial

import numpy as np
import pytest

from agdata import blocks, chillseason
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import rebuild_year
from agdata.daily import rollup_days
from agdata.grid import Window
from agdata.store import CUMULATIVE, DAILY, HOURLY, GridStore
from agdata.timezones import GRID_ZONE

WINDOW = Window(j0=900, j1=916, i0=1400, i1=1412)  # 16 × 12 cells: blocks of 8 make 2 × 2, two of them 8 × 4
HOUR = timedelta(hours=1)


def double(x: int):
    """A task a worker process can run: a builtin, since spawned workers can't import a test module."""
    return partial(int.__mul__, x, 2)


@pytest.mark.parametrize("n", [1, 2])
def test_run_handles_each_task_with_its_key_and_keeps_each_chain_in_order(n):
    seen: list = []
    chains = [[((c, k), double(10 * c + k)) for k in range(3)] for c in range(3)]
    assert blocks.run(chains, lambda key, result: seen.append((key, result)), n=n)
    assert sorted(seen) == sorted(((c, k), 2 * (10 * c + k)) for c in range(3) for k in range(3))
    for c in range(3):
        assert [key[1] for key, _ in seen if key[0] == c] == [0, 1, 2]


@pytest.mark.parametrize("n", [1, 2])
def test_run_reports_each_task_handled(n):
    reported: list[tuple[int, int]] = []
    chains = [[(k, double(k)) for k in range(2)], [(9, double(9))]]
    blocks.run(chains, lambda *_: None, n=n, progress=lambda done, total: reported.append((done, total)))
    assert reported == [(1, 3), (2, 3), (3, 3)]


def test_blocks_come_largest_first():
    from agdata import coverage

    found = blocks.blocks(coverage.preset("upper_midwest").window)
    assert [p.size for p in found] == sorted((p.size for p in found), reverse=True)
    assert found[0].shape == (blocks.SIZE, blocks.SIZE)


@pytest.mark.parametrize("n", [1, 2])
def test_run_starts_nothing_once_stopped_and_raises_a_tasks_error(n):
    seen = []
    chains = [[(k, double(k))] for k in range(6)]
    assert not blocks.run(chains, lambda key, _: seen.append(key), stop=lambda: len(seen) >= 1, n=n)
    assert 1 <= len(seen) <= n
    with pytest.raises(ValueError, match="invalid literal"):
        blocks.run([[(k, partial(int, "x") if k == 3 else double(k))] for k in range(5)], lambda *_: None, n=n)


def test_run_holds_the_lock_while_tasks_run_and_lets_go_between_waves():
    held = []

    @contextmanager
    def hold():
        held.append("in")
        yield
        held.append("out")

    events = []
    blocks.run([[(k, double(k))] for k in range(5)], lambda key, _: events.append(held[-1]), hold=hold, n=2)
    assert set(events) == {"in"}  # every result was handled under the lock
    assert held.count("in") == 3  # waves of 2, 2 and 1
    blocks.run([[(k, double(k))] for k in range(3)], lambda *_: None, hold=hold, n=1)
    assert held.count("in") == 6  # inline, one task each


def hourly(tmp_path):
    """Four days of hours over WINDOW, varying by cell, with ET0 missing on part of the window one afternoon."""
    start = datetime(2025, 6, 30, 6, tzinfo=UTC)
    times = [start + k * HOUR for k in range(24 * 4)]
    h = np.array([t.hour for t in times], dtype=float)[:, None, None]
    shape = (len(times), *WINDOW.shape)
    rng = np.random.default_rng(1)
    cell = rng.normal(0, 2, WINDOW.shape)[None]
    temperature = 20 + cell + 6 * np.sin(2 * np.pi * (h - 15) / 24) + rng.normal(0, 0.5, shape)
    values = {
        "air_temperature": temperature,
        "dew_point": temperature - 5 + rng.normal(0, 1, shape),
        "wind_speed": np.abs(rng.normal(3, 1, shape)),
        "shortwave_radiation": np.broadcast_to(np.clip(600 * np.sin(np.pi * (h - 11) / 14), 0, None), shape).copy(),
        "precipitation": np.where(rng.random(shape) < 0.1, 0.5, 0.0),
        "surface_pressure": np.full(shape, 98.0),
        "et0": np.full(shape, 0.1),
        "soil_temperature_10cm": temperature - 2,
    }
    values["et0"][30:34, :5, :5] = np.nan
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())
    store.write(start, values, source="urma")


def stores_in_blocks(tmp_path):
    """The daily and running-totals stores chunked in 8 × 8, as the real ones are in SIZE blocks, so workers
    writing blocks of 8 never share a chunk."""

    def with_zones(group) -> None:
        group.attrs["timezones"] = [GRID_ZONE]
        group.create_array("_meta/timezone", shape=WINDOW.shape, dtype="uint8", fill_value=0)

    GridStore.create(tmp_path, DAILY, 2025, WINDOW, DAILY_VARIABLES.values(), chunks=(1, 8, 8), finish=with_zones)
    GridStore.create(tmp_path, CUMULATIVE, 2025, WINDOW, CUMULATIVE_VARIABLES.values(), chunks=(1, 8, 8))


def test_a_rollup_its_totals_and_chill_in_blocks_and_workers_match_one_block_inline(tmp_path, monkeypatch):
    one, split = tmp_path / "one", tmp_path / "split"
    for path in (one, split):
        hourly(path)
    rollup_days(one, WINDOW, date(2025, 7, 1), date(2025, 7, 3))
    rebuild_year(one, WINDOW, 2025)
    chillseason.update(one, WINDOW, date(2025, 7, 1), date(2025, 7, 3))
    stores_in_blocks(split)
    monkeypatch.setattr(blocks, "SIZE", 8)
    assert len(blocks.blocks(WINDOW)) == 4
    blocks.set_workers(2)
    try:
        rollup_days(split, WINDOW, date(2025, 7, 1), date(2025, 7, 3))
        rebuild_year(split, WINDOW, 2025)
        chillseason.update(split, WINDOW, date(2025, 7, 1), date(2025, 7, 3))
    finally:
        blocks.set_workers(None)
    for layout, names in ((DAILY, DAILY_VARIABLES), (CUMULATIVE, CUMULATIVE_VARIABLES)):
        a = GridStore.open(one, layout, 2025, names.values())
        b = GridStore.open(split, layout, 2025, names.values())
        t0, t1 = a.index_of(date(2025, 7, 1)), a.index_of(date(2025, 7, 3)) + 1
        compared = 0
        for name in names:
            if name not in a.group or not a.has_data(name, t0, t1).any():
                continue
            np.testing.assert_array_equal(a.read_steps(name, t0, t1), b.read_steps(name, t0, t1), err_msg=name)
            assert a.sources(name, t0, t1) == b.sources(name, t0, t1), name
            assert b.written(name, t0, t1) is not None, name
            compared += 1
        assert compared > 20
        if layout == CUMULATIVE:
            assert b.has_data("chill_portions", t0, t1).all()
    estimate = GridStore.open(split, DAILY, 2025, DAILY_VARIABLES.values()).read_steps("et0_sum_estimate", t0, t0 + 1)[
        0
    ]
    assert np.isfinite(estimate[:5, :5]).any() and np.isnan(estimate[5:, 5:]).all()
