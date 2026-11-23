"""Insect models as declarative specs (Phase 3 D, like the Crop Risk Tool's `Insect()`), run by one engine.

Each insect accumulates single-sine degree days (°F) from its biofix between its thresholds. Its phenology is
declared one of three ways:

- `life_stages` (D36): each stage of the first generation (adult flight, larval feeding) a PERT curve in degree
  days from (start, peak, end), equal-area, so a wider generation has a lower peak. Later generations follow every
  `generation_dd`, until the season ends, spreading as a distributed delay (Manetsch 1976): generation *n* is the
  first convolved with *n*−1 generation times, each gamma-distributed (mean `generation_dd`, SD `generation_sd`), so
  their variances add and the spread grows with √*n*. A stage's activity is the sum over its generations, 1 at the
  first generation's peak; risk is the sum of each stage's weight times its activity, continuous, with words from
  `risk_thresholds`. Action windows are the days a stage is between two fractions of complete in some generation
  (10–90% of adult flight: "Avoid planting during adult flight"), or, for a stage timed from another, the days from
  when its first individuals enter it until most have left (black cutworm's cutting caterpillars).
  Generations may weigh differently in the risk (`generation_weights`: the generation that does the damage), and an
  insect may take another set of life stages where a fixed value of the place is below a bound (`PlaceForm`: European
  corn borer's one flight where the normal season is short).
- `life_stages` as `FittedStage`s: each stage's abundance fitted to field counts over degree days, every generation at
  once (a GAM of log(count + 1), tabulated), read off the fit: the typical count and activity (1 at the fit's peak).
  Colorado potato beetle (Bradford and Groves, unpublished). No generations, derived stages or action windows. A
  fitted stage may also carry the same fit on the calendar (day of year); the insect then takes a `clock` option,
  degree days or calendar, its default `Insect.clock` (D101): the calendar curve is the typical season where the
  data came from, the degree-day curve the one that moves with the year's weather and carries farther.
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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date
from functools import cache
from typing import Literal

import numpy as np

from agmodels.accumulate import rolling_sum
from agmodels.degree_days import (
    degree_days_average,
    degree_days_average_capped_mean,
    degree_days_modified,
    degree_days_sine,
)
from agmodels.ingredients import Accumulation, DegreeDays, Ingredient, finished
from agmodels.spec import (
    SEVERITY_LEVELS,
    Biofix,
    Change,
    Check,
    Citation,
    ExplorerInput,
    Input,
    ModelSpec,
    Option,
    PlaceNormal,
    Quantity,
    Risk,
    TrainingArea,
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
class FittedStage:
    """A life stage's abundance as fitted to field counts by degree days (°F) from the biofix, all generations at
    once, tabulated at increasing totals `dd`: the fit's log(count + 1) (`transform="log1p"`, a GAM of log counts), or
    the log of the fitted mean (`"log"`, a log-link GAM of an index). Read off by linear interpolation; before the
    first total (before the data begin) it's 0; past the last (the end of the data) held at its last value until fall
    freezes end the season. Its value is the fit back-transformed: exp(fit) − 1, a typical count (a geometric mean,
    below counts' arithmetic mean), below 0 taken as 0; or exp(fit). Its activity is that value over its peak."""

    label: str
    count_label: str  # what a value is, e.g. "Adults per 25 sweeps (typical count)"
    dd: tuple[float, ...]
    log_count: tuple[float, ...]  # the fit on its link scale, by `transform`
    weight: float = 1.0
    transform: Literal["log1p", "log"] = "log1p"
    # The same stage fitted on the calendar (D101): days of year, increasing, with the fit at each on the same link
    # scale; read as the degree-day fit is (0 before the first day, held after the last). Empty: degree days only
    days: tuple[float, ...] = ()
    log_count_by_day: tuple[float, ...] = ()

    def __post_init__(self):
        if len(self.dd) != len(self.log_count) or len(self.dd) < 2 or np.any(np.diff(self.dd) <= 0):
            raise ValueError(f"{self.label}: dd must increase, one log count each")
        if len(self.days) != len(self.log_count_by_day) or (
            self.days
            and (len(self.days) < 2 or np.any(np.diff(self.days) <= 0) or not 1 <= self.days[0] <= self.days[-1] <= 366)
        ):
            raise ValueError(f"{self.label}: days must increase within 1–366, one log count each")

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
    """When to act (D36), in each generation: by default (`when="complete"`) the days a life stage is between two
    fractions of complete (for a stage timed from another, the share that has left it). With `when="present"`, for
    a stage timed from another (`DerivedStage`), the days from when the share `between[0]` has entered the stage until
    the share `between[1]` has left it: a window that opens with the first individuals, such as the first caterpillars
    big enough to cut plants, rather than once a share has passed through."""

    label: str  # the intervention, e.g. "Avoid planting during adult flight"
    stage: str  # the label of the life stage it follows
    between: tuple[float, float] = (0.1, 0.9)
    when: Literal["complete", "present"] = "complete"

    @property
    def key(self) -> str:
        return slug(self.label)


@dataclass(frozen=True, kw_only=True)
class EstimatedBiofix:
    """The biofix event's expected degree days from January 1 (°F, by the insect's method) at a latitude (D36). Where
    the biofix is left at its default of January 1, the life stages are timed from the day each place reaches it;
    a grower's own date replaces the estimate. Codling moth's first catch (Jones et al. 2013)."""

    event: str  # e.g. "first catch": names the outputs (`dd_after_first_catch`, `first_catch_estimated`)
    dd_at: Callable[[np.ndarray], np.ndarray]  # latitude (°N) → degree days from January 1

    @property
    def key(self) -> str:
        return slug(self.event)


@dataclass(frozen=True, kw_only=True)
class GenerationSize:
    """How much of a generation develops the same season rather than entering diapause, as a class by the degree
    days from January 1 on the date diapause begins (Riedl and Croft 1978 for codling moth): class 1 below the first
    bound, 2 from it, and so on. An output only: every generation still counts alike in risk (D37)."""

    name: str
    label: str
    on: str  # MM-DD, the date the degree days are read (blank before it)
    bounds: tuple[float, ...]


@dataclass(frozen=True, kw_only=True)
class PlaceForm:
    """Another set of life stages for places where a fixed value of the place, a normal total (`PlaceNormal`), is
    below a bound: European corn borer's one-flight form where the normal season is short. The stages carry the
    same labels as the insect's (the outputs and windows are the same); its generations replace the insect's. Where
    the normal is missing (outside the normals' area), the insect's own stages apply, and the run says so."""

    name: str  # the output saying where it applies, e.g. "one_flight"
    label: str  # that output's label: "One flight here (1) or two (0)"
    words: str  # the form in a sentence's middle, e.g. "one flight a year"
    normal: PlaceNormal
    below: float  # the form applies where the normal is below this
    life_stages: tuple[LifeStage | DerivedStage, ...]
    generation_dd: float | None = None
    generation_sd: float | None = None
    max_generations: int | None = None


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
    biofix_label: str | None = None  # None: the default date, "or your own date" (`default_biofix_label`)
    source: str = "VDIFN"
    # what the 0.1 changelog line says it was ported from, when the model has since moved to another source
    ported_from: str = ""
    status: str = "beta"
    citations: tuple[Citation, ...] = ()
    topic: str = ""  # the pest's topic page, when several models share one (Colorado potato beetle); default its id
    # the first a LifeStage (it sets the default spread), or all FittedStages
    life_stages: tuple[LifeStage | DerivedStage | FittedStage, ...] = ()
    # the method its source's thresholds use (D37); "average_capped_mean" caps the day's mean, not each temperature,
    # and has no shared running total on the grid, so its daily degree days are kept per model (`agdata.modelmaps`)
    dd_method: Literal["sine", "average", "modified", "average_capped_mean"] = "sine"
    generation_dd: float | None = None  # degree days between generations; None: one generation
    generation_sd: float | None = None  # SD of a generation's time; None: the first stage's first-generation SD
    action_windows: tuple[ActionWindow, ...] = ()
    risk_thresholds: tuple[float, ...] = RISK_THRESHOLDS
    max_generations: int | None = None  # None: generations repeat until the season ends
    estimated_biofix: EstimatedBiofix | None = None  # the biofix event by latitude where the biofix is January 1
    generation_size: GenerationSize | None = None
    version: str = "0.1"
    changelog: tuple[Change, ...] = ()  # after the port (1.0)
    checks: tuple[Check, ...] = ()  # D98
    clock: Literal["degree_days", "calendar"] = "degree_days"  # the default clock of fitted stages with both (D101)
    trained: TrainingArea | None = None  # where the fitted stages' data came from (D101)
    # Each generation's weight in the risk, the first generation's first, later generations the last one's; empty:
    # all 1 (D37's equal generations). For insects whose sources say which generation does the damage
    generation_weights: tuple[float, ...] = ()
    place_form: PlaceForm | None = None  # other life stages where a normal of the place is below a bound
    biofix_fixed: bool = False  # the biofix is always the default: no grower's date (`Biofix.fixed`)

    @property
    def has_calendar(self) -> bool:
        """Whether its fitted stages carry calendar curves too (all of them do, or none)."""
        return any(isinstance(s, FittedStage) and s.days for s in self.life_stages)

    def __post_init__(self):
        stages = {s.label for s in self.life_stages}
        timed = {s.label for s in self.life_stages if isinstance(s, LifeStage)}
        fitted = [isinstance(s, FittedStage) for s in self.life_stages]
        if any(fitted) and not (all(fitted) and self.generation_dd is None and not self.action_windows):
            raise ValueError(f"{self.id}: fitted stages stand alone, without other stages, generations or windows")
        if self.life_stages and not any(fitted) and not isinstance(self.life_stages[0], LifeStage):
            raise ValueError(f"{self.id}: the first life stage needs its own start, peak and end")
        for s in self.life_stages:
            if isinstance(s, DerivedStage) and s.follows not in timed:
                raise ValueError(f"{self.id}: {s.label!r} follows {s.follows!r}, which isn't a timed life stage")
        for w in self.action_windows:
            if w.stage not in stages:
                raise ValueError(f"{self.id}: action window {w.label!r} follows an unknown stage {w.stage!r}")
        if self.max_generations is not None and self.max_generations < 1:
            raise ValueError(f"{self.id}: max_generations must be at least 1")
        if (self.estimated_biofix or self.generation_size) and not self.life_stages:
            raise ValueError(f"{self.id}: an estimated biofix or generation size needs life stages")
        if self.estimated_biofix and self.biofix != "01-01":
            raise ValueError(f"{self.id}: an estimated biofix replaces a January 1 biofix")
        if self.has_calendar and not all(isinstance(s, FittedStage) and s.days for s in self.life_stages):
            raise ValueError(f"{self.id}: every fitted stage needs a calendar curve, or none")
        if self.clock == "calendar" and not self.has_calendar:
            raise ValueError(f"{self.id}: a calendar clock needs calendar curves")
        derived = {s.label for s in self.life_stages if isinstance(s, DerivedStage)}
        for w in self.action_windows:
            if w.when == "present" and w.stage not in derived:
                raise ValueError(f"{self.id}: a 'present' window follows a stage timed from another, not {w.stage!r}")
        if (self.generation_weights or self.place_form) and (any(fitted) or not self.life_stages):
            raise ValueError(f"{self.id}: generation weights and place forms need timed life stages")
        if any(w < 0 for w in self.generation_weights):
            raise ValueError(f"{self.id}: generation weights can't be negative")
        if (f := self.place_form) is not None:
            if [s.label for s in f.life_stages] != [s.label for s in self.life_stages]:
                raise ValueError(f"{self.id}: a place form's stages carry the insect's labels, in order")
            if not isinstance(f.life_stages[0], LifeStage):
                raise ValueError(f"{self.id}: a place form's first stage needs its own start, peak and end")
            if [s.weight for s in f.life_stages] != [s.weight for s in self.life_stages]:
                # the risk without generation weights sums the insect's stages' weights over either form's activity
                raise ValueError(f"{self.id}: a place form's stages carry the insect's weights")


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
                Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
                Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
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
            biofix=Biofix(
                default=insect.biofix,
                label=insect.biofix_label or default_biofix_label(insect.biofix),
                fixed=insect.biofix_fixed,
            ),
            context=self._context(),
            changelog=(
                *(
                    (
                        Change(
                            version="0.1", date="2026-10-28", note=f"Ported from {insect.ported_from or insect.source}."
                        ),
                    )
                    if not any(c.version == "0.1" for c in insect.changelog)  # a new model gives its own 0.1
                    else ()
                ),
                *insect.changelog,
            ),
            checks=insect.checks,
            trained=insect.trained,
            options=(clock_option(insect.clock),) if insect.has_calendar else (),
            place_normals=(insect.place_form.normal,) if insect.place_form else (),
            ingredients=(
                Ingredient(
                    name="dd",
                    unit="degF_day",
                    degree_days=None
                    if insect.dd_method == "average_capped_mean"
                    else DegreeDays(method=insect.dd_method, base_f=insect.base_f, upper_f=insect.upper_f),
                ),
                Ingredient(name=self.FREEZE, unit="index", shared=self.FREEZE, running_minimum=self.HELD),
            ),
            accumulations=(
                Accumulation(name="dd_total", of="dd"),
                *(
                    (Accumulation(name=GENERATION_SIZE_DD, of="dd", until=insect.generation_size.on),)
                    if insect.generation_size
                    else ()
                ),
            ),
        )

    def _context(self) -> tuple[str, ...]:
        """The freeze reduction reads the day of year (without it there's none); an estimated biofix the latitude,
        a generation size the year (its date's day of year in leap years), and a place form its normal."""
        i = self.insect
        return (
            "day_of_year",
            *(("latitude",) if i.estimated_biofix else ()),
            *(("year",) if i.generation_size else ()),
            *((i.place_form.normal.key,) if i.place_form else ()),
        )

    # The shared freeze ingredient: the days in the last 14 at or below −2 °C after day 250 (the legacy reduction)
    FREEZE = "insect_freeze_reduction"
    HELD = False

    def _explored(self) -> tuple[Quantity, ...]:
        return (Quantity(name="severity", label="Severity", unit="index"),)

    def _outputs(self) -> tuple[Quantity, ...]:
        return (
            Quantity(name="stage", label="Life stage", unit="index"),
            Quantity(name="freeze_reduction", label="Severity removed by recent freezes", unit="index"),
        )

    def _risk(self) -> Risk:
        return Risk(levels=SEVERITY_LEVELS, criteria=criteria(self.insect))

    def ingredients(self, inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
        lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
        dd = insect_degree_days(insect=self.insect, min_f=lo, max_f=hi)
        return {"dd": dd, self.FREEZE: self._freeze(inputs, dd)}

    def _freeze(self, inputs: Mapping[str, np.ndarray], dd: np.ndarray) -> np.ndarray:
        if "day_of_year" not in inputs:
            return np.zeros_like(dd)
        return freeze_reduction(inputs["air_temperature_min"], inputs["day_of_year"])

    def finish(self, values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
        total = values["dd_total"]
        return {
            "dd_total": total,
            "dd": values["dd"],
            "stage": stage_index(total, self.insect.stages),
            "freeze_reduction": values[self.FREEZE],
        }

    def outputs(self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
        return finished(
            accumulations=self.SPEC.accumulations,
            values=self.ingredients(inputs),
            inputs=inputs,
            biofix_index=biofix_index,
            finish=self.finish,
            options=options,
        )

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
                    Quantity(name=f"count_{s.key}", label=s.count_label, unit="index")
                    if isinstance(s, FittedStage)
                    else Quantity(
                        name=f"generations_{s.key}", label=f"Generations of {s.label.lower()} complete", unit="index"
                    ),
                )
            ),
            *(Quantity(name=f"window_{w.key}", label=w.label, unit="index") for w in i.action_windows),
            *(
                (
                    Quantity(name=f"dd_after_{e.key}", label=f"Degree days since the {e.event}", unit="degF_day"),
                    Quantity(
                        name=f"{e.key}_dd_estimate",
                        label=f"Expected degree days from January 1 to the {e.event} here",
                        unit="degF_day",
                    ),
                    Quantity(
                        name=f"{e.key}_estimated", label=f"The {e.event} is estimated (1) or given (0)", unit="index"
                    ),
                )
                if (e := i.estimated_biofix)
                else ()
            ),
            *((Quantity(name=g.name, label=g.label, unit="index"),) if (g := i.generation_size) else ()),
            *(
                (
                    Quantity(name=f.name, label=f.label, unit="index"),
                    Quantity(name=f.normal.key, label=_capitalized(f.normal.label), unit=f.normal.unit),
                )
                if (f := i.place_form)
                else ()
            ),
            Quantity(name="freeze_factor", label="Share left after fall freezes", unit="index"),
            Quantity(name="season_complete", label="Season ended by freezes", unit="index"),
        )

    def _risk(self) -> Risk:
        return Risk(
            levels=SEVERITY_LEVELS, criteria=phenology_criteria(self.insect), thresholds=self.insect.risk_thresholds
        )

    # The shared freeze ingredient: 1 until fall freezes, then the share left, held at its lowest that year
    FREEZE = "insect_freeze_factor"
    HELD = True

    def _freeze(self, inputs: Mapping[str, np.ndarray], dd: np.ndarray) -> np.ndarray:
        if "day_of_year" not in inputs:
            return np.ones_like(dd)
        return freeze_factor(tmin_c=inputs["air_temperature_min"], day_of_year=inputs["day_of_year"])

    def finish(self, values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
        total, factor = values["dd_total"], values[self.FREEZE]
        alive = factor > 0
        out = {"dd_total": total, "dd": values["dd"]}
        timed, extra = self._timed(values, total)
        if options.get("clock", self.insect.clock) == "calendar":
            if "day_of_year" not in values:
                raise KeyError(f"{self.insect.id}'s calendar curves need the day of year")
            read = evaluate_calendar(insect=self.insect, day_of_year=values["day_of_year"], like=total)
        else:
            read = evaluate(insect=self.insect, dd_total=timed)
            if (f := self.insect.place_form) is not None:
                normal, here = self._place_form(values)
                read = _with_form(read, insect=form_insect(self.insect), dd_total=timed, here=here)
                extra[f.name] = np.where(np.isnan(total), np.nan, here.astype(float))
                extra[f.normal.key] = np.where(np.isnan(total), np.nan, normal)
        for name, value in read.items():
            if name.startswith(("activity_", "count_")):
                value = value * factor
            elif name.startswith("window_"):
                value = np.where(alive | np.isnan(value), value, 0.0)
            out[name] = value
        out |= extra
        out["freeze_factor"] = np.where(np.isnan(total), np.nan, factor)
        out["season_complete"] = np.where(np.isnan(total), np.nan, (~alive).astype(float))
        return out

    def _timed(self, values: Mapping[str, np.ndarray], total: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """The degree days the curves are read at, and the outputs of an estimated biofix and a generation size.
        With an estimated biofix and the default biofix (January 1, or no day of year given), the curves start where
        the total reaches the estimate at the place's latitude; with a grower's date, at that date."""
        i, extra = self.insect, {}
        timed, event_dd, estimated = total, None, None
        if (e := i.estimated_biofix) is not None:
            if "latitude" not in values:
                raise KeyError(f"{i.id} needs the place's latitude to estimate its {e.event}")
            event_dd = np.asarray(e.dd_at(np.asarray(values["latitude"], dtype=float)), dtype=float)
            biofix_doy = np.asarray(values.get("biofix_day_of_year", 1.0), dtype=float)
            estimated = np.isnan(biofix_doy) | (biofix_doy == 1)
            timed = np.where(estimated, total - event_dd, total)
            blank = np.isnan(total)
            extra[f"dd_after_{e.key}"] = np.where(blank, np.nan, np.maximum(timed, 0.0))
            extra[f"{e.key}_dd_estimate"] = np.where(blank, np.nan, event_dd)
            extra[f"{e.key}_estimated"] = np.where(blank, np.nan, estimated.astype(float))
        if (g := i.generation_size) is not None:
            dd_from_january = np.asarray(values[GENERATION_SIZE_DD], dtype=float)
            if event_dd is not None and estimated is not None:  # from a grower's date: add the days before it
                dd_from_january = np.where(estimated, dd_from_january, dd_from_january + event_dd)
            size = 1.0 + np.sum([dd_from_january >= b for b in g.bounds], axis=0)
            reached = _on_or_after(g.on, values["day_of_year"], values["year"])
            if reached.ndim == 1 and total.ndim > 1:  # a series of days against a grid's days × cells
                reached = reached.reshape(-1, *([1] * (total.ndim - 1)))
            extra[g.name] = np.where(np.isnan(total) | ~reached, np.nan, size)
        return timed, extra

    def _place_form(self, values: Mapping[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        """The place's normal (NaN where it isn't known) and whether the place form applies (never where unknown)."""
        f = self.insect.place_form
        assert f is not None
        if f.normal.key not in values:  # every caller passes it, NaN where it isn't known: never silently two flights
            raise KeyError(f"{self.insect.id} needs the place's {f.normal.key} (NaN where it isn't known)")
        normal = np.asarray(values[f.normal.key], dtype=float)
        with np.errstate(invalid="ignore"):
            return normal, np.isfinite(normal) & (normal < f.below)

    def risk(self, outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
        """The sum of each stage's weight times its activity: 1 at a weight-1 stage's first-generation peak. With
        generation weights, each generation's activity times its weight, read off the risk's own curve at the
        degree days the stages are timed by, and scaled by the freeze factor as activity is."""
        i = self.insect
        if not i.generation_weights:
            return np.sum(
                [s.weight * np.asarray(outputs[f"activity_{s.key}"], dtype=float) for s in i.life_stages], axis=0
            )
        e = i.estimated_biofix
        timed = np.asarray(outputs[f"dd_after_{e.key}" if e else "dd_total"], dtype=float)
        here = np.asarray(outputs[i.place_form.name], dtype=float) == 1 if i.place_form else None
        factor = np.asarray(outputs.get("freeze_factor", 1.0), dtype=float)
        return np.where(np.isnan(timed), np.nan, weighted_risk(insect=i, dd=timed, here=here) * factor)

    def explore(self, dd_total: float) -> dict[str, float]:
        total = np.array([dd_total])
        values = evaluate(insect=self.insect, dd_total=total)
        values["risk"] = (
            weighted_risk(insect=self.insect, dd=total, here=None)
            if self.insect.generation_weights
            else self.risk(values)
        )
        return {k: float(v[0]) for k, v in values.items()}


GENERATION_SIZE_DD = "dd_to_generation_size_date"  # the accumulation a generation size reads


def _on_or_after(month_day: str, day_of_year: np.ndarray, year: np.ndarray) -> np.ndarray:
    """Whether each day is on or after MM-DD in its year."""
    month, day = (int(p) for p in month_day.split("-"))
    doy, years = np.asarray(day_of_year, dtype=float), np.asarray(year, dtype=float)
    leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
    first = date(2001, month, day).timetuple().tm_yday + (leap & (month > 2))
    return doy >= first


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
    """Daily degree days by the insect's method: single sine, the simple average with both temperatures capped at the
    upper threshold, or the modified average (the minimum also raised to the base)."""
    if insect.dd_method == "average":
        return degree_days_average(min_f, max_f, base=insect.base_f, upper=insect.upper_f)
    if insect.dd_method == "average_capped_mean":
        if insect.upper_f is None:
            raise ValueError(f"{insect.id}: a capped mean needs an upper threshold")
        return degree_days_average_capped_mean(min_f, max_f, base=insect.base_f, upper=insect.upper_f)
    if insect.dd_method == "modified":
        return degree_days_modified(min_f, max_f, base=insect.base_f, upper=insect.upper_f)
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
    last = insect.max_generations or math.inf
    while n <= last and stage.start + (n - 1) * mean - 4 * math.sqrt(n - 1) * sd < DD_MAX:  # until a tail is past
        # n − 1 gamma generation times sum to a gamma with n − 1 times the shape
        delay = gamma_pdf(x, shape=(n - 1) * mean**2 / sd**2, scale=sd**2 / mean)
        density = np.fft.irfft(first_f * np.fft.rfft(delay, size), size)[: len(x)] * DD_STEP
        densities.append(np.where(density > 1e-12 * density.max(), density, 0.0))  # drop the transform's rounding
        n += 1
    return densities


@dataclass(frozen=True, kw_only=True)
class _Generations:
    """A timed stage's tables on `dd_grid()`, one per generation: the share present, entered and left (complete)."""

    present: list[np.ndarray]
    entered: list[np.ndarray]
    complete: list[np.ndarray]


@cache
def _generations(insect: Insect) -> dict[str, _Generations]:
    """Each timed stage's generations (`_Generations`), by label."""
    found: dict[str, _Generations] = {}
    for stage in insect.life_stages:
        if isinstance(stage, LifeStage):
            present = generation_densities(insect=insect, stage=stage)
            complete = [np.minimum(np.cumsum(d) * DD_STEP, 1.0) for d in present]
            found[stage.label] = _Generations(present=present, entered=complete, complete=complete)
        elif isinstance(stage, DerivedStage):  # entered `lag` after the followed stage, left `duration` later
            followed = found[stage.follows].complete
            entered = [_shift(f, by=stage.lag) for f in followed]
            complete = [_shift(f, by=stage.lag + stage.duration) for f in followed]
            present = [a - b for a, b in zip(entered, complete, strict=True)]
            found[stage.label] = _Generations(present=present, entered=entered, complete=complete)
    return found


@cache
def curves(insect: Insect) -> dict[str, np.ndarray]:
    """Each output that depends only on degree days, tabulated on `dd_grid()`: per stage its activity (1 at the
    first generation's peak) and generations complete (the sum of each generation's fraction complete), and per
    action window whether it's open (0 or 1)."""
    tables: dict[str, np.ndarray] = {}
    timed = _generations(insect)
    for stage in insect.life_stages:
        if isinstance(stage, FittedStage):
            x = dd_grid()
            fit = np.interp(x, stage.dd, stage.log_count)
            count = np.expm1(np.maximum(fit, 0.0)) if stage.transform == "log1p" else np.exp(fit)
            count = np.where(x < stage.dd[0], 0.0, count)  # before the data begin
            tables[f"activity_{stage.key}"] = count / count.max()
            tables[f"count_{stage.key}"] = count
            continue
        g = timed[stage.label]
        tables[f"activity_{stage.key}"] = np.sum(g.present, axis=0) / g.present[0].max()
        tables[f"generations_{stage.key}"] = np.sum(g.complete, axis=0)
    for w in insect.action_windows:
        low, high = w.between
        g = timed[w.stage]
        open_ = np.zeros_like(dd_grid(), dtype=bool)
        for entered, left in zip(g.entered, g.complete, strict=True):
            if w.when == "present":  # from the first individuals in until most have left
                open_ |= (entered >= low) & (left <= high)
            else:
                open_ |= (left >= low) & (left <= high)
        tables[f"window_{w.key}"] = open_.astype(float)
    return tables


def generation_weight(insect: Insect, n: int) -> float:
    """Generation n's weight in the risk (from 1): its own, or the last one given; 1 without weights."""
    weights = insect.generation_weights
    return 1.0 if not weights else weights[min(n, len(weights)) - 1]


@cache
def risk_curve(insect: Insect) -> np.ndarray:
    """The risk on `dd_grid()` before fall freezes: the sum over stages and generations of the stage's weight times
    the generation's weight times its activity (1 at a weight-1 stage's first-generation peak)."""
    total = np.zeros_like(dd_grid())
    for stage in insect.life_stages:
        if stage.weight and not isinstance(stage, FittedStage):
            g = _generations(insect)[stage.label]
            peak = g.present[0].max()
            for n, present in enumerate(g.present, start=1):
                total = total + stage.weight * generation_weight(insect, n) * present / peak
    return total


def weighted_risk(insect: Insect, dd: np.ndarray, here: np.ndarray | None) -> np.ndarray:
    """`risk_curve` at each total (degree days from the stages' start), the place form's where `here` is true."""
    x = dd_grid()
    dd = np.asarray(dd, dtype=float)
    value = np.interp(dd, x, risk_curve(insect))
    if insect.place_form is not None and here is not None and np.any(here):
        where = np.broadcast_to(here, dd.shape)
        value[where] = np.interp(dd[where], x, risk_curve(form_insect(insect)))
    return value


def _with_form(
    read: dict[str, np.ndarray], *, insect: Insect, dd_total: np.ndarray, here: np.ndarray
) -> dict[str, np.ndarray]:
    """`read` (`evaluate`'s curves) with the place form's (`insect`, `form_insect`'s) where `here` is true, evaluated
    only at those cells' totals: a map where no cell takes the form costs nothing more (`here` broadcasts against the
    totals, a map's as 1 × y × x). `read`'s arrays are written in place."""
    if not here.any():
        return read
    total = np.asarray(dd_total, dtype=float)
    where = np.broadcast_to(here, total.shape)
    other = evaluate(insect=insect, dd_total=total[where])
    for name, value in read.items():  # `evaluate`'s own arrays, written in place
        value[where] = other[name]
    return read


@cache
def form_insect(insect: Insect) -> Insect:
    """The insect with its place form's life stages and generations, for the places the form applies."""
    f = insect.place_form
    assert f is not None
    return replace(
        insect,
        life_stages=f.life_stages,
        generation_dd=f.generation_dd,
        generation_sd=f.generation_sd,
        max_generations=f.max_generations,
        place_form=None,
    )


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


def clock_option(default: str) -> Option:
    """The `clock` option of an insect whose fitted stages carry calendar curves (D101)."""
    return Option(
        name="clock",
        label="Read the curves by",
        choices=(("degree_days", "Degree days (this year's weather)"), ("calendar", "Calendar date (a typical year)")),
        default=default,
    )


@cache
def calendar_curves(insect: Insect) -> dict[str, np.ndarray]:
    """The fitted stages' calendar curves tabulated on days of year 1–366: each stage's activity (1 at its own
    calendar peak) and typical count, 0 before the data's first day and held after its last."""
    x = np.arange(1.0, 367.0)
    tables: dict[str, np.ndarray] = {}
    for stage in insect.life_stages:
        assert isinstance(stage, FittedStage) and stage.days
        fit = np.interp(x, stage.days, stage.log_count_by_day)
        count = np.expm1(np.maximum(fit, 0.0)) if stage.transform == "log1p" else np.exp(fit)
        count = np.where(x < stage.days[0], 0.0, count)
        tables[f"activity_{stage.key}"] = count / count.max()
        tables[f"count_{stage.key}"] = count
    return tables


def evaluate_calendar(insect: Insect, day_of_year: np.ndarray, like: np.ndarray) -> dict[str, np.ndarray]:
    """The calendar curves on each day, shaped like `like` (a point's days, or a grid's days × cells, whose days of
    year come as days × 1 × 1) and missing where it is: a day without weather stays missing, as on degree days."""
    like = np.asarray(like, dtype=float)
    doy = np.asarray(day_of_year, dtype=float)
    if doy.ndim == 1 and like.ndim > 1:  # a series of days against a grid's days × cells
        doy = doy.reshape(-1, *([1] * (like.ndim - 1)))
    out = {}
    for name, table in calendar_curves(insect).items():
        value = np.broadcast_to(np.interp(doy, np.arange(1.0, 367.0), table), like.shape)
        out[name] = np.where(np.isnan(like), np.nan, value)
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
    if insect.life_stages and isinstance(insect.life_stages[0], FittedStage):
        return _fitted_criteria(insect)
    upper = "no upper threshold" if insect.upper_f is None else f"upper {insect.upper_f:g} °F"
    method = {
        "sine": "Single-sine",
        "average": "Average",
        "modified": "Modified-average",
        "average_capped_mean": "Average (the day's mean capped at the upper threshold)",
    }[insect.dd_method]
    stages = "; ".join(_stage_words(s) for s in insect.life_stages)
    repeat = (
        f" Later generations follow every {insect.generation_dd:,g} degree days, spreading as each generation's timing varies."
        if insect.generation_dd
        else ""
    )
    if insect.max_generations:
        repeat += f" At most {insect.max_generations} generations."
    if (f := insect.place_form) is not None:
        form_stages = "; ".join(_stage_words(s) for s in f.life_stages)
        if f.generation_dd:
            form_repeat = f", later generations every {f.generation_dd:,g} degree days"
            form_repeat += f" (at most {f.max_generations})" if f.max_generations else ""
        else:
            form_repeat = ", one generation"
        repeat += f" Where {f.normal.label} is below {f.below:,g}, {f.words} instead: {form_stages}{form_repeat}. Where that normal isn't known, the stages above."
    weighting = "Risk is the sum of each stage's weight times its activity (1 at the first generation's peak)"
    if insect.generation_weights:
        weights = ", ".join(f"{_ordinal(n)} {w:g}" for n, w in enumerate(insect.generation_weights, start=1))
        weighting += (
            f", each generation's activity also times its weight ({weights}; any later generation, the last weight)"
        )
    levels = ", ".join(
        f"{word} from {t:g}" for word, t in zip(SEVERITY_LEVELS[1:], insect.risk_thresholds, strict=True)
    )
    since = "the biofix"
    if (e := insect.estimated_biofix) is not None:
        since = f"the {e.event} (a grower's date, or where none is given the day the total from January 1 reaches the {e.event} expected at the place's latitude)"
    return f"{method} degree days (base {insect.base_f:g} °F, {upper}) since {since} time each life stage's first generation ({stages}).{repeat} {weighting}: {levels}. After day 250, fall freezes end the season."


def _fitted_criteria(insect: Insect) -> str:
    upper = "no upper threshold" if insect.upper_f is None else f"upper {insect.upper_f:g} °F"
    stages = [s for s in insect.life_stages if isinstance(s, FittedStage)]
    peaks = "; ".join(f"{_lower(s.label)} peaking at {s.dd[int(np.argmax(s.log_count))]:,g}" for s in stages)
    weighted = " plus ".join(f"{s.weight:g} × {_lower(s.label)}" for s in stages if s.weight) or "none"
    levels = ", ".join(
        f"{word} from {t:g}" for word, t in zip(SEVERITY_LEVELS[1:], insect.risk_thresholds, strict=True)
    )
    since = "January 1" if insect.biofix == "01-01" else "the biofix"
    return f"Single-sine degree days (base {insect.base_f:g} °F, {upper}) since {since} read each stage's value off a curve fitted to field counts ({peaks}). Activity is a stage's value over its curve's peak; risk is {weighted}: {levels}. After day 250, fall freezes end the season."


def _ordinal(n: int) -> str:
    return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}.get(n, f"{n}th")


def _capitalized(text: str) -> str:
    return text[:1].upper() + text[1:]


def _lower(label: str) -> str:
    """A label mid-sentence: its first letter lowercase unless it starts an acronym ("PVY vector pressure")."""
    return label if label[:2].isupper() else label[:1].lower() + label[1:]


def _stage_words(stage: LifeStage | DerivedStage | FittedStage) -> str:
    if isinstance(stage, LifeStage):
        when = f"start, peak and end {stage.start:,g}, {stage.peak:,g} and {stage.end:,g}"
    elif isinstance(stage, FittedStage):
        when = f"fitted, peaking at {stage.dd[int(np.argmax(stage.log_count))]:,g}"
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
        rule = f"{dd} set the severity, rising along a half sine from each generation's start to 4 at its peak and falling to its end (start, peak and end: {spans})."
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
    level = np.zeros(total.shape, dtype=np.int8)
    for start, peak, end in insect.generations:
        within = (total >= start) & (total <= end)
        level = np.where(within, _sine_ramp(total, start, peak, end), level)
    return np.where(np.isnan(total), np.nan, level.astype(float))


def freeze_reduction(tmin_c: np.ndarray, day_of_year: np.ndarray) -> np.ndarray:
    """After day 250, the days in the last 14 with a minimum at or below −2 °C; 0 before."""
    tmin = np.asarray(tmin_c, dtype=float)
    freezing = rolling_sum((tmin <= FREEZE_C).astype(float), 14)
    doy = np.asarray(day_of_year).reshape(-1, *([1] * (tmin.ndim - 1)))
    return np.where(doy > SEASON_END_DAY, freezing, 0.0)


# Where VDIFN's ramp steps up a level, as a share of the way from start to peak: its height (1 − cos πx) / 2, times 4
# and rounded up, passes 0, 1/4, 2/4 and 3/4 at x = arccos(1 − k/2) / π
RAMP_STEPS = (0.0, 1 / 3, 1 / 2, 2 / 3)


def _sine_ramp(total: np.ndarray, start: float, peak: float, end: float) -> np.ndarray:
    """VDIFN's `sev_ramp`: 0–4 along a half sine up from start to peak and down from peak to end, rounded up, and 0
    outside start..end. The rounded sine is a step function of the total, so it's counted from the four totals where
    it steps on each side (`_sine_ramp_reference` computes the sine, ~6× slower over a season's map)."""
    total = np.asarray(total, dtype=float)
    rising = total <= peak
    level = np.zeros(total.shape, dtype=np.int8)
    for k in RAMP_STEPS:
        up, down = start + k * (peak - start), end - k * (end - peak)
        with np.errstate(invalid="ignore"):
            level += np.where(rising, total > up, total < down)
    return level


def _sine_ramp_reference(total: np.ndarray, start: float, peak: float, end: float) -> np.ndarray:
    """VDIFN's `sev_ramp` term for term, the reference `_sine_ramp` is tested against."""

    def half(value, a, b):
        x = (value - a) / (b - a)
        return np.ceil((np.sin(x * math.pi - math.pi / 2) + 1) / 2 * 4)

    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total <= peak, half(total, start, peak), half(-total, -end, -peak))


def default_biofix_label(biofix: str) -> str:
    """'05-15' → 'May 15, or your own date' (the insect's default start, which a grower can replace)."""
    month, day = (int(part) for part in biofix.split("-"))
    return f"{date(2001, month, day):%B} {day}, or your own date"
