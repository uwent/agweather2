"""Cercospora leaf blight of soybean: spore probabilities for three Cercospora species (beta).

Logistic models (Webster, NDSU, as in the Crop Risk Tool): C. flagellaris from the 5-day mean minimum temperature
and dew point depression; C. cf. sigesbeckiae from the 14-day mean maximum wind and 10-day mean hours with
RH ≥ 90%; C. kikuchii from the 14-day mean hours with RH ≥ 90% and the 5-day mean maximum dew point depression.
Each has its own risk thresholds; the model's risk is the highest of the three.

Ported from the Crop Risk Tool (`predict_soybean_cercospora`, `build_soybean_cercospora`) with parity tests.
Open question (PLAN.md Phase 3 D): the tool passes wind in km/h (Open-Meteo's default) to the C. sigesbeckiae
model; kept here until the unit of the fit is confirmed.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk, Susceptibility

KMH_PER_MS = 3.6
SPECIES = {  # output name: (label, risk thresholds in %)
    "probability_flagellaris": ("C. flagellaris", (1, 10, 15)),
    "probability_sigesbeckiae": ("C. cf. sigesbeckiae", (1, 5, 10)),
    "probability_kikuchii": ("C. kikuchii", (1, 5, 10)),
}

SPEC = ModelSpec(
    id="soybean-cercospora",
    name="Soybean Cercospora leaf blight spore probability",
    group="disease",
    version="1.0",
    status="beta",
    summary="Spore probabilities for three Cercospora species causing leaf blight of soybean, from recent "
    "temperature, dew point depression, wind and humid hours.",
    topics=("soybean-cercospora-leaf-blight",),
    crops=("Soybean",),
    citations=(
        Citation("Richard Webster (North Dakota State University), as implemented in the Crop Risk Tool."),
        Citation(
            "Crop Protection Network: Cercospora leaf blight of soybean.",
            "https://cropprotectionnetwork.org/encyclopedia/cercospora-leaf-blight-of-soybean",
        ),
        Citation(
            "Crop Protection Network: An overview of Cercospora leaf blight of soybean.",
            "https://cropprotectionnetwork.org/publications/an-overview-of-cercospora-leaf-blight-of-soybean",
        ),
    ),
    inputs=(
        Quantity("air_temperature_min", "Minimum temperature", "degC", "5-day moving average"),
        Quantity("dew_point_depression_mean", "Mean dew point depression", "degC", "5-day moving average"),
        Quantity("dew_point_depression_max", "Maximum dew point depression", "degC", "5-day moving average"),
        Quantity("wind_speed_max", "Maximum wind speed", "m_s", "14-day moving average"),
        Quantity("hours_rh_over_90", "Hours with RH ≥ 90%", "hour", "10- and 14-day moving averages"),
    ),
    outputs=tuple(Quantity(name, f"{label} spore probability", "percent") for name, (label, _) in SPECIES.items()),
    risk=Risk(
        PROBABILITY_LEVELS,
        "The highest of the three species' levels. C. flagellaris: Low from 1%, Moderate from 10%, High from 15%. "
        "C. cf. sigesbeckiae and C. kikuchii: Low from 1%, Moderate from 5%, High from 10%.",
    ),
    explorer=(
        ExplorerInput("min_temp_5day", "Minimum temperature, 5-day average", "degC", 0, 30, 0.5, 18),
        ExplorerInput("mean_dpd_5day", "Mean dew point depression, 5-day average", "degC", 0, 15, 0.5, 4),
        ExplorerInput("max_dpd_5day", "Maximum dew point depression, 5-day average", "degC", 0, 25, 0.5, 10),
        ExplorerInput("max_wind_14day", "Maximum wind, 14-day average", "m_s", 0, 15, 0.5, 5),
        ExplorerInput("hours_rh90_10day", "Hours RH ≥ 90%, 10-day average", "hour", 0, 24, 0.5, 6),
        ExplorerInput("hours_rh90_14day", "Hours RH ≥ 90%, 14-day average", "hour", 0, 24, 0.5, 6),
    ),
    sweep={
        "min_temp_5day": (12.0, 20.0),
        "mean_dpd_5day": (2.0, 6.0),
        "max_dpd_5day": (6.0, 14.0),
        "max_wind_14day": (3.0, 7.0),
        "hours_rh90_10day": (2.0, 10.0),
        "hours_rh90_14day": (2.0, 10.0),
    },
    lookback_days=14,
    susceptible=Susceptibility(
        "soybean-stages",
        "R3",
        "R6",
        "Provisional: CPN (symptoms from beginning seed set)",
        "The fit is unpublished and its author gave no risk period: confirm with Webster.",
    ),
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool."),),
)


def probabilities(min_temp_5day, mean_dpd_5day, max_dpd_5day, max_wind_14day, hours_rh90_10day, hours_rh90_14day):
    """Each species' probability; wind in m/s (converted to km/h as the tool passes it)."""
    wind_kmh = np.asarray(max_wind_14day, dtype=float) * KMH_PER_MS
    return {
        "probability_flagellaris": logistic(
            -6.30565 + 0.19559 * np.asarray(min_temp_5day) + 0.16999 * np.asarray(mean_dpd_5day)
        ),
        "probability_sigesbeckiae": logistic(3.25803 - 0.35362 * wind_kmh + 0.05473 * np.asarray(hours_rh90_10day)),
        "probability_kikuchii": logistic(
            -7.67159 + 0.34914 * np.asarray(hours_rh90_14day) + 0.25508 * np.asarray(max_dpd_5day)
        ),
    }


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return probabilities(
        moving_mean(inputs["air_temperature_min"], 5),
        moving_mean(inputs["dew_point_depression_mean"], 5),
        moving_mean(inputs["dew_point_depression_max"], 5),
        moving_mean(inputs["wind_speed_max"], 14),
        moving_mean(inputs["hours_rh_over_90"], 10),
        moving_mean(inputs["hours_rh_over_90"], 14),
    )


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return np.fmax.reduce([risk_level(outputs[name], *thresholds) for name, (_, thresholds) in SPECIES.items()])


def explore(**values: float) -> dict[str, float]:
    return {name: float(p) for name, p in probabilities(**values).items()}
