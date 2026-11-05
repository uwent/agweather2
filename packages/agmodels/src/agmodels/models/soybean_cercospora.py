"""Cercospora leaf blight of soybean: spore probabilities for three Cercospora species (beta).

Logistic models (Webster, NDSU, as in the Crop Risk Tool): C. flagellaris from the 5-day mean minimum temperature
and dew point depression; C. cf. sigesbeckiae from the 14-day mean maximum wind and 10-day mean hours with
RH ≥ 90%; C. kikuchii from the 14-day mean hours with RH ≥ 90% and the 5-day mean maximum dew point depression.
Each has its own risk thresholds; the model's risk is the highest of the three.

Ported from the Crop Risk Tool (`predict_soybean_cercospora`, `build_soybean_cercospora`) with parity tests.
Open question (PLAN.md Phase 3 D): the tool passes wind in km/h (Open-Meteo's default) to the C. sigesbeckiae
model; kept here until the unit of the fit is confirmed.

Gridded RH ≥ 90% is counted at 88%, a station's 90% (D50, `features.STATION_RH_90_AS_GRIDDED`).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.ingredients import Ingredient, finished
from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import (
    PROBABILITY_LEVELS,
    Change,
    Citation,
    ExplorerInput,
    Input,
    ModelSpec,
    Quantity,
    Risk,
    Susceptibility,
)

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
    version="0.1",
    status="beta",
    summary="Spore probabilities for three Cercospora species causing leaf blight of soybean, from recent "
    "temperature, dew point depression, wind and humid hours.",
    topics=("soybean-cercospora-leaf-blight",),
    crops=("Soybean",),
    citations=(
        Citation(text="Richard Webster (North Dakota State University), as implemented in the Crop Risk Tool."),
        Citation(
            text="Crop Protection Network: Cercospora leaf blight of soybean.",
            url="https://cropprotectionnetwork.org/encyclopedia/cercospora-leaf-blight-of-soybean",
        ),
        Citation(
            text="Crop Protection Network: An overview of Cercospora leaf blight of soybean.",
            url="https://cropprotectionnetwork.org/publications/an-overview-of-cercospora-leaf-blight-of-soybean",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC", description="5-day moving average"),
        Input(
            name="dew_point_depression_mean",
            label="Mean dew point depression",
            unit="delta_degC",
            description="5-day moving average",
        ),
        Input(
            name="dew_point_depression_max",
            label="Maximum dew point depression",
            unit="delta_degC",
            description="5-day moving average",
        ),
        Input(name="wind_speed_max", label="Maximum wind speed", unit="m_s", description="14-day moving average"),
        Input(
            name="hours_rh_over_90",
            label="Hours with RH ≥ 90%",
            unit="hour",
            description="10- and 14-day moving averages",
        ),
    ),
    outputs=tuple(
        Quantity(name=name, label=f"{label} spore probability", unit="percent") for name, (label, _) in SPECIES.items()
    ),
    risk=Risk(
        levels=PROBABILITY_LEVELS,
        criteria="The highest of the three species' levels. C. flagellaris: Low from 1%, Moderate from 10%, High from "
        "15%. C. cf. sigesbeckiae and C. kikuchii: Low from 1%, Moderate from 5%, High from 10%.",
    ),
    explorer=(
        ExplorerInput(
            name="min_temp_5day",
            label="Minimum temperature, 5-day average",
            unit="degC",
            minimum=0,
            maximum=30,
            step=0.5,
            default=18,
        ),
        ExplorerInput(
            name="mean_dpd_5day",
            label="Mean dew point depression, 5-day average",
            unit="delta_degC",
            minimum=0,
            maximum=15,
            step=0.5,
            default=4,
        ),
        ExplorerInput(
            name="max_dpd_5day",
            label="Maximum dew point depression, 5-day average",
            unit="delta_degC",
            minimum=0,
            maximum=25,
            step=0.5,
            default=10,
        ),
        ExplorerInput(
            name="max_wind_14day",
            label="Maximum wind, 14-day average",
            unit="m_s",
            minimum=0,
            maximum=15,
            step=0.5,
            default=5,
        ),
        ExplorerInput(
            name="hours_rh90_10day",
            label="Hours RH ≥ 90%, 10-day average",
            unit="hour",
            minimum=0,
            maximum=24,
            step=0.5,
            default=6,
        ),
        ExplorerInput(
            name="hours_rh90_14day",
            label="Hours RH ≥ 90%, 14-day average",
            unit="hour",
            minimum=0,
            maximum=24,
            step=0.5,
            default=6,
        ),
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
        crop="soybean-stages",
        first="R3",
        last="R6",
        source="Provisional: CPN (symptoms from beginning seed set)",
        note="The fit is unpublished and its author gave no risk period: confirm with Webster.",
    ),
    ingredients=(
        Ingredient(name="air_temperature_min_5_day", unit="degC"),
        Ingredient(name="dew_point_depression_mean_5_day", unit="delta_degC"),
        Ingredient(name="dew_point_depression_max_5_day", unit="delta_degC"),
        Ingredient(name="wind_speed_max_14_day", unit="m_s"),
        Ingredient(name="hours_rh_over_90_10_day", unit="hour"),
        Ingredient(name="hours_rh_over_90_14_day", unit="hour"),
    ),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
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


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "air_temperature_min_5_day": moving_mean(inputs["air_temperature_min"], 5),
        "dew_point_depression_mean_5_day": moving_mean(inputs["dew_point_depression_mean"], 5),
        "dew_point_depression_max_5_day": moving_mean(inputs["dew_point_depression_max"], 5),
        "wind_speed_max_14_day": moving_mean(inputs["wind_speed_max"], 14),
        "hours_rh_over_90_10_day": moving_mean(inputs["hours_rh_over_90"], 10),
        "hours_rh_over_90_14_day": moving_mean(inputs["hours_rh_over_90"], 14),
    }


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    return probabilities(*(values[i.name] for i in SPEC.ingredients))


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
    """The highest of the three species' levels. A species whose inputs are missing for a whole window is left out
    (`fmax`), so the level is at least what the others say rather than unknown; it's NaN only if all three are."""
    return np.fmax.reduce([risk_level(outputs[name], *thresholds) for name, (_, thresholds) in SPECIES.items()])


def explore(**values: float) -> dict[str, float]:
    return {name: float(p) for name, p in probabilities(**values).items()}
