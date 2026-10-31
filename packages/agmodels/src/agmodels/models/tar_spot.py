"""Tar spot of corn: the probability of Phyllachora maydis spores being present.

Two logistic models (Webster et al. 2023) from 30-day mean temperature, 30-day mean daily maximum RH and 14-day
mean night hours with RH ≥ 90%, averaged, then scaled down as the 21-day mean minimum falls below 10 °C (the
Crop Risk Tool's attenuation). Corn is susceptible from V10 to R3.

Ported from the Crop Risk Tool (`predict_tarspot`, `build_tar_spot`) with parity tests.

Gridded RH ≥ 90% is counted at 88%, a station's 90% (D50, `features.STATION_RH_90_AS_GRIDDED`).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import attenuate_for_cold, logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk, Susceptibility

SPEC = ModelSpec(
    id="tar-spot",
    name="Tar spot spore probability",
    group="disease",
    version="0.1",
    status="stable",
    summary="The probability of tar spot spores being present, from a month of temperature and humidity; corn "
    "is susceptible from V10 (10th leaf) to R3 (milk).",
    topics=("tar-spot",),
    crops=("Corn",),
    citations=(
        Citation(
            text="Webster, R. W., Nicolli, C., Allen, T. W., et al. (2023). Uncovering the environmental conditions "
            "required for Phyllachora maydis infection and tar spot development on corn in the United States for "
            "use as predictive models for future epidemics. Scientific Reports 13, 17064.",
            doi="10.1038/s41598-023-44338-6",
        ),
        Citation(
            text="Crop Protection Network: Tar spot of corn.",
            url="https://cropprotectionnetwork.org/encyclopedia/tar-spot-of-corn",
        ),
    ),
    inputs=(
        Quantity(
            name="air_temperature_mean", label="Mean temperature", unit="degC", description="30-day moving average"
        ),
        Quantity(name="relative_humidity_max", label="Maximum RH", unit="percent", description="30-day moving average"),
        Quantity(
            name="hours_rh_over_90_night",
            label="Night hours with RH ≥ 90%",
            unit="hour",
            description="14-day moving average",
        ),
        Quantity(
            name="air_temperature_min",
            label="Minimum temperature",
            unit="degC",
            description="21-day moving average, for cold attenuation",
        ),
    ),
    outputs=(Quantity(name="probability", label="Spore probability", unit="percent"),),
    risk=Risk(levels=PROBABILITY_LEVELS, criteria="Very low below 1%, Low from 1%, Moderate from 20%, High from 35%."),
    explorer=(
        ExplorerInput(
            name="temperature_mean_30day",
            label="Mean temperature, 30-day average",
            unit="degC",
            minimum=10,
            maximum=35,
            step=0.5,
            default=22,
        ),
        ExplorerInput(
            name="rh_max_30day",
            label="Maximum RH, 30-day average",
            unit="percent",
            minimum=50,
            maximum=100,
            step=1,
            default=90,
        ),
        ExplorerInput(
            name="night_hours_rh_90_14day",
            label="Night hours RH ≥ 90%, 14-day average",
            unit="hour",
            minimum=0,
            maximum=11,
            step=0.5,
            default=5,
        ),
    ),
    sweep={
        "temperature_mean_30day": (15.0, 20.0, 25.0, 30.0),
        "rh_max_30day": (70.0, 85.0, 100.0),
        "night_hours_rh_90_14day": (0.0, 4.0, 8.0),
    },
    lookback_days=30,
    season=("07-01", "08-15"),
    susceptible=Susceptibility(
        crop="corn-stages",
        first="V10",
        last="R3",
        source="The Crop Risk Tool (V10–R3, 10th leaf to milk); Tarspotter's fungicide window",
    ),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
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
