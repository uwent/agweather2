"""Cotton planting risk: the probability that the emerged stand falls below a yield-limiting population.

Zachary Noel's model (Auburn University, for Cotton Incorporated; as given to the Crop Risk Tool): each day is a
possible planting date, and the proportion of seed that emerges is a logistic function of Pythium presence, the year,
the rain over the 3 days from planting and the mean minimum temperature over the 9 days from planting. The fit's
variance–covariance matrix gives the prediction a standard error (the delta method on the response scale); with
emergence taken as normal, the risk is the probability that planting population × emergence falls below the
limiting population. Risk levels: Very low below 1%, Low from 1%, Moderate from 20%, High from 35%.

Ported from the Crop Risk Tool (`cotton_planting_model`, `build_cotton_planting`) with parity tests. Intended
difference: where the series ends before a window does (the tool's forward windows shrink there), or rain is
missing in it, there's no value; with the forecast (Phase 4) the windows reach 9 days ahead. Open: the year term
(0.0112 a year) extrapolates the fit's trend to later years; ask Noel which years it was fitted on. Southern,
beta.
"""

import math
from collections.abc import Mapping

import numpy as np

from agmodels.crops import number_option
from agmodels.ingredients import Ingredient, finished
from agmodels.probability import logistic, risk_level
from agmodels.spec import PROBABILITY_LEVELS, Change, Citation, ExplorerInput, Input, ModelSpec, Option, Quantity, Risk

RAIN_DAYS, COLD_DAYS = 3, 9
COEFFICIENTS = (-22.4611, -0.3359, 0.01118, -0.00750, 0.03929)  # intercept, Pythium, year, rain (mm), min temp (°C)
COVARIANCE = np.array(
    [
        [89.9570756007, 9.339412e-04, -4.501716e-02, 1.145290e-03, 2.718934e-02],
        [9.339412e-04, 2.248671e-02, -1.077674e-05, -2.326803e-05, 1.823261e-05],
        [-4.501716e-02, -1.077674e-05, 2.253921e-05, -6.018538e-07, -1.454077e-05],
        [1.145290e-03, -2.326803e-05, -6.018538e-07, 4.905222e-06, 1.451229e-06],
        [2.718934e-02, 1.823261e-05, -1.454077e-05, 1.451229e-06, 1.518877e-04],
    ]
)
COTTON_STATES = ("AL", "AR", "AZ", "CA", "FL", "GA", "KS", "LA", "MO", "MS", "NC", "NM", "OK", "SC", "TN", "TX", "VA")

PYTHIUM = Option(
    name="pythium", label="Pythium", choices=(("present", "Present"), ("absent", "Absent")), default="present"
)
PLANTING = Option(
    name="planting_population",
    label="Seeding rate (seeds per acre)",
    choices=tuple((str(n), f"{n:,}") for n in (30000, 40000, 50000)),
    default="40000",
)
LIMITING = Option(
    name="limiting_population",
    label="Yield-limiting stand (plants per acre)",
    choices=(("15000", "15,000"), ("20000", "20,000")),
    default="15000",
)

SPEC = ModelSpec(
    id="cotton-planting",
    name="Cotton planting stand risk",
    group="agronomic",
    version="0.1",
    status="beta",
    summary="For each possible planting date, the probability that the emerged cotton stand falls below a "
    "yield-limiting population, from the rain over the next 3 days and the minimum temperatures over the next 9.",
    topics=("cotton-stand-establishment",),
    crops=("Cotton",),
    citations=(
        Citation(
            text="Zachary Noel (Auburn University), with funding from Cotton Incorporated, as in the Crop Risk Tool."
        ),
        Citation(
            text="Adams, C., Thapa, S. and Kimura, E. (2019). Determination of a plant population density threshold "
            "for optimizing cotton lint yield: a synthesis. Field Crops Research 230, 11–16.",
            doi="10.1016/j.fcr.2018.10.005",
        ),
        Citation(
            text="Rothrock, C. S., Winters, S. A., Miller, P. K., et al. (2012). Importance of fungicide seed "
            "treatment and environment on seedling diseases of cotton. Plant Disease 96, 1805–1817.",
            doi="10.1094/PDIS-01-12-0031-SR",
        ),
    ),
    inputs=(
        Input(
            name="precipitation_sum",
            label="Precipitation",
            unit="mm",
            description="Total over the 3 days from planting",
        ),
        Input(
            name="air_temperature_min",
            label="Minimum temperature",
            unit="degC",
            description="Mean over the 9 days from planting",
        ),
    ),
    outputs=(
        Quantity(name="probability", label="Probability of a stand below the limit", unit="percent"),
        Quantity(name="emergence", label="Predicted emergence", unit="percent"),
    ),
    risk=Risk(levels=PROBABILITY_LEVELS, criteria="Very low below 1%, Low from 1%, Moderate from 20%, High from 35%."),
    explorer=(
        ExplorerInput(
            name="rain_3day",
            label="Rain over the 3 days from planting",
            unit="mm",
            minimum=0,
            maximum=100,
            step=1,
            default=10,
        ),
        ExplorerInput(
            name="min_temp_9day",
            label="Mean minimum temperature over the 9 days from planting",
            unit="degC",
            minimum=0,
            maximum=30,
            step=0.5,
            default=15,
        ),
    ),
    sweep={
        "rain_3day": tuple(float(r) for r in range(0, 61, 5)),
        "min_temp_9day": tuple(float(t) for t in range(0, 26)),
    },
    options=(PYTHIUM, PLANTING, LIMITING),
    context=("year",),
    region=COTTON_STATES,
    season=("03-15", "06-30"),
    ingredients=(
        Ingredient(name="precipitation_3_day_ahead", unit="mm", description="The planting day and the two after"),
        Ingredient(name="air_temperature_min_9_day_ahead", unit="degC", description="The planting day and the 8 after"),
    ),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),),
)


def probability_below(rain_3day, min_temp_9day, pythium, planting, limiting, year):
    """Noel's model: (probability the stand is below `limiting`, predicted emergence), both as fractions."""
    x = np.broadcast_arrays(*(np.asarray(v, dtype=float) for v in (1.0, pythium, year, rain_3day, min_temp_9day)))
    x = np.stack(x, axis=-1)
    emergence = logistic(x @ np.array(COEFFICIENTS))
    # Delta method: g = p(1 − p)·x, so var = p²(1 − p)² · xᵀΣx and se = p(1 − p)·√(xᵀΣx)
    se = emergence * (1 - emergence) * np.sqrt(np.einsum("...i,ij,...j->...", x, COVARIANCE, x))
    sd = np.asarray(planting, dtype=float) * se  # the CI's half-width over 1.96, on the plants scale
    z = (np.asarray(limiting, dtype=float) - emergence * planting) / sd
    return _normal_cdf(z), emergence


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "precipitation_3_day_ahead": _forward(inputs["precipitation_sum"], RAIN_DAYS, np.sum),
        "air_temperature_min_9_day_ahead": _forward(inputs["air_temperature_min"], COLD_DAYS, _mean_of_present),
    }


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    rain, cold = values["precipitation_3_day_ahead"], values["air_temperature_min_9_day_ahead"]
    year = np.asarray(values["year"], dtype=float).reshape((-1,) + (1,) * (rain.ndim - 1))
    pythium = 1.0 if options.get(PYTHIUM.name, PYTHIUM.default) == "present" else 0.0
    p, emergence = probability_below(
        rain, cold, pythium, number_option(options, PLANTING), number_option(options, LIMITING), year
    )
    return {"probability": p * 100, "emergence": emergence * 100}


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
    return risk_level(np.asarray(outputs["probability"], dtype=float) / 100, 1, 20, 35)


def explore(rain_3day: float, min_temp_9day: float) -> dict[str, float]:
    p, emergence = probability_below(rain_3day, min_temp_9day, 1.0, 40000, 15000, 2025)
    return {"probability": float(p) * 100, "emergence": float(emergence) * 100}


def _forward(values, days: int, reduce) -> np.ndarray:
    """Each day's window of `days` days from it (NaN where the series ends first)."""
    v = np.asarray(values, dtype=float)
    out = np.full(v.shape, np.nan)
    for d in range(v.shape[0] - days + 1):
        out[d] = reduce(v[d : d + days], axis=0)
    return out


def _mean_of_present(window: np.ndarray, axis: int = 0) -> np.ndarray:
    count = np.isfinite(window).sum(axis=axis)
    with np.errstate(invalid="ignore"):
        return np.where(count > 0, np.nansum(window, axis=axis) / np.maximum(count, 1), np.nan)


_normal_cdf = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))) if math.isfinite(z) else math.nan)
