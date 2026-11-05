"""Late blight of potato and tomato: Wallin's disease severity values (DSV), accumulated from crop emergence.

Each day earns 0–4 DSV from how long the air stayed humid (RH ≥ 90%) and how warm it was meanwhile (Wallin
1962, as BLITECAST; Krause et al. 1975). Risk follows the Crop Risk Tool: 18 season DSVs is the usual spray
threshold, and the last 14 days' DSVs say how fast it's building.

Ported from the Crop Risk Tool (`calc_late_blight_dsv`, `risk_for_late_blight`), with parity tests. One intended
difference: the tool counts humid hours over the calendar day but averages their temperature over the day from
8 pm; Wallin pairs the hours with their own temperature, so both come from the day from 8 pm here (an overnight
wet period counts whole). A day without its inputs has no DSV rather than 0.

Gridded RH ≥ 90% is counted at 88%, a station's 90% (D50, `features.STATION_RH_90_AS_GRIDDED`).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.ingredients import Accumulation, Ingredient, finished, with_accumulations
from agmodels.lookup import steps_over
from agmodels.spec import (
    SEVERITY_LEVELS,
    Biofix,
    Change,
    Citation,
    ExplorerInput,
    Input,
    ModelSpec,
    Quantity,
    Risk,
)

SPEC = ModelSpec(
    id="late-blight-dsv",
    name="Late blight disease severity values",
    group="disease",
    version="0.2",
    status="stable",
    summary="Daily disease severity values (0–4) from hours of high humidity and their temperature, "
    "accumulated from crop emergence to time fungicide sprays for potato and tomato late blight.",
    topics=("late-blight",),
    crops=("Potato", "Tomato"),
    citations=(
        Citation(
            text="Wallin, J. R. (1962). Summary of recent progress in predicting late blight epidemics in United "
            "States and Canada. American Potato Journal 39, 306–312.",
            doi="10.1007/BF02862155",
        ),
        Citation(
            text="Krause, R. A., Massie, L. B. and Hyre, R. A. (1975). Blitecast: a computerized forecast of potato "
            "late blight. Plant Disease Reporter 59, 95–98."
        ),
        Citation(
            text="UC IPM: Potato late blight.", url="https://ipm.ucanr.edu/DISEASE/DATABASE/potatolateblight.html"
        ),
        Citation(
            text="UW Vegetable Pathology: Potato late blight.",
            url="https://vegpath.plantpath.wisc.edu/diseases/potato-late-blight/",
        ),
    ),
    inputs=(
        Input(
            name="hours_rh_over_90_from_8pm",
            label="Hours with RH ≥ 90%",
            unit="hour",
            description="Day from 8 pm the evening before",
        ),
        Input(name="temperature_mean_rh_over_90_from_8pm", label="Mean temperature during RH ≥ 90%", unit="degC"),
    ),
    outputs=(
        Quantity(name="dsv", label="Disease severity values", unit="index"),
        Quantity(name="dsv_14_day", label="DSVs in the last 14 days", unit="index"),
        Quantity(name="dsv_total", label="DSVs since emergence", unit="index"),
    ),
    risk=Risk(
        levels=SEVERITY_LEVELS,
        criteria="Very high: 21 or more DSVs in the last 14 days once the season total reaches 30. High: 14 or more in "
        "14 days once the total reaches 18. Moderate: a season total of 18 or more (the usual first-spray "
        "threshold). Low: any DSVs in the last 14 days. Very low: none.",
    ),
    explorer=(
        ExplorerInput(
            name="temperature",
            label="Mean temperature during RH ≥ 90%",
            unit="degC",
            minimum=0,
            maximum=30,
            step=0.5,
            default=16,
        ),
        ExplorerInput(
            name="hours", label="Hours with RH ≥ 90%", unit="hour", minimum=0, maximum=24, step=1, default=14
        ),
    ),
    sweep={"temperature": tuple(float(t) for t in range(0, 31)), "hours": tuple(float(h) for h in range(25))},
    region=(),
    season=("05-01", "09-30"),
    biofix=Biofix(default="05-15", label="Crop emergence or the last fungicide application"),
    biofix_stage=("potato-stages", "EM"),  # emergence from a planting date, when one is given
    ingredients=(Ingredient(name="dsv", unit="index"),),
    accumulations=(
        Accumulation(name="dsv_total", of="dsv"),
        Accumulation(name="dsv_14_day", of="dsv", how="sum", days=14),
    ),
    changelog=(
        Change(
            version="0.1",
            date="2026-10-28",
            note="Ported from the Crop Risk Tool; humid hours and their temperature from "
            "the same window (the day from 8 pm).",
        ),
        Change(
            version="0.2",
            date="2026-11-03",
            note="DSV totals (season and 14-day) count from the biofix, as the risk does "
            "(were from the first day read).",
        ),
    ),
)


def dsv(temperature_c, hours) -> np.ndarray:
    """Wallin's daily DSV (0–4) from the mean temperature during RH ≥ 90% and the number of those hours."""
    t = np.asarray(temperature_c, dtype=float)
    h = np.asarray(hours, dtype=float)
    steps = np.select(
        [t < 7.2, t <= 11.6, t <= 15.0, t <= 26.6],
        [np.zeros_like(h), steps_over(h, 15, 18, 21), steps_over(h, 12, 15, 18, 21), steps_over(h, 9, 12, 15, 18)],
        0.0,
    )
    # No humid hours means no DSV (and no temperature to average); missing hours mean unknown
    return np.where(h == 0, 0.0, np.where(np.isnan(h) | np.isnan(t), np.nan, steps))


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {"dsv": dsv(inputs["temperature_mean_rh_over_90_from_8pm"], inputs["hours_rh_over_90_from_8pm"])}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    return {name: values[name] for name in ("dsv", "dsv_14_day", "dsv_total")}


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
    values = with_accumulations(outputs, SPEC.accumulations, biofix_index)
    total, recent = values["dsv_total"], values["dsv_14_day"]
    level = np.select(
        [(recent >= 21) & (total >= 30), (recent >= 14) & (total >= 18), total >= 18, recent >= 1], [4, 3, 2, 1], 0
    ).astype(float)
    return np.where(np.isnan(total), np.nan, level)  # before the biofix


def explore(temperature: float, hours: float) -> dict[str, float]:
    return {"dsv": float(dsv(temperature, hours))}
