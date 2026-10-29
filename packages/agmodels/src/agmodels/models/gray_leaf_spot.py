"""Gray leaf spot of corn: the probability of Cercospora zeae-maydis spores being present.

A logistic model of the 21-day mean minimum temperature and 30-day mean minimum dew point (Smith lab, UW–Madison,
and Webster, NDSU, as in the Crop Risk Tool). Corn is susceptible from V10 to R3.

Ported from the Crop Risk Tool (`predict_gls`, `build_gray_leaf_spot`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk, Susceptibility

SPEC = ModelSpec(
    id="gray-leaf-spot",
    name="Gray leaf spot spore probability",
    group="disease",
    version="1.0",
    status="stable",
    summary="The probability of gray leaf spot spores being present, from three weeks of minimum temperature "
    "and a month of minimum dew point; corn is susceptible from V10 to R3.",
    topics=("gray-leaf-spot",),
    crops=("Corn",),
    citations=(
        Citation(text="Damon Smith (UW–Madison) and Richard Webster (NDSU), as implemented in the Crop Risk Tool."),
        Citation(
            text="Crop Protection Network: Gray leaf spot of corn.",
            url="https://cropprotectionnetwork.org/encyclopedia/gray-leaf-spot-of-corn",
        ),
    ),
    inputs=(
        Quantity(
            name="air_temperature_min", label="Minimum temperature", unit="degC", description="21-day moving average"
        ),
        Quantity(name="dew_point_min", label="Minimum dew point", unit="degC", description="30-day moving average"),
    ),
    outputs=(Quantity(name="probability", label="Spore probability", unit="percent"),),
    risk=Risk(levels=PROBABILITY_LEVELS, criteria="Very low below 1%, Low from 1%, Moderate from 40%, High from 60%."),
    explorer=(
        ExplorerInput(
            name="temperature_min_21day",
            label="Minimum temperature, 21-day average",
            unit="degC",
            minimum=0,
            maximum=30,
            step=0.5,
            default=16,
        ),
        ExplorerInput(
            name="dew_point_min_30day",
            label="Minimum dew point, 30-day average",
            unit="degC",
            minimum=-5,
            maximum=25,
            step=0.5,
            default=14,
        ),
    ),
    sweep={"temperature_min_21day": (10.0, 15.0, 20.0), "dew_point_min_30day": (5.0, 10.0, 15.0, 20.0)},
    lookback_days=30,
    season=("07-01", "08-15"),
    susceptible=Susceptibility(
        crop="corn-stages", first="V10", last="R3", source="The Crop Risk Tool (V10–R3, 10th leaf to milk)"
    ),
    changelog=(Change(version="1.0", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
)


def probability(temperature_min_21day, dew_point_min_30day) -> np.ndarray:
    return logistic(-2.9467 - 0.03729 * np.asarray(temperature_min_21day) + 0.6534 * np.asarray(dew_point_min_30day))


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return {
        "probability": probability(
            moving_mean(inputs["air_temperature_min"], 21), moving_mean(inputs["dew_point_min"], 30)
        )
    }


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["probability"], 1, 40, 60)


def explore(temperature_min_21day: float, dew_point_min_30day: float) -> dict[str, float]:
    return {"probability": float(probability(temperature_min_21day, dew_point_min_30day))}
