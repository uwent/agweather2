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
        Citation("Pierce Paul and Cristiano Nesi (Ohio State University), as implemented in the Crop Risk Tool."),
        Citation(
            "Crop Protection Network: Gibberella ear rot of corn.",
            "https://cropprotectionnetwork.org/encyclopedia/gibberella-ear-rot-of-corn",
        ),
    ),
    inputs=(
        Quantity("air_temperature_max", "Maximum temperature", "degC", "14-day mean, 7 days earlier"),
        Quantity("air_temperature_min", "Minimum temperature", "degC", "14-day mean, 7 days earlier"),
        Quantity("air_temperature_mean", "Mean temperature", "degC", "Days ≥ 25 °C in 14, 7 days earlier"),
        Quantity("precipitation_sum", "Precipitation", "mm", "Days with rain in 14, 7 days earlier"),
        Quantity("relative_humidity_mean", "Mean RH", "percent", "14-day mean, and days above 80%"),
    ),
    outputs=(Quantity("probability", "Probability of DON > 1 ppm", "percent"),),
    risk=Risk(PROBABILITY_LEVELS, "Very low below 1%, Low from 1%, Moderate from 20%, High from 40%."),
    explorer=(
        ExplorerInput("w7_max_temp", "Mean maximum temperature, 21–7 days before", "degC", 15, 40, 0.5, 29),
        ExplorerInput("w7_min_temp", "Mean minimum temperature, 21–7 days before", "degC", 5, 30, 0.5, 17),
        ExplorerInput("w7_days_temp_over_25", "Days with mean ≥ 25 °C, 21–7 days before", "day", 0, 14, 1, 3),
        ExplorerInput("w7_days_precip", "Days with rain, 21–7 days before", "day", 0, 14, 1, 5),
        ExplorerInput("w0_mean_rh", "Mean RH, last 14 days", "percent", 40, 100, 1, 75),
        ExplorerInput("w0_days_rh_over_80", "Days with mean RH > 80%, last 14 days", "day", 0, 14, 1, 4),
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
        "corn-stages",
        "R1",
        "R1",
        "The Crop Risk Tool (susceptible during silking); the model's windows end on silking day",
    ),
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool; missing precip isn't counted as dry."),),
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
