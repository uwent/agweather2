"""Crop growth stages (D32): what the crop models share.

A crop model is one module under `agmodels.models` (group `crop`, no risk layer) whose `stages(**options)` lists the
crop's stages in order, and whose outputs include `stage`: each day, the index in that list of the latest stage
reached (−1 before the first, NaN where unknown). The list is fixed per crop so an index means the same stage for
every maturity; a stage a variety doesn't have (a leaf beyond its last) is never reached and the index skips it.

Development counts from the biofix, the planting date by default. Missing days add nothing (`agmodels.accumulate`),
so a gap holds development back rather than blanking the season; in the box the inputs come gap-filled (D25).
Stages a model estimates between the ones its source predicts are flagged `estimated`, so the page can say so.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, cast

import numpy as np

from agmodels.spec import ModelSpec, Option


@dataclass(frozen=True, kw_only=True)
class CropStage:
    code: str  # the staging system's label: VE, V6, R1, …
    name: str
    description: str = ""
    estimated: bool = False  # placed between stages the source predicts, not predicted by it


class CropModel(Protocol):
    SPEC: ModelSpec
    MARGIN_DAYS: int  # how far off its stage dates typically are, either way: the muted margin of gated risk (D33)

    def stages(self, **options: str) -> tuple[CropStage, ...]: ...

    def outputs(
        self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str
    ) -> dict[str, np.ndarray]: ...

    def explore(self, **values: float) -> dict[str, float]: ...


def stage_reached(progress, thresholds) -> np.ndarray:
    """Index of the latest stage whose threshold `progress` has reached, by stage (thresholds along the last axis
    of `thresholds`, NaN for a stage the variety skips); −1 before the first, NaN where progress is."""
    p = np.asarray(progress, dtype=float)
    t = np.asarray(thresholds, dtype=float)
    reached = p[..., None] >= t  # NaN thresholds compare False
    index = np.where(reached.any(axis=-1), t.shape[-1] - 1 - np.argmax(reached[..., ::-1], axis=-1), -1)
    return np.where(np.isnan(p), np.nan, index.astype(float))


def stage_days(stage: np.ndarray, count: int) -> np.ndarray:
    """The first day index on which each of `count` stages is reached or passed (axis 0 of the result is the
    stage, the rest the grid's), NaN if never in the series: the dates a chart marks, through the forecast and
    projection when the series runs on."""
    s = np.asarray(stage, dtype=float)
    out = np.full((count, *s.shape[1:]), np.nan)
    for k in range(count):
        passed = s >= k
        out[k] = np.where(passed.any(axis=0), np.argmax(passed, axis=0), np.nan)
    return out


def number_option(options: dict[str, str], option: Option) -> float:
    """A numeric option's value: one of its choices or any number (a rating from the seed bag)."""
    value = options.get(option.name, option.default)
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"{option.name} must be a number, got {value!r}") from None


# Disease risk by crop stage (D33)

NOT_SUSCEPTIBLE, MARGIN, SUSCEPTIBLE = 0.0, 1.0, 2.0


def susceptibility(stage, stages: tuple[CropStage, ...], first: str, last: str, margin_days: int) -> np.ndarray:
    """Each day: SUSCEPTIBLE while the crop is from `first` through `last`, MARGIN within `margin_days` of such a
    day (stage estimates are a few days off either way), NOT_SUSCEPTIBLE otherwise, NaN where the stage is unknown
    (before planting). Days on axis 0; a risk chart greys NOT_SUSCEPTIBLE days and mutes MARGIN ones."""
    s = np.asarray(stage, dtype=float)
    codes = [st.code for st in stages]
    lo, hi = codes.index(first), codes.index(last)
    if lo > hi:
        raise ValueError(f"{first} comes after {last}")
    inside = (s >= lo) & (s <= hi)
    # any susceptible day within margin_days either side: a window count over the padded series
    count = np.cumsum(np.concatenate([np.zeros((1, *s.shape[1:])), inside.astype(float)]), axis=0)
    n = s.shape[0]
    days = np.arange(n)
    upper = np.minimum(days + margin_days + 1, n)
    lower = np.maximum(days - margin_days, 0)
    near = (count[upper] - count[lower]) > 0
    level = np.where(inside, SUSCEPTIBLE, np.where(near, MARGIN, NOT_SUSCEPTIBLE))
    return np.where(np.isnan(s), np.nan, level)


def disease_susceptibility(spec: ModelSpec, crop_stage: np.ndarray, **crop_options: str) -> np.ndarray | None:
    """`susceptibility` for a disease model from its crop model's `stage` output; None if the model isn't gated."""
    if spec.susceptible is None:
        return None
    from agmodels.registry import model  # the registry imports the crop modules, which import this one

    gate = spec.susceptible
    crop = cast(CropModel, model(gate.crop))
    return susceptibility(crop_stage, crop.stages(**crop_options), gate.first, gate.last, crop.MARGIN_DAYS)
