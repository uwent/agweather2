"""Model specs: what a model predicts, from which weather, and how its output becomes a risk score (PLAN.md D30).

Every model is one module under `agmodels.models` with a `SPEC` and three functions, matching the three layers
the API and charts show (the Crop Risk Tool's view):

- `outputs(inputs) -> dict`: the model's outputs (an index, a probability, degree days, a life stage) from its
  inputs, daily arrays with time on axis 0 (a point's series or the grid);
- `risk(outputs, biofix_index) -> array`: the risk level (0 … len(levels) − 1, NaN where unknown) over the same
  days, from outputs accumulated from the biofix; never stored, so changing the criteria changes nothing on disk;
- `explore(**values) -> dict`: the model's core at single values of its explorer inputs, for the model page's
  interactive chart (through the API, so the page never re-implements the math).

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
    text: str
    url: str = ""


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
class Biofix:
    default: str  # MM-DD
    label: str  # what the date means to a grower, e.g. "Crop emergence or last fungicide application"


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
    risk: Risk
    explorer: tuple[ExplorerInput, ...]
    sweep: Mapping[str, tuple[float, ...]] = field(default_factory=dict)  # explorer values to run, for snapshots
    region: tuple[str, ...] = ()  # state abbreviations where it's valid; empty: anywhere
    season: tuple[str, str] | None = None  # MM-DD first and last day it's shown
    biofix: Biofix | None = None
    changelog: tuple[Change, ...] = ()


class Model(Protocol):
    SPEC: ModelSpec

    def outputs(self, inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]: ...

    def risk(self, outputs: Mapping[str, np.ndarray], biofix_index: int = 0) -> np.ndarray: ...

    def explore(self, **values: float) -> dict[str, float]: ...
