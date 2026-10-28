"""Gray leaf spot of corn: the probability of Cercospora zeae-maydis spores being present.

A logistic model of the 21-day mean minimum temperature and 30-day mean minimum dew point (Smith lab, UW–Madison,
and Webster, NDSU, as in the Crop Risk Tool). Corn is susceptible from V10 to R3.

Ported from the Crop Risk Tool (`predict_gls`, `build_gray_leaf_spot`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk

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
        Citation("Damon Smith (UW–Madison) and Richard Webster (NDSU), as implemented in the Crop Risk Tool."),
        Citation(
            "Crop Protection Network: Gray leaf spot of corn.",
            "https://cropprotectionnetwork.org/encyclopedia/gray-leaf-spot-of-corn",
        ),
    ),
    inputs=(
        Quantity("air_temperature_min", "Minimum temperature", "degC", "21-day moving average"),
        Quantity("dew_point_min", "Minimum dew point", "degC", "30-day moving average"),
    ),
    outputs=(Quantity("probability", "Spore probability", "percent"),),
    risk=Risk(PROBABILITY_LEVELS, "Very low below 1%, Low from 1%, Moderate from 40%, High from 60%."),
    explorer=(
        ExplorerInput("temperature_min_21day", "Minimum temperature, 21-day average", "degC", 0, 30, 0.5, 16),
        ExplorerInput("dew_point_min_30day", "Minimum dew point, 30-day average", "degC", -5, 25, 0.5, 14),
    ),
    sweep={"temperature_min_21day": (10.0, 15.0, 20.0), "dew_point_min_30day": (5.0, 10.0, 15.0, 20.0)},
    lookback_days=30,
    season=("07-01", "08-15"),
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool."),),
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
