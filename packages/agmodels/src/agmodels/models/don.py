"""Gibberella ear rot of corn: the probability of deoxynivalenol (DON) above 1 ppm in grain.

A logistic model (Paul and Nesi, Ohio State, as in the Crop Risk Tool) of two windows around silking: 21 to 7
days before (mean maximum and minimum temperature, days with mean temperature ≥ 25 °C, days with rain) and the
last 14 days (mean RH, days with mean RH > 80%). Corn is susceptible during silking.

Ported from the Crop Risk Tool (`predict_don`, `build_don`) with parity tests. Difference: the tool counts a day
with missing precip as dry; here it isn't counted either way (the windows count the days that have data).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import rolling_sum
from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk, Susceptibility

SPEC = ModelSpec(
    id="gibberella-ear-rot-don",
    name="Gibberella ear rot DON probability",
    group="disease",
    version="1.0",
    status="stable",
    summary="The probability of DON above 1 ppm from Gibberella ear rot, from temperature and rain 21 to 7 days "
    "before and humidity over the last 14 days; corn is susceptible during silking.",
    topics=("gibberella-ear-rot",),
    crops=("Corn",),
    citations=(
        Citation(text="Pierce Paul and Cristiano Nesi (Ohio State University), as implemented in the Crop Risk Tool."),
        Citation(
            text="Crop Protection Network: Gibberella ear rot of corn.",
            url="https://cropprotectionnetwork.org/encyclopedia/gibberella-ear-rot-of-corn",
        ),
    ),
    inputs=(
        Quantity(
            name="air_temperature_max",
            label="Maximum temperature",
            unit="degC",
            description="14-day mean, 7 days earlier",
        ),
        Quantity(
            name="air_temperature_min",
            label="Minimum temperature",
            unit="degC",
            description="14-day mean, 7 days earlier",
        ),
        Quantity(
            name="air_temperature_mean",
            label="Mean temperature",
            unit="degC",
            description="Days ≥ 25 °C in 14, 7 days earlier",
        ),
        Quantity(
            name="precipitation_sum",
            label="Precipitation",
            unit="mm",
            description="Days with rain in 14, 7 days earlier",
        ),
        Quantity(
            name="relative_humidity_mean",
            label="Mean RH",
            unit="percent",
            description="14-day mean, and days above 80%",
        ),
    ),
    outputs=(Quantity(name="probability", label="Probability of DON > 1 ppm", unit="percent"),),
    risk=Risk(levels=PROBABILITY_LEVELS, criteria="Very low below 1%, Low from 1%, Moderate from 20%, High from 40%."),
    explorer=(
        ExplorerInput(
            name="w7_max_temp",
            label="Mean maximum temperature, 21–7 days before",
            unit="degC",
            minimum=15,
            maximum=40,
            step=0.5,
            default=29,
        ),
        ExplorerInput(
            name="w7_min_temp",
            label="Mean minimum temperature, 21–7 days before",
            unit="degC",
            minimum=5,
            maximum=30,
            step=0.5,
            default=17,
        ),
        ExplorerInput(
            name="w7_days_temp_over_25",
            label="Days with mean ≥ 25 °C, 21–7 days before",
            unit="day",
            minimum=0,
            maximum=14,
            step=1,
            default=3,
        ),
        ExplorerInput(
            name="w7_days_precip",
            label="Days with rain, 21–7 days before",
            unit="day",
            minimum=0,
            maximum=14,
            step=1,
            default=5,
        ),
        ExplorerInput(
            name="w0_mean_rh",
            label="Mean RH, last 14 days",
            unit="percent",
            minimum=40,
            maximum=100,
            step=1,
            default=75,
        ),
        ExplorerInput(
            name="w0_days_rh_over_80",
            label="Days with mean RH > 80%, last 14 days",
            unit="day",
            minimum=0,
            maximum=14,
            step=1,
            default=4,
        ),
    ),
    sweep={
        "w7_max_temp": (26.0, 30.0),
        "w7_min_temp": (14.0, 18.0),
        "w7_days_temp_over_25": (0.0, 5.0),
        "w7_days_precip": (2.0, 8.0),
        "w0_mean_rh": (65.0, 80.0, 95.0),
        "w0_days_rh_over_80": (0.0, 7.0),
    },
    lookback_days=21,
    season=("07-01", "08-07"),
    susceptible=Susceptibility(
        crop="corn-stages",
        first="R1",
        last="R1",
        source="The Crop Risk Tool (susceptible during silking); the model's windows end on silking day",
    ),
    changelog=(
        Change(
            version="1.0",
            date="2026-10-28",
            note="Ported from the Crop Risk Tool; missing precip isn't counted as dry.",
        ),
    ),
)


def probability(w7_max_temp, w7_min_temp, w7_days_temp_over_25, w7_days_precip, w0_mean_rh, w0_days_rh_over_80):
    a = [
        np.asarray(x, dtype=float)
        for x in (w7_max_temp, w7_min_temp, w7_days_temp_over_25, w7_days_precip, w0_mean_rh, w0_days_rh_over_80)
    ]
    return logistic(
        -59.6309 + 1.3057 * a[0] + 0.9090 * a[1] - 1.6158 * a[2] - 0.9350 * a[3] + 0.2255 * a[4] - 0.9249 * a[5]
    )


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    def count(condition) -> np.ndarray:
        return rolling_sum(np.asarray(condition, dtype=float), 14)

    def lag(values: np.ndarray) -> np.ndarray:
        return np.concatenate([np.full((7, *values.shape[1:]), np.nan), values[:-7]])[: values.shape[0]]

    rh = np.asarray(inputs["relative_humidity_mean"], dtype=float)
    p = probability(
        lag(moving_mean(inputs["air_temperature_max"], 14)),
        lag(moving_mean(inputs["air_temperature_min"], 14)),
        lag(count(np.asarray(inputs["air_temperature_mean"]) >= 25)),
        lag(count(np.asarray(inputs["precipitation_sum"]) > 0)),
        moving_mean(rh, 14),
        count(rh > 80),
    )
    return {"probability": p}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["probability"], 1, 20, 40)


def explore(**values: float) -> dict[str, float]:
    return {"probability": float(probability(**values))}
