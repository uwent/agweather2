"""A model over several scenarios at once (D63's projection: this season's days, then each past year's), and the
spread across them: per-day P10/P50/P90 and when each stage, risk level or action window is first reached.

Inputs are (days × scenarios), run as a grid's cells (every model takes extra axes after time), so ten years cost
about one run. What can differ between scenarios is handled here: a biofix at a crop stage (the blights' emergence,
red crown rot's R1) can fall on different days, so scenarios are grouped by it; action windows are found per
scenario. The result is one `ModelRun` per scenario, the same as running each alone."""

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import cast

import numpy as np

from agmodels.crops import CropModel, stage_days
from agmodels.gaps import GapFill, fill_inputs
from agmodels.phenology import PhenologyModel, window_periods
from agmodels.registry import model as find_model
from agmodels.runner import ModelRun, _context, _crop_stage, _index, crop_models, default_biofix, run
from agmodels.spec import Model

PERCENTILES = (10, 50, 90)


def run_scenarios(
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
) -> list[ModelRun]:
    """`runner.run` over `daily`'s (days × scenarios) arrays: one `ModelRun` per scenario, in column order."""
    m = find_model(m) if isinstance(m, str) else m
    dates = list(dates)
    n = next(iter(daily.values())).shape[1]
    raw = {name: np.asarray(v, dtype=float) for name, v in daily.items()}

    def go(columns: list[int] | int, day: date | None) -> ModelRun:
        return run(
            m,
            dates=dates,
            daily={name: v[:, columns] for name, v in raw.items()},
            latitude=latitude,
            start=start,
            kinds=kinds,
            biofix=day,
            planting=planting,
            options=options,
            crop_options=crop_options,
            in_region=in_region,
            gap_fill=gap_fill,
        )

    groups: dict[date | None, list[int]] = {biofix: list(range(n))}
    spec = m.SPEC
    if biofix is None and spec.biofix_stage is not None and planting is not None and in_region:
        stage = _crop_stage(
            spec, dates, _filled(raw, gap_fill), _context(dates, latitude), planting, crop_options or {}
        )
        if stage is not None:
            crop = cast(CropModel, find_model(spec.biofix_stage[0]))
            k = [s.code for s in crop.stages(**(crop_options or {}))].index(spec.biofix_stage[1])
            reached = stage_days(stage, k + 1)[k]
            groups = {}
            for j in range(n):
                day = dates[int(reached[j])] if np.isfinite(reached[j]) else None
                groups.setdefault(day, []).append(j)
    found: dict[int, ModelRun] = {}
    for day, columns in groups.items():
        if day is None and spec.biofix_stage is not None and planting is not None and biofix is None and in_region:
            for j in columns:  # the stage isn't reached in this scenario: not started (as `run` says it)
                found[j] = go(j, None)
            continue
        together = go(columns, day)
        for position, j in enumerate(columns):
            found[j] = _column(m, together, position)
    return [found[j] for j in range(n)]


def _filled(raw: dict[str, np.ndarray], gap_fill) -> dict[str, np.ndarray]:
    return fill_inputs(raw, gap_fill or {})[0]


def _column(m: Model, together: ModelRun, j: int) -> ModelRun:
    """Scenario j of a run over (days × scenarios), with its own action windows."""

    def pick(a):
        return None if a is None else (a[:, j] if np.ndim(a) > 1 else a)

    one = replace(
        together,
        inputs={k: v[:, j] for k, v in together.inputs.items()},
        outputs={k: v[:, j] for k, v in together.outputs.items()},
        risk=pick(together.risk),
        level=pick(together.level),
        susceptibility=pick(together.susceptibility),
        estimated={k: v[:, j] for k, v in together.estimated.items() if v[:, j].any()},
        missing={k: v[:, j] for k, v in together.missing.items() if v[:, j].any()},
        windows={},
    )
    if isinstance(m, PhenologyModel) and one.outputs:
        for w in m.insect.action_windows:
            periods = window_periods(one.outputs[f"window_{w.key}"])
            one.windows[w.label] = [(one.dates[a], one.dates[b]) for a, b in periods]
    return one


# --- The spread ---------------------------------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Spread:
    """Per day: P10, P50, P90 over the scenarios with a value, and how many had one. P10 and P90 need 2."""

    p10: np.ndarray
    p50: np.ndarray
    p90: np.ndarray
    count: np.ndarray


def spread(values: Sequence[np.ndarray]) -> Spread:
    """The spread of one series across scenarios (each a day-aligned array)."""
    a = np.stack([np.asarray(v, dtype=float) for v in values], axis=1)
    count = np.isfinite(a).sum(axis=1)
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # days with no scenario
        for p in PERCENTILES:
            out[p] = np.nanpercentile(a, p, axis=1) if a.size else np.full(a.shape[0], np.nan)
    out[10] = np.where(count >= 2, out[10], np.nan)
    out[90] = np.where(count >= 2, out[90], np.nan)
    return Spread(p10=out[10], p50=out[50], p90=out[90], count=count)


@dataclass(frozen=True, kw_only=True)
class Reached:
    """When something is first reached across scenarios: in `reached` of `of`, and the dates' P10/P50/P90."""

    what: str  # "stage", "risk" or "window"
    name: str  # a stage code, a risk level's label, an action window's label
    reached: int
    of: int
    p10: date | None
    p50: date | None
    p90: date | None


def first_days(dates: Sequence[date], flags: Sequence[np.ndarray]) -> list[date | None]:
    """Per scenario, the first date its flag is true, or None."""
    out = []
    for f in flags:
        hits = np.flatnonzero(np.nan_to_num(np.asarray(f, dtype=float)) > 0)
        out.append(dates[int(hits[0])] if hits.size else None)
    return out


def reached(what: str, name: str, days: Sequence[date | None]) -> Reached:
    found = sorted(d for d in days if d is not None)
    if not found:
        return Reached(what=what, name=name, reached=0, of=len(days), p10=None, p50=None, p90=None)
    ordinals = np.array([d.toordinal() for d in found], dtype=float)
    p10, p50, p90 = (date.fromordinal(round(float(np.percentile(ordinals, p)))) for p in PERCENTILES)
    return Reached(what=what, name=name, reached=len(found), of=len(days), p10=p10, p50=p50, p90=p90)


def milestones(m: Model, runs: Sequence[ModelRun], **crop_options: str) -> list[Reached]:
    """When each crop stage, each risk level above the lowest, and each action window's first opening comes, across
    scenarios (the runs share dates)."""
    if not runs or not runs[0].dates:
        return []
    dates = runs[0].dates
    spec = m.SPEC
    out: list[Reached] = []
    if spec.group == "crop" and all("stage" in r.outputs for r in runs):
        for k, s in enumerate(cast(CropModel, m).stages(**crop_options)):
            out.append(reached("stage", s.code, first_days(dates, [r.outputs["stage"] >= k for r in runs])))
    if spec.risk is not None:
        for level, label in enumerate(spec.risk.levels[1:], start=1):
            flags = [np.zeros(len(dates)) if r.level is None else r.level >= level for r in runs]
            out.append(reached("risk", label, first_days(dates, flags)))
    labels = sorted({label for r in runs for label in r.windows})
    for label in labels:
        out.append(reached("window", label, [r.windows[label][0][0] if r.windows.get(label) else None for r in runs]))
    return out


__all__ = ["Reached", "Spread", "_index", "crop_models", "default_biofix", "milestones", "run_scenarios", "spread"]
