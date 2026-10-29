"""Red crown rot of soybean: predicted field-level incidence (beta).

Ochi et al. (2026) fitted logistic models of field-level incidence to weather around the beginning of flowering
(R1): mean temperature over the 31 days from R1 and precipitation over the 31 days before and after it. Their
ensemble weighs each by its R² (0.66, 0.16, 0.18). Until the 31 days from R1 are complete, the running mean
temperature is used and precipitation is prorated to a full window, as the Crop Risk Tool does; after, the final
values hold. The biofix is the R1 date.

Ported from the Crop Risk Tool (`predict_red_crown_rot`, `build_red_crown_rot`) with parity tests.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.probability import risk_level
from agmodels.spec import (
    PROBABILITY_LEVELS,
    Biofix,
    Change,
    Citation,
    ExplorerInput,
    ModelSpec,
    Quantity,
    Risk,
)

WINDOW = 31

SPEC = ModelSpec(
    id="red-crown-rot",
    name="Red crown rot incidence",
    group="disease",
    version="1.0",
    status="beta",
    summary="Predicted share of soybean plants with red crown rot, from temperature and rain in the month either "
    "side of the beginning of flowering (R1).",
    topics=("red-crown-rot",),
    crops=("Soybean",),
    citations=(
        Citation(
            text="Ochi, S., Kishi, S., Kawaguchi, A. and Akamatsu, H. (2026). Meteorological and agronomic factors "
            "analysis on the field-level incidence of red crown rot of soybean. Phytopathology 116, 1405–1413.",
            doi="10.1094/PHYTO-06-25-0207-R",
        ),
        Citation(
            text="Crop Protection Network: Red crown rot of soybean.",
            url="https://cropprotectionnetwork.org/encyclopedia/red-crown-rot-of-soybean",
        ),
    ),
    inputs=(
        Quantity(
            name="air_temperature_mean",
            label="Mean temperature",
            unit="degC",
            description="Mean over the 31 days from R1",
        ),
        Quantity(
            name="precipitation_sum",
            label="Precipitation",
            unit="mm",
            description="Totals over the 31 days before and from R1",
        ),
    ),
    outputs=(
        Quantity(name="incidence", label="Predicted incidence", unit="percent"),
        Quantity(name="temperature_mean_reproductive", label="Mean temperature from R1", unit="degC"),
        Quantity(name="precipitation_vegetative", label="Precipitation, 31 days before R1", unit="mm"),
        Quantity(name="precipitation_reproductive", label="Precipitation from R1 (prorated to 31 days)", unit="mm"),
    ),
    risk=Risk(
        levels=PROBABILITY_LEVELS,
        criteria="Provisional: Very low below 5%, Low from 5%, Moderate from 30%, High from 60%.",
    ),
    explorer=(
        ExplorerInput(
            name="temperature_reproductive",
            label="Mean temperature, 31 days from R1",
            unit="degC",
            minimum=15,
            maximum=35,
            step=0.5,
            default=25,
        ),
        ExplorerInput(
            name="precipitation_vegetative",
            label="Precipitation, 31 days before R1",
            unit="mm",
            minimum=0,
            maximum=400,
            step=5,
            default=100,
        ),
        ExplorerInput(
            name="precipitation_reproductive",
            label="Precipitation, 31 days from R1",
            unit="mm",
            minimum=0,
            maximum=400,
            step=5,
            default=100,
        ),
    ),
    sweep={
        "temperature_reproductive": (20.0, 24.0, 28.0),
        "precipitation_vegetative": (25.0, 100.0, 250.0),
        "precipitation_reproductive": (25.0, 100.0, 250.0),
    },
    lookback_days=WINDOW,
    biofix=Biofix(default="07-01", label="R1 (beginning flowering)"),
    biofix_stage=("soybean-stages", "R1"),  # the soybean model's R1 is the default when it has run
    changelog=(Change(version="1.0", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
)


def incidence(temperature_reproductive, precipitation_vegetative, precipitation_reproductive) -> np.ndarray:
    def fli(logit):
        return 1 / (1 + np.exp(np.asarray(logit, dtype=float)))

    return (
        0.66 * fli(15.067 - 0.602 * np.asarray(temperature_reproductive, dtype=float))
        + 0.16 * fli(0.184 - 0.004 * np.asarray(precipitation_vegetative, dtype=float))
        + 0.18 * fli(-1.257 + 0.005 * np.asarray(precipitation_reproductive, dtype=float))
    )


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    temperature = np.asarray(inputs["air_temperature_mean"], dtype=float)
    precip = np.asarray(inputs["precipitation_sum"], dtype=float)
    n = temperature.shape[0]
    day = np.arange(n).reshape(-1, *([1] * (temperature.ndim - 1)))
    r1, veg_start = biofix_index, max(0, biofix_index - WINDOW)
    in_veg = (day >= veg_start) & (day < r1)
    in_rep = (day >= r1) & (day < r1 + WINDOW)

    with np.errstate(invalid="ignore"):
        veg_days = precip[veg_start:r1]
        veg_total = np.nanmean(veg_days, axis=0) * WINDOW if veg_days.shape[0] else np.full(precip.shape[1:], np.nan)
    veg_running = np.cumsum(np.where(in_veg, np.nan_to_num(precip), 0), axis=0)
    precipitation_vegetative = np.where(day < veg_start, np.nan, np.where(in_veg, veg_running, veg_total))

    temperature_rep = _cumulative_mean(np.where(in_rep, temperature, np.nan))
    precipitation_rep = _cumulative_mean(np.where(in_rep, precip, np.nan)) * WINDOW
    return {
        "incidence": incidence(temperature_rep, veg_total, precipitation_rep),
        "temperature_mean_reproductive": temperature_rep,
        "precipitation_vegetative": precipitation_vegetative,
        "precipitation_reproductive": precipitation_rep,
    }


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return risk_level(outputs["incidence"], 5, 30, 60)


def explore(temperature_reproductive: float, precipitation_vegetative: float, precipitation_reproductive: float):
    return {
        "incidence": float(incidence(temperature_reproductive, precipitation_vegetative, precipitation_reproductive))
    }


def _cumulative_mean(values: np.ndarray) -> np.ndarray:
    """Mean of the values so far, NaN until the first (the tool's `cummean_na`)."""
    count = np.cumsum(np.isfinite(values), axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, np.cumsum(np.nan_to_num(values), axis=0) / count, np.nan)
