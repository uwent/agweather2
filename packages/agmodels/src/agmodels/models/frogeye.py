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
    version="0.1",
    status="stable",
    summary="The probability of frogeye leaf spot spores being present, from a month of maximum temperature and "
    "humid hours; soybean is susceptible from R1 (flowering) to R5 (beginning seed).",
    topics=("frogeye-leaf-spot",),
    crops=("Soybean",),
    citations=(
        Citation(text="Damon Smith (UW–Madison) and Richard Webster (NDSU), as implemented in the Crop Risk Tool."),
        Citation(
            text="Crop Protection Network: Frogeye leaf spot of soybean.",
            url="https://cropprotectionnetwork.org/encyclopedia/frogeye-leaf-spot-of-soybean",
        ),
    ),
    inputs=(
        Quantity(
            name="air_temperature_max", label="Maximum temperature", unit="degC", description="30-day moving average"
        ),
        Quantity(
            name="hours_rh_over_80", label="Hours with RH ≥ 80%", unit="hour", description="30-day moving average"
        ),
    ),
    outputs=(Quantity(name="probability", label="Spore probability", unit="percent"),),
    risk=Risk(levels=PROBABILITY_LEVELS, criteria="Very low below 1%, Low from 1%, Moderate from 40%, High from 50%."),
    explorer=(
        ExplorerInput(
            name="temperature_max_30day",
            label="Maximum temperature, 30-day average",
            unit="degC",
            minimum=10,
            maximum=40,
            step=0.5,
            default=28,
        ),
        ExplorerInput(
            name="hours_rh_80_30day",
            label="Hours RH ≥ 80%, 30-day average",
            unit="hour",
            minimum=0,
            maximum=24,
            step=0.5,
            default=10,
        ),
    ),
    sweep={"temperature_max_30day": (20.0, 25.0, 30.0, 35.0), "hours_rh_80_30day": (0.0, 6.0, 12.0, 18.0, 24.0)},
    lookback_days=30,
    season=("06-15", "09-07"),
    susceptible=Susceptibility(
        crop="soybean-stages", first="R1", last="R5", source="The Crop Risk Tool (R1–R5, flowering to beginning seed)"
    ),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
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
