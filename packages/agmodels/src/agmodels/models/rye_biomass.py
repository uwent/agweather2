"""Winter (cereal) rye cover crop biomass in spring, from growing degree days since fall planting.

A logistic growth fit (unpublished, trained on Wisconsin data; as in the Crop Risk Tool's `predict_rye_biomass`):
biomass (lb/ac) = ((423.1 − 1.031 × planting day − 0.2878 × fall precip) / (1 + exp(−0.003663 (GDD − 1049))))², with
GDD single sine above 0 °C, capped at 35 °C, since planting, and fall precip (mm) from planting through December 31.
Later planting and a wetter fall mean less biomass in spring. Levels by cover crop goals (UW–Madison Extension):
Low below 2000 lb/ac (some nitrate leaching reduction), Moderate from 2000 (erosion, runoff P and nitrate), High
from 4500 (weed suppression too).

Ported from the Crop Risk Tool (`build_rye_biomass`) with parity tests. Intended difference: v2's sine GDD apply the
35 °C cutoff on every day (the tool's `gdd_sine` skips it when the minimum is above the base, D3's finding), which
only changes days over 35 °C. Beta, Upper Midwest.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import running_total
from agmodels.degree_days import degree_days_sine
from agmodels.lookup import level_reached
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk

BASE_C, UPPER_C = 0.0, 35.0
B0, B_PLANTING, B_FALL_PRECIP, K, X0 = 423.1, -1.031, -0.2878, 0.003663, 1049.0
LEVELS_LB_AC = (2000, 4500)

SPEC = ModelSpec(
    id="rye-biomass",
    name="Winter rye cover crop biomass",
    group="agronomic",
    version="1.0",
    status="beta",
    summary="Spring biomass of a fall-planted cereal rye cover crop, from growing degree days (base 0 °C) since "
    "planting, the planting date and fall precipitation, against the biomass cover crop goals need.",
    topics=("cereal-rye-cover-crop",),
    crops=("Rye",),
    citations=(
        Citation("Unpublished logistic growth fit on Wisconsin data, as in the Crop Risk Tool."),
        Citation(
            "UW–Madison Extension: Biomass thresholds for cereal rye cover crop goals.",
            "https://cropsandsoils.extension.wisc.edu/articles/biomass-thresholds-for-cereal-rye-cover-crop-goals/",
        ),
        Citation(
            "Badger Crop Network: How much cereal rye cover crop biomass is needed to suppress troublesome weeds in "
            "Wisconsin?",
            "https://badgercropnetwork.com/how-much-cereal-rye-cover-crop-biomass-is-needed-to-suppress-troublesome-weeds-in-wisconsin/",
        ),
    ),
    inputs=(
        Quantity("air_temperature_min", "Minimum temperature", "degC"),
        Quantity("air_temperature_max", "Maximum temperature", "degC"),
        Quantity("precipitation_sum", "Precipitation", "mm", "From planting through December 31"),
    ),
    outputs=(
        Quantity("biomass", "Predicted biomass", "lb_ac"),
        Quantity("gdd_total", "GDD (0/35 °C) since planting", "degC_day"),
        Quantity("precipitation_fall", "Precipitation from planting through December 31", "mm"),
    ),
    risk=Risk(
        ("Low", "Moderate", "High"),
        "Biomass: Low below 2,000 lb/ac (modest nitrate leaching reduction), Moderate from 2,000 (erosion, runoff "
        "phosphorus and nitrate), High from 4,500 (weed suppression as well).",
    ),
    explorer=(
        ExplorerInput("gdd_total", "GDD (0/35 °C) since planting", "degC_day", 0, 3000, 10, 1200),
        ExplorerInput("planting_day", "Planting day of year", "day", 230, 330, 1, 274),
        ExplorerInput("precipitation_fall", "Precipitation from planting through December 31", "mm", 0, 400, 5, 100),
    ),
    sweep={
        "gdd_total": tuple(float(g) for g in range(0, 3001, 100)),
        "planting_day": (250.0, 280.0, 310.0),
        "precipitation_fall": (0.0, 100.0, 300.0),
    },
    context=("day_of_year",),
    region=("WI", "MN", "IA", "IL", "MI"),
    season=("09-01", "06-30"),
    biofix=Biofix("10-01", "Fall planting date"),
    changelog=(Change("1.0", "2026-10-28", "Ported from the Crop Risk Tool."),),
)


def biomass(gdd_total, planting_day, precipitation_fall) -> np.ndarray:
    g, d, p = (np.asarray(x, dtype=float) for x in (gdd_total, planting_day, precipitation_fall))
    return ((B0 + B_PLANTING * d + B_FALL_PRECIP * p) / (1 + np.exp(-K * (g - X0)))) ** 2


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) for k in ("air_temperature_min", "air_temperature_max"))
    gdd_total = running_total(degree_days_sine(lo, hi, BASE_C, UPPER_C), biofix_index)
    doy = np.asarray(inputs["day_of_year"], dtype=float)
    planting_day = doy[biofix_index] if doy.size > biofix_index else np.nan
    # Fall precip: planting through December 31, the days before the day of year first falls back (January 1)
    new_year = np.flatnonzero(np.diff(doy[biofix_index:]) < 0)
    fall_end = biofix_index + int(new_year[0]) + 1 if new_year.size else doy.size
    precip = np.array(inputs["precipitation_sum"], dtype=float)
    precip[fall_end:] = 0.0
    fall = running_total(precip, biofix_index)
    return {"biomass": biomass(gdd_total, planting_day, fall), "gdd_total": gdd_total, "precipitation_fall": fall}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return level_reached(outputs["biomass"], *LEVELS_LB_AC)


def explore(gdd_total: float, planting_day: float, precipitation_fall: float) -> dict[str, float]:
    value = biomass(gdd_total, planting_day, precipitation_fall)
    return {"biomass": float(value), "level": float(level_reached(value, *LEVELS_LB_AC))}
