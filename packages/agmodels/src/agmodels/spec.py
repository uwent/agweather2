"""Model specs: what a model predicts, from which weather, and how its output becomes a risk score (PLAN.md D30).

Every model is one module under `agmodels.models` with a `SPEC` and three functions, matching the three layers
the API and charts show (the Crop Risk Tool's view):

- `outputs(inputs, biofix_index, **options) -> dict`: the model's outputs (an index, a probability, degree days, a
  life stage) from its inputs, daily arrays with time on axis 0 (a point's series or the grid); most models ignore
  the biofix here, but one anchored to a growth stage (red crown rot's R1) can't;
- `risk(outputs, biofix_index, **options) -> array`: the risk level (0 … len(levels) − 1, NaN where unknown), or a
  continuous value whose levels start at `Risk.thresholds`, over the same days, from outputs accumulated from the
  biofix; never stored, so changing the criteria changes nothing on disk;
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

from agmodels.ingredients import Accumulation, Ingredient
from agmodels.names import DailyName, UnitSymbol

Status = Literal["beta", "stable", "retired"]
Group = Literal["disease", "insect", "crop", "agronomic", "degree_days"]  # agronomic: field management (volunteers)

SEVERITY_LEVELS = ("Very low", "Low", "Moderate", "High", "Very high")
PROBABILITY_LEVELS = ("Very low", "Low", "Moderate", "High")


@dataclass(frozen=True, kw_only=True)
class Citation:
    """A source: the reference as text, its DOI where it has one (bare, `10.…`), and a URL for a copy to read or a
    source with no DOI (an extension page, a report)."""

    text: str
    url: str = ""
    doi: str = ""

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""


@dataclass(frozen=True, kw_only=True)
class Quantity:
    """An output series (or an explored value): its name in the frame, a label for charts and its unit
    (`agdata.units`)."""

    name: str
    label: str
    unit: UnitSymbol
    description: str = ""


@dataclass(frozen=True, kw_only=True)
class Input:
    """A model's input: a daily variable or feature from the catalog (`agmodels.names`, generated from
    `agdata.catalog`), so a name the grid doesn't store is a type error where it's written."""

    name: DailyName
    label: str
    unit: UnitSymbol
    description: str = ""


@dataclass(frozen=True, kw_only=True)
class Risk:
    levels: tuple[str, ...]
    criteria: str  # how outputs become each level, in words, for the model page and chart legends
    # Lower bounds of levels[1:] when `risk()` returns a continuous value (insects' summed activity, D36); empty when
    # it returns the level itself
    thresholds: tuple[float, ...] = ()


@dataclass(frozen=True, kw_only=True)
class ExplorerInput:
    name: str
    label: str
    unit: UnitSymbol
    minimum: float
    maximum: float
    step: float
    default: float


@dataclass(frozen=True, kw_only=True)
class Option:
    """A choice that changes the model (a resistance class, irrigation, a growth-stage date)."""

    name: str
    label: str
    choices: tuple[tuple[str, str], ...]  # (value, label); empty for a date or number given by the user
    default: str


@dataclass(frozen=True, kw_only=True)
class Seasonal:
    """A product that settles once a season (PLAN.md Phase 4 H, D68): counted over the spec's `season` from its
    biofix, it is one map a season. `agmodels.seasons` names seasons and says which one is current."""

    appears: str  # MM-DD the season's product is first shown (it has data to chew on by then); the last one before


@dataclass(frozen=True, kw_only=True)
class Biofix:
    default: str  # MM-DD
    label: str  # what the date means to a grower, e.g. "Crop emergence or last fungicide application"


@dataclass(frozen=True, kw_only=True)
class StageDate:
    """A susceptible window from a date the user gives (the day their crop reached a stage), which replaces the crop
    model's estimate, or stands in for it where there's none (winter wheat). The date is one of the model's
    options (no choices; YYYY-MM-DD, empty for none), refused on maps (D66)."""

    option: str  # the option's name
    first: int  # the window's first and last days, counted from the date (inclusive)
    last: int
    margin_days: int  # days muted either side, as a crop model's MARGIN_DAYS
    source: str  # where the window comes from


@dataclass(frozen=True, kw_only=True)
class Susceptibility:
    """The crop stages a disease affects (D33): its risk shows only from `first` through `last` (inclusive: until
    the stage after `last`), muted for the crop model's margin either side, grey elsewhere. A `stage_date` given
    replaces the stages with days around that date."""

    crop: str  # the crop model's id
    first: str  # stage codes in that model's list
    last: str
    source: str  # where the window comes from
    note: str = ""
    # True when the crop model covers only some of the model's crops (wheat scab: spring wheat's stages, not winter
    # wheat's): the gate then runs only from a planting date the user gives, never from a typical one, and maps
    # aren't gated (they show the risk for the crop at the window's stage on each day)
    planting_given_only: bool = False
    # The window runs on through this many days after the crop reaches `last` (wheat scab: 7 days from the start of
    # flowering, the fungicide window), so it ends a set time after a stage begins rather than at the next stage
    extend_days: int = 0
    stage_date: StageDate | None = None  # a date the user gives instead of the crop model's estimate


@dataclass(frozen=True, kw_only=True)
class Change:
    version: str
    date: str
    note: str


@dataclass(frozen=True, kw_only=True)
class Check:
    """One check of a model against results it wasn't built from (D98), summarized for the public: its source's own
    numbers, another system on the same weather, or observations in the field. The evidence is a section of the
    model's validation report (`docs/validation/models/<id>.md`); every number in `result` must appear in that
    section, so a copying slip or a rerun that changed the numbers fails a test (`test_checks`)."""

    kind: Literal["published", "system", "observations"]
    against: str  # what it was compared with, e.g. "Wisconsin's apple pest trap network (DATCP), 2020–2025"
    result: str  # one or two plain sentences, with the numbers
    report: str  # the report's path and section anchor, "docs/validation/models/codling-moth.md#first-catch"


@dataclass(frozen=True, kw_only=True)
class TrainingArea:
    """Where and when the data a model was fitted to came from (D101), so a place outside it can be told that the
    model is reaching beyond its data: the model still runs everywhere in its `region`, with a warning. Kept coarse
    (counties or states, never fields or farms), since the data are often growers'."""

    description: str  # public text, completing "fitted to …": "scouting counts in commercial potato fields in Wisconsin's Central Sands"
    years: tuple[int, int]  # first and last year of the data
    states: tuple[str, ...] = ()  # postal abbreviations; the whole state counts as inside
    counties: tuple[str, ...] = ()  # five-digit FIPS codes; inside these counties as well as anywhere in `states`

    def __post_init__(self):
        if not self.states and not self.counties:
            raise ValueError("a training area needs states or counties")
        if any(len(c) != 5 or not c.isdigit() for c in self.counties):
            raise ValueError("counties are five-digit FIPS codes")

    def contains(self, *, state: str | None, fips: str | None) -> bool:
        """Whether a place in this state and county (either may be unknown) is inside."""
        return (state is not None and state in self.states) or (fips is not None and fips in self.counties)


@dataclass(frozen=True, kw_only=True)
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
    inputs: tuple[Input, ...]
    outputs: tuple[Quantity, ...]  # the first is the primary output (risk coloring, maps)
    risk: Risk | None  # None for crop growth-stage models
    explorer: tuple[ExplorerInput, ...]
    # what `explore()` returns beyond `outputs` (a rate, each method's degree days, the risk), with units
    explorer_outputs: tuple[Quantity, ...] = ()
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
    trained: TrainingArea | None = None  # where its data came from (D101); None: not a fit to data, or not recorded
    season: tuple[str, str] | None = None  # MM-DD first and last day it's shown
    seasonal: Seasonal | None = None  # a once-a-season product (`agmodels.seasons`); None: a daily model
    biofix: Biofix | None = None
    changelog: tuple[Change, ...] = ()
    checks: tuple[Check, ...] = ()  # how the model was checked (D98); empty only for models listed in `test_checks`
    # What the outputs are finished from (`agmodels.ingredients`, D66): the module then defines `ingredients()` and
    # `finish()`, and a map combines them per cell. Empty: no ingredients (a state machine such as soybean stages)
    ingredients: tuple[Ingredient, ...] = ()
    accumulations: tuple[Accumulation, ...] = ()


class Model(Protocol):
    SPEC: ModelSpec

    def outputs(
        self, inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str
    ) -> dict[str, np.ndarray]: ...

    def risk(self, outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray: ...

    def explore(self, **values: float) -> dict[str, float]: ...
