"""Model specs: what a model predicts, from which weather, and how its output becomes a risk score (PLAN.md D30).

Every model is one module under `agmodels.models` with a `SPEC` and three functions, matching the three layers
the API and charts show (the Crop Risk Tool's view):

- `outputs(inputs, biofix_index, **options) -> dict`: the model's outputs (an index, a probability, degree days, a
  life stage) from its inputs, daily arrays with time on axis 0 (a point's series or the grid); most models ignore
  the biofix here, but one anchored to a growth stage (red crown rot's R1) can't;
- `risk(outputs, biofix_index, **options) -> array`: the risk level (0 … len(levels) − 1, NaN where unknown) over
  the same days, from outputs accumulated from the biofix; never stored, so changing the criteria changes nothing
  on disk;
- `explore(**values) -> dict`: the model's core at single values of its explorer inputs, for the model page's
  interactive chart (through the API, so the page never re-implements the math).

Crop growth-stage models (group `crop`, `agmodels.crops`, D32) have no risk layer: their `SPEC.risk` is None and they
define no `risk`. They're shown on their own page and under the crop's disease models, which use the stages they
reach to grey out risk where the crop isn't susceptible (D33).

Inputs name daily features (`agmodels.features`) or daily statistics from the catalog. Missing stays missing:
a day without its inputs has NaN outputs, not 0 (CLAUDE.md).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np

Status = Literal["beta", "stable", "retired"]
Group = Literal["disease", "insect", "crop", "degree_days"]

SEVERITY_LEVELS = ("Very low", "Low", "Moderate", "High", "Very high")
PROBABILITY_LEVELS = ("Very low", "Low", "Moderate", "High")


@dataclass(frozen=True)
class Citation:
    """A source: the reference as text, its DOI where it has one (bare, `10.…`), and a URL for a copy to read or a
    source with no DOI (an extension page, a report)."""

    text: str
    url: str = ""
    doi: str = ""

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""


@dataclass(frozen=True)
class Quantity:
    """An input or output series: its name in the frame, a label for charts and its unit (`agdata.units`)."""

    name: str
    label: str
    unit: str
    description: str = ""


@dataclass(frozen=True)
class Risk:
    levels: tuple[str, ...]
    criteria: str  # how outputs become each level, in words, for the model page and chart legends


@dataclass(frozen=True)
class ExplorerInput:
    name: str
    label: str
    unit: str
    minimum: float
    maximum: float
    step: float
    default: float


@dataclass(frozen=True)
class Option:
    """A choice that changes the model (a resistance class, irrigation, a growth-stage date)."""

    name: str
    label: str
    choices: tuple[tuple[str, str], ...]  # (value, label); empty for a date or number given by the user
    default: str


@dataclass(frozen=True)
class Biofix:
    default: str  # MM-DD
    label: str  # what the date means to a grower, e.g. "Crop emergence or last fungicide application"


@dataclass(frozen=True)
class Susceptibility:
    """The crop stages a disease affects (D33): its risk shows only from `first` through `last` (inclusive: until
    the stage after `last`), muted for the crop model's margin either side, grey elsewhere."""

    crop: str  # the crop model's id
    first: str  # stage codes in that model's list
    last: str
    source: str  # where the window comes from
    note: str = ""


@dataclass(frozen=True)
class Change:
    version: str
    date: str
    note: str


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    group: Group
    version: str
    status: Status
    summary: str
    topics: tuple[str, ...]  # ids of the disease or insect pages it predicts
    crops: tuple[str, ...]
    citations: tuple[Citation, ...]
    inputs: tuple[Quantity, ...]
    outputs: tuple[Quantity, ...]  # the first is the primary output (risk coloring, maps)
    risk: Risk | None  # None for crop growth-stage models
    explorer: tuple[ExplorerInput, ...]
    sweep: Mapping[str, tuple[float, ...]] = field(default_factory=dict)  # explorer values to run, for snapshots
    options: tuple[Option, ...] = ()
    lookback_days: int = 0  # days of inputs needed before the first output (moving averages)
    # values the runner supplies from the place and the dates rather than the weather: "day_of_year", "latitude"
    context: tuple[str, ...] = ()
    susceptible: Susceptibility | None = None  # crop stages the disease affects; None: shown all season
    biofix_stage: tuple[str, str] | None = (
        None  # (crop model id, stage code) whose predicted date is the default biofix
    )
    region: tuple[str, ...] = ()  # state abbreviations where it's valid; empty: anywhere
    season: tuple[str, str] | None = None  # MM-DD first and last day it's shown
    biofix: Biofix | None = None
    changelog: tuple[Change, ...] = ()


class Model(Protocol):
    SPEC: ModelSpec

    def outputs(
        self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str
    ) -> dict[str, np.ndarray]: ...

    def risk(self, outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray: ...

    def explore(self, **values: float) -> dict[str, float]: ...
