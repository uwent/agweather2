"""White mold of soybean: the probability of Sclerotinia sclerotiorum apothecia being present.

Willbur et al. (2018): for non-irrigated fields, three logistic models of 30-day mean maximum temperature, maximum
wind speed and maximum RH, averaged and scaled down as the 21-day mean minimum falls below 10 °C; for irrigated
fields, one of maximum temperature, maximum RH and row spacing. Soybean is susceptible from R1 to R3.

Ported from the Crop Risk Tool (`predict_white_mold_dry`, `predict_white_mold_irrig`, `build_white_mold`) with
parity tests. Wind is m/s, as the tool converts it to before the dry model.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import attenuate_for_cold, logistic, moving_mean, risk_level
from agmodels.spec import (
    PROBABILITY_LEVELS,
    Change,
    Citation,
    ExplorerInput,
    ModelSpec,
    Option,
    Quantity,
    Risk,
    Susceptibility,
)

SPEC = ModelSpec(
    id="white-mold",
    name="White mold apothecia probability",
    group="disease",
    version="1.0",
    status="stable",
    summary="The probability of white mold apothecia in soybean fields, from a month of temperature, humidity "
    "and wind (non-irrigated) or temperature, humidity and row spacing (irrigated); susceptible from R1 to R3.",
    topics=("white-mold",),
    crops=("Soybean",),
    citations=(
        Citation(
            text="Willbur, J. F., Fall, M. L., Blackwell, T., et al. (2018). Weather-based models for assessing the "
            "risk of Sclerotinia sclerotiorum apothecial presence in soybean (Glycine max) fields. Plant Disease "
            "102, 73–84.",
            doi="10.1094/PDIS-04-17-0504-RE",
        ),
        Citation(
            text="Crop Protection Network: White mold of soybean.",
            url="https://cropprotectionnetwork.org/encyclopedia/white-mold-of-soybean",
        ),
    ),
    inputs=(
        Quantity(
            name="air_temperature_max", label="Maximum temperature", unit="degC", description="30-day moving average"
        ),
        Quantity(name="relative_humidity_max", label="Maximum RH", unit="percent", description="30-day moving average"),
        Quantity(
            name="wind_speed_max",
            label="Maximum wind speed",
            unit="m_s",
            description="30-day moving average (non-irrigated)",
        ),
        Quantity(
            name="air_temperature_min",
            label="Minimum temperature",
            unit="degC",
            description="21-day moving average, for cold attenuation",
        ),
    ),
    outputs=(Quantity(name="probability", label="Apothecia probability", unit="percent"),),
    risk=Risk(
        levels=PROBABILITY_LEVELS,
        criteria="Non-irrigated: Very low below 1%, Low from 1%, Moderate from 20%, High from 35%. Irrigated: Very low "
        "below 1%, Low from 1%, Moderate from 5%, High from 10%.",
    ),
    explorer=(
        ExplorerInput(
            name="temperature_max_30day",
            label="Maximum temperature, 30-day average",
            unit="degC",
            minimum=10,
            maximum=40,
            step=0.5,
            default=27,
        ),
        ExplorerInput(
            name="rh_max_30day",
            label="Maximum RH, 30-day average",
            unit="percent",
            minimum=50,
            maximum=100,
            step=1,
            default=95,
        ),
        ExplorerInput(
            name="wind_max_30day",
            label="Maximum wind, 30-day average",
            unit="m_s",
            minimum=0,
            maximum=15,
            step=0.5,
            default=5,
        ),
    ),
    sweep={
        "temperature_max_30day": (20.0, 25.0, 30.0),
        "rh_max_30day": (80.0, 90.0, 100.0),
        "wind_max_30day": (2.0, 5.0, 8.0),
    },
    options=(
        Option(
            name="irrigation",
            label="Irrigation",
            choices=(("dry", "Non-irrigated"), ("irrigated", "Irrigated")),
            default="dry",
        ),
        Option(
            name="row_spacing",
            label="Row spacing (irrigated)",
            choices=(("30", "30 in"), ("15", "15 in")),
            default="30",
        ),
    ),
    lookback_days=30,
    season=("06-15", "08-07"),
    susceptible=Susceptibility(
        crop="soybean-stages",
        first="R1",
        last="R3",
        source="The Crop Risk Tool (R1–R3); Sporecaster runs only with flowers present",
    ),
    changelog=(Change(version="1.0", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
)


def probability_dry(temperature_max_30day, wind_max_30day, rh_max_30day) -> np.ndarray:
    t, w, rh = (np.asarray(x, dtype=float) for x in (temperature_max_30day, wind_max_30day, rh_max_30day))
    m1 = -0.47 * t - 1.01 * w + 16.65
    m2 = -0.68 * t + 17.19
    m3 = -0.86 * t + 0.1 * rh - 0.75 * w + 8.2
    return (logistic(m1) + logistic(m2) + logistic(m3)) / 3


def probability_irrigated(temperature_max_30day, rh_max_30day, row_spacing: str) -> np.ndarray:
    wide = 1.0 if row_spacing == "30" else 0.0
    return logistic(-52.65 - 2.38 * wide + 0.65 * np.asarray(temperature_max_30day) + 0.38 * np.asarray(rh_max_30day))


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    t = moving_mean(inputs["air_temperature_max"], 30)
    rh = moving_mean(inputs["relative_humidity_max"], 30)
    if options.get("irrigation", "dry") == "irrigated":
        return {"probability": probability_irrigated(t, rh, options.get("row_spacing", "30"))}
    p = probability_dry(t, moving_mean(inputs["wind_speed_max"], 30), rh)
    return {"probability": attenuate_for_cold(p, moving_mean(inputs["air_temperature_min"], 21))}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    if options.get("irrigation", "dry") == "irrigated":
        return risk_level(outputs["probability"], 1, 5, 10)
    return risk_level(outputs["probability"], 1, 20, 35)


def explore(temperature_max_30day: float, rh_max_30day: float, wind_max_30day: float) -> dict[str, float]:
    return {
        "probability_dry": float(probability_dry(temperature_max_30day, wind_max_30day, rh_max_30day)),
        "probability_irrigated_30in": float(probability_irrigated(temperature_max_30day, rh_max_30day, "30")),
        "probability_irrigated_15in": float(probability_irrigated(temperature_max_30day, rh_max_30day, "15")),
    }
