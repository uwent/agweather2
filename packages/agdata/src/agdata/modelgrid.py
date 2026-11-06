"""Model maps finished from the stored ingredients (PLAN.md Phase 5 F3, D47, D66): what `/grids/{model}` serves.

A model with ingredients (`agmodels.ingredients`) is finished day by day, so a map of days first..last needs only
those days of each ingredient and a few of its running totals (`agdata.modelmaps`, and `agdata.cumulative` for
degree days and rain):

- an ingredient's daily values are read as stored; one the running totals stand in for (degree days, rye's rain)
  is the change in its total over the day;
- an accumulation from the biofix `b` to day `d` is a difference of running totals from January 1,
  `T(d) − T(b − 1)` (zero before January 1), summed year by year when the season crosses New Year (rye); a `sum`
  or `mean` over N days starts at `max(b, d − N + 1)`, and a mean divides by the days with a value (`.known`);
- the context (`day_of_year`, `year`, `latitude`, `biofix_day_of_year`), then the model's `finish` and `risk`,
  exactly as `runner.run` calls them at a point.

The biofix is the spec's default for the season each day falls in (D66: maps take each place's settings, never a
user's dates); a day before it is missing, as a point returns nothing before its biofix. Without a planting tier
yet, a stage-gated disease isn't gated and a stage-anchored biofix (the blights' potato emergence) is the spec's
date, as at a point given no planting date (`api.runs`). Cells outside a model's states are missing. The forecast's
days come from the current run's own stores, which continue the archive's totals, as `series.grid_days` splits
them.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from typing import cast

import numpy as np

from agdata import croptiers, modelmaps, planting, regions, series
from agdata import units as agunits
from agdata.grid import Window
from agdata.grids import cube_terms
from agdata.store import CUMULATIVE, DAILY, INGREDIENTS, StoreLayout
from agmodels.crops import CropModel, disease_susceptibility, stage_days
from agmodels.ingredients import Accumulation, Ingredient, until_day
from agmodels.registry import all_models
from agmodels.registry import model as find_model
from agmodels.runner import default_biofix
from agmodels.spec import Model, ModelSpec

# Models with ingredients that aren't model layers, and why
NOT_MAPPED = {
    "degree-days": "custom degree days are the degree_days layer",
}
# Options that describe the place rather than a scenario: maps use each place's (D66; the model's default until
# location-adjusted maturity lands)
PLACE_OPTIONS = ("black_layer_gdd", "maturity_group")
# The precision a map output is given to, by unit
OUTPUT_STEPS = {
    "index": 0.001,
    "percent": 0.1,
    "degF_day": 0.1,
    "degC_day": 0.1,
    "hour": 0.1,
    "mm": 0.1,
    "degC": 0.01,
    "day": 1,
    "lb_ac": 1,
}


def mapped() -> dict[str, Model]:
    """The models with a map: every one with ingredients but those in NOT_MAPPED, the crops stored per planting
    tier (`agdata.croptiers`) and those computed on request (ON_REQUEST)."""
    return {
        i: m
        for i, m in all_models().items()
        if (m.SPEC.ingredients and i not in NOT_MAPPED) or i in modelmaps.TIER_MODELS or i in ON_REQUEST
    }


@dataclass(kw_only=True)
class ModelDays:
    """A model over the window on days first..last: each output, the risk and its level as (days, y, x)."""

    dates: list[date]
    kinds: list[str | None]
    outputs: dict[str, np.ndarray]
    risk: np.ndarray | None  # what the model's `risk` returns: a level, or a continuous value
    level: np.ndarray | None  # the risk as an index into the spec's levels
    biofix: list[date | None]  # per day, the spec's biofix for its season (None: the model has none)
    # per day and cell, the biofix used (date ordinals; NaN: none, inf: its crop stage isn't reached yet)
    cell_biofix: np.ndarray | None = None
    in_season: list[bool] | None  # per day, from the spec's season; None if it has none
    in_region: np.ndarray | None  # (y, x): cells in the model's states; None if it's valid anywhere
    stale: bool  # an ingredient a newer version of its model hasn't rebuilt yet (D29)
    sources: tuple[str, ...]
    forecast: series.Forecast
    run_from: int  # the first day read from the forecast run
    reads: int = 0  # map-days read, for timing
    options: dict[str, str] = field(default_factory=dict)
    accumulated: dict[str, np.ndarray] = field(default_factory=dict)  # each accumulation, (days, y, x)


def model_days(
    data_dir: Path,
    model_id: str,
    first: date,
    last: date,
    window: Window,
    options: Mapping[str, str] | None = None,
    now=None,
    stores: series.Stores | None = None,
    cell_biofix: Callable[[date], np.ndarray] | None = None,
) -> ModelDays:
    """A model's outputs and risk over the window on days first..last, finished from the stored ingredients.
    `cell_biofix(day)` gives each cell's biofix for the season `day` falls in (a planting tier's date, a crop
    stage's), as date ordinals: NaN takes the spec's default, inf is a stage not reached yet (not started)."""
    m = find_model(model_id)
    spec = m.SPEC
    if not spec.ingredients:
        raise ValueError(f"{model_id} has no ingredients to map")
    opts = {o.name: o.default for o in spec.options} | dict(options or {})
    n = (last - first).days + 1
    dates = [first + timedelta(days=k) for k in range(n)]
    stores = stores or series.Stores([])
    stores.names |= {q.name for q in spec.inputs} | set(read_names(model_id))  # named before any store opens
    base = series.grid_days(data_dir, DAILY, spec.inputs[0].name, first, last, window, now, stores, read=False)
    reader = _Reader(
        stores=stores,
        data_dir=data_dir,
        run_path=base.forecast.path,
        cut=first + timedelta(days=base.run_from),
        window=window,
    )
    biofix = [default_biofix(spec, d) for d in dates]
    cells = np.full((n, *window.shape), np.nan)
    for k, (d, b) in enumerate(zip(dates, biofix, strict=True)):
        own = cell_biofix(d) if cell_biofix is not None else None
        default = np.nan if b is None else float(b.toordinal())
        cells[k] = default if own is None else np.where(np.isnan(own), default, own)
    values = {i.name: reader.daily(spec, i, dates) for i in spec.ingredients}
    for a in spec.accumulations:
        values[a.name] = _accumulated(reader, spec, a, dates, cells)
    shape = (n, 1, 1)
    values["day_of_year"] = np.array([d.timetuple().tm_yday for d in dates], dtype=float).reshape(shape)
    values["year"] = np.array([d.year for d in dates], dtype=float).reshape(shape)
    if "latitude" in spec.context:
        from agdata.grid import NDFD

        values["latitude"] = NDFD.window_latlon(window)[0][None].astype(float)
    values["biofix_day_of_year"] = _day_of_year(cells)

    outputs = {k: np.broadcast_to(v, (n, *window.shape)).copy() for k, v in m.finish(values, **opts).items()}  # type: ignore[attr-defined]
    risk = level = None
    if spec.risk is not None:
        accumulated = {a.name: values[a.name] for a in spec.accumulations}
        risk = np.broadcast_to(
            np.asarray(m.risk(outputs | accumulated, biofix_index=0, **opts), dtype=float), (n, *window.shape)
        ).copy()
        thresholds = spec.risk.thresholds
        found = np.searchsorted(np.asarray(thresholds), risk, side="right") if thresholds else risk
        level = np.where(np.isfinite(risk), found, np.nan).astype(float)
    in_region = _region_mask(spec, window)
    ordinals = np.array([d.toordinal() for d in dates], dtype=float).reshape(shape)
    before = ordinals < cells  # NaN (no biofix) compares False
    for v in (*outputs.values(), *(x for x in (risk, level) if x is not None)):
        v[before] = np.nan  # not started, as at a point: nothing before the season's biofix
        if in_region is not None:
            v[:, ~in_region] = np.nan
    kinds = list(base.kinds)
    first_ingredient = values[spec.ingredients[0].name]
    for k in range(n):  # a day with no ingredient anywhere has nothing to show (the run's last, partial day)
        if np.isnan(first_ingredient[k]).all():
            kinds[k] = None
    return ModelDays(
        dates=dates,
        kinds=kinds,
        outputs=outputs,
        risk=risk,
        level=level,
        biofix=biofix,
        cell_biofix=cells if cell_biofix is not None else None,
        in_season=None if spec.season is None else [_in_season(spec, d) for d in dates],
        in_region=in_region,
        stale=reader.stale,
        sources=base.sources,
        forecast=base.forecast,
        run_from=base.run_from,
        reads=reader.reads,
        options=opts,
        accumulated={a.name: values[a.name] for a in spec.accumulations},
    )


def read_names(model_id: str) -> list[str]:
    """Every store variable a model's map reads: its stored ingredients, their totals and counts, and the running
    totals that stand in for the rest."""
    spec = find_model(model_id).SPEC
    crop = planting.planting_crop(spec)
    tiers = (
        [
            modelmaps.tier_key(crop[0], q.name, t)
            for t in modelmaps.TIERS
            for q in find_model(crop[0]).SPEC.outputs
            if crop is not None and crop[0] in modelmaps.TIER_MODELS
        ]
        if crop is not None
        else []
    )
    stored, totals = stamped(model_id)
    stored += tiers
    accumulated = {a.of: a for a in spec.accumulations}
    extra = []
    for i in spec.ingredients:
        k = modelmaps.key(model_id, i)
        if k in stored and i.name in accumulated:
            extra.append(f"{k}.total")
            if any(a.how == "mean" and a.of == i.name for a in spec.accumulations):
                extra.append(f"{k}.known")
    return [*stored, *extra, *totals]


def tiered(model_id: str) -> tuple[str, str] | None:
    """(crop model, crop) whose planting tier a model's map takes (`agdata.planting.planting_crop`), or None."""
    found = planting.planting_crop(find_model(model_id).SPEC)
    return found if found is not None and found[0] in mapped() else None


@dataclass(frozen=True, kw_only=True)
class _Planting:
    """A crop planted at a tier over the window: each cell's date per season (ordinals; NaN where none)."""

    crop_id: str  # its stage model
    crop: str  # `agdata.planting`'s name
    tier: str
    window: Window

    def __call__(self, day: date) -> np.ndarray:
        return planting.planting_map(self.crop, self.tier, self.window, season=day.year)


def model_map(
    data_dir: Path,
    model_id: str,
    first: date,
    last: date,
    window: Window,
    options: Mapping[str, str] | None = None,
    tier: str | None = "mid",
    now=None,
    stores: series.Stores | None = None,
) -> ModelDays:
    """A model's map with each place's own settings (D66): with a planting `tier` (early, mid, late; None for none),
    a crop model starts at each cell's typical planting date (soybean's and spring wheat's stored per tier,
    `agdata.croptiers`), a stage-anchored biofix is the day the crop reaches that stage from it (not started until
    then), and a stage-gated disease gets `susceptibility` (D33) from the crop's stages. Cells without a typical
    date take the spec's defaults, as a point given no planting date (a stored crop has no stages there)."""
    spec = find_model(model_id).SPEC
    crop = tiered(model_id)
    sown = None if tier is None or crop is None else _Planting(crop_id=crop[0], crop=crop[1], tier=tier, window=window)
    if model_id in modelmaps.TIER_MODELS:
        if sown is not None:
            return _stored_days(data_dir, sown, first, last, now, stores)
        if not spec.ingredients:
            raise ValueError(f"{model_id} is stored per planting tier: give one")
        # corn and potato without a tier: the spec's dates, finished from their ingredients as any model
    cell_biofix = None
    if sown is not None and sown.crop_id == model_id:
        cell_biofix = sown
    elif sown is not None and spec.biofix_stage is not None:
        cell_biofix = _stage_reached(data_dir, sown, spec.biofix_stage[1], last, now)
    if model_id in ON_REQUEST:
        found = _anchored_days(data_dir, model_id, first, last, window, now, stores, cell_biofix)
    else:
        found = model_days(
            data_dir, model_id, first, last, window, options, now=now, stores=stores, cell_biofix=cell_biofix
        )
    if sown is not None and spec.susceptible is not None:
        found.outputs["susceptibility"] = _susceptibility(data_dir, spec, sown, first, last, now)
    return found


def _base(data_dir, spec: ModelSpec, first: date, last: date, window: Window, now, stores, names=()):
    """The days' kinds and forecast run (`series.grid_days` on the model's first input), and a reader of stores
    split at the run the same way."""
    stores = stores or series.Stores([])
    stores.names |= {q.name for q in spec.inputs} | set(names)  # named before any store opens
    base = series.grid_days(data_dir, DAILY, spec.inputs[0].name, first, last, window, now, stores, read=False)
    reader = _Reader(
        stores=stores,
        data_dir=data_dir,
        run_path=base.forecast.path,
        cut=first + timedelta(days=base.run_from),
        window=window,
    )
    return base, reader


def _finished(spec, base, dates, outputs, risk, level, reader, cells=None) -> ModelDays:
    """A ModelDays from outputs computed outside `model_days`: missing days (nothing stored anywhere) have no kind."""
    primary = outputs[spec.outputs[0].name]
    kinds = [None if np.isnan(primary[k]).all() else kind for k, kind in enumerate(base.kinds)]
    return ModelDays(
        dates=dates,
        kinds=kinds,
        outputs=outputs,
        risk=risk,
        level=level,
        biofix=[default_biofix(spec, d) for d in dates],
        cell_biofix=cells,
        in_season=None if spec.season is None else [_in_season(spec, d) for d in dates],
        in_region=None,
        stale=reader.stale,
        sources=base.sources,
        forecast=base.forecast,
        run_from=base.run_from,
        reads=reader.reads,
    )


def _stored_days(data_dir, sown: _Planting, first: date, last: date, now, stores, only=None) -> ModelDays:
    """A tier-stored crop model's outputs (`agdata.croptiers`) on days first..last: all of them, or those named in
    `only` (a crop's stages for gating need `stage` alone; each output is a read of every day)."""
    spec = find_model(sown.crop_id).SPEC
    wanted = [q for q in spec.outputs if only is None or q.name in only]
    names = [modelmaps.tier_key(spec.id, q.name, sown.tier) for q in wanted]
    base, reader = _base(data_dir, spec, first, last, sown.window, now, stores, names)
    dates = [first + timedelta(days=k) for k in range(len(base.steps))]
    outputs = {}
    for q, name in zip(wanted, names, strict=True):
        found = reader.days(INGREDIENTS, name, dates)
        outputs[q.name] = np.stack([found[d] for d in dates])
    planted = np.stack([sown(d) for d in dates])  # the biofix is the planting
    return _finished(spec, base, dates, outputs, None, None, reader, cells=planted)


# Models with neither ingredients nor stored outputs, computed on request from the days around their biofix
ON_REQUEST = ("red-crown-rot",)


def _anchored_days(data_dir, model_id: str, first: date, last: date, window: Window, now, stores, cell_biofix):
    """A model anchored to a crop stage (red crown rot: 31 days either side of R1), each cell from its own biofix:
    cells grouped by biofix day, each group run over the days around it, as `runner.run` runs a point."""
    m = find_model(model_id)
    spec = m.SPEC
    base, reader = _base(data_dir, spec, first, last, window, now, stores)
    n = (last - first).days + 1
    dates = [first + timedelta(days=k) for k in range(n)]
    default = default_biofix(spec, first)
    cells = np.full(window.shape, np.nan if default is None else float(default.toordinal()))
    if cell_biofix is not None:
        own = cell_biofix(first)
        cells = np.where(np.isnan(own), cells, own)
    reach = spec.lookback_days  # days of weather before the biofix a run reads
    outputs = {q.name: np.full((n, *window.shape), np.nan) for q in spec.outputs}
    starts = np.unique(cells[np.isfinite(cells)])
    if starts.size:
        a = min(date.fromordinal(int(starts.min())) - timedelta(days=reach), first)
        days = [a + timedelta(days=k) for k in range((last - a).days + 1)]
        raw = {q.name: reader.days(DAILY, q.name, days) for q in spec.inputs}
        series_ = {name: np.stack([v[d] for d in days]) for name, v in raw.items()}
        filled = {name: modelmaps._filled(name, v.copy()) for name, v in series_.items()}
        for u in starts:
            biofix = date.fromordinal(int(u))
            if biofix > last:
                continue
            group = cells == u
            k0 = max(0, (biofix - a).days - reach)
            given = {name: v[k0:, group] for name, v in filled.items()}
            given |= {f"{name}_estimated": np.isnan(series_[name][k0:, group]) for name in filled}
            found = m.outputs(given, biofix_index=(biofix - a).days - k0)
            shown = (first - a).days - k0
            for name, v in found.items():
                outputs[name][:, group] = np.asarray(v, dtype=float)[shown : shown + n]
    ordinals = np.array([d.toordinal() for d in dates], dtype=float)[:, None, None]
    before = ordinals < cells[None]  # not started, as at a point (inf: R1 not reached)
    for v in outputs.values():
        v[before | np.isnan(cells)[None]] = np.nan
    risk = level = None
    if spec.risk is not None:
        risk = np.asarray(m.risk(outputs), dtype=float)
        level = np.where(np.isfinite(risk), risk, np.nan)
    return _finished(spec, base, dates, outputs, risk, level, reader, cells=np.broadcast_to(cells, (n, *window.shape)))


def _crop_stages(data_dir, sown: _Planting, first: date, last: date, now) -> np.ndarray:
    """The crop's `stage` (days × cells) from each cell's planting at the tier (NaN before it, or without one)."""
    if sown.crop_id in modelmaps.TIER_MODELS:
        return _stored_days(data_dir, sown, first, last, now, None, only=("stage",)).outputs["stage"]

    def only_planted(day: date) -> np.ndarray:
        p = sown(day)
        return np.where(np.isnan(p), np.inf, p)  # no typical date: no crop

    crop = model_days(data_dir, sown.crop_id, first, last, sown.window, now=now, cell_biofix=only_planted)
    return crop.outputs["stage"]


def _stage_reached(data_dir, sown: _Planting, code: str, last: date, now):
    """Each cell's first day at the crop stage `code` from its planting (date ordinals; inf if not reached by
    `last`, NaN where there's no planting), as a biofix: `cell_biofix(day)`, per season. Found over the season once
    per data stamp (cached), so each day's map of a stage-anchored model reuses it."""
    crop = cast(CropModel, find_model(sown.crop_id))
    k = [s.code for s in crop.stages()].index(code)
    seasons: dict[int, np.ndarray] = {}

    def biofix(day: date) -> np.ndarray:
        if day.year not in seasons:
            p = sown(day)
            stored = _stored_reached(data_dir, sown, day.year, now) if np.isfinite(p).any() else None
            if not np.isfinite(p).any():
                seasons[day.year] = p
            elif stored is not None:
                # As `update` kept them (D70): a day after the request's last counts as not reached yet
                seasons[day.year] = np.where(stored[k] > last.toordinal(), np.inf, stored[k])
            else:
                # The season's, whatever the request's last day: a day after it counts as not reached yet
                begin, end = date.fromordinal(int(np.nanmin(p))), date(day.year, 12, 31)
                ingredients, totals = _crop_stamped(sown)
                stamp = series.last_written(
                    data_dir, begin, end, totals=totals, ingredients=ingredients, now=now, hourly=[]
                )
                key = (str(data_dir), sown, k, stamp)
                if key not in _REACHED:
                    while len(_REACHED) >= _REACHED_KEEP:
                        _REACHED.pop(next(iter(_REACHED)))
                    _REACHED[key] = _first_day_at(data_dir, sown, k, p, begin, end, now)
                found = _REACHED[key]
                seasons[day.year] = np.where(found > last.toordinal(), np.inf, found)
        return seasons[day.year]

    return biofix


def _stored_reached(data_dir, sown: _Planting, year: int, now) -> np.ndarray | None:
    """A stored crop's first day at each stage (`croptiers.reached`): the current forecast run's, which runs on
    through the forecast, else the archive's; None for a crop not stored, or stores from before they were kept."""
    if sown.crop_id not in modelmaps.TIER_MODELS:
        return None
    run = series.current_forecast(data_dir, now).path
    for root in (run, data_dir):
        found = None if root is None else croptiers.reached(root, sown.crop_id, sown.tier, year, sown.window)
        if found is not None:
            return found[0]
    return None


def _crop_stamped(sown: _Planting) -> tuple[list[str], list[str]]:
    """What a crop's stages are read from: (ingredient store variables, running totals)."""
    if sown.crop_id in modelmaps.TIER_MODELS:
        spec = find_model(sown.crop_id).SPEC
        return [modelmaps.tier_key(sown.crop_id, q.name, sown.tier) for q in spec.outputs], []
    return stamped(sown.crop_id)


# The days a stage is reached, per crop, planting, span and data stamp (the stores' write times and the run): a
# blight map reads its emergence many times a day and the season's changes only with new data
_REACHED: dict[tuple, np.ndarray] = {}
_REACHED_KEEP = 32
STAGE_BLOCK_DAYS = 15  # days of a crop's stages computed at once while finding when each cell reaches one


def _first_day_at(data_dir, sown: _Planting, k: int, p: np.ndarray, begin: date, end: date, now):
    """Each planted cell's first day at stage index `k` (date ordinals; inf if not by `end`, NaN unplanted),
    computed block by block from the earliest planting until every planted cell is there."""
    out = np.where(np.isnan(p), np.nan, np.inf)
    a = begin
    while a <= end and np.isinf(out).any():
        b = min(end, a + timedelta(days=STAGE_BLOCK_DAYS - 1))
        stage = _crop_stages(data_dir, sown, a, b, now)
        if np.isnan(stage).all():
            break  # past the archive and forecast
        index = stage_days(stage, k + 1)[k]
        newly = np.isinf(out) & np.isfinite(index)
        out[newly] = a.toordinal() + index[newly]
        a = b + timedelta(days=1)
    return out


def _susceptibility(data_dir, spec: ModelSpec, sown: _Planting, first: date, last: date, now) -> np.ndarray:
    """D33's susceptibility on days first..last, from the crop's stages over the crop's margin either side."""
    assert spec.susceptible is not None
    crop = cast(CropModel, find_model(spec.susceptible.crop))
    margin = timedelta(days=crop.MARGIN_DAYS)
    stage = _crop_stages(data_dir, sown, first - margin, last + margin, now)
    gate = disease_susceptibility(spec, stage)
    assert gate is not None
    return gate[crop.MARGIN_DAYS : crop.MARGIN_DAYS + (last - first).days + 1]


def stamped(model_id: str) -> tuple[list[str], list[str]]:
    """What a model's map reads, for its ETag: (ingredient store variables, running totals)."""
    spec = find_model(model_id).SPEC
    stored, totals = [], []
    for i in spec.ingredients:
        if i.degree_days is not None:
            totals += [t for t in _cube(i) if t]
        elif i.cumulative is not None:
            totals.append(i.cumulative)
        else:
            stored.append(modelmaps.key(model_id, i))
    return stored, totals


# --- Reading -------------------------------------------------------------------------------------------------------


@dataclass(kw_only=True)
class _Reader:
    """Reads days of a store's variable over the window, the archive's before `cut` and the run's from it, each
    contiguous run of days once."""

    stores: series.Stores
    data_dir: Path
    run_path: Path | None
    cut: date
    window: Window
    stale: bool = False
    reads: int = 0
    cache: dict[tuple[str, str, date], np.ndarray] = field(default_factory=dict)

    def days(self, layout: StoreLayout, name: str, days: Iterable[date]) -> dict[date, np.ndarray]:
        wanted = sorted(set(days))
        missing = [d for d in wanted if (layout.kind, name, d) not in self.cache]
        for run in _runs(missing):
            cut = sum(d < self.cut for d in run)
            values, stale, _ = series.read_split(
                self.stores, self.data_dir, self.run_path, layout, name, run, cut, self.window
            )
            self.stale |= bool(stale.any())
            self.reads += len(run)
            for k, d in enumerate(run):
                self.cache[(layout.kind, name, d)] = values[k].astype(np.float64)
        return {d: self.cache[(layout.kind, name, d)] for d in wanted}

    def total(self, ingredient: Ingredient, model_id: str, days: Iterable[date]) -> dict[date, np.ndarray]:
        """An ingredient's running total from January 1 on each day, in its unit."""
        days = list(days)
        if ingredient.degree_days is not None:
            cube, minus = _cube(ingredient)
            out = self.days(CUMULATIVE, cube, days)
            if minus is not None:
                less = self.days(CUMULATIVE, minus, days)
                out = {d: out[d] - less[d] for d in out}
            return {d: agunits.convert(v, "degF_day", ingredient.unit) for d, v in out.items()}
        if ingredient.cumulative is not None:
            return self.days(CUMULATIVE, ingredient.cumulative, days)
        return self.days(modelmaps.INGREDIENTS, f"{modelmaps.key(model_id, ingredient)}.total", days)

    def known(self, ingredient: Ingredient, model_id: str, days: Iterable[date]) -> dict[date, np.ndarray]:
        """The running count of days with a value from January 1 (an averaged ingredient's)."""
        return self.days(modelmaps.INGREDIENTS, f"{modelmaps.key(model_id, ingredient)}.known", days)

    def daily(self, spec: ModelSpec, ingredient: Ingredient, dates: list[date]) -> np.ndarray:
        """An ingredient's values on `dates`: as stored, or its running total's change over each day."""
        if ingredient.degree_days is None and ingredient.cumulative is None:
            found = self.days(modelmaps.INGREDIENTS, modelmaps.key(spec.id, ingredient), dates)
            return np.stack([found[d] for d in dates])
        return _spans(lambda days: self.total(ingredient, spec.id, days), [(d, d) for d in dates], self.window)


def _runs(days: list[date]) -> list[list[date]]:
    """Sorted days as runs of consecutive days."""
    runs: list[list[date]] = []
    for d in days:
        if runs and (d - runs[-1][-1]).days == 1:
            runs[-1].append(d)
        else:
            runs.append([d])
    return runs


def _cube(ingredient: Ingredient) -> tuple[str, str | None]:
    dd = ingredient.degree_days
    assert dd is not None
    terms = cube_terms(dd.method, dd.base_f, dd.upper_f)
    if terms is None:
        raise ValueError(f"{ingredient.name}: no running total for {dd}")
    return terms


# --- Accumulating --------------------------------------------------------------------------------------------------


def _spans(total, pairs: list[tuple[date | None, date]], window: Window) -> np.ndarray:
    """Per (a, d) pair, the sum of daily values over days a..d from running totals since January 1 (`total(days)` →
    {day: map}), year by year; NaN where a is None or after d."""
    needed: set[date] = set()
    segments: list[list[tuple[date, date]]] = []
    for a, d in pairs:
        parts = []
        if a is not None and a <= d:
            for year in range(a.year, d.year + 1):
                lo, hi = max(a, date(year, 1, 1)), min(d, date(year, 12, 31))
                parts.append((lo, hi))
                needed.add(hi)
                if (lo.month, lo.day) != (1, 1):
                    needed.add(lo - timedelta(days=1))
        segments.append(parts)
    found = total(needed) if needed else {}
    out = np.full((len(pairs), *window.shape), np.nan)
    for k, parts in enumerate(segments):
        if not parts:
            continue
        acc = np.zeros(window.shape)
        for lo, hi in parts:
            # A missing day adds nothing (`agmodels.accumulate`), so a total the day before the store's first day
            # of weather is zero; a segment's end without a total (a year the archive lacks) leaves it unknown
            end = found[hi]
            if (lo.month, lo.day) != (1, 1):
                end = end - np.nan_to_num(found[lo - timedelta(days=1)])
            acc = acc + end
        out[k] = acc
    return out


def _accumulated(reader: _Reader, spec: ModelSpec, a: Accumulation, dates: list[date], biofix: np.ndarray):
    """An accumulation from each cell's biofix (`biofix`: days × cells of date ordinals; NaN before it or without
    one), as `agmodels.ingredients.accumulate` computes it. Cells are grouped by their start day, so a planting
    tier's county dates cost a read each."""
    ingredient = next(i for i in spec.ingredients if i.name == a.of)
    if spec.biofix is None:
        raise ValueError(f"{spec.id}: an accumulation needs a biofix")
    out = np.full(biofix.shape, np.nan)

    def total(days):
        return reader.total(ingredient, spec.id, days)

    def known(days):
        return reader.known(ingredient, spec.id, days)

    for k, d in enumerate(dates):
        b = biofix[k]
        started = np.isfinite(b) & (b <= d.toordinal())
        if not started.any():
            continue
        start = b if a.how == "total" else np.maximum(b, (d - timedelta(days=a.days - 1)).toordinal())
        starts = np.unique(start[started])
        firsts = [date.fromordinal(int(u)) for u in starts]
        ends = [min(d, until_day(a.until, f)) if a.until is not None else d for f in firsts]
        pairs: list[tuple[date | None, date]] = list(zip(firsts, ends, strict=True))
        sums = _spans(total, pairs, reader.window)
        if a.how == "mean":
            counts = _spans(known, pairs, reader.window)
            with np.errstate(invalid="ignore", divide="ignore"):
                sums = np.where(counts > 0, sums / counts, np.nan)
        for u, v in zip(starts, sums, strict=True):
            cells = started & (start == u)
            out[k][cells] = v[cells]
    return out


def _day_of_year(ordinals: np.ndarray) -> np.ndarray:
    """Day of year of each date ordinal (NaN and inf stay NaN)."""
    out = np.full(ordinals.shape, np.nan)
    finite = np.isfinite(ordinals)
    for u in np.unique(ordinals[finite]):
        out[ordinals == u] = date.fromordinal(int(u)).timetuple().tm_yday
    return out


def _region_mask(spec: ModelSpec, window: Window) -> np.ndarray | None:
    return _states_mask(spec.region, window) if spec.region else None


@cache
def _states_mask(states: tuple[str, ...], window: Window) -> np.ndarray:
    """Cells in any of the states (cached: ~0.2 s for a box and 17 states)."""
    found = [regions.find(code) for code in states]
    mask = np.any([regions.mask(r, window) for r in found if r is not None], axis=0)
    mask.setflags(write=False)
    return mask


def _in_season(spec: ModelSpec, day: date) -> bool:
    assert spec.season is not None
    md = (day.month, day.day)
    first, last = (tuple(int(p) for p in s.split("-")) for s in spec.season)
    return first <= md <= last if first <= last else (md >= first or md <= last)
