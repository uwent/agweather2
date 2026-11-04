"""Running a model over a daily series (PLAN.md Phase 4 D): one place for every caller (API, alerts, tests).

The caller reads the days (`agdata.series`): `required_inputs` says which, `first_day_needed` from when (the
biofix or planting, less the model's lookback). `run` supplies the context (day of year, latitude, year), places
the biofix (a date, the spec's default for the season, or a crop stage's predicted date), runs the outputs and
risk, gates the risk by crop stage (D33), finds the action windows' dates (D36) and which days are in season, and
returns it all with each day's kind (observed, partial, forecast) and the model's id and version.

Missing days in the inputs are estimated first, by each variable's method (`gap_fill`, from the catalog: D45,
`agmodels.gaps`). The model sees the filled values and, as `<input>_estimated`, which days were filled; the inputs
layer returned keeps the raw values with their gaps, and `estimated` says which days were filled.

No I/O and nothing from `agdata`: region masks need the county grid, so the caller says whether the point is in
the model's region.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import cast

import numpy as np

from agmodels.crops import CropModel, disease_susceptibility, stage_days
from agmodels.gaps import GapFill, fill_inputs
from agmodels.phenology import PhenologyModel, window_periods
from agmodels.registry import model as find_model
from agmodels.spec import Model, ModelSpec

CONTEXT = ("day_of_year", "latitude", "year")


@dataclass(kw_only=True)
class ModelRun:
    """A model's three layers over the days from `start`, with each day's kind (D30)."""

    model_id: str
    version: str
    dates: list[date]
    kinds: list[str | None]
    inputs: dict[str, np.ndarray] = field(default_factory=dict)
    outputs: dict[str, np.ndarray] = field(default_factory=dict)
    risk: np.ndarray | None = None  # what the model's `risk` returns: a level, or a continuous value
    level: np.ndarray | None = None  # the risk as an index into the spec's levels (NaN where unknown)
    susceptibility: np.ndarray | None = None  # D33: 0 not susceptible, 1 margin, 2 susceptible; None if not gated
    in_season: np.ndarray | None = None  # per day, from the spec's season; None if it has none
    windows: dict[str, list[tuple[date, date]]] = field(default_factory=dict)  # action windows' periods (D36)
    estimated: dict[str, np.ndarray] = field(default_factory=dict)  # per input with any, the days filled (D45)
    # Per input with any, the days still missing after the fill (a gap longer than MAX_GAP_DAYS): a running total
    # adds nothing for them, so a long outage would otherwise read as a quiet stretch
    missing: dict[str, np.ndarray] = field(default_factory=dict)
    biofix: date | None = None
    # Why there are no outputs: "outside the model's region", "biofix after the series" (not started yet), "biofix
    # not in the series" (the days given start after it: read from `first_day_needed`), "<stage> isn't reached in the
    # series" (a biofix at a crop stage the planting hasn't reached: not started yet)
    reason: str | None = None


def required_inputs(m: Model) -> list[str]:
    """The daily variables `run` needs for a model: its own and those of the crop model it's gated or anchored by."""
    names = [q.name for q in m.SPEC.inputs]
    for crop_id in crop_models(m.SPEC):
        names += [q.name for q in find_model(crop_id).SPEC.inputs if q.name not in names]
    return names


def default_biofix(spec: ModelSpec, start: date) -> date | None:
    """The spec's biofix (MM-DD) for the season `start` falls in, or the next one if it falls between seasons; a
    season that crosses New Year (potato volunteer, rye) takes its biofix from the year it begins."""
    if spec.biofix is None:
        return None
    month, day = (int(p) for p in spec.biofix.default.split("-"))
    if spec.season is None or _mmdd(spec.season[0]) <= _mmdd(spec.season[1]):
        return date(start.year, month, day)
    first = _mmdd(spec.season[0])
    begins = start.year if (start.month, start.day) >= first or _after_season(spec, start) else start.year - 1
    biofix = date(begins, month, day)
    return biofix if (month, day) >= first else date(begins + 1, month, day)


def first_day_needed(m: Model, start: date, biofix: date | None = None, planting: date | None = None) -> date:
    """The first day `run` needs for outputs from `start`: the earliest of start less the lookback, the biofix and
    the planting date (for a gated or stage-anchored model)."""
    first = start - timedelta(days=m.SPEC.lookback_days)
    for anchor in (biofix or default_biofix(m.SPEC, start), planting if crop_models(m.SPEC) else None):
        if anchor is not None:
            first = min(first, anchor)
    return first


def run(
    m: Model | str,
    *,
    dates: Sequence[date],
    daily: Mapping[str, np.ndarray],
    latitude: float,
    start: date | None = None,
    kinds: Sequence[str | None] | None = None,
    biofix: date | None = None,
    planting: date | None = None,
    options: Mapping[str, str] | None = None,
    crop_options: Mapping[str, str] | None = None,
    in_region: bool = True,
    gap_fill: Mapping[str, GapFill] | None = None,
) -> ModelRun:
    """Runs a model over consecutive `dates` (with `daily[name]` for each, as `required_inputs` lists) and returns
    the days from `start` (default the first). `planting` is the crop's planting date, for stage gating and for a
    biofix at a crop stage; without it, gated models aren't gated. `gap_fill` gives each input's estimate for
    missing days (the catalog's `GAP_FILL`); inputs without one are passed as they are."""
    m = find_model(m) if isinstance(m, str) else m
    spec = m.SPEC
    dates = list(dates)
    day_kinds: list[str | None] = list(kinds) if kinds is not None else [None] * len(dates)
    start = start or dates[0]
    shown = _index(dates, start)
    if shown is None:
        raise ValueError(f"start {start} isn't in the series")
    result = ModelRun(model_id=spec.id, version=spec.version, dates=dates[shown:], kinds=day_kinds[shown:])
    if not in_region:
        result.reason = "outside the model's region"
        return result

    raw = {name: np.asarray(values, dtype=float) for name, values in daily.items()}
    daily, estimated = fill_inputs(raw, gap_fill or {})
    context = _context(dates, latitude)
    crop_stage = _crop_stage(spec, dates, daily, context, planting, crop_options or {})
    if biofix is None and spec.biofix_stage is not None and crop_stage is not None:
        code = spec.biofix_stage[1]
        crop = cast(CropModel, find_model(spec.biofix_stage[0]))
        k = [s.code for s in crop.stages(**(crop_options or {}))].index(code)
        reached = stage_days(crop_stage, k + 1)[k]
        if not np.isfinite(reached):  # not there yet: the model hasn't started, rather than starting on a guess
            result.reason = f"{code} isn't reached in the series"
            return result
        biofix = dates[int(reached)]
    biofix = biofix or default_biofix(spec, start)
    biofix_index = 0 if biofix is None else _index(dates, biofix)
    if biofix_index is None:
        assert biofix is not None
        result.reason = "biofix after the series" if biofix > dates[-1] else "biofix not in the series"
        result.biofix = biofix
        return result
    result.biofix = biofix

    inputs = {q.name: daily[q.name] for q in spec.inputs}
    inputs |= {f"{q.name}_estimated": estimated[q.name] for q in spec.inputs}
    inputs |= {name: context[name] for name in spec.context}
    opts = dict(options or {})
    outputs = m.outputs(inputs, biofix_index=biofix_index, **opts)
    risk = None if spec.risk is None else np.asarray(m.risk(outputs, biofix_index=biofix_index, **opts), dtype=float)

    result.inputs = {q.name: raw[q.name][shown:] for q in spec.inputs}
    result.estimated = {q.name: estimated[q.name][shown:] for q in spec.inputs if estimated[q.name][shown:].any()}
    gaps = {q.name: np.isnan(daily[q.name][shown:]) for q in spec.inputs}
    result.missing = {name: gap for name, gap in gaps.items() if gap.any()}
    result.outputs = {name: np.asarray(values, dtype=float)[shown:] for name, values in outputs.items()}
    if risk is not None and spec.risk is not None:
        result.risk = risk[shown:]
        thresholds = spec.risk.thresholds
        level = np.searchsorted(np.asarray(thresholds), result.risk, side="right") if thresholds else result.risk
        result.level = np.where(np.isfinite(result.risk), level, np.nan).astype(float)
    if crop_stage is not None and spec.susceptible is not None:
        gate = disease_susceptibility(spec, crop_stage, **(crop_options or {}))
        result.susceptibility = None if gate is None else gate[shown:]
    if spec.season is not None:
        result.in_season = np.array([_in_season(spec, d) for d in result.dates])
    if isinstance(m, PhenologyModel):
        for w in m.insect.action_windows:
            periods = window_periods(result.outputs[f"window_{w.key}"])
            result.windows[w.label] = [(result.dates[a], result.dates[b]) for a, b in periods]
    return result


def crop_models(spec: ModelSpec) -> list[str]:
    """The crop models a model is gated by or anchors its biofix to (D33)."""
    ids = []
    if spec.susceptible is not None:
        ids.append(spec.susceptible.crop)
    if spec.biofix_stage is not None and spec.biofix_stage[0] not in ids:
        ids.append(spec.biofix_stage[0])
    return ids


def _crop_stage(spec, dates, daily, context, planting, crop_options) -> np.ndarray | None:
    """The gating or anchoring crop model's stage each day from `planting` (NaN before), or None."""
    crops = crop_models(spec)
    if not crops or planting is None:
        return None
    k = _index(dates, planting)
    if k is None:
        return None
    crop = find_model(crops[0])
    inputs = {q.name: np.asarray(daily[q.name], dtype=float) for q in crop.SPEC.inputs}
    inputs |= {name: context[name] for name in crop.SPEC.context}
    return np.asarray(crop.outputs(inputs, biofix_index=k, **crop_options)["stage"], dtype=float)


def _context(dates: list[date], latitude: float) -> dict[str, np.ndarray]:
    return {
        "day_of_year": np.array([d.timetuple().tm_yday for d in dates], dtype=float),
        "latitude": np.array(latitude, dtype=float),
        "year": np.array([d.year for d in dates], dtype=float),
    }


def _index(dates: list[date], day: date) -> int | None:
    k = (day - dates[0]).days
    return k if 0 <= k < len(dates) else None


def _mmdd(text: str) -> tuple[int, int]:
    month, day = (int(p) for p in text.split("-"))
    return month, day


def _after_season(spec: ModelSpec, day: date) -> bool:
    """Between a New Year–crossing season's end and its next start (the next season is the one that applies)."""
    assert spec.season is not None
    return _mmdd(spec.season[1]) < (day.month, day.day) < _mmdd(spec.season[0])


def _in_season(spec: ModelSpec, day: date) -> bool:
    assert spec.season is not None
    first, last, md = _mmdd(spec.season[0]), _mmdd(spec.season[1]), (day.month, day.day)
    return first <= md <= last if first <= last else (md >= first or md <= last)
