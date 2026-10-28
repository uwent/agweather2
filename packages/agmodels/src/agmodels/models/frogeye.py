"""Frogeye leaf spot of soybean: the probability of Cercospora sojina spores being present.

A logistic model of the 30-day mean maximum temperature and 30-day mean hours with RH ≥ 80% (Smith lab,
UW–Madison, and Webster, NDSU, as in the Crop Risk Tool). Soybean is susceptible from R1 to R5.

Ported from the Crop Risk Tool (`predict_fls`, `build_frogeye_leaf_spot`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk, Susceptibility

SPEC = ModelSpec(
    id="frogeye-leaf-spot",
    name="Frogeye leaf spot spore probability",
    group="disease",
    version="1.0",
    status="stable",
    summary="The probability of frogeye leaf spot spores being present, from a month of maximum temperature and "
    "humid hours; soybean is susceptible from R1 (flowering) to R5 (beginning seed).",
    topics=("frogeye-leaf-spot",),
    crops=("Soybean",),
    citations=(
        Citation("Damon Smith (UW–Madison) and Richard Webster (NDSU), as implemented in the Crop Risk Tool."),
        Citation(
            "Crop Protection Network: Frogeye leaf spot of soybean.",
            "https://cropprotectionnetwork.org/encyclopedia/frogeye-leaf-spot-of-soybean",
        ),
    ),
    inputs=(
        Quantity("air_temperature_max", "Maximum temperature", "degC", "30-day moving average"),
        Quantity("hours_rh_over_80", "Hours with RH ≥ 80%", "hour", "30-day moving average"),
    ),
    outputs=(Quantity("probability", "Spore probability", "percent"),),
    risk=Risk(PROBABILITY_LEVELS, "Very low below 1%, Low from 1%, Moderate from 40%, High from 50%."),
    explorer=(
        ExplorerInput("temperature_max_30day", "Maximum temperature, 30-day average", "degC", 10, 40, 0.5, 28),
        ExplorerInput("hours_rh_80_30day", "Hours RH ≥ 80%, 30-day average", "hour", 0, 24, 0.5, 10),
    ),
    sweep={"temperature_max_30day": (20.0, 25.0, 30.0, 35.0), "hours_rh_80_30day": (0.0, 6.0, 12.0, 18.0, 24.0)},
    lookback_days=30,
    season=("06-15", "09-07"),
    susceptible=Susceptibility("soybean-stages", "R1", "R5", "The Crop Risk Tool (R1–R5, flowering to beginning seed)"),
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool."),),
)


def probability(temperature_max_30day, hours_rh_80_30day) -> np.ndarray:
    return logistic(-5.92485 + 0.12208 * np.asarray(temperature_max_30day) + 0.17326 * np.asarray(hours_rh_80_30day))


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return {
        "probability": probability(
            moving_mean(inputs["air_temperature_max"], 30), moving_mean(inputs["hours_rh_over_80"], 30)
        )
    }


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["probability"], 1, 40, 50)


def explore(temperature_max_30day: float, hours_rh_80_30day: float) -> dict[str, float]:
    return {"probability": float(probability(temperature_max_30day, hours_rh_80_30day))}
