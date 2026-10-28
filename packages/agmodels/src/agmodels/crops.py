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
from typing import Protocol

import numpy as np

from agmodels.spec import ModelSpec, Option


@dataclass(frozen=True)
class CropStage:
    code: str  # the staging system's label: VE, V6, R1, …
    name: str
    description: str = ""
    estimated: bool = False  # placed between stages the source predicts, not predicted by it


class CropModel(Protocol):
    SPEC: ModelSpec

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
