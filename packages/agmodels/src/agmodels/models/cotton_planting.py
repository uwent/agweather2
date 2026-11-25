"""Cotton planting: the predicted emerged stand for each planting date, against a yield-limiting population.

Zachary Noel's model (Auburn University, for Cotton Incorporated; as given to the Crop Risk Tool): each day is a
possible planting date, and the proportion of seed that emerges is a logistic function of Pythium presence, the year,
the rain over the 3 days from planting and the mean minimum temperature over the 9 days from planting. The fit's
variance–covariance matrix gives the prediction a standard error (the delta method on the response scale), and so a
95% confidence interval of the mean emergence. The outputs are the predicted stand (emergence × seeding rate, plants
per acre) and that interval; risk compares the predicted stand with the limiting population: High below it,
Moderate within 25% above it, Low otherwise.

Ported from the Crop Risk Tool (`cotton_planting_model`, `build_cotton_planting`) with parity tests of the
emergence model through the tool's probability (`probability_below`). Intended differences: where the series ends
before a window does (the tool's forward windows shrink there), rain is missing in it, or fewer than 7 of its 9
minimum temperatures are known, there's no value; with the forecast (Phase 4) the windows reach 9 days ahead.

0.2 (audit round 2, `tmp/crt-model-audit-2-cotton-pecan-rye.md`): the tool's risk, the probability that the stand
falls below the limit, comes from the standard error of the *mean* emergence, not the spread of stands between
fields, so it is nearly all-or-nothing and set by the options rather than the weather. Until the beta regression's
precision φ comes from the authors (then the beta predictive distribution gives a field-level probability), the
model shows the predicted stand and its interval instead, and the year term is held at LAST_FIT_YEAR. No
seed-treatment option yet (the authors' documents disagree on whether the fit has a term for it). Southern, beta.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.crops import number_option
from agmodels.ingredients import Ingredient, finished
from agmodels.normal import normal_cdf
from agmodels.probability import logistic
from agmodels.spec import (
    Change,
    Check,
    Citation,
    ExplorerInput,
    Input,
    ModelSpec,
    Option,
    Quantity,
    Risk,
)

RAIN_DAYS, COLD_DAYS = 3, 9
MIN_COLD_DAYS = 7  # minimum temperatures needed of the 9 for a mean (the gaps rule: a mostly missing window is missing)
# The fit's last year: the year term (0.0112 a year on the logit scale) isn't carried past it. Provisional: the
# authors haven't said which years the fit covers (the covariance centres it near 2006); 2025 is the last full season
# their March 2026 document could have used.
LAST_FIT_YEAR = 2025
Z_95 = 1.959964  # the authors' 95% interval
MODERATE_MARGIN = 1.25  # Moderate: a predicted stand within 25% above the limit
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
    version="0.2",
    checks=(
        Check(
            kind="system",
            against="The Crop Risk Tool's cotton stand model, which AgWeather replaces",
            result="Our emergence model and its uncertainty reproduce the tool's results in all 2,704 combinations of rain, temperature, Pythium, seeding rate and year tested, and on 357 planting dates through 2025. This shows that we reproduce the tool; the model hasn't been compared with stands counted in the field.",
            report="docs/validation/models/cotton-planting.md#against-the-crop-risk-tool",
        ),
    ),
    status="beta",
    summary="For each possible planting date, the predicted emerged cotton stand in plants per acre, with its 95% confidence interval, from the rain over the next 3 days and the minimum temperatures over the next 9, compared with a yield-limiting stand.",
    topics=("cotton-stand-establishment",),
    crops=("cotton",),
    citations=(
        Citation(
            text="Zachary Noel (Auburn University), with funding from Cotton Incorporated, as in the Crop Risk Tool."
        ),
        Citation(
            text="Adams, C., Thapa, S. and Kimura, E. (2019). Determination of a plant population density threshold for optimizing cotton lint yield: a synthesis. Field Crops Research 230, 11–16.",
            doi="10.1016/j.fcr.2018.10.005",
        ),
        Citation(
            text="Rothrock, C. S., Winters, S. A., Miller, P. K., et al. (2012). Importance of fungicide seed treatment and environment on seedling diseases of cotton. Plant Disease 96, 1805–1817.",
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
        Quantity(name="stand", label="Predicted stand", unit="plants_ac"),
        Quantity(
            name="stand_low",
            label="Predicted stand, low end",
            unit="plants_ac",
            description="Lower end of the 95% confidence interval of the predicted stand",
        ),
        Quantity(
            name="stand_high",
            label="Predicted stand, high end",
            unit="plants_ac",
            description="Upper end of the 95% confidence interval of the predicted stand",
        ),
        Quantity(name="emergence", label="Predicted emergence", unit="percent"),
    ),
    risk=Risk(
        levels=("Low", "Moderate", "High"),
        criteria="The predicted stand against the yield-limiting stand: High below it, Moderate from it to less than 25% above it, Low from 25% above it.",
    ),
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
        Ingredient(
            name="precipitation_3_day_ahead",
            unit="mm",
            description="The planting day and the two after",
            ahead_days=RAIN_DAYS - 1,
        ),
        Ingredient(
            name="air_temperature_min_9_day_ahead",
            unit="degC",
            description="The planting day and the 8 after",
            ahead_days=COLD_DAYS - 1,
        ),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),
        Change(
            version="0.2",
            date="2026-11-19",
            note="The predicted stand and its 95% confidence interval replace the probability of a stand below the limit, which measured the uncertainty of the mean emergence rather than the spread between fields; risk is the predicted stand against the limit (High below it, Moderate within 25% above it). The year term is held at 2025, and the 9-day mean needs 7 of its minimum temperatures.",
        ),
    ),
)


def emergence_interval(rain_3day, min_temp_9day, pythium, year):
    """Noel's model: (predicted emergence, its 95% confidence interval's low and high ends), as fractions."""
    emergence, se = _emergence_and_error(rain_3day=rain_3day, min_temp_9day=min_temp_9day, pythium=pythium, year=year)
    return emergence, np.clip(emergence - Z_95 * se, 0, 1), np.clip(emergence + Z_95 * se, 0, 1)


def probability_below(rain_3day, min_temp_9day, pythium, planting, limiting, year):
    """The Crop Risk Tool's risk, kept for the parity tests and not shown: (the probability that the stand is below
    `limiting`, predicted emergence), both as fractions, with emergence taken as normal around the prediction with the
    standard error of the mean. It measures how sure the fit is of the mean stand, not how stands vary between fields
    (audit round 2), so it is near 0 or 1 almost everywhere."""
    emergence, se = _emergence_and_error(rain_3day=rain_3day, min_temp_9day=min_temp_9day, pythium=pythium, year=year)
    sd = np.asarray(planting, dtype=float) * se  # the CI's half-width over 1.96, on the plants scale
    z = (np.asarray(limiting, dtype=float) - emergence * planting) / sd
    return normal_cdf(z), emergence


def _emergence_and_error(rain_3day, min_temp_9day, pythium, year) -> tuple[np.ndarray, np.ndarray]:
    """Predicted emergence and its standard error (the delta method on the response scale), as fractions."""
    x = np.broadcast_arrays(*(np.asarray(v, dtype=float) for v in (1.0, pythium, year, rain_3day, min_temp_9day)))
    x = np.stack(x, axis=-1)
    emergence = logistic(x @ np.array(COEFFICIENTS))
    # g = p(1 − p)·x, so var = p²(1 − p)² · xᵀΣx and se = p(1 − p)·√(xᵀΣx)
    se = emergence * (1 - emergence) * np.sqrt(np.einsum("...i,ij,...j->...", x, COVARIANCE, x))
    return emergence, se


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "precipitation_3_day_ahead": _forward(inputs["precipitation_sum"], RAIN_DAYS, np.sum),
        "air_temperature_min_9_day_ahead": _forward(inputs["air_temperature_min"], COLD_DAYS, _mean_of_present),
    }


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    rain, cold = values["precipitation_3_day_ahead"], values["air_temperature_min_9_day_ahead"]
    year = np.minimum(np.asarray(values["year"], dtype=float), LAST_FIT_YEAR)
    year = year.reshape((-1,) + (1,) * (rain.ndim - 1))
    pythium = 1.0 if options.get(PYTHIUM.name, PYTHIUM.default) == "present" else 0.0
    return _stands(rain=rain, cold=cold, pythium=pythium, planting=number_option(options, PLANTING), year=year)


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
    """High (2) where the predicted stand is below the limit, Moderate (1) up to 25% above it, Low (0) beyond."""
    stand = np.asarray(outputs["stand"], dtype=float)
    limit = number_option(options, LIMITING)
    level = (stand < MODERATE_MARGIN * limit).astype(float) + (stand < limit)
    return np.where(np.isnan(stand), np.nan, level)


def explore(rain_3day: float, min_temp_9day: float) -> dict[str, float]:
    """With Pythium present, 40,000 seeds per acre and the year at LAST_FIT_YEAR."""
    found = _stands(
        rain=rain_3day, cold=min_temp_9day, pythium=1.0, planting=float(PLANTING.default), year=LAST_FIT_YEAR
    )
    return {name: float(v) for name, v in found.items()}


def _stands(rain, cold, pythium: float, planting: float, year) -> dict[str, np.ndarray]:
    emergence, low, high = emergence_interval(rain_3day=rain, min_temp_9day=cold, pythium=pythium, year=year)
    return {
        "stand": emergence * planting,
        "stand_low": low * planting,
        "stand_high": high * planting,
        "emergence": emergence * 100,
    }


def _forward(values, days: int, reduce) -> np.ndarray:
    """Each day's window of `days` days from it (NaN where the series ends first)."""
    v = np.asarray(values, dtype=float)
    out = np.full(v.shape, np.nan)
    for d in range(v.shape[0] - days + 1):
        out[d] = reduce(v[d : d + days], axis=0)
    return out


def _mean_of_present(window: np.ndarray, axis: int = 0) -> np.ndarray:
    """The mean of the days with values, if at least MIN_COLD_DAYS have them (else NaN)."""
    count = np.isfinite(window).sum(axis=axis)
    with np.errstate(invalid="ignore"):
        return np.where(count >= MIN_COLD_DAYS, np.nansum(window, axis=axis) / np.maximum(count, 1), np.nan)
