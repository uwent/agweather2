"""Insect models as declarative specs (PLAN.md Phase 3 D, like the Crop Risk Tool's `Insect()`), run by one engine.

Each insect accumulates single-sine degree days (°F) from its biofix between its thresholds, and maps the total
to a severity of 0–4 in one of two ways:

- `stages`: a step table of degree-day starts with a severity and a life-stage label (the Crop Risk Tool's key);
- `generations`: VDIFN's (start, peak, end) per generation, severity rising along a half sine from start to peak
  and falling from peak to end, rounded up (`Insect#sev_ramp`); a later generation overrides where they touch.

At the end of the season (after day 250, early September), severity drops by the number of days in the last 14
with a minimum at or below −2 °C (the Crop Risk Tool's rule; VDIFN's applied only from November). The three
layers: daily minimum and maximum temperature (inputs), degree days, their total and the life stage (outputs),
and the severity less the freeze reduction (risk). `day_of_year` is supplied with the inputs by whoever runs the
model (it isn't stored); without it there's no freeze reduction.

The insect list is in `agmodels.insect_list`.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from agmodels.accumulate import rolling_sum, running_total
from agmodels.degree_days import degree_days_sine
from agmodels.spec import (
    SEVERITY_LEVELS,
    Biofix,
    Change,
    Citation,
    ExplorerInput,
    ModelSpec,
    Quantity,
    Risk,
)

FREEZE_C = -2.0
SEASON_END_DAY = 250


@dataclass(frozen=True)
class Stage:
    start: float  # degree days (°F) from the biofix
    severity: int
    label: str


@dataclass(frozen=True)
class Insect:
    id: str
    name: str
    crops: tuple[str, ...]
    base_f: float
    upper_f: float | None
    biofix: str  # MM-DD
    criteria: str  # what the degree days mean, for the model page and legend
    stages: tuple[Stage, ...] = ()
    generations: tuple[tuple[float, float, float], ...] = ()
    biofix_label: str = "January 1, or the biofix event named in the description"
    source: str = "VDIFN"
    status: str = "stable"
    citations: tuple[Citation, ...] = ()


class InsectModel:
    """An `agmodels.spec.Model` for one insect."""

    def __init__(self, insect: Insect):
        self.insect = insect
        upper = "no upper threshold" if insect.upper_f is None else f"upper {insect.upper_f:g} °F"
        self.SPEC = ModelSpec(
            id=insect.id,
            name=insect.name,
            group="insect",
            version="1.0",
            status=insect.status,  # type: ignore[arg-type]
            summary=f"{insect.name} development from degree days (base {insect.base_f:g} °F, {upper}), with the "
            "risk of damage it implies.",
            topics=(insect.id,),
            crops=insect.crops,
            citations=insect.citations or (Citation(f"{insect.source} (UW–Madison Vegetable Entomology)"),),
            inputs=(
                Quantity("air_temperature_min", "Minimum temperature", "degC"),
                Quantity("air_temperature_max", "Maximum temperature", "degC"),
            ),
            outputs=(
                Quantity("dd_total", "Degree days since the biofix", "degF_day"),
                Quantity("dd", "Degree days", "degF_day"),
                Quantity("stage", "Life stage", "index"),
                Quantity("freeze_reduction", "Severity removed by recent freezes", "index"),
            ),
            risk=Risk(SEVERITY_LEVELS, insect.criteria),
            explorer=(ExplorerInput("dd_total", "Degree days since the biofix", "degF_day", 0, 4000, 10, 500),),
            sweep={"dd_total": tuple(float(d) for d in range(0, 4001, 100))},
            biofix=Biofix(insect.biofix, insect.biofix_label),
            context=("day_of_year",),  # the freeze reduction; without it there's none
            changelog=(Change("1.0", "2026-10-28", f"Ported from {insect.source}."),),
        )

    def outputs(self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
        i = self.insect
        lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
        dd = degree_days_sine(lo, hi, i.base_f, i.upper_f)
        total = running_total(dd, biofix_index)
        reduction = (
            freeze_reduction(inputs["air_temperature_min"], inputs["day_of_year"])
            if "day_of_year" in inputs
            else np.zeros_like(total)
        )
        return {"dd_total": total, "dd": dd, "stage": stage_index(total, i.stages), "freeze_reduction": reduction}

    def risk(self, outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
        level = severity(np.asarray(outputs["dd_total"], dtype=float), self.insect)
        return np.where(np.isnan(level), np.nan, np.maximum(level - outputs["freeze_reduction"], 0))

    def explore(self, dd_total: float) -> dict[str, float]:
        total = np.asarray([dd_total], dtype=float)
        return {
            "severity": float(severity(total, self.insect)[0]),
            "stage": float(stage_index(total, self.insect.stages)[0]),
        }


def stage_index(dd_total: np.ndarray, stages: tuple[Stage, ...]) -> np.ndarray:
    """Index of the last stage whose start the total has reached (-1 before the first; NaN without stages)."""
    total = np.asarray(dd_total, dtype=float)
    if not stages:
        return np.full(total.shape, np.nan)
    reached = sum(((total >= s.start).astype(float) for s in stages), np.zeros_like(total)) - 1
    return np.where(np.isnan(total), np.nan, reached)


def severity(dd_total: np.ndarray, insect: Insect) -> np.ndarray:
    total = np.asarray(dd_total, dtype=float)
    if insect.stages:
        index = stage_index(total, insect.stages)
        levels = np.array([0.0] + [s.severity for s in insect.stages])
        return np.where(np.isnan(index), np.nan, levels[np.nan_to_num(index, nan=-1).astype(int) + 1])
    level = np.zeros_like(total)
    for start, peak, end in insect.generations:
        within = (total >= start) & (total <= end)
        level = np.where(within, _sine_ramp(total, start, peak, end), level)
    return np.where(np.isnan(total), np.nan, level)


def freeze_reduction(tmin_c: np.ndarray, day_of_year: np.ndarray) -> np.ndarray:
    """After day 250, the days in the last 14 with a minimum at or below −2 °C; 0 before."""
    tmin = np.asarray(tmin_c, dtype=float)
    freezing = rolling_sum((tmin <= FREEZE_C).astype(float), 14)
    doy = np.asarray(day_of_year).reshape(-1, *([1] * (tmin.ndim - 1)))
    return np.where(doy > SEASON_END_DAY, freezing, 0.0)


def _sine_ramp(total: np.ndarray, start: float, peak: float, end: float) -> np.ndarray:
    """VDIFN's `sev_ramp`: 0–4 along a half sine up from start to peak and down from peak to end, rounded up."""

    def half(value, a, b):
        x = (value - a) / (b - a)
        return np.ceil((np.sin(x * math.pi - math.pi / 2) + 1) / 2 * 4)

    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total <= peak, half(total, start, peak), half(-total, -end, -peak))
