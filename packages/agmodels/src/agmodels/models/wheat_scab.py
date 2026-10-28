"""Fusarium head blight (scab) of wheat: the probability of an epidemic, by cultivar resistance.

A logistic model of the 14-day mean RH (De Wolf, as in the Crop Risk Tool), shifted for four resistance classes.
Wheat is susceptible at flowering (anthesis).

Ported from the Crop Risk Tool (`predict_wheat_scab`, `build_wheat_scab`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Option, Quantity, Risk

RESISTANCE = {  # option value: (label, intercept shift)
    "vs": ("Very susceptible", 0.0),
    "s": ("Susceptible", -0.82795556),
    "ms": ("Moderately susceptible", -1.4812696),
    "mr": ("Moderately resistant", -1.8484537),
}

SPEC = ModelSpec(
    id="wheat-scab",
    name="Wheat scab (Fusarium head blight) probability",
    group="disease",
    version="1.0",
    status="stable",
    summary="The probability of a Fusarium head blight epidemic from two weeks of humidity, for the cultivar's "
    "resistance class; wheat is susceptible at flowering.",
    topics=("wheat-scab",),
    crops=("Wheat",),
    citations=(
        Citation("Erick De Wolf, as implemented in the Crop Risk Tool."),
        Citation(
            "Crop Protection Network: An overview of Fusarium head blight.",
            "https://cropprotectionnetwork.org/publications/an-overview-of-fusarium-head-blight",
        ),
    ),
    inputs=(Quantity("relative_humidity_mean", "Mean RH", "percent", "14-day moving average"),),
    outputs=(
        Quantity("probability", "Probability for the chosen resistance", "percent"),
        *(Quantity(f"probability_{key}", label, "percent") for key, (label, _) in RESISTANCE.items()),
    ),
    risk=Risk(PROBABILITY_LEVELS, "Very low below 1%, Low from 1%, Moderate from 24%, High from 32%."),
    explorer=(ExplorerInput("rh_mean_14day", "Mean RH, 14-day average", "percent", 40, 100, 1, 80),),
    sweep={"rh_mean_14day": (50.0, 60.0, 70.0, 80.0, 90.0, 100.0)},
    options=(Option("resistance", "Cultivar resistance", tuple((k, v[0]) for k, v in RESISTANCE.items()), "s"),),
    lookback_days=14,
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool."),),
)


def probabilities(rh_mean_14day) -> dict[str, np.ndarray]:
    rh = np.asarray(rh_mean_14day, dtype=float)
    return {
        f"probability_{key}": logistic(-3.6432643 + shift + 0.051459669 * rh) for key, (_, shift) in RESISTANCE.items()
    }


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    each = probabilities(moving_mean(inputs["relative_humidity_mean"], 14))
    return {"probability": each[f"probability_{options.get('resistance', 's')}"], **each}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["probability"], 1, 24, 32)


def explore(rh_mean_14day: float) -> dict[str, float]:
    return {name: float(p) for name, p in probabilities(rh_mean_14day).items()}
