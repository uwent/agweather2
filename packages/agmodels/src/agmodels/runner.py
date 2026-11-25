"""Running a model over a daily series (Phase 4 D): one place for every caller (API, alerts, tests).

The caller reads the days (`agdata.series`): `required_inputs` says which, `first_day_needed` from when (the
biofix or planting, less the model's lookback). `run` supplies the context (day of year, latitude, year), places
the biofix (a date, the spec's default for the season, or a crop stage's predicted date), runs the outputs and
risk, gates the risk by crop stage or a stage date the user gives (D33), finds the action windows' dates (D36) and which days are in season, and
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
from typing import Any, cast

import numpy as np

from agmodels.crops import CropModel, date_susceptibility, disease_susceptibility, stage_days
from agmodels.gaps import GapFill, fill_inputs
from agmodels.phenology import PhenologyModel, window_periods
from agmodels.registry import model as find_model
from agmodels.spec import Model, ModelSpec, StageDate, Susceptibility

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
    # The place is outside the area the model's data came from (`ModelSpec.trained`, D101), set by the caller that
    # knows the place (`agdata.series`): the run is made, and the answer says it reaches beyond the data
    outside_training_area: bool = False
    # Public warnings for the place's fixed values the model reads and didn't get (`ModelSpec.place_normals`): each
    # one's `missing`, saying what the model did without it
    place_warnings: tuple[str, ...] = ()
    # Where the weather came from, set by the caller that read it (`agdata.series`): its sources and corrections
    sources: tuple[str, ...] = ()
    corrections: tuple[str, ...] = ()
    # The forecast the weather came with (`agdata.series.Forecast`, set there): which run, or why none and whether
    # another source stood in (D114), for the answer's warnings
    forecast: Any = None


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


class FixedBiofixError(ValueError):
    """A biofix date given to a model whose biofix is fixed (`Biofix.fixed`) that isn't its default date."""


def check_biofix(spec: ModelSpec, biofix: date | None) -> None:
    """Refuses a grower's biofix for a model whose biofix is fixed (`Biofix.fixed`: western bean cutworm's March 1),
    whatever calls the runner (the API, scenarios, sites, alerts): a date equal to the default in its own season is
    the same run, and accepted."""
    if biofix is None or spec.biofix is None or not spec.biofix.fixed:
        return
    if biofix != default_biofix(spec, biofix):
        raise FixedBiofixError(
            f"{spec.id} always counts from {spec.biofix.default} (MM-DD); it takes no other biofix, got {biofix}"
        )


def first_day_needed(m: Model, start: date, biofix: date | None = None, planting: date | None = None) -> date:
    """The first day `run` needs for outputs from `start`: the earliest of start less the lookback, the biofix and
    the planting date (for a gated or stage-anchored model)."""
    first = start - timedelta(days=m.SPEC.lookback_days)
    if planting is None and crop_models(m.SPEC):
        planting = january_crop_start(m.SPEC, start)
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
    place: Mapping[str, float] | None = None,
) -> ModelRun:
    """Runs a model over consecutive `dates` (with `daily[name]` for each, as `required_inputs` lists) and returns
    the days from `start` (default the first). `planting` is the crop's planting date, for stage gating and for a
    biofix at a crop stage; without it, gated models aren't gated, unless the options give the gate's stage date
    (`stage_date`, which replaces the crop's stages when given). `gap_fill` gives each input's estimate for
    missing days (the catalog's `GAP_FILL`); inputs without one are passed as they are. `place` gives the place's
    fixed values the model reads (`ModelSpec.place_normals`, by key); one missing or NaN is passed as NaN, and the
    run carries its warning. A biofix other than the default for a model whose biofix is fixed raises
    `FixedBiofixError` (`check_biofix`)."""
    m = find_model(m) if isinstance(m, str) else m
    spec = m.SPEC
    check_biofix(spec, biofix)
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
    context = _context(dates, latitude) | place_context(spec, place)
    result.place_warnings = place_warnings(spec, place)
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
    given = stage_date(spec, opts)
    if given is not None:  # the user's own date replaces the crop model's estimate
        window = cast(StageDate, cast(Susceptibility, spec.susceptible).stage_date)
        result.susceptibility = date_susceptibility(
            np.array([(d - given).days for d in result.dates]),
            first=window.first,
            last=window.last,
            margin_days=window.margin_days,
        )
    if spec.season is not None:
        result.in_season = np.array([_in_season(spec, d) for d in result.dates])
    if isinstance(m, PhenologyModel) and next(iter(result.outputs.values())).ndim == 1:  # scenarios: per year
        for w in m.insect.action_windows:
            periods = window_periods(result.outputs[f"window_{w.key}"])
            result.windows[w.label] = [(result.dates[a], result.dates[b]) for a, b in periods]
    return result


def stage_date_option(spec: ModelSpec) -> str | None:
    """The name of the option giving the date for the model's susceptible window (`spec.StageDate`), or None."""
    gate = spec.susceptible
    return None if gate is None or gate.stage_date is None else gate.stage_date.option


def stage_date(spec: ModelSpec, options: Mapping[str, str] | None) -> date | None:
    """The date the user gave for the model's susceptible window (`spec.StageDate`), or None if it takes none or none
    was given; ValueError if it isn't a date (YYYY-MM-DD)."""
    name = stage_date_option(spec)
    if name is None:
        return None
    value = (options or {}).get(name, "")
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} must be a date (YYYY-MM-DD), got {value!r}") from None


def crop_models(spec: ModelSpec) -> list[str]:
    """The crop models a model is gated by or anchors its biofix to (D33)."""
    ids = []
    if spec.susceptible is not None:
        ids.append(spec.susceptible.crop)
    if spec.biofix_stage is not None and spec.biofix_stage[0] not in ids:
        ids.append(spec.biofix_stage[0])
    return ids


def january_crop_start(spec: ModelSpec, start: date | None) -> date | None:
    """January 1 of `start`'s year when the crop model a model is gated by or anchored to counts from January 1 rather
    than a planting (apple stages): nothing to plant, so it always runs. None otherwise, or without a start."""
    crops = crop_models(spec)
    if not crops or start is None:
        return None
    crop = find_model(crops[0]).SPEC
    return date(start.year, 1, 1) if crop.biofix is not None and crop.biofix.default == "01-01" else None


def _crop_stage(spec, dates, daily, context, planting, crop_options) -> np.ndarray | None:
    """The gating or anchoring crop model's stage each day from `planting` (NaN before), or None."""
    crops = crop_models(spec)
    if crops and planting is None:
        planting = january_crop_start(spec, dates[0] if dates else None)
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


def place_context(spec: ModelSpec, place: Mapping[str, float] | None) -> dict[str, np.ndarray]:
    """The place's fixed values a model reads, by key: NaN for one not given."""
    return {n.key: np.array(float((place or {}).get(n.key, np.nan))) for n in spec.place_normals}


def place_warnings(spec: ModelSpec, place: Mapping[str, float] | None) -> tuple[str, ...]:
    """The warnings for the place's fixed values a model reads and didn't get (each normal's `missing`)."""
    return tuple(n.missing for n in spec.place_normals if not np.isfinite(float((place or {}).get(n.key, np.nan))))


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
