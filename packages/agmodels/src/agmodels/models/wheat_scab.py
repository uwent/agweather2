"""Fusarium head blight (scab) of wheat: the probability of an epidemic, by cultivar resistance.

A logistic model of the 14-day mean RH (De Wolf, as in the Crop Risk Tool), shifted for four resistance classes.
Wheat is susceptible at flowering (anthesis).

Ported from the Crop Risk Tool (`predict_wheat_scab`, `build_wheat_scab`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.ingredients import Ingredient, finished
from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, Input, ModelSpec, Option, Quantity, Risk

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
    version="0.1",
    status="stable",
    summary="The probability of a Fusarium head blight epidemic from two weeks of humidity, for the cultivar's "
    "resistance class; wheat is susceptible at flowering.",
    topics=("wheat-scab",),
    crops=("Wheat",),
    citations=(
        Citation(text="Erick De Wolf, as implemented in the Crop Risk Tool."),
        Citation(
            text="Crop Protection Network: An overview of Fusarium head blight.",
            url="https://cropprotectionnetwork.org/publications/an-overview-of-fusarium-head-blight",
        ),
    ),
    inputs=(
        Input(name="relative_humidity_mean", label="Mean RH", unit="percent", description="14-day moving average"),
    ),
    outputs=(
        Quantity(name="probability", label="Probability for the chosen resistance", unit="percent"),
        *(Quantity(name=f"probability_{key}", label=label, unit="percent") for key, (label, _) in RESISTANCE.items()),
    ),
    risk=Risk(levels=PROBABILITY_LEVELS, criteria="Very low below 1%, Low from 1%, Moderate from 24%, High from 32%."),
    explorer=(
        ExplorerInput(
            name="rh_mean_14day",
            label="Mean RH, 14-day average",
            unit="percent",
            minimum=40,
            maximum=100,
            step=1,
            default=80,
        ),
    ),
    sweep={"rh_mean_14day": (50.0, 60.0, 70.0, 80.0, 90.0, 100.0)},
    options=(
        Option(
            name="resistance",
            label="Cultivar resistance",
            choices=tuple((k, v[0]) for k, v in RESISTANCE.items()),
            default="s",
        ),
    ),
    lookback_days=14,
    ingredients=(Ingredient(name="relative_humidity_mean_14_day", unit="percent"),),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
)


def probabilities(rh_mean_14day) -> dict[str, np.ndarray]:
    rh = np.asarray(rh_mean_14day, dtype=float)
    return {
        f"probability_{key}": logistic(-3.6432643 + shift + 0.051459669 * rh) for key, (_, shift) in RESISTANCE.items()
    }


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "relative_humidity_mean_14_day": moving_mean(inputs["relative_humidity_mean"], 14),
    }


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    each = probabilities(values["relative_humidity_mean_14_day"])
    return {"probability": each[f"probability_{options.get('resistance', 's')}"], **each}


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return finished(
        accumulations=(),
        values=ingredients(inputs),
        inputs=inputs,
        biofix_index=biofix_index,
        finish=finish,
        options=options,
    )


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["probability"], 1, 24, 32)


def explore(rh_mean_14day: float) -> dict[str, float]:
    return {name: float(p) for name, p in probabilities(rh_mean_14day).items()}
