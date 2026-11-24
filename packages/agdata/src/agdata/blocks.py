"""Work over a store's window in square blocks, run inline or in a pool of worker processes.

Jobs that compute over the grid (the rollup, the running totals, the models' ingredients, chill portions, the crop
tiers, the past-years copies) divide a window into squares of SIZE cells from its southwest corner (`blocks`). SIZE is
the daily stores' chunk, so each chunk is written by one block, and a multiple of the hourly store's 32 × 32, so its
reads take whole chunks too. Over a coverage preset's window, which lies on the grid-wide lattice of SIZE cells
(D107), the squares are the same squares of the grid in every store; only those with a covered cell are kept, each
trimmed to its covered cells in 32-cell steps (`coverage.parts`, D105): the work follows the coverage, and cells added
to it later are whole new blocks.

Every daily statistic, feature and model works on each cell's own series, so a block's result doesn't depend on its
neighbours: blocks run in any order and in separate processes. `run` hands tasks to a pool of `workers()` processes
(`BLOCK_WORKERS` in the environment or `set_workers`; 1 by default, inline). A task writes its block's values itself
with `GridStore.write(record=False)`, so no two processes write one chunk, and returns what it wrote; the calling
process records the writes (`GridStore.record`) and makes every other change to a store (creating it and its arrays,
attributes, whole-window arrays), so a store's `_meta` arrays, a chunk each, have one writer. The write lock stays
with the caller: tasks run while it's held (`hold`, or the caller holding it throughout).

Tasks come in chains: a chain's next task starts only once the one before it has been handled, for work that
continues from what the step before stored (the ingredients' running totals). Independent tasks are chains of one.
"""

import os
from collections import deque
from collections.abc import Callable, Hashable, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from contextlib import AbstractContextManager, nullcontext
from multiprocessing import get_context
from typing import Any

from agdata import coverage
from agdata.grid import Window

SIZE = coverage.LATTICE  # 256 cells a side: the daily stores' chunk (`store.DEFAULT_CHUNKS`)

Task = tuple[Hashable, Callable[[], Any]]  # a key for the caller and a picklable call (`functools.partial`)

_workers: int | None = None


def blocks(window: Window) -> list[Window]:
    """The window's squares of SIZE cells from its corner (smaller at the north and east edges), in row order; over
    a coverage preset's window, only those with a covered cell, trimmed to them."""
    return coverage.parts(window, SIZE)


def set_workers(n: int | None) -> None:
    """Worker processes for `run` from now on in this process (None: back to `BLOCK_WORKERS`, default 1)."""
    global _workers
    _workers = n


def workers() -> int:
    if _workers is not None:
        return max(1, _workers)
    return max(1, int(os.environ.get("BLOCK_WORKERS") or 1))


def run(
    chains: Sequence[Sequence[Task]],
    handle: Callable[[Hashable, Any], None],
    stop: Callable[[], bool] | None = None,
    hold: Callable[[], AbstractContextManager] | None = None,
    n: int | None = None,
) -> bool:
    """Runs each chain's tasks in order, calling `handle(key, result)` in this process as each finishes, up to `n`
    (default `workers()`) at a time in worker processes, or inline with one. With `hold` (a write lock's factory),
    tasks run only while it's held: inline, each task in its own hold; in the pool, waves of `n` tasks, released
    between waves so others waiting for it get their turn. Once `stop()` is true no task starts; tasks already
    running finish and are handled. Returns False if stopped before every task ran. A task's exception is raised
    here once the tasks already running finish."""
    n = min(n or workers(), sum(1 for chain in chains if chain))
    shared = hold is not None  # waves only to let others take the lock between them
    hold = hold or nullcontext
    if n <= 1:
        for chain in chains:
            for key, call in chain:
                if stop is not None and stop():
                    return False
                with hold():
                    result = call()
                    handle(key, result)
        return True
    ready = deque((c, 0) for c, chain in enumerate(chains) if chain)
    # spawn, not fork: the parent may hold zarr's and Numba's threads, and a forked copy of a held lock deadlocks
    with ProcessPoolExecutor(max_workers=n, mp_context=get_context("spawn")) as pool:
        while ready:
            if stop is not None and stop():
                return False
            with hold():
                _wave(pool, chains, ready, handle, stop, n, n if shared else None)
    return True


def _wave(pool, chains, ready: deque, handle, stop, n: int, limit: int | None) -> None:
    """Starts up to `limit` tasks from `ready` (None: all of them), `n` at a time, and waits for them."""
    pending: dict[Future, tuple[int, int]] = {}
    started = 0
    failure: BaseException | None = None
    while True:
        while (
            ready
            and len(pending) < n
            and (limit is None or started < limit)
            and failure is None
            and not (stop is not None and stop())
        ):
            c, step = ready.popleft()
            pending[pool.submit(chains[c][step][1])] = (c, step)
            started += 1
        if not pending:
            break
        done, _ = wait(pending, return_when=FIRST_COMPLETED)
        for future in done:
            c, step = pending.pop(future)
            try:
                result = future.result()
            except BaseException as e:
                failure = failure or e
                continue
            handle(chains[c][step][0], result)
            if step + 1 < len(chains[c]):
                ready.appendleft((c, step + 1))  # the chain goes on first: its next step reads what this wrote
    if failure is not None:
        raise failure
