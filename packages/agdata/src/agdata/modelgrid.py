"""Model maps finished from the stored ingredients (Phase 5 F3, D47, D66): what `/grids/{model}` serves.

A model with ingredients (`agmodels.ingredients`) is finished day by day, so a map of days first..last needs only
those days of each ingredient and a few of its running totals (`agdata.modelmaps`, and `agdata.cumulative` for
degree days and rain):

- an ingredient's daily values are read as stored; one the running totals stand in for (degree days, a catalog variable)
  is the change in its total over the day;
- an accumulation from the biofix `b` to day `d` is a difference of running totals from January 1,
  `T(d) − T(b − 1)` (zero before January 1), summed year by year when the season crosses New Year (rye); a `sum`
  or `mean` over N days starts at `max(b, d − N + 1)`, and a mean divides by the days with a value (`.known`);
- the context (`day_of_year`, `year`, `latitude`, `biofix_day_of_year`, and each cell's normals the model reads,
  `ModelSpec.place_normals`, from the normal maps), then the model's `finish` and `risk`, exactly as `runner.run`
  calls them at a point.

`model_days` takes the spec's default biofix for the season each day falls in, or one per cell (`cell_biofix`); a
day before it is missing, as a point returns nothing before its biofix. Maps take each place's settings, never a
user's dates (D66). `model_map` adds the planting tier (early, mid, late; `/grids`' `planting=`): a crop model
starts at each cell's typical planting date, a stage-anchored biofix (the blights' potato emergence) is each cell's
first day at that stage, read from what `agdata.croptiers` stored (`_reached`), and a stage-gated disease gets
`susceptibility`. Soybean, spring wheat, corn and potato stages are read as stored per tier (D70); red crown rot,
apple scab and fire blight carry a state from each cell's biofix (`ON_REQUEST`): their stored seasons are read (`agdata.seasonmaps`; red crown rot's mid tier only), and computed on request, a block at a time, past what's stored. With `tier=None` nothing is gated and a stage-anchored
biofix is the spec's date, as at a point given no planting date (`api.runs`). Cells outside a model's states are
missing. The forecast's days come from the current run's own stores, which continue the archive's totals, as
`series.grid_days` splits them.

Each map counts, per cell and day, the days of its inputs still missing after the gap fill that the day's results rest
on (`ModelDays.missing_days`, D56), from running counts as its accumulations are: `temperature_missing_days` for
degree days and crop stages, a stored ingredient's `….missing`, a stored season's own, or its inputs when computed on
request. Its reads never mark the map stale: a store built before the counts reads as none counted.
"""

from collections.abc import Callable, Iterable, Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from typing import cast

import numpy as np

from agdata import (
    blocks,
    climatology,
    croptiers,
    modelmaps,
    normals,
    planting,
    regions,
    seasonmaps,
    seasonopens,
    series,
)
from agdata import units as agunits
from agdata.catalog import CUMULATIVE_VARIABLES
from agdata.grid import Window
from agdata.grids import cube_terms
from agdata.store import CUMULATIVE, DAILY, INGREDIENTS, StoreLayout
from agmodels import seasons
from agmodels.crops import CropModel, disease_susceptibility
from agmodels.ingredients import Accumulation, Ingredient, until_day
from agmodels.registry import all_models
from agmodels.registry import model as find_model
from agmodels.runner import default_biofix, january_crop_start, unfilled_gaps
from agmodels.spec import Model, ModelSpec, OpensOnCropStage, OpensOnDegreeDays

# The running count of days without a usable minimum and maximum temperature (`agdata.cumulative`): degree days' and
# crop stages' days missing past the gap fill (D56)
TEMPERATURE_MISSING = "temperature_missing_days"

# Models with ingredients that aren't model layers, and why
NOT_MAPPED = {
    "custom-degree-days": "custom degree days are the degree_days layer",
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
    "degC_hour": 0.1,
    "hour": 0.1,
    "mm": 0.1,
    "degC": 0.01,
    "day": 1,
    "lb_ac": 1,
    "plants_ac": 1,
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
    in_season: list[bool] | None  # per day, from the spec's season (opening on the region's day); None if it has none
    # (y, x): the calendar slot each cell's insect season opens on (`season_opens`); None for other models
    opens: np.ndarray | None = None
    in_region: np.ndarray | None  # (y, x): cells in the model's states; None if it's valid anywhere
    stale: bool  # an ingredient a newer version of its model hasn't rebuilt yet (D29)
    sources: tuple[str, ...]
    forecast: series.Forecast
    run_from: int  # the first day read from the forecast run
    reads: int = 0  # map-days read, for timing
    options: dict[str, str] = field(default_factory=dict)
    accumulated: dict[str, np.ndarray] = field(default_factory=dict)  # each accumulation, (days, y, x)
    # each normal of the place the model reads (`ModelSpec.place_normals`), (y, x), NaN where the normals don't reach
    place: dict[str, np.ndarray] = field(default_factory=dict)
    # (days, y, x): the days still missing after the gap fill (D56) that each day's results rest on, from each cell's
    # biofix (its accumulations' spans, or the season's state): a running total added nothing for them. NaN where it
    # isn't counted (not started, a model without accumulations); None if the map counts none
    missing_days: np.ndarray | None = None


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
    base, reader = _base(data_dir, spec, first, last, window, now, stores, read_names(model_id))
    biofix = [default_biofix(spec, d) for d in dates]
    cells = np.full((n, *window.shape), np.nan)
    for k, (d, b) in enumerate(zip(dates, biofix, strict=True)):
        own = cell_biofix(d) if cell_biofix is not None else None
        default = np.nan if b is None else float(b.toordinal())
        cells[k] = default if own is None else np.where(np.isnan(own), default, own)
    values = {i.name: reader.daily(spec, i, dates) for i in spec.ingredients}
    for a in spec.accumulations:
        values[a.name] = _accumulated(reader, spec, a, dates, cells)
    missing_days = _missing_days(reader, spec, dates, cells)
    shape = (n, 1, 1)
    values["day_of_year"] = np.array([d.timetuple().tm_yday for d in dates], dtype=float).reshape(shape)
    values["year"] = np.array([d.year for d in dates], dtype=float).reshape(shape)
    if "latitude" in spec.context:
        from agdata.grid import NDFD

        values["latitude"] = NDFD.window_latlon(window)[0][None].astype(float)
    values["biofix_day_of_year"] = _day_of_year(cells)
    place = normals.place_normals(data_dir, spec, window)
    values |= {key: v[None] for key, v in place.items()}

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
    opens = season_opens(data_dir, spec, window)
    for v in (*outputs.values(), *(x for x in (risk, level) if x is not None)):
        v[before] = np.nan  # not started, as at a point: nothing before the season's biofix
        if in_region is not None:
            v[:, ~in_region] = np.nan
    if opens is not None:  # an insect's season not open yet at the cell (D128): its activity and risk blank there
        slots = np.array([climatology.slot(d) for d in dates], dtype=float).reshape(shape)
        closed = np.broadcast_to(slots < opens[None], (n, *window.shape))
        blank = blank_before_opening(spec)
        for v in (*(v for k, v in outputs.items() if k in blank), *(x for x in (risk, level) if x is not None)):
            v[closed] = np.nan
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
        in_season=None if spec.season is None else [_in_season(spec, d, data_dir) for d in dates],
        in_region=in_region,
        opens=opens,
        stale=reader.stale,
        sources=base.sources,
        forecast=base.forecast,
        run_from=base.run_from,
        reads=reader.reads,
        options=opts,
        accumulated={a.name: values[a.name] for a in spec.accumulations},
        place=place,
        missing_days=missing_days,
    )


def read_names(model_id: str) -> list[str]:
    """Every store variable a model's map reads: its stored ingredients, their totals and counts, and the running
    totals that stand in for the rest."""
    spec = find_model(model_id).SPEC
    crop = planting.map_crop(spec)
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
            extra.append(modelmaps.missing_key(k))
    if any(i.degree_days is not None for i in spec.ingredients):
        totals.append(TEMPERATURE_MISSING)
    return [*stored, *extra, *totals]


def tiered(model_id: str) -> tuple[str, str] | None:
    """(crop model, crop) whose planting tier a model's map takes (`agdata.planting.map_crop`), or None."""
    found = planting.map_crop(find_model(model_id).SPEC)
    return found if found is not None and found[0] in mapped() else None


@dataclass(frozen=True, kw_only=True)
class _Planting:
    """A crop planted at a tier over the window: each cell's date per season (ordinals; NaN where none)."""

    crop_id: str  # its stage model
    crop: str  # `agdata.planting`'s name
    tier: str
    window: Window
    data_dir: Path  # its normals give potato's dates (`agdata.potatoplanting`)

    def __call__(self, day: date) -> np.ndarray:
        return planting.planting_map(self.crop, self.tier, self.window, season=day.year, data_dir=self.data_dir)


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
    compute: bool = False,
    on_request: Callable[[], AbstractContextManager[object]] | None = None,
) -> ModelDays:
    """A model's map with each place's own settings (D66): with a planting `tier` (early, mid, late; None for none),
    a crop model starts at each cell's typical planting date (soybean's and spring wheat's stored per tier,
    `agdata.croptiers`), a stage-anchored biofix is the day the crop reaches that stage from it (not started until
    then), and a stage-gated disease gets `susceptibility` (D33) from the crop's stages. A cell without a typical
    date for the tier is missing, as a point without one refuses (`no_estimate`; Ben 2026-11-26): the spec's default
    dates there were a guess the map didn't show as one.

    A season-stored model (`modelmaps.SEASON_MODELS`, `agdata.seasonmaps`) is read from its stored season where it's
    stored through the days asked for, else computed as `compute` asks (the job storing it). A model computed on
    request (`ON_REQUEST`) runs a block at a time (`agdata.blocks`) and the blocks are put together: it reads a
    season of days, and over a whole launch-size window that was tens of GB (D109). Its blocks are computed inside
    `on_request()` if given: the web app's limit on heavy computations (`api.heavy`), which can refuse."""
    found = _model_map(data_dir, model_id, first, last, window, options, tier, now, stores, compute, on_request)
    crop = tiered(model_id)
    if tier is not None and crop is not None:
        _unplanted_missing(
            found, planting=_Planting(crop_id=crop[0], crop=crop[1], tier=tier, window=window, data_dir=data_dir)
        )
    return found


def _unplanted_missing(found: ModelDays, planting: "_Planting") -> None:
    """Makes `found` missing, in place, in the cells with no typical planting date for its tier in each day's season."""
    by_season: dict[int, np.ndarray] = {}
    days = []
    for k, d in enumerate(found.dates):
        if d.year not in by_season:
            by_season[d.year] = np.isnan(planting(d))
        if by_season[d.year].any():
            days.append(k)
    if not days:
        return

    def blank(v: np.ndarray) -> np.ndarray:
        if v.ndim != 3:
            return v
        if not (np.issubdtype(v.dtype, np.floating) and v.flags.writeable):
            v = v.astype(np.result_type(v.dtype, np.float32))
        for k in days:
            v[k][by_season[found.dates[k].year]] = np.nan
        return v

    found.outputs = {name: blank(v) for name, v in found.outputs.items()}
    found.accumulated = {name: blank(v) for name, v in found.accumulated.items()}
    found.risk = None if found.risk is None else blank(found.risk)
    found.level = None if found.level is None else blank(found.level)
    found.missing_days = None if found.missing_days is None else blank(found.missing_days)


def _model_map(
    data_dir: Path,
    model_id: str,
    first: date,
    last: date,
    window: Window,
    options: Mapping[str, str] | None,
    tier: str | None,
    now,
    stores: series.Stores | None,
    compute: bool,
    on_request: Callable[[], AbstractContextManager[object]] | None,
) -> ModelDays:
    if (
        model_id in modelmaps.SEASON_MODELS
        and not compute
        and (tiered(model_id) is None or tier == seasonmaps.tier(model_id))
    ):
        found = _stored_season(data_dir, model_id, first, last, window, now, stores)
        if found is not None:
            return found
    if model_id in ON_REQUEST:
        parts = blocks.blocks(window)
        if len(parts) > 1 or (parts and parts[0] != window):
            with on_request() if on_request is not None else nullcontext():
                found = [
                    model_map(
                        data_dir, model_id, first, last, part, options, tier=tier, now=now, stores=stores, compute=True
                    )
                    for part in parts
                ]
            return _merged(window, parts, found)
    spec = find_model(model_id).SPEC
    crop = tiered(model_id)
    sown = (
        None
        if tier is None or crop is None
        else _Planting(crop_id=crop[0], crop=crop[1], tier=tier, window=window, data_dir=data_dir)
    )
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
    elif spec.biofix_stage is not None and january_crop_start(spec, first) is not None:
        cell_biofix = _january_stage_reached(data_dir, spec.biofix_stage, window, last, now, stores)
    if model_id in ON_REQUEST:
        found = _anchored_days(data_dir, model_id, first, last, window, now, stores, cell_biofix)
    else:
        found = model_days(
            data_dir, model_id, first, last, window, options, now=now, stores=stores, cell_biofix=cell_biofix
        )
    if sown is not None and spec.susceptible is not None:
        found.outputs["susceptibility"] = _susceptibility(data_dir, spec, sown, first, last, now)
    return found


def _merged(window: Window, parts: list[Window], found: list[ModelDays]) -> ModelDays:
    """Blocks' maps (`parts` of `window`) as one over the window: missing where no block reaches."""
    one = found[0]
    n = len(one.dates)

    def whole(arrays: list[np.ndarray | None]) -> np.ndarray | None:
        if arrays[0] is None:
            return None
        shape = (*arrays[0].shape[:-2], *window.shape)
        flags = arrays[0].dtype == bool  # in_region: False where no block reaches
        out = (
            np.zeros(shape, dtype=bool)
            if flags
            else np.full(shape, np.nan, dtype=np.result_type(arrays[0], np.float32))
        )
        for part, values in zip(parts, arrays, strict=True):
            assert values is not None
            out[..., part.j0 - window.j0 : part.j1 - window.j0, part.i0 - window.i0 : part.i1 - window.i0] = values
        return out

    def each(get: Callable[[ModelDays], dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
        return {name: cast(np.ndarray, whole([get(f)[name] for f in found])) for name in get(one)}

    kinds = [next((f.kinds[k] for f in found if f.kinds[k] is not None), None) for k in range(n)]
    return ModelDays(
        dates=one.dates,
        kinds=kinds,
        outputs=each(lambda f: f.outputs),
        risk=whole([f.risk for f in found]),
        level=whole([f.level for f in found]),
        biofix=one.biofix,
        cell_biofix=whole([f.cell_biofix for f in found]),
        in_season=one.in_season,
        in_region=None if one.in_region is None else whole([f.in_region for f in found]),
        opens=whole([f.opens for f in found]),
        stale=any(f.stale for f in found),
        sources=one.sources,
        forecast=one.forecast,
        run_from=one.run_from,
        reads=sum(f.reads for f in found),
        options=one.options,
        accumulated=each(lambda f: f.accumulated),
        place=each(lambda f: f.place),
        missing_days=None if any(f.missing_days is None for f in found) else whole([f.missing_days for f in found]),
    )


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


def _finished(spec, base, dates, outputs, risk, level, reader, cells=None, place=None, missing_days=None) -> ModelDays:
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
        place=place or {},
        missing_days=missing_days,
    )


def _stored_days(data_dir, sown: _Planting, first: date, last: date, now, stores, only=None) -> ModelDays:
    """A tier-stored crop model's outputs (`agdata.croptiers`) on days first..last: all of them, or those named in
    `only` (a crop's stages for gating need `stage` alone; each output is a read of every day)."""
    spec = find_model(sown.crop_id).SPEC
    wanted = [q for q in spec.outputs if only is None or q.name in only]
    names = [modelmaps.tier_key(spec.id, q.name, sown.tier) for q in wanted]
    base, reader = _base(data_dir, spec, first, last, sown.window, now, stores, [*names, TEMPERATURE_MISSING])
    dates = [first + timedelta(days=k) for k in range(len(base.steps))]
    outputs = {}
    for q, name in zip(wanted, names, strict=True):
        found = reader.days(INGREDIENTS, name, dates)
        outputs[q.name] = np.stack([found[d] for d in dates])
    planted = np.stack([sown(d) for d in dates])  # the biofix is the planting
    gaps = None
    if only is None:  # the stages run on temperature from planting: its days missing past the fill (D56)
        gaps = _spanned(
            lambda days: reader.counted(TEMPERATURE_MISSING, days),
            None,
            Accumulation(name=TEMPERATURE_MISSING, of=TEMPERATURE_MISSING),
            dates,
            planted,
            sown.window,
        )
    return _finished(spec, base, dates, outputs, None, None, reader, cells=planted, missing_days=gaps)


def _stored_season(data_dir, model_id: str, first: date, last: date, window: Window, now, stores) -> ModelDays | None:
    """A season-stored model's map from what `agdata.seasonmaps` keeps, or None where it isn't kept for the days
    asked (outside its season, before the job has run, or past what's stored): the archive's through the day before
    the forecast run's first, the run's from it."""
    m = find_model(model_id)
    spec = m.SPEC
    if first.year != last.year:
        return None
    start, end = seasonmaps.season(model_id, first.year)
    gaps = modelmaps.season_key(model_id, modelmaps.SEASON_MISSING)
    keys = [k for k in seasonmaps.names(model_id) if k != gaps]
    if last < start or first > end:  # wholly out of the season it's shown in: nothing to show, nothing to compute
        base, reader = _base(data_dir, spec, first, last, window, now, stores, keys)
        dates = [first + timedelta(days=k) for k in range(len(base.steps))]
        empty = np.full((len(dates), *window.shape), np.nan)
        outputs = {q.name: empty.copy() for q in spec.outputs}
        risk = None if spec.risk is None else empty.copy()
        return _finished(spec, base, dates, outputs, risk, risk, reader, cells=empty)
    if first < start or last > end:
        return None
    base, reader = _base(data_dir, spec, first, last, window, now, stores, [*keys, gaps])
    dates = [first + timedelta(days=k) for k in range(len(base.steps))]
    archive_last = min(last, reader.cut - timedelta(days=1))
    if first <= archive_last:
        through = seasonmaps.stored_through(data_dir, model_id, first.year)
        if through is None or through < archive_last:
            return None
    if last >= reader.cut:
        if reader.run_path is None:
            return None
        through = seasonmaps.stored_through(reader.run_path, model_id, first.year)
        if through is None or through < last:
            return None
    found = {name: reader.days(INGREDIENTS, name, dates) for name in keys}
    outputs = {
        q.name: np.stack([found[modelmaps.season_key(model_id, q.name)][d] for d in dates]) for q in spec.outputs
    }
    risk = level = None
    if spec.risk is not None:
        risk = np.stack([found[modelmaps.season_key(model_id, modelmaps.SEASON_RISK)][d] for d in dates])
        level = np.where(np.isfinite(risk), risk, np.nan)
    root = reader.run_path if last >= reader.cut and reader.run_path is not None else data_dir
    cells = seasonmaps.biofix(root, model_id, first.year, window)
    counted = reader.days(INGREDIENTS, gaps, dates, quiet=True)  # a season stored before they were kept: none
    return _finished(
        spec,
        base,
        dates,
        outputs,
        risk,
        level,
        reader,
        cells=np.broadcast_to(cells, (len(dates), *window.shape)),
        missing_days=np.stack([counted[d] for d in dates]),
    )


# Models with neither ingredients nor stored outputs, computed on request from the days around their biofix (red crown
# rot from R1; apple scab from green tip and fire blight from January 1, states carried day to day)
ON_REQUEST = ("red-crown-rot", "apple-scab", "fire-blight")


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
    place = normals.place_normals(data_dir, spec, window)  # each cell's normals the model reads, (y, x)
    outputs = {q.name: np.full((n, *window.shape), np.nan) for q in spec.outputs}
    missing_days = np.full((n, *window.shape), np.nan)
    starts = np.unique(cells[np.isfinite(cells)])
    if starts.size:
        a = min(date.fromordinal(int(starts.min())) - timedelta(days=reach), first)
        days = [a + timedelta(days=k) for k in range((last - a).days + 1)]
        raw = {q.name: reader.days(DAILY, q.name, days) for q in spec.inputs}
        series_ = {name: np.stack([v[d] for d in days]) for name, v in raw.items()}
        filled, blank = modelmaps.filled_inputs({name: v.copy() for name, v in series_.items()})
        # Cells in biofix order, so each group is a run of columns (days, cells): picking a group's cells out of
        # (days, y, x) with a mask took ~2 s an array over a block, and a model with many biofix days has many groups
        order = np.argsort(cells.ravel(), kind="stable")
        ranked = cells.ravel()[order]
        nd = len(days)
        by_cell = {name: np.take(v.reshape(nd, -1), order, axis=1) for name, v in filled.items()}
        # The days each input's fill estimated (`<input>_estimated`, as the runner's): a no-value day isn't one
        missing = {
            name: np.take((np.isnan(v) & np.isfinite(filled[name])).reshape(nd, -1), order, axis=1)
            for name, v in series_.items()
        }
        place_by_cell = {key: v.ravel()[order] for key, v in place.items()}
        ranked_out = {q.name: np.full((n, cells.size), np.nan) for q in spec.outputs}
        gone = _gone(
            list(by_cell.values()),
            answered=[
                None if (b := blank.get(name)) is None else np.take(b.reshape(nd, -1), order, axis=1)
                for name in by_cell
            ],
        )
        ranked_gone = np.full((n, cells.size), np.nan)
        for u in starts:
            biofix = date.fromordinal(int(u))
            if biofix > last:
                continue
            lo, hi = int(np.searchsorted(ranked, u, side="left")), int(np.searchsorted(ranked, u, side="right"))
            k0 = max(0, (biofix - a).days - reach)
            given = {name: v[k0:, lo:hi] for name, v in by_cell.items()}
            given |= {f"{name}_estimated": missing[name][k0:, lo:hi] for name in filled}
            context = {
                "day_of_year": np.array([d.timetuple().tm_yday for d in days[k0:]], dtype=float),
                "year": np.array([d.year for d in days[k0:]], dtype=float),
            }
            context |= {key: v[lo:hi][None] for key, v in place_by_cell.items()}  # (1, cells), as the inputs
            given |= {name: context[name] for name in spec.context if name in context}
            found = m.outputs(given, biofix_index=(biofix - a).days - k0)
            # The run's row j is days[k0 + j]; the asked day i is days[(first - a).days + i]. A group whose run starts
            # after `first` (a late biofix) fills only the days from its start
            shown = (first - a).days - k0
            i0 = max(0, -shown)
            for name, v in found.items():
                v = np.asarray(v, dtype=float)
                count = min(n - i0, len(v) - (shown + i0))
                if count > 0:
                    ranked_out[name][i0 : i0 + count, lo:hi] = v[shown + i0 : shown + i0 + count]
            count = min(n - i0, nd - k0 - (shown + i0))
            if count > 0:  # the days missing past the fill from the run's first day, as the outputs are placed
                counted = np.cumsum(gone[k0:, lo:hi], axis=0)
                ranked_gone[i0 : i0 + count, lo:hi] = counted[shown + i0 : shown + i0 + count]
        for name, v in ranked_out.items():
            flat = outputs[name].reshape(n, -1)
            flat[:, order] = v
        missing_days.reshape(n, -1)[:, order] = ranked_gone
    ordinals = np.array([d.toordinal() for d in dates], dtype=float)[:, None, None]
    before = ordinals < cells[None]  # not started, as at a point (inf: R1 not reached)
    for v in (*outputs.values(), missing_days):
        v[before | np.isnan(cells)[None]] = np.nan
    risk = level = None
    if spec.risk is not None:
        risk = np.asarray(m.risk(outputs), dtype=float)
        level = np.where(np.isfinite(risk), risk, np.nan)
    return _finished(
        spec,
        base,
        dates,
        outputs,
        risk,
        level,
        reader,
        cells=np.broadcast_to(cells, (n, *window.shape)),
        place=place,
        missing_days=missing_days,
    )


def _gone(inputs: list[np.ndarray], answered: list[np.ndarray | None] | None = None) -> np.ndarray:
    """(days, cells): the days any input (filled) is in a gap the fill didn't reach, with data on each side (D56), as
    a point counts them (`runner.unfilled_gaps`): days before the data start or after they end aren't a gap. `answered`,
    beside each input, marks its nulls that are the day's answer (a conditional mean's, `agmodels.gaps.no_value`)."""
    marks: list[np.ndarray | None] = list(answered) if answered else [None] * len(inputs)
    return np.any([unfilled_gaps(v, answered=a) for v, a in zip(inputs, marks, strict=True)], axis=0)


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
    `last`, NaN where there's no planting), as a biofix: `cell_biofix(day)`, per season, as `agdata.croptiers` kept
    them (D70). A season with none kept (its ingredients not built yet; `modelmaps.status` says so) counts as not
    reached, so the model's map is missing there rather than started on a guess."""
    crop = cast(CropModel, find_model(sown.crop_id))
    k = [s.code for s in crop.stages()].index(code)
    seasons: dict[int, np.ndarray] = {}

    def biofix(day: date) -> np.ndarray:
        if day.year not in seasons:
            p = sown(day)
            stored = _stored_reached(data_dir, sown, day.year, now) if np.isfinite(p).any() else None
            if stored is None:
                seasons[day.year] = np.where(np.isnan(p), np.nan, np.inf)
            else:
                # As `update` kept them: a day after the request's last counts as not reached yet, and a cell
                # planted now that the store kept none for (built before its planting date was known) as not
                # reached, not the spec's default
                kept = np.where(stored[k] > last.toordinal(), np.inf, stored[k])
                seasons[day.year] = np.where(np.isnan(p), np.nan, np.where(np.isnan(kept), np.inf, kept))
        return seasons[day.year]

    return biofix


def _january_stage_reached(data_dir, anchor: tuple[str, str], window: Window, last: date, now, stores):
    """Each cell's first day at a stage of a crop model counted from January 1 (apple stages' green tip), as date
    ordinals (inf if not reached by `last`): `cell_biofix(day)` for the season `day` falls in, from the crop's map."""
    crop_id, code = anchor
    crop = cast(CropModel, find_model(crop_id))
    k = [s.code for s in crop.stages()].index(code)
    seasons: dict[int, np.ndarray] = {}

    def biofix(day: date) -> np.ndarray:
        if day.year not in seasons:
            january = date(day.year, 1, 1)
            end = min(last, date(day.year, 12, 31))
            stage = model_days(data_dir, crop_id, january, end, window, now=now, stores=stores).outputs["stage"]
            passed = stage >= k
            first = np.argmax(passed, axis=0)
            seasons[day.year] = np.where(passed.any(axis=0), january.toordinal() + first, np.inf).astype(float)
        return seasons[day.year]

    return biofix


def _stored_reached(data_dir, sown: _Planting, year: int, now) -> np.ndarray | None:
    """A stored crop's first day at each stage (`croptiers.reached`): the current forecast run's, which runs on
    through the forecast, else the archive's; None if neither store has them."""
    run = series.current_forecast(data_dir, now).path
    for root in (run, data_dir):
        found = None if root is None else croptiers.reached(root, sown.crop_id, sown.tier, year, sown.window)
        if found is not None:
            return found[0]
    return None


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
    firsts: dict[int, date | None] = field(default_factory=dict)  # each year's first day of weather (`first_day`)

    def days(self, layout: StoreLayout, name: str, days: Iterable[date], quiet: bool = False) -> dict[date, np.ndarray]:
        """`name` on `days`; `quiet` doesn't mark the map stale where the store lacks it or holds an older version (the
        days missing past the fill, D56: a store built before they were kept reads as none counted)."""
        wanted = sorted(set(days))
        missing = [d for d in wanted if (layout.kind, name, d) not in self.cache]
        for run in _runs(missing):
            cut = sum(d < self.cut for d in run)
            values, stale, _ = series.read_split(
                self.stores, self.data_dir, self.run_path, layout, name, run, cut, self.window
            )
            self.stale |= bool(stale.any()) and not quiet
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

    def missing(self, ingredient: Ingredient, model_id: str, days: Iterable[date]) -> dict[date, np.ndarray] | None:
        """The running count from January 1 of days an ingredient's inputs were still missing after the gap fill
        (D56): the temperature's for degree days, a catalog total's own, a stored one's (`modelmaps.missing_key`);
        None where none is kept."""
        if ingredient.degree_days is not None:
            return self.counted(TEMPERATURE_MISSING, days)
        if ingredient.cumulative is not None:
            name = f"{ingredient.cumulative}_missing_days"
            return self.counted(name, days) if name in CUMULATIVE_VARIABLES else None
        return self.days(INGREDIENTS, modelmaps.missing_key(modelmaps.key(model_id, ingredient)), days, quiet=True)

    def counted(self, name: str, days: Iterable[date]) -> dict[date, np.ndarray]:
        """A running count of missing days from the cumulative store, from each year's first day of weather: it
        counts every day from January 1 without one, and the days before the archive starts aren't a gap (as a
        stored ingredient's count leaves them out, `modelmaps._gone`)."""
        days = list(days)
        starts = {year: self.first_day(year) for year in {d.year for d in days}}
        before = {f - timedelta(days=1) for f in starts.values() if f is not None and (f.month, f.day) != (1, 1)}
        found = self.days(CUMULATIVE, name, [*days, *before], quiet=True)
        out = {}
        for d in days:
            f = starts[d.year]
            if f is None or (f.month, f.day) == (1, 1):
                out[d] = found[d]
            else:
                out[d] = np.maximum(found[d] - np.nan_to_num(found[f - timedelta(days=1)]), 0)
        return out

    def first_day(self, year: int) -> date | None:
        """The first day of `year` the archive has weather for (None: none)."""
        if year not in self.firsts:
            rolled = modelmaps._rolled_days(self.data_dir, year)
            self.firsts[year] = None if rolled is None else date(year, 1, 1) + timedelta(days=int(rolled[0]))
        return self.firsts[year]

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

    def total(days):
        return reader.total(ingredient, spec.id, days)

    def known(days):
        return reader.known(ingredient, spec.id, days)

    return _spanned(total, known, a, dates, biofix, reader.window)


def _missing_days(reader: _Reader, spec: ModelSpec, dates: list[date], biofix: np.ndarray) -> np.ndarray | None:
    """Each cell's days missing past the gap fill (D56) in its accumulations' spans on each day, the most of any:
    those a total or sum added nothing for. A mean divides by the days with a value, so it doesn't run low; a model
    without accumulations reads each day's ingredients, which carry their own gaps. None where none is counted."""
    counts = []
    for a in spec.accumulations:
        if a.how == "mean":
            continue
        ingredient = next(i for i in spec.ingredients if i.name == a.of)
        if reader.missing(ingredient, spec.id, []) is None:
            continue

        def total(days, ingredient=ingredient):
            found = reader.missing(ingredient, spec.id, days)
            assert found is not None
            return found

        counts.append(_spanned(total, None, a, dates, biofix, reader.window))
    if not counts:
        return None
    with np.errstate(invalid="ignore"):
        return np.fmax.reduce(counts) if len(counts) > 1 else counts[0]


def _spanned(total, known, a: Accumulation, dates: list[date], biofix: np.ndarray, window: Window) -> np.ndarray:
    """`_accumulated` on running totals from `total(days)` ({day: map}) and, for a mean, counts from `known(days)`."""
    out = np.full(biofix.shape, np.nan)
    for k, d in enumerate(dates):
        b = biofix[k]
        started = np.isfinite(b) & (b <= d.toordinal())
        if not started.any():
            continue
        start = b if a.how == "total" else np.maximum(b, (d - timedelta(days=a.days - 1)).toordinal())
        starts = np.unique(start[started])
        firsts = [date.fromordinal(int(u)) for u in starts]
        ends = [min(d, until_day(a.until, f)) if a.until is not None else d for f in firsts]
        within = list(zip(firsts, ends, strict=True))
        if all(f.year == e.year for f, e in within):  # each a difference of two days' totals, cell by cell
            cells = np.flatnonzero(started.ravel())
            group = np.searchsorted(starts, start.ravel()[cells])  # each started cell's pair
            sums = _cell_spans(total, within, group, cells)
            if a.how == "mean":
                counts = _cell_spans(known, within, group, cells)
                with np.errstate(invalid="ignore", divide="ignore"):
                    sums = np.where(counts > 0, sums / counts, np.nan)
            out[k].reshape(-1)[cells] = sums
            continue
        pairs: list[tuple[date | None, date]] = list(within)
        sums = _spans(total, pairs, window)
        if a.how == "mean":
            counts = _spans(known, pairs, window)
            with np.errstate(invalid="ignore", divide="ignore"):
                sums = np.where(counts > 0, sums / counts, np.nan)
        for u, v in zip(starts, sums, strict=True):
            cells = started & (start == u)
            out[k][cells] = v[cells]
    return out


def _cell_spans(total, pairs: list[tuple[date, date]], group: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """`_spans` for pairs within one year each, taken only at the cells that use them (`cells`, flat indices into
    the window, each with its pair's index in `group`): each cell's total on its pair's last day less its total the
    day before its first (nothing before January 1). `_spans` made a whole map per pair, and a crop's emergence
    varies across the launch box by a hundred days (early blight's week took 5 s of a 7 s first tile)."""
    needed = sorted({e for _, e in pairs} | {f - timedelta(days=1) for f, _ in pairs if (f.month, f.day) != (1, 1)})
    found = total(needed)
    index = {d: k for k, d in enumerate(needed)}
    ends = np.array([index[e] for _, e in pairs])[group]
    before = np.array([index.get(f - timedelta(days=1), -1) for f, _ in pairs])[group]  # -1: from January 1

    def at(which: np.ndarray) -> np.ndarray:
        """Each cell's total on its day `which` (an index into `needed`; NaN for -1), each day's map read once
        for just the cells that need it."""
        out = np.full(cells.size, np.nan)
        order = np.argsort(which, kind="stable")
        days, starts = np.unique(which[order], return_index=True)
        for k, (day, lo) in enumerate(zip(days, starts, strict=True)):
            if day < 0:
                continue
            hi = starts[k + 1] if k + 1 < len(starts) else order.size
            picked = order[lo:hi]
            out[picked] = found[needed[day]].reshape(-1)[cells[picked]]
        return out

    out = at(ends)
    later = before >= 0  # a first day of January 1 has nothing before it
    out[later] = out[later] - np.nan_to_num(at(before)[later])
    return out


def _day_of_year(ordinals: np.ndarray) -> np.ndarray:
    """Day of year of each date ordinal (NaN and inf stay NaN)."""
    out = np.full(ordinals.shape, np.nan)
    finite = np.isfinite(ordinals)
    for u in np.unique(ordinals[finite]):
        out[ordinals == u] = date.fromordinal(int(u)).timetuple().tm_yday
    return out


def _region_mask(spec: ModelSpec, window: Window) -> np.ndarray | None:
    return _areas_mask(spec.region, window) if spec.region else None


def training_mask(spec: ModelSpec, window: Window) -> np.ndarray | None:
    """Cells inside the area the model's data came from (D101); None if it records none."""
    t = spec.trained
    return None if t is None else _areas_mask((*t.states, *t.counties), window)


@cache
def _areas_mask(codes: tuple[str, ...], window: Window) -> np.ndarray:
    """Cells in any of the states or counties (postal codes or five-digit FIPS), cached (~0.2 s for a box and 17
    states)."""
    found = [regions.find(code) for code in codes]
    masks = [regions.mask(r, window) for r in found if r is not None]
    mask = np.any(masks, axis=0) if masks else np.zeros(window.shape, dtype=bool)
    mask.setflags(write=False)
    return mask


def _in_season(spec: ModelSpec, day: date, data_dir: Path | None = None) -> bool:
    """Whether the map's day is in season over the region: an insect's season opens on the region's day
    (`seasonopens.region`, D128); a map's cells open (`season_opens`) and end their seasons on their own days."""
    return seasons.in_season(spec, day, opens=seasonopens.region(data_dir, spec))


def blank_before_opening(spec: ModelSpec) -> set[str]:
    """The outputs a map leaves blank where an insect's season hasn't opened (D128), with its risk: all but its
    degree days, which are the weather's, not the insect's."""
    return {q.name for q in spec.outputs if q.unit not in ("degF_day", "degC_day")}


def season_opens(data_dir: Path, spec: ModelSpec, window: Window) -> np.ndarray | None:
    """The calendar slot each cell's season opens on (y, x) for an insect whose season opens by the normal (D128),
    the season's calendar first day where a cell has no normal; None for any other model."""
    if not isinstance(spec.opens, OpensOnDegreeDays | OpensOnCropStage) or spec.season is None:
        return None
    found = seasonopens.slots(data_dir, spec, window)
    first = climatology.slot(date(climatology.LEAP, *(int(p) for p in spec.season[0].split("-"))))
    return np.where(np.isnan(found), float(first), found)
