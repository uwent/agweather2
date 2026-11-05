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

from agmodels.degree_days import degree_days_sine
from agmodels.ingredients import Accumulation, DegreeDays, Ingredient, finished
from agmodels.lookup import level_reached
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, Input, ModelSpec, Quantity, Risk

BASE_C, UPPER_C = 0.0, 35.0
B0, B_PLANTING, B_FALL_PRECIP, K, X0 = 423.1, -1.031, -0.2878, 0.003663, 1049.0
LEVELS_LB_AC = (2000, 4500)

SPEC = ModelSpec(
    id="rye-biomass",
    name="Winter rye cover crop biomass",
    group="agronomic",
    version="0.2",
    status="beta",
    summary="Spring biomass of a fall-planted cereal rye cover crop, from growing degree days (base 0 °C) since "
    "planting, the planting date and fall precipitation, against the biomass cover crop goals need.",
    topics=("cereal-rye-cover-crop",),
    crops=("Rye",),
    citations=(
        Citation(text="Unpublished logistic growth fit on Wisconsin data, as in the Crop Risk Tool."),
        Citation(
            text="UW–Madison Extension: Biomass thresholds for cereal rye cover crop goals.",
            url="https://cropsandsoils.extension.wisc.edu/articles/biomass-thresholds-for-cereal-rye-cover-crop-goals/",
        ),
        Citation(
            text="Badger Crop Network: How much cereal rye cover crop biomass is needed to suppress troublesome weeds "
            "in Wisconsin?",
            url="https://badgercropnetwork.com/how-much-cereal-rye-cover-crop-biomass-is-needed-to-suppress-troublesome-weeds-in-wisconsin/",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
        Input(
            name="precipitation_sum", label="Precipitation", unit="mm", description="From planting through December 31"
        ),
    ),
    outputs=(
        Quantity(name="biomass", label="Predicted biomass", unit="lb_ac"),
        Quantity(name="gdd_total", label="GDD (0/35 °C) since planting", unit="degC_day"),
        Quantity(name="precipitation_fall", label="Precipitation from planting through December 31", unit="mm"),
    ),
    risk=Risk(
        levels=("Low", "Moderate", "High"),
        criteria="Biomass: Low below 2,000 lb/ac (modest nitrate leaching reduction), Moderate from 2,000 (erosion, "
        "runoff phosphorus and nitrate), High from 4,500 (weed suppression as well).",
    ),
    explorer=(
        ExplorerInput(
            name="gdd_total",
            label="GDD (0/35 °C) since planting",
            unit="degC_day",
            minimum=0,
            maximum=3000,
            step=10,
            default=1200,
        ),
        ExplorerInput(
            name="planting_day", label="Planting day of year", unit="day", minimum=230, maximum=330, step=1, default=274
        ),
        ExplorerInput(
            name="precipitation_fall",
            label="Precipitation from planting through December 31",
            unit="mm",
            minimum=0,
            maximum=400,
            step=5,
            default=100,
        ),
    ),
    explorer_outputs=(
        Quantity(name="level", label="Biomass level", unit="index", description="Index into the risk levels"),
    ),
    sweep={
        "gdd_total": tuple(float(g) for g in range(0, 3001, 100)),
        "planting_day": (250.0, 280.0, 310.0),
        "precipitation_fall": (0.0, 100.0, 300.0),
    },
    context=("day_of_year",),
    region=("WI", "MN", "IA", "IL", "MI"),
    season=("09-01", "06-30"),
    biofix=Biofix(default="10-01", label="Fall planting date"),
    ingredients=(
        Ingredient(name="gdd", unit="degC_day", degree_days=DegreeDays(method="sine", base_f=32, upper_f=95)),
        Ingredient(name="precipitation", unit="mm", cumulative="precipitation"),
    ),
    accumulations=(
        Accumulation(name="gdd_total", of="gdd"),
        Accumulation(name="precipitation_fall", of="precipitation", until="12-31"),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),
        Change(
            version="0.2",
            date="2026-11-01",
            note="Biomass is 0 where the fit's linear term goes negative (a late planting after a very wet fall); "
            "squaring it had made biomass rise again with more rain.",
        ),
    ),
)


def biomass(gdd_total, planting_day, precipitation_fall) -> np.ndarray:
    """Spring biomass (lb/ac): the square of a logistic in GDD whose height falls with later planting and wetter
    falls; held at 0 once that height reaches 0 (squaring a negative one would make biomass rise again)."""
    g, d, p = (np.asarray(x, dtype=float) for x in (gdd_total, planting_day, precipitation_fall))
    height = np.maximum(B0 + B_PLANTING * d + B_FALL_PRECIP * p, 0.0)
    return (height / (1 + np.exp(-K * (g - X0)))) ** 2


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) for k in ("air_temperature_min", "air_temperature_max"))
    return {
        "gdd": degree_days_sine(lo, hi, BASE_C, UPPER_C),
        "precipitation": np.asarray(inputs["precipitation_sum"], dtype=float),
    }


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    """Biomass from the GDD and fall rain (planting through December 31) since planting, and its day of year."""
    gdd_total, fall = values["gdd_total"], values["precipitation_fall"]
    return {
        "biomass": biomass(gdd_total, values["biofix_day_of_year"], fall),
        "gdd_total": gdd_total,
        "precipitation_fall": fall,
    }


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return finished(
        accumulations=SPEC.accumulations,
        values=ingredients(inputs),
        inputs=inputs,
        biofix_index=biofix_index,
        finish=finish,
        options=options,
    )


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return level_reached(outputs["biomass"], *LEVELS_LB_AC)


def explore(gdd_total: float, planting_day: float, precipitation_fall: float) -> dict[str, float]:
    value = biomass(gdd_total, planting_day, precipitation_fall)
    return {"biomass": float(value), "level": float(level_reached(value, *LEVELS_LB_AC))}
