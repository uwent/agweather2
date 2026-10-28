"""Tar spot of corn: the probability of Phyllachora maydis spores being present.

Two logistic models (Webster et al. 2023) from 30-day mean temperature, 30-day mean daily maximum RH and 14-day
mean night hours with RH ≥ 90%, averaged, then scaled down as the 21-day mean minimum falls below 10 °C (the
Crop Risk Tool's attenuation). Corn is susceptible from V10 to R3.

Ported from the Crop Risk Tool (`predict_tarspot`, `build_tar_spot`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import attenuate_for_cold, logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk, Susceptibility

SPEC = ModelSpec(
    id="tar-spot",
    name="Tar spot spore probability",
    group="disease",
    version="1.0",
    status="stable",
    summary="The probability of tar spot spores being present, from a month of temperature and humidity; corn "
    "is susceptible from V10 (10th leaf) to R3 (milk).",
    topics=("tar-spot",),
    crops=("Corn",),
    citations=(
        Citation(
            "Webster, R. W., Nicolli, C., Allen, T. W., et al. (2023). Uncovering the environmental conditions "
            "required for Phyllachora maydis infection and tar spot development on corn in the United States for "
            "use as predictive models for future epidemics. Scientific Reports 13, 17064.",
            doi="10.1038/s41598-023-44338-6",
        ),
        Citation(
            "Crop Protection Network: Tar spot of corn.",
            "https://cropprotectionnetwork.org/encyclopedia/tar-spot-of-corn",
        ),
    ),
    inputs=(
        Quantity("air_temperature_mean", "Mean temperature", "degC", "30-day moving average"),
        Quantity("relative_humidity_max", "Maximum RH", "percent", "30-day moving average"),
        Quantity("hours_rh_over_90_night", "Night hours with RH ≥ 90%", "hour", "14-day moving average"),
        Quantity("air_temperature_min", "Minimum temperature", "degC", "21-day moving average, for cold attenuation"),
    ),
    outputs=(Quantity("probability", "Spore probability", "percent"),),
    risk=Risk(PROBABILITY_LEVELS, "Very low below 1%, Low from 1%, Moderate from 20%, High from 35%."),
    explorer=(
        ExplorerInput("temperature_mean_30day", "Mean temperature, 30-day average", "degC", 10, 35, 0.5, 22),
        ExplorerInput("rh_max_30day", "Maximum RH, 30-day average", "percent", 50, 100, 1, 90),
        ExplorerInput("night_hours_rh_90_14day", "Night hours RH ≥ 90%, 14-day average", "hour", 0, 11, 0.5, 5),
    ),
    sweep={
        "temperature_mean_30day": (15.0, 20.0, 25.0, 30.0),
        "rh_max_30day": (70.0, 85.0, 100.0),
        "night_hours_rh_90_14day": (0.0, 4.0, 8.0),
    },
    lookback_days=30,
    season=("07-01", "08-15"),
    susceptible=Susceptibility(
        "corn-stages", "V10", "R3", "The Crop Risk Tool (V10–R3, 10th leaf to milk); Tarspotter's fungicide window"
    ),
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool."),),
)


def probability(temperature_mean_30day, rh_max_30day, night_hours_rh_90_14day) -> np.ndarray:
    t, rh, night = (np.asarray(x, dtype=float) for x in (temperature_mean_30day, rh_max_30day, night_hours_rh_90_14day))
    return (logistic(32.06987 - 0.89471 * t - 0.14373 * rh) + logistic(20.35950 - 0.91093 * t - 0.29240 * night)) / 2


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    p = probability(
        moving_mean(inputs["air_temperature_mean"], 30),
        moving_mean(inputs["relative_humidity_max"], 30),
        moving_mean(inputs["hours_rh_over_90_night"], 14),
    )
    return {"probability": attenuate_for_cold(p, moving_mean(inputs["air_temperature_min"], 21))}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["probability"], 1, 20, 35)


def explore(temperature_mean_30day: float, rh_max_30day: float, night_hours_rh_90_14day: float) -> dict[str, float]:
    return {"probability": float(probability(temperature_mean_30day, rh_max_30day, night_hours_rh_90_14day))}
