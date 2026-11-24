"""Apple scab's, fire blight's and red crown rot's seasons on the grid, kept in the ingredients store (Phase 6 step 7
D3, D5, D109).

Each carries a state day to day from each cell's biofix (apple scab from green tip, from apple's stages; fire blight
from January 1; red crown rot from soybean's R1 at the mid planting tier, its default: `modelmaps.SEASON_TIERS`), so
a map can't be finished from a few days' ingredients as `agdata.modelgrid` does for the rest.
Computed on request over the launch box, a map took minutes and, before it was done in blocks, tens of GB (it
crashed the development machine). Instead their outputs and risk are kept for every day of the season
(`modelmaps.SEASON_MODELS`, `season_key`), as `agdata.croptiers` keeps crop stages, and a map reads them.

Each update computes the season from its first day through the last day with weather, a block at a time in the block
pool (`agdata.blocks`), by the same code a map computed on request runs (`modelgrid.model_map(compute=True)`), so a
stored map is what that would have shown. Only the last `croptiers.REWRITE_DAYS` are rewritten once the season
before them is stored. The forecast run gets its own from its first day. Each cell's biofix is kept beside them
(`BIOFIX`, (y, x) date ordinals), and how far each model's season is stored (`through`, in the store's attributes).
"""

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from datetime import date, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import zarr

from agdata import blocks, modelmaps
from agdata.grid import Window
from agdata.store import INGREDIENTS, GridStore
from agmodels.registry import model as find_model

BIOFIX = "_season_biofix"  # in each ingredients store: `{model_id}`, each cell's biofix (y, x) as date ordinals
RUN_STAMP = "seasonmaps.first_day"  # in a forecast run: the first day its seasons were computed from


# The days kept for a model whose spec sets no season: red crown rot's 31 days either side of soybean's R1
SEASONS = {"red-crown-rot": ("05-15", "10-15")}


def season(model_id: str, year: int) -> tuple[date, date]:
    """The days of `year` a model's season is kept for: its spec's season, or `SEASONS`'."""
    spec = find_model(model_id).SPEC
    found = spec.season or SEASONS[model_id]
    first, last = ((int(p) for p in s.split("-")) for s in found)
    return date(year, *first), date(year, *last)


def tier(model_id: str) -> str | None:
    """The planting tier a model's season is kept for (None: it takes none)."""
    return modelmaps.SEASON_TIERS.get(model_id)


def in_season(day: date) -> bool:
    """Whether any season-stored model is in season on `day`."""
    return any(a <= day <= b for a, b in (season(m, day.year) for m in modelmaps.SEASON_MODELS))


def names(model_id: str) -> list[str]:
    """The variables a model's season is kept in: its outputs, then its risk where it has one."""
    spec = find_model(model_id).SPEC
    risk = [modelmaps.season_key(model_id, modelmaps.SEASON_RISK)] if spec.risk is not None else []
    return [modelmaps.season_key(model_id, q.name) for q in spec.outputs] + risk


def update(
    data_dir: Path,
    window: Window,
    year: int,
    last: date,
    run: Path | None = None,
    run_first: date | None = None,
    lock: Callable[[], AbstractContextManager] | None = None,
    since: date | None = None,
    progress: Callable[[int, int], None] | None = None,
    now: datetime | None = None,
) -> list[str]:
    """Computes each model's season of `year` through `last` (the last day with weather) and writes it: the
    archive's, or with `run` the forecast run's days from `run_first` (the archive's weather before, the run's
    from then: the run must be the current one, which `modelgrid` reads). Only days from `since` are written (an
    update's last days, once the season before them is stored). Blocks run while `lock` is held (`blocks.run`'s
    `hold`); returns the variables written. `now` is the clock the maps read the run by (None: now)."""
    root = run if run is not None else data_dir
    store_window = modelmaps._store_window(root, data_dir, year, window)
    with (lock or nullcontext)():
        store = modelmaps.open_or_create(root, year, store_window)  # made here, before a worker writes to it
    parts = blocks.blocks(window)
    chains = []
    spans: dict[str, tuple[date, date, date]] = {}
    for model_id in modelmaps.SEASON_MODELS:
        first, season_end = season(model_id, year)
        end = min(last, season_end)
        write_from = max(first, run_first or first, since or first)
        if write_from > end:
            continue
        spans[model_id] = (first, end, write_from)
        for part in parts:
            task = partial(_season_block, data_dir, root, model_id, first, end, write_from, now, part)
            chains.append([((model_id, part), task)])
    written: list[str] = []

    def handle(key, found: tuple[list[str], np.ndarray]) -> None:
        model_id, part = key
        _, end, write_from = spans[model_id]
        kept, biofix = found
        store.record(kept, write_from, (end - write_from).days + 1, "derived")
        _write_biofix(store, model_id, part, biofix)
        written.extend(n for n in kept if n not in written)

    blocks.run(chains, handle, hold=lock, progress=progress)
    with (lock or nullcontext)():
        for model_id, (_, end, _) in spans.items():
            store.group.attrs[f"{BIOFIX}.{model_id}.through"] = end.isoformat()
        store.mark_current([n for m in modelmaps.SEASON_MODELS for n in names(m)])  # out of season: nothing to keep
    return written


def _season_block(
    data_dir: Path,
    root: Path,
    model_id: str,
    first: date,
    end: date,
    write_from: date,
    now: datetime | None,
    part: Window,
) -> tuple[list[str], np.ndarray]:
    """One model's season over a block, days first..end, written from `write_from` (a task for `blocks.run`);
    returns the variables written and each cell's biofix (y, x)."""
    from agdata import modelgrid  # it reads the seasons this module keeps

    found = modelgrid.model_map(data_dir, model_id, first, end, part, tier=tier(model_id), now=now, compute=True)
    k = (write_from - first).days
    values = {modelmaps.season_key(model_id, name): v[k:] for name, v in found.outputs.items()}
    if found.risk is not None:
        values[modelmaps.season_key(model_id, modelmaps.SEASON_RISK)] = found.risk[k:]
    store = GridStore.open(root, INGREDIENTS, write_from.year, modelmaps.variables())
    store.write(write_from, values, source="derived", window=part, record=False)
    biofix = found.cell_biofix[-1] if found.cell_biofix is not None else np.full(part.shape, np.nan)
    return list(values), np.asarray(biofix, dtype=np.float32)


def _write_biofix(store: GridStore, model_id: str, part: Window, values: np.ndarray) -> None:
    group = store.group.require_group(BIOFIX)
    if model_id not in group:
        group.create_array(
            model_id, shape=store.window.shape, chunks=store.window.shape, dtype="float32", fill_value=np.nan
        )
    array = group[model_id]
    assert isinstance(array, zarr.Array)
    y0, x0 = store.window.local(part.j0, part.i0)
    array[y0 : y0 + part.shape[0], x0 : x0 + part.shape[1]] = values


def stored_through(root: Path, model_id: str, year: int) -> date | None:
    """The last day of `year` a model's season is stored through under `root` (the archive, or a run's), or None."""
    path = INGREDIENTS.path(root, year)
    if not (path / "zarr.json").exists():
        return None
    attrs: dict[str, Any] = dict(zarr.open_group(path, mode="r").attrs)
    found = attrs.get(f"{BIOFIX}.{model_id}.through")
    return date.fromisoformat(str(found)) if found else None


def biofix(root: Path, model_id: str, year: int, window: Window) -> np.ndarray:
    """Each cell's biofix over `window` (date ordinals; NaN where none is stored)."""
    path = INGREDIENTS.path(root, year)
    if not (path / BIOFIX / model_id / "zarr.json").exists():
        return np.full(window.shape, np.nan)
    group = zarr.open_group(path, mode="r")
    attrs: dict[str, Any] = dict(group.attrs)
    w = attrs["window"]
    store_window = Window(j0=w["j0"], j1=w["j1"], i0=w["i0"], i1=w["i1"])
    array = group[f"{BIOFIX}/{model_id}"]
    assert isinstance(array, zarr.Array)
    out = np.full(window.shape, np.nan)
    j0, j1 = max(window.j0, store_window.j0), min(window.j1, store_window.j1)
    i0, i1 = max(window.i0, store_window.i0), min(window.i1, store_window.i1)
    if j0 < j1 and i0 < i1:
        out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = array[
            j0 - store_window.j0 : j1 - store_window.j0, i0 - store_window.i0 : i1 - store_window.i0
        ]
    return out


def refresh(
    data_dir: Path, window: Window, today: date, lock: Callable[[], AbstractContextManager] | None = None
) -> dict[str, list[str]]:
    """What the crop stages job does for these models too (after an update or a new forecast run, D108): the
    archive's season through its last rolled-up day (only the last REWRITE_DAYS rewritten once the season before
    them is stored) and the current forecast run's, while a model is in season. Returns the variables written, by
    where."""
    from agdata import croptiers, series

    done: dict[str, list[str]] = {}
    if not in_season(today) and not in_season(today - timedelta(days=croptiers.REWRITE_DAYS)):
        return done
    rolled = modelmaps._rolled_days(data_dir, today.year)
    if rolled is None:
        return done
    last = date(today.year, 1, 1) + timedelta(days=int(rolled[-1]))
    since = last - timedelta(days=croptiers.REWRITE_DAYS)
    stored = [stored_through(data_dir, m, today.year) for m in modelmaps.SEASON_MODELS]
    ready = all(s is not None and s >= since for s in stored)
    done["archive"] = update(data_dir, window, today.year, last, lock=lock, since=since if ready else None)
    run = series.current_forecast(data_dir)
    if run.path is not None:
        first_day = croptiers.forecast_first_day(run.path)
        stamp = run.path / RUN_STAMP
        if not stamp.exists() or stamp.read_text().strip() != first_day:
            first = date.fromisoformat(first_day)
            end = run.last_hour.date() if run.last_hour is not None else first
            done["run"] = update(data_dir, window, first.year, end, run=run.path, run_first=first, lock=lock)
            stamp.write_text(first_day)
    return done
