"""Fusarium head blight (scab) of wheat: the probability of a severe epidemic for wheat flowering on the day.

Model M6 of the U.S. Fusarium head blight prediction models (Shah et al. 2013's model 3; M6 in Shah et al. 2021),
with the coefficients refit for 2026 by the model team (unpublished; "Wheat Scab Models Deployment 2026"): the
probability of severe head blight (field severity of 10 % or more) for wheat flowering on the day, from the mean RH
of the 14 days before (ending the day before flowering), shifted for four resistance classes.

Ported from the Crop Risk Tool (`predict_wheat_scab`, `build_wheat_scab`) with parity tests, then (0.2, audit round
2, `tmp/crt-model-audit-2-wheat-rcr.md`): shown May 1 to July 31 (the tool showed every day of the year, High on
winter days); the national FHB Risk Tool's three levels (Low below 24 %); the window ends the day before and needs
12 of its 14 days.

0.3: gated at a point by flowering (D33). The map isn't gated: it's the risk for wheat flowering on each day, as on
the national tool, for winter and spring wheat alike. At a point, a spring wheat planting date the user gives runs
`spring-wheat-stages` and shows the risk from heading (Haun 10.2) through 7 days after flowering begins (11.4; 0.4, Ben: Haun 11.6, the end of flowering, came only 2–3 days after its start); a flowering
date the user gives (`flowering_date`, the only gate for winter wheat, which has no stage model yet) replaces that
estimate and shows it from that day through 7 days after, the fungicide window from early flowering (Feekes 10.5.1).
Either way the gate is `susceptibility` beside the probability, which stays as computed: muted for 3 days either
side, greyed outside. A typical planting date is never assumed, since `wheat` covers winter wheat too.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import rolling_sum
from agmodels.ingredients import Ingredient, finished
from agmodels.probability import logistic, moving_mean, risk_level
from agmodels.spec import (
    PROBABILITY_LEVELS,
    Change,
    Check,
    Citation,
    ExplorerInput,
    Input,
    ModelSpec,
    Option,
    Quantity,
    Risk,
    StageDate,
    Susceptibility,
)

RESISTANCE = {  # option value: (label, intercept shift)
    "vs": ("Very susceptible", 0.0),
    "s": ("Susceptible", -0.82795556),
    "ms": ("Moderately susceptible", -1.4812696),
    "mr": ("Moderately resistant", -1.8484537),
}

SPEC = ModelSpec(
    id="wheat-scab",
    name="Wheat scab (Fusarium head blight) probability",
    group="disease",
    version="0.5",
    status="beta",
    summary="The probability of severe Fusarium head blight (scab) for wheat flowering on the day shown, from the mean humidity of the two weeks before, for the variety's resistance class.",
    topics=("wheat-scab",),
    crops=("wheat",),
    citations=(
        Citation(
            text="Shah, D. A., Molineros, J. E., Paul, P. A., Willyerd, K. T., Madden, L. V. and De Wolf, E. D. (2013). Predicting Fusarium head blight epidemics with weather-driven pre- and post-anthesis logistic regression models. Phytopathology 103, 906–919.",
            doi="10.1094/PHYTO-11-12-0304-R",
        ),
        Citation(
            text="Shah, D. A., De Wolf, E. D., Paul, P. A. and Madden, L. V. (2021). Accuracy in the prediction of disease epidemics when ensembling simple but highly correlated models. PLOS Computational Biology 17, e1008831.",
            doi="10.1371/journal.pcbi.1008831",
        ),
        Citation(
            text="The Fusarium head blight prediction model team: wheat scab models for deployment in 2026 (model M6, refit coefficients), as used by the Crop Risk Tool."
        ),
        Citation(
            text="Crop Protection Network: An overview of Fusarium head blight.",
            url="https://cropprotectionnetwork.org/publications/an-overview-of-fusarium-head-blight",
        ),
    ),
    inputs=(
        Input(name="relative_humidity_mean", label="Mean RH", unit="percent", description="Mean of the 14 days before"),
    ),
    outputs=(
        Quantity(
            name="probability", label="Probability of severe head blight, for the chosen resistance", unit="percent"
        ),
        *(Quantity(name=f"probability_{key}", label=label, unit="percent") for key, (label, _) in RESISTANCE.items()),
    ),
    risk=Risk(
        levels=PROBABILITY_LEVELS,
        criteria="Low below 24%, Moderate from 24%, High from 32% (the national FHB Risk Tool's levels).",
    ),
    explorer=(
        ExplorerInput(
            name="rh_mean_14day",
            label="Mean RH, 14-day average",
            unit="percent",
            minimum=40,
            maximum=100,
            step=1,
            default=80,
        ),
    ),
    sweep={"rh_mean_14day": (50.0, 60.0, 70.0, 80.0, 90.0, 100.0)},
    options=(
        Option(
            name="resistance",
            label="Cultivar resistance",
            choices=tuple((k, v[0]) for k, v in RESISTANCE.items()),
            default="s",
        ),
        Option(
            name="flowering_date",
            label="Date your wheat began flowering",
            choices=(),
            default="",
        ),
    ),
    susceptible=Susceptibility(
        crop="spring-wheat-stages",
        first="H10.2",
        last="H11.4",
        extend_days=7,
        source="Heading begins (Haun 10.2) through 7 days after flowering begins (Haun 11.4): the days before and at flowering for which the model's risk applies (Shah et al. 2013's prediction at anthesis), to the end of the fungicide window from early flowering (Feekes 10.5.1; Friskop et al. 2021, Smith 2022), as for a flowering date you give",
        note="For spring wheat, from a planting date you give. A flowering date you give, for winter or spring wheat, replaces it: the risk then shows from that day through 7 days after. Maps aren't gated: they show the risk for wheat flowering on each day.",
        planting_given_only=True,
        stage_date=StageDate(
            option="flowering_date",
            first=0,
            last=7,
            margin_days=3,
            source="The fungicide window, from the start of flowering (Feekes 10.5.1) to about 7 days after (Friskop et al. 2021, Crop Protection Network; Smith 2022, Wisconsin Crop Manager)",
        ),
    ),
    lookback_days=15,
    season=("05-01", "07-31"),
    ingredients=(Ingredient(name="relative_humidity_mean_14_day_lag_1", unit="percent"),),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),
        Change(
            version="0.2",
            date="2026-11-19",
            note="Cites Shah et al. 2013 and 2021 (model M6, refit for 2026); the probability of severe head blight for wheat flowering on the day; shown May 1 to July 31; Low below 24 % as in the national FHB Risk Tool; the 14-day window ends the day before and needs 12 known days.",
        ),
        Change(
            version="0.3",
            date="2026-11-19",
            note="Gated by flowering at a location: for spring wheat from a planting date you give (heading through the end of flowering, by the spring wheat stages model), or from a flowering date you give for any wheat (that day through 7 days after). Maps stay ungated, the risk for wheat flowering on each day. The probabilities are unchanged.",
        ),
        Change(
            version="0.4",
            date="2026-11-19",
            note="For spring wheat from a planting date, the window runs through 7 days after flowering begins (Haun 11.4), as for a flowering date you give, rather than ending at the end of flowering (Haun 11.6), which came only 2 to 3 days after its start.",
        ),
        Change(
            version="0.5",
            date="2026-11-26",
            note="The probabilities are given in percent (0 to 100), as their unit says, rather than as fractions (0 to 1). Risk levels are unchanged.",
        ),
    ),
    checks=(
        Check(
            kind="system",
            against="The Crop Risk Tool, which AgWeather's wheat scab model was ported from, on the tool's own 2025 weather for Eau Claire, Wisconsin",
            result="Given the tool's daily weather, our probability matched the tool's for each of the four resistance classes on every day from January 15, 2025, with our window of humidity ending the day before, as the model team's deployment document says. This shows that we reproduce the tool, not that its predictions are right: the model hasn't been compared with scab in fields.",
            report="docs/validation/models/wheat-scab.md#against-the-crop-risk-tool-on-the-same-weather",
        ),
    ),
)


def probabilities(rh_mean_14day) -> dict[str, np.ndarray]:
    rh = np.asarray(rh_mean_14day, dtype=float)
    return {
        f"probability_{key}": logistic(-3.6432643 + shift + 0.051459669 * rh) for key, (_, shift) in RESISTANCE.items()
    }


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "relative_humidity_mean_14_day_lag_1": rh_before(inputs["relative_humidity_mean"]),
    }


def rh_before(relative_humidity_mean) -> np.ndarray:
    """The mean RH of the 14 days before each day (not the day itself), given only when 12 or more are known."""
    rh = np.asarray(relative_humidity_mean, dtype=float)
    known = rolling_sum(np.isfinite(rh).astype(float), 14)
    mean = np.where(known >= 12, moving_mean(rh, 14), np.nan)
    return np.concatenate([np.full((1, *rh.shape[1:]), np.nan), mean[:-1]])[: rh.shape[0]]


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    each = {name: 100 * p for name, p in probabilities(values["relative_humidity_mean_14_day_lag_1"]).items()}
    return {"probability": each[f"probability_{options.get('resistance', 's')}"], **each}


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
    return risk_level(outputs["probability"], 0, 24, 32)


def explore(rh_mean_14day: float) -> dict[str, float]:
    return {name: float(100 * p) for name, p in probabilities(rh_mean_14day).items()}
