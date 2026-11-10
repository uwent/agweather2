"""Crop stages per planting tier on the grid (PLAN.md Phase 5 F3 step 2b, D66; corn and potato D70).

Soybean and spring wheat are day-by-day state machines (soybean's photothermal development, spring wheat's GDD whose
cap switches at Haun 2.0), so a map can't finish one day from a few stored ingredients the way `agdata.modelgrid`
does for the rest: a season over Wisconsin takes 4.65 s for soybean and 1.5 s for spring wheat. Corn and potato can
be finished from ingredients, but every map of a disease gated by their stages (tar spot, the blights) computed them
over every cell (0.2-0.3 s a map, early blight's emergence a season), so they're stored too. Instead each tier's
outputs are kept for every day of the season in the ingredients store (`modelmaps.tier_key`), computed from each
cell's typical planting date for the tier (`agdata.planting.planting_map`; NaN where there's none) with the model's
default options (soybean MG 2.0 until location-adjusted maturity, D66).

Each update recomputes the season from planting (simple and exact; option (a), Ben 2026-11-05): cells are grouped
by planting day and each group runs once from it, over bands of the daily store's chunk rows. `ops.tasks`
runs it in its own job after the ingest, outside the ingest's write lock (computing outside, writing inside), only
while a crop is in season; the forecast run gets its own from its first day, continuing from the archive's days
before. `modelmaps.build` builds a past year's with the rest of its ingredients.

Each update also keeps every cell's first day at each stage (`_reached/{crop}.{tier}`: (stages, y, x) date
ordinals, inf if not reached by the update's last day, NaN unplanted; `reached`), so a map whose biofix is a stage
(the blights' potato emergence) reads it rather than searching the season (`agdata.modelgrid`).
"""

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np
import zarr

from agdata import modelmaps, planting
from agdata.grid import NDFD, Window
from agdata.store import INGREDIENTS, GridStore
from agmodels.crops import CropModel, stage_days
from agmodels.registry import model as find_model

# The days an hourly update rewrites: the ingest's own reach back (`ops.ingest`, the last week) and a margin
REWRITE_DAYS = 10
CROPS = {  # model → `agdata.planting` crop
    "soybean-stages": "soybean",
    "spring-wheat-stages": "spring-wheat",
    "corn-stages": "corn",
    "potato-stages": "potato",
}
RUN_STAMP = "croptiers.first_day"  # in a forecast run: the first day its tiers were computed from
# In each ingredients store: each crop and tier's first day at each stage by cell, (stages, y, x), from the season
# `update` computes (D70): a stage-anchored biofix (the blights' potato emergence) reads it rather than searching
# the stages day by day (~0.15 s a blight map after each update, Phase 5 H4)
REACHED = "_reached"


def season(model_id: str, year: int) -> tuple[date, date]:
    """The model's season (its spec's) in `year`."""
    spec = find_model(model_id).SPEC
    assert spec.season is not None
    first, last = ((int(p) for p in s.split("-")) for s in spec.season)
    return date(year, *first), date(year, *last)


def in_season(day: date) -> bool:
    """Whether any tiered crop is in season on `day` (an update then has something to do)."""
    return any(a <= day <= b for a, b in (season(m, day.year) for m in modelmaps.TIER_MODELS))


def update(
    data_dir: Path,
    window: Window,
    year: int,
    last: date,
    run: Path | None = None,
    run_first: date | None = None,
    lock: Callable[[], AbstractContextManager] | None = None,
    since: date | None = None,
) -> list[str]:
    """Recomputes each tier's season of `year` through `last` (the last day with weather) and writes it: the
    archive's, or with `run` the forecast run's days from `run_first` (weather from the run from then, the
    archive's before). Computing happens outside `lock`, writing inside it; only days from `since` are written (an
    hourly update rewrites the days whose weather can have changed, `REWRITE_DAYS`; each day of each variable is a
    chunk, so writing a season is most of the time). Returns the variables written."""
    root = run if run is not None else data_dir
    store_window = modelmaps._store_window(root, data_dir, year, window)
    rows = modelmaps._chunk_rows(store_window)
    written: list[str] = []
    for model_id, crop in CROPS.items():
        m = find_model(model_id)
        spec = m.SPEC
        options = {o.name: o.default for o in spec.options}
        names = [q.name for q in spec.inputs]
        _, season_end = season(model_id, year)
        end = min(last, season_end)
        # Each tier with planting dates here and days to write: (its planting map, the first day written)
        tiers: dict[str, tuple[np.ndarray, date]] = {}
        for tier in modelmaps.TIERS:
            sown = planting.planting_map(crop, tier, window, season=year)
            if not np.isfinite(sown).any():
                continue
            planted_from = date.fromordinal(int(np.nanmin(sown)))
            write_from = max(planted_from, run_first or planted_from, since or planted_from)
            if write_from <= end:
                tiers[tier] = (sown, write_from)
        if not tiers:
            continue
        # The inputs are read once a band from the earliest planting of any tier, and each tier runs from them
        begin = min(date.fromordinal(int(np.nanmin(sown))) for sown, _ in tiers.values())
        n = (end - begin).days + 1
        for j in range(window.j0, window.j1, rows):
            band = Window(j0=j, j1=min(j + rows, window.j1), i0=window.i0, i1=window.i1)
            y0 = j - window.j0
            inputs = {
                name: modelmaps._filled(name, modelmaps._read(data_dir, run, run_first, name, begin, n, band))
                for name in names
            }
            for tier, (sown, write_from) in tiers.items():
                planted = sown[y0 : y0 + band.shape[0]]
                found = _season(m, spec, inputs, planted, begin, n, band, options)
                k = (write_from - begin).days
                values = {modelmaps.tier_key(model_id, q, tier): v[k:] for q, v in found.items()}
                reached = _reached_days(m, found["stage"], planted, begin)
                with (lock or nullcontext)():
                    store = modelmaps.open_or_create(root, year, store_window)
                    store.write(write_from, values, source="derived", window=band)
                    store.mark_current(list(values))
                    _write_reached(store, model_id, tier, band, reached, end)
                written += [name for name in values if name not in written]
    return written


def _season(m, spec, inputs, planted: np.ndarray, begin: date, n: int, band: Window, options) -> dict[str, np.ndarray]:
    """The model's outputs on days begin.. over the band, each cell from its planting day (NaN before)."""
    lat = NDFD.window_latlon(band)[0]
    dates = [begin + timedelta(days=k) for k in range(n)]
    doy = np.array([d.timetuple().tm_yday for d in dates], dtype=float)
    out = {q.name: np.full((n, *band.shape), np.nan) for q in spec.outputs}
    for u in np.unique(planted[np.isfinite(planted)]):
        cells = planted == u
        k0 = int(u) - begin.toordinal()
        if k0 < 0 or k0 >= n:
            continue
        given = {name: v[k0:, cells] for name, v in inputs.items()}
        given |= {f"{name}_estimated": np.zeros(v.shape, dtype=bool) for name, v in given.items()}
        context = {"day_of_year": doy[k0:, None], "latitude": lat[cells], "year": np.full((n - k0, 1), begin.year)}
        given |= {name: context[name] for name in spec.context}
        found = m.outputs(given, biofix_index=0, **options)
        for name, v in found.items():
            out[name][k0:, cells] = v
    return out


def _reached_days(m, stage: np.ndarray, planted: np.ndarray, begin: date) -> np.ndarray:
    """(stages, y, x): each cell's first day at each of the crop's stages (date ordinals) over the season computed,
    inf where it isn't reached by its end, NaN where there's no planting."""
    count = len(cast(CropModel, m).stages())
    index = stage_days(stage, count)
    found = np.where(np.isfinite(index), begin.toordinal() + index, np.inf)
    return np.where(np.isfinite(planted)[None], found, np.nan).astype(np.float32)


def _write_reached(store: GridStore, model_id: str, tier: str, band: Window, values: np.ndarray, through: date) -> None:
    group = store.group.require_group(REACHED)
    name = f"{model_id}.{tier}"
    if name not in group:
        group.create_array(
            name,
            shape=(values.shape[0], *store.window.shape),
            chunks=(values.shape[0], *store.window.shape),
            dtype="float32",
            fill_value=np.nan,
        )
    array = group[name]
    assert isinstance(array, zarr.Array)
    y0, x0 = store.window.local(band.j0, band.i0)
    array[:, y0 : y0 + band.shape[0], x0 : x0 + band.shape[1]] = values
    array.attrs["through"] = through.isoformat()


def reached(root: Path, model_id: str, tier: str, year: int, window: Window) -> tuple[np.ndarray, date] | None:
    """A crop's first day at each stage by cell, (stages, y, x) over `window` (date ordinals; inf not reached by
    `through`, NaN unplanted), and `through`, from the ingredients store under `root` (the archive, or a forecast
    run's), as `update` wrote them; None if that store has none (one built before they were kept)."""
    path = INGREDIENTS.path(root, year)
    if not (path / REACHED / f"{model_id}.{tier}" / "zarr.json").exists():
        return None
    group = zarr.open_group(path, mode="r")
    attrs: dict[str, Any] = dict(group.attrs)
    w = attrs["window"]
    store_window = Window(j0=w["j0"], j1=w["j1"], i0=w["i0"], i1=w["i1"])
    array = group[f"{REACHED}/{model_id}.{tier}"]
    assert isinstance(array, zarr.Array)
    y0, x0 = window.j0 - store_window.j0, window.i0 - store_window.i0
    values = np.asarray(array[:, y0 : y0 + window.shape[0], x0 : x0 + window.shape[1]], dtype=np.float64)
    return values, date.fromisoformat(str(array.attrs["through"]))


def missing_reached(store: GridStore) -> list[str]:
    """The crops and tiers (`{crop}.{tier}`) whose stages the ingredients store holds without their first days: a
    store built before `update` kept them (D70). A tier not computed yet (out of season, or before this hour's job)
    has neither, so isn't listed."""
    missing = []
    for model_id in CROPS:
        for tier in modelmaps.TIERS:
            name = f"{model_id}.{tier}"
            if (
                store.has_data(modelmaps.tier_key(model_id, "stage", tier)).any()
                and not (store.path / REACHED / name / "zarr.json").exists()
            ):
                missing.append(name)
    return missing


def last_stored(data_dir: Path, year: int, root: Path | None = None) -> date | None:
    """The last day any tier's stage is written for in `year` (the archive's, or a run's under `root`)."""
    try:
        store = GridStore.open(root or data_dir, INGREDIENTS, year, modelmaps.variables(), add_missing=True)
    except FileNotFoundError:
        return None
    days = [
        np.flatnonzero(store.read_meta(f"{modelmaps.tier_key(m, 'stage', t)}.source") > 0)
        for m in modelmaps.TIER_MODELS
        for t in modelmaps.TIERS
    ]
    found = [int(d[-1]) for d in days if d.size]
    return date(year, 1, 1) + timedelta(days=max(found)) if found else None


def refresh(
    data_dir: Path, window: Window, today: date, lock: Callable[[], AbstractContextManager] | None = None
) -> dict[str, list[str]]:
    """What the hourly job does: the archive's season through its last rolled-up day (only the last REWRITE_DAYS
    rewritten once the season before them is stored) and the current forecast run's, while a crop is in season.
    Returns the variables written, by where."""
    from agdata import series  # reads the forecast run

    done: dict[str, list[str]] = {}
    if not in_season(today) and not in_season(today - timedelta(days=REWRITE_DAYS)):
        return done
    rolled = modelmaps._rolled_days(data_dir, today.year)
    if rolled is None:
        return done
    last = date(today.year, 1, 1) + timedelta(days=int(rolled[-1]))
    stored = last_stored(data_dir, today.year)
    since = last - timedelta(days=REWRITE_DAYS)
    done["archive"] = update(
        data_dir, window, today.year, last, lock=lock, since=since if stored is not None and stored >= since else None
    )
    run = series.current_forecast(data_dir)
    if run.path is not None:
        # The run is restitched as observed hours come in (`forecast.stitch` moves its first day forward), so its
        # tiers are recomputed whenever the first day they were computed from isn't the run's now
        first_day = forecast_first_day(run.path)
        stamp = run.path / RUN_STAMP
        if not stamp.exists() or stamp.read_text().strip() != first_day:
            first = date.fromisoformat(first_day)
            end = run.last_hour.date() if run.last_hour is not None else first
            done["run"] = update(data_dir, window, first.year, end, run=run.path, run_first=first, lock=lock)
            stamp.write_text(first_day)
    return done


def forecast_first_day(path: Path) -> str:
    from agdata import forecast

    return forecast.run_info(path)["first_day"]
