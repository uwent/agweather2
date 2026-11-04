"""Insect models as declarative specs (PLAN.md Phase 3 D, like the Crop Risk Tool's `Insect()`), run by one engine.

Each insect accumulates single-sine degree days (°F) from its biofix between its thresholds. Its phenology is
declared one of three ways:

- `life_stages` (D36): each stage of the first generation (adult flight, larval feeding) a PERT curve in degree
  days from (start, peak, end), equal-area, so a wider generation has a lower peak. Later generations follow every
  `generation_dd`, until the season ends, spreading as a distributed delay (Manetsch 1976): generation *n* is the
  first convolved with *n*−1 generation times, each gamma-distributed (mean `generation_dd`, SD `generation_sd`), so
  their variances add and the spread grows with √*n*. A stage's activity is the sum over its generations, 1 at the
  first generation's peak; risk is the sum of each stage's weight times its activity, continuous, with words from
  `risk_thresholds`. Action windows are the days a stage is between two fractions of complete in some generation
  (10–90% of adult flight: "Avoid planting during adult flight").
- `stages` (legacy, until each insect moves to life stages): a step table of degree-day starts with a severity and a
  life-stage label (the Crop Risk Tool's key);
- `generations` (legacy): VDIFN's (start, peak, end) per generation, severity rising along a half sine from start to
  peak and falling from peak to end, rounded up (`Insect#sev_ramp`); a later generation overrides where they touch.

At the end of the season (after day 250, early September), freezes end it. With life stages, activity is scaled by a
freeze factor, max(0, 1 − f/4) for f days in the last 14 with a minimum at or below −2 °C, held at its lowest so
far that year, so a warm spell can't bring insects back; once it reaches 0 the season is complete. The legacy
definitions instead lower severity by f (the Crop Risk Tool's rule; VDIFN's applied only from November).
`day_of_year` is supplied with the inputs by whoever runs the model (it isn't stored); without it there's no freeze
reduction.

The insects, one module each, are in `agmodels.insects`.
"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Literal

import numpy as np

from agmodels.accumulate import rolling_sum, running_total
from agmodels.degree_days import degree_days_average, degree_days_sine
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
FREEZE_KILL_DAYS = 4  # freezing days in the last 14 that end the season (VDIFN's subtraction from peak severity)
DD_STEP, DD_MAX = 1.0, 10_000.0  # the degree-day grid the curves are tabulated on; totals past it read its last value
RISK_THRESHOLDS = (0.05, 0.25, 0.5, 0.75)  # lower bounds of Low … Very high, in first-generation peaks of weight 1


@dataclass(frozen=True, kw_only=True)
class Stage:
    start: float  # degree days (°F) from the biofix
    severity: int
    label: str


@dataclass(frozen=True, kw_only=True)
class LifeStage:
    """A life stage's first generation, in degree days (°F) from the biofix: a PERT curve from start through peak
    to end, and its weight, the crop risk at the first generation's peak."""

    label: str
    start: float
    peak: float
    end: float
    weight: float = 1.0

    def __post_init__(self):
        if not self.start < self.peak < self.end:
            raise ValueError(f"{self.label}: start, peak and end must increase")

    @property
    def key(self) -> str:
        return slug(self.label)


@dataclass(frozen=True, kw_only=True)
class DerivedStage:
    """A stage timed from another (D36): present from `lag` degree days after each individual enters the stage it
    follows, for `duration` (larvae from egg-laying adults: pre-oviposition and egg, then the larval period). Its
    generations are the followed stage's."""

    label: str
    follows: str  # the label of a `LifeStage`
    lag: float
    duration: float
    weight: float = 1.0

    @property
    def key(self) -> str:
        return slug(self.label)


@dataclass(frozen=True, kw_only=True)
class ActionWindow:
    """When to act (D36): the days a life stage is between two fractions of complete in some generation."""

    label: str  # the intervention, e.g. "Avoid planting during adult flight"
    stage: str  # the label of the life stage it follows
    between: tuple[float, float] = (0.1, 0.9)

    @property
    def key(self) -> str:
        return slug(self.label)


@dataclass(frozen=True, kw_only=True)
class Insect:
    id: str
    name: str
    crops: tuple[str, ...]
    base_f: float
    upper_f: float | None
    biofix: str  # MM-DD
    stages: tuple[Stage, ...] = ()
    generations: tuple[tuple[float, float, float], ...] = ()
    biofix_label: str = "January 1, or the biofix event named in the description"
    source: str = "VDIFN"
    status: str = "stable"
    citations: tuple[Citation, ...] = ()
    topic: str = ""  # the pest's topic page, when several models share one (Colorado potato beetle); default its id
    life_stages: tuple[LifeStage | DerivedStage, ...] = ()  # the first a LifeStage; it sets the default spread
    dd_method: Literal["sine", "average"] = "sine"  # the method its source's thresholds use (D37)
    generation_dd: float | None = None  # degree days between generations; None: one generation
    generation_sd: float | None = None  # SD of a generation's time; None: the first stage's first-generation SD
    action_windows: tuple[ActionWindow, ...] = ()
    risk_thresholds: tuple[float, ...] = RISK_THRESHOLDS
    version: str = "0.1"
    changelog: tuple[Change, ...] = ()  # after the port (1.0)

    def __post_init__(self):
        stages = {s.label for s in self.life_stages}
        timed = {s.label for s in self.life_stages if isinstance(s, LifeStage)}
        if self.life_stages and not isinstance(self.life_stages[0], LifeStage):
            raise ValueError(f"{self.id}: the first life stage needs its own start, peak and end")
        for s in self.life_stages:
            if isinstance(s, DerivedStage) and s.follows not in timed:
                raise ValueError(f"{self.id}: {s.label!r} follows {s.follows!r}, which isn't a timed life stage")
        for w in self.action_windows:
            if w.stage not in stages:
                raise ValueError(f"{self.id}: action window {w.label!r} follows an unknown stage {w.stage!r}")


class InsectModel:
    """An `agmodels.spec.Model` for one insect; its summary is the `summary` in its page's front matter."""

    def __init__(self, insect: Insect, summary: str):
        self.insect = insect
        self.SPEC = ModelSpec(
            id=insect.id,
            name=insect.name,
            group="insect",
            version=insect.version,
            status=insect.status,  # type: ignore[arg-type]
            summary=summary,
            topics=(insect.topic or insect.id,),
            crops=insect.crops,
            citations=insect.citations or (Citation(text=f"{insect.source} (UW–Madison Vegetable Entomology)"),),
            inputs=(
                Quantity(name="air_temperature_min", label="Minimum temperature", unit="degC"),
                Quantity(name="air_temperature_max", label="Maximum temperature", unit="degC"),
            ),
            outputs=(
                Quantity(name="dd_total", label="Degree days since the biofix", unit="degF_day"),
                Quantity(name="dd", label="Degree days", unit="degF_day"),
                *self._outputs(),
            ),
            risk=self._risk(),
            explorer=(
                ExplorerInput(
                    name="dd_total",
                    label="Degree days since the biofix",
                    unit="degF_day",
                    minimum=0,
                    maximum=4000,
                    step=10,
                    default=500,
                ),
            ),
            explorer_outputs=self._explored(),
            sweep={"dd_total": tuple(float(d) for d in range(0, 4001, 100))},
            biofix=Biofix(default=insect.biofix, label=insect.biofix_label),
            context=("day_of_year",),  # the freeze reduction; without it there's none
            changelog=(
                Change(version="0.1", date="2026-10-28", note=f"Ported from {insect.source}."),
                *insect.changelog,
            ),
        )

    def _explored(self) -> tuple[Quantity, ...]:
        return (Quantity(name="severity", label="Severity", unit="index"),)

    def _outputs(self) -> tuple[Quantity, ...]:
        return (
            Quantity(name="stage", label="Life stage", unit="index"),
            Quantity(name="freeze_reduction", label="Severity removed by recent freezes", unit="index"),
        )

    def _risk(self) -> Risk:
        return Risk(levels=SEVERITY_LEVELS, criteria=criteria(self.insect))

    def outputs(self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
        i = self.insect
        lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
        dd = insect_degree_days(insect=i, min_f=lo, max_f=hi)
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


class PhenologyModel(InsectModel):
    def _explored(self) -> tuple[Quantity, ...]:
        return (Quantity(name="risk", label="Activity (1: a weight-1 stage's first-generation peak)", unit="index"),)

    """An insect declared by its life stages (D36)."""

    def _outputs(self) -> tuple[Quantity, ...]:
        i = self.insect
        return (
            *(
                q
                for s in i.life_stages
                for q in (
                    Quantity(name=f"activity_{s.key}", label=f"{s.label} activity", unit="index"),
                    Quantity(
                        name=f"generations_{s.key}", label=f"Generations of {s.label.lower()} complete", unit="index"
                    ),
                )
            ),
            *(Quantity(name=f"window_{w.key}", label=w.label, unit="index") for w in i.action_windows),
            Quantity(name="freeze_factor", label="Share left after fall freezes", unit="index"),
            Quantity(name="season_complete", label="Season ended by freezes", unit="index"),
        )

    def _risk(self) -> Risk:
        return Risk(
            levels=SEVERITY_LEVELS, criteria=phenology_criteria(self.insect), thresholds=self.insect.risk_thresholds
        )

    def outputs(self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
        i = self.insect
        lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
        dd = insect_degree_days(insect=i, min_f=lo, max_f=hi)
        total = running_total(dd, biofix_index)
        factor = (
            freeze_factor(tmin_c=inputs["air_temperature_min"], day_of_year=inputs["day_of_year"])
            if "day_of_year" in inputs
            else np.ones_like(total)
        )
        alive = factor > 0
        out = {"dd_total": total, "dd": dd}
        for name, value in evaluate(insect=i, dd_total=total).items():
            if name.startswith("activity_"):
                value = value * factor
            elif name.startswith("window_"):
                value = np.where(alive | np.isnan(value), value, 0.0)
            out[name] = value
        out["freeze_factor"] = np.where(np.isnan(total), np.nan, factor)
        out["season_complete"] = np.where(np.isnan(total), np.nan, (~alive).astype(float))
        return out

    def risk(self, outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
        """The sum of each stage's weight times its activity: 1 at a weight-1 stage's first-generation peak."""
        stages = self.insect.life_stages
        return np.sum([s.weight * np.asarray(outputs[f"activity_{s.key}"], dtype=float) for s in stages], axis=0)

    def explore(self, dd_total: float) -> dict[str, float]:
        values = evaluate(insect=self.insect, dd_total=np.array([dd_total]))
        values["risk"] = self.risk(values)
        return {k: float(v[0]) for k, v in values.items()}


def model_for(insect: Insect, summary: str) -> InsectModel:
    """The model for an insect: by its life stages (D36), or the legacy stage table or generations."""
    return (PhenologyModel if insect.life_stages else InsectModel)(insect=insect, summary=summary)


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def pert_pdf(x: np.ndarray, start: float, peak: float, end: float) -> np.ndarray:
    """The PERT density (a beta scaled to start–end, its mode at peak) at x."""
    a = 1 + 4 * (peak - start) / (end - start)
    b = 1 + 4 * (end - peak) / (end - start)
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    inside = (x > start) & (x < end)
    xi = np.where(inside, x, (start + end) / 2)
    log_pdf = (a - 1) * np.log(xi - start) + (b - 1) * np.log(end - xi) - log_beta - (a + b - 1) * math.log(end - start)
    return np.where(inside, np.exp(log_pdf), 0.0)


def pert_sd(start: float, peak: float, end: float) -> float:
    mean = (start + 4 * peak + end) / 6
    return math.sqrt((mean - start) * (end - mean) / 7)


def gamma_pdf(x: np.ndarray, shape: float, scale: float) -> np.ndarray:
    positive = x > 0
    xi = np.where(positive, x, 1.0)
    log_pdf = (shape - 1) * np.log(xi) - xi / scale - math.lgamma(shape) - shape * math.log(scale)
    return np.where(positive, np.exp(log_pdf), 0.0)


def dd_grid() -> np.ndarray:
    return np.arange(0, DD_MAX + DD_STEP, DD_STEP)


def insect_degree_days(insect: Insect, min_f: np.ndarray, max_f: np.ndarray) -> np.ndarray:
    """Daily degree days by the insect's method: single sine, or the simple average with both temperatures capped
    at the upper threshold."""
    if insect.dd_method == "average":
        return degree_days_average(min_f, max_f, base=insect.base_f, upper=insect.upper_f)
    return degree_days_sine(min_f, max_f, base=insect.base_f, upper=insect.upper_f)


def generation_densities(insect: Insect, stage: LifeStage) -> list[np.ndarray]:
    """A stage's density in each generation on `dd_grid()` (each integrating to 1 within the grid)."""
    x = dd_grid()
    first = pert_pdf(x, start=stage.start, peak=stage.peak, end=stage.end)
    if insect.generation_dd is None:
        return [first]
    first_stage = insect.life_stages[0]
    assert isinstance(first_stage, LifeStage)
    sd = insect.generation_sd or pert_sd(start=first_stage.start, peak=first_stage.peak, end=first_stage.end)
    mean = insect.generation_dd
    size = 1 << math.ceil(math.log2(2 * len(x)))
    first_f = np.fft.rfft(first, size)
    densities = [first]
    n = 2
    while stage.start + (n - 1) * mean - 4 * math.sqrt(n - 1) * sd < DD_MAX:  # until a generation's tail is past
        # n − 1 gamma generation times sum to a gamma with n − 1 times the shape
        delay = gamma_pdf(x, shape=(n - 1) * mean**2 / sd**2, scale=sd**2 / mean)
        density = np.fft.irfft(first_f * np.fft.rfft(delay, size), size)[: len(x)] * DD_STEP
        densities.append(np.where(density > 1e-12 * density.max(), density, 0.0))  # drop the transform's rounding
        n += 1
    return densities


@cache
def curves(insect: Insect) -> dict[str, np.ndarray]:
    """Each output that depends only on degree days, tabulated on `dd_grid()`: per stage its activity (1 at the
    first generation's peak) and generations complete (the sum of each generation's fraction complete), and per
    action window whether it's open (0 or 1)."""
    tables: dict[str, np.ndarray] = {}
    complete: dict[str, list[np.ndarray]] = {}
    for stage in insect.life_stages:
        if isinstance(stage, LifeStage):
            present = generation_densities(insect=insect, stage=stage)
            complete[stage.label] = [np.minimum(np.cumsum(d) * DD_STEP, 1.0) for d in present]
        else:  # entered `lag` after the followed stage, left `duration` later
            entered = [_shift(f, by=stage.lag) for f in complete[stage.follows]]
            complete[stage.label] = [_shift(f, by=stage.lag + stage.duration) for f in complete[stage.follows]]
            present = [a - b for a, b in zip(entered, complete[stage.label], strict=True)]
        tables[f"activity_{stage.key}"] = np.sum(present, axis=0) / present[0].max()
        tables[f"generations_{stage.key}"] = np.sum(complete[stage.label], axis=0)
    for w in insect.action_windows:
        low, high = w.between
        open_ = np.zeros_like(dd_grid(), dtype=bool)
        for fraction in complete[w.stage]:
            open_ |= (fraction >= low) & (fraction <= high)
        tables[f"window_{w.key}"] = open_.astype(float)
    return tables


def _shift(values: np.ndarray, by: float) -> np.ndarray:
    """A table moved `by` degree days later on the grid (0 before)."""
    steps = round(by / DD_STEP)
    return np.r_[np.zeros(steps), values[: len(values) - steps]]


def evaluate(insect: Insect, dd_total: np.ndarray) -> dict[str, np.ndarray]:
    """The degree-day curves at each total (any shape; NaN stays NaN)."""
    total = np.asarray(dd_total, dtype=float)
    x = dd_grid()
    out = {}
    for name, table in curves(insect).items():
        value = np.interp(total, x, table)
        if name.startswith("window_"):  # open or not, at the nearest grid point
            value = np.interp(np.round(total / DD_STEP) * DD_STEP, x, table)
        out[name] = np.where(np.isnan(total), np.nan, value)
    return out


def freeze_factor(tmin_c: np.ndarray, day_of_year: np.ndarray) -> np.ndarray:
    """1 until fall freezes, then max(0, 1 − f/4) for f days in the last 14 at or below −2 °C (after day 250), held
    at its lowest so far each year, so a warm spell can't raise it: frozen insects don't come back."""
    tmin = np.asarray(tmin_c, dtype=float)
    freezing = rolling_sum((tmin <= FREEZE_C).astype(float), 14)
    doy = np.asarray(day_of_year).reshape(-1)
    late = (doy > SEASON_END_DAY).reshape(-1, *([1] * (tmin.ndim - 1)))
    raw = np.where(late, np.maximum(0.0, 1 - freezing / FREEZE_KILL_DAYS), 1.0)
    year = np.cumsum(np.r_[True, np.diff(doy) < 0])  # a new year starts where the day of year falls
    out = np.empty_like(raw)
    for y in np.unique(year):
        days = year == y
        out[days] = np.minimum.accumulate(raw[days], axis=0)
    return out


def window_periods(open_: np.ndarray) -> list[tuple[int, int]]:
    """The first and last index of each run of open days in a point's series (an action window's dates)."""
    flags = np.nan_to_num(np.asarray(open_, dtype=float)) > 0
    edges = np.diff(np.r_[0, flags.astype(int), 0])
    return list(zip(np.flatnonzero(edges == 1).tolist(), (np.flatnonzero(edges == -1) - 1).tolist(), strict=True))


def phenology_criteria(insect: Insect) -> str:
    """How life stages become risk, in words."""
    upper = "no upper threshold" if insect.upper_f is None else f"upper {insect.upper_f:g} °F"
    method = "Single-sine" if insect.dd_method == "sine" else "Average"
    stages = "; ".join(_stage_words(s) for s in insect.life_stages)
    repeat = (
        f" Later generations follow every {insect.generation_dd:,g} degree days, spreading as each generation's "
        "timing varies."
        if insect.generation_dd
        else ""
    )
    levels = ", ".join(
        f"{word} from {t:g}" for word, t in zip(SEVERITY_LEVELS[1:], insect.risk_thresholds, strict=True)
    )
    return (
        f"{method} degree days (base {insect.base_f:g} °F, {upper}) since the biofix time each life stage's first "
        f"generation ({stages}).{repeat} Risk is the sum of each stage's weight times its activity (1 at "
        f"the first generation's peak): {levels}. After day 250, fall freezes end the season."
    )


def _stage_words(stage: LifeStage | DerivedStage) -> str:
    if isinstance(stage, LifeStage):
        when = f"start, peak and end {stage.start:,g}, {stage.peak:,g} and {stage.end:,g}"
    else:
        when = f"from {stage.lag:,g} after {stage.follows.lower()} for {stage.duration:,g}"
    return f"{stage.label.lower()}: {when}, weight {stage.weight:g}"


def criteria(insect: Insect) -> str:
    """How degree days become severity, in words, from the stage table or generations."""
    upper = "no upper threshold" if insect.upper_f is None else f"upper {insect.upper_f:g} °F"
    dd = f"Degree days (base {insect.base_f:g} °F, {upper}) since the biofix"
    if insect.stages:
        steps = ", ".join(f"{s.severity} from {s.start:,g}" for s in insect.stages)
        rule = f"{dd} set the severity: {steps}."
    else:
        spans = "; ".join(f"{a:,g}, {b:,g} and {c:,g}" for a, b, c in insect.generations)
        rule = (
            f"{dd} set the severity, rising along a half sine from each generation's start to 4 at its peak and "
            f"falling to its end (start, peak and end: {spans})."
        )
    return f"{rule} After day 250, less 1 for each day at or below −2 °C in the last 14."


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
