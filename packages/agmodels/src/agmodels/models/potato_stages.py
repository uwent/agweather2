"""Potato emergence from planting, by degree days in air above 4 °C (fitted to UW Vegetable Pathology's estimates).

Daily degree days are the mean of the maximum and minimum less 4 °C (none below it), counted from planting; 50%
emergence comes at 208 °C·d. The threshold was fitted to the planting and 50% emergence dates that UW Vegetable
Pathology's Vegetable Crop Updates give each season for early, mid and late plantings at Wisconsin's potato areas
(120 dates at 7 locations, 2020–2026, compiled by Ben Bradford; `tmp/potato/` in the repository holds the fit), on
Open-Meteo's daily temperature at each location: held out by year, 3.3 days' mean error (RMSE 4.0), against 7.5 days
for a fixed 24 days from planting. Bases from 2 to 7 °C fit about as well, and soil temperature no better than air;
at a 45 °F base the same dates take about 250 °F·d, inside the 200–300 °F·d that Columbia Basin extension work gives
for emergence. The newsletters' dates are estimates (planting from growers' reports), not field records.

Only planting and emergence are modelled: emergence is the biofix of the early and late blight models
(`biofix_stage`), so a planting date times their start. Tuber initiation and later stages need another source.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.crops import CropStage, stage_reached
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Quantity

BASE_C = 4.0
EMERGENCE_DD = 208.0
MARGIN_DAYS = 4  # the fit's held-out RMSE, rounded up

STAGES = (
    CropStage(code="PL", name="Planted", description="Seed pieces in the ground; sprouts growing toward the surface."),
    CropStage(code="EM", name="Emerged", description="Half the plants have emerged."),
)
THRESHOLDS = np.array([0.0, EMERGENCE_DD])

SPEC = ModelSpec(
    id="potato-stages",
    name="Potato emergence",
    group="crop",
    version="0.1",
    status="beta",
    summary="The date half of a potato planting has emerged, by degree days in air above 4 °C from planting: the "
    "start of the early and late blight models.",
    topics=("potato",),
    crops=("Potato",),
    citations=(
        Citation(
            text="UW Vegetable Pathology, Vegetable Crop Updates (2020–2026): early, mid and late planting and 50% "
            "emergence dates by location, in each season's early and late blight table.",
            url="https://vegpath.plantpath.wisc.edu/2026/08/23/vegetable-crop-update-aug-23-2026/",
        ),
    ),
    inputs=(
        Quantity(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Quantity(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="stage", label="Growth stage", unit="index", description="Index in the crop's stage list"),
        Quantity(name="dd_total", label="Degree days (base 4 °C) since planting", unit="degC_day"),
        Quantity(name="dd", label="Degree days (base 4 °C)", unit="degC_day"),
    ),
    risk=None,
    explorer=(
        ExplorerInput(
            name="dd_total",
            label="Degree days since planting",
            unit="degC_day",
            minimum=0,
            maximum=400,
            step=5,
            default=150,
        ),
    ),
    sweep={"dd_total": tuple(float(d) for d in range(0, 401, 5))},
    season=("03-15", "07-31"),
    biofix=Biofix(default="05-01", label="Planting date"),
    changelog=(Change(version="0.1", date="2026-11-03", note="First version, fitted to Veg Path's 2020–2026 dates."),),
)


def stages(**options: str) -> tuple[CropStage, ...]:
    return STAGES


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) for k in ("air_temperature_min", "air_temperature_max"))
    dd = np.maximum((lo + hi) / 2 - BASE_C, 0.0)  # NaN where either is missing
    dd[:biofix_index] = np.nan
    total = np.full(dd.shape, np.nan)
    total[biofix_index:] = np.cumsum(np.nan_to_num(dd[biofix_index:]), axis=0)  # a missing day adds nothing
    return {"stage": stage_reached(total, THRESHOLDS), "dd_total": total, "dd": dd}


def explore(dd_total: float) -> dict[str, float]:
    return {"stage": float(stage_reached(dd_total, THRESHOLDS))}
