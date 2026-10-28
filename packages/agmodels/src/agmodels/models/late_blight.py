"""Late blight of potato and tomato: Wallin's disease severity values (DSV), accumulated from crop emergence.

Each day earns 0–4 DSV from how long the air stayed humid (RH ≥ 90%) and how warm it was meanwhile (Wallin
1962, as BLITECAST; Krause et al. 1975). Risk follows the Crop Risk Tool: 18 season DSVs is the usual spray
threshold, and the last 14 days' DSVs say how fast it's building.

Ported from the Crop Risk Tool (`calc_late_blight_dsv`, `risk_for_late_blight`), with parity tests. One intended
difference: the tool counts humid hours over the calendar day but averages their temperature over the day from
8 pm; Wallin pairs the hours with their own temperature, so both come from the day from 8 pm here (an overnight
wet period counts whole). A day without its inputs has no DSV rather than 0.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.spec import (
    SEVERITY_LEVELS,
    Biofix,
    Change,
    Citation,
    ExplorerInput,
    ModelSpec,
    Quantity,
    Risk,
)

SPEC = ModelSpec(
    id="late-blight-dsv",
    name="Late blight disease severity values",
    group="disease",
    version="1.0",
    status="stable",
    summary="Daily disease severity values (0–4) from hours of high humidity and their temperature, "
    "accumulated from crop emergence to time fungicide sprays for potato and tomato late blight.",
    topics=("late-blight",),
    crops=("Potato", "Tomato"),
    citations=(
        Citation(
            "Wallin, J. R. (1962). Summary of recent progress in predicting late blight epidemics in United "
            "States and Canada. American Potato Journal 39, 306–312.",
            "https://doi.org/10.1007/BF02862200",
        ),
        Citation(
            "Krause, R. A., Massie, L. B. and Hyre, R. A. (1975). Blitecast: a computerized forecast of potato "
            "late blight. Plant Disease Reporter 59, 95–98."
        ),
        Citation("UC IPM: Potato late blight.", "https://ipm.ucanr.edu/DISEASE/DATABASE/potatolateblight.html"),
        Citation(
            "UW Vegetable Pathology: Potato late blight.",
            "https://vegpath.plantpath.wisc.edu/diseases/potato-late-blight/",
        ),
    ),
    inputs=(
        Quantity("hours_rh_over_90_from_8pm", "Hours with RH ≥ 90%", "hour", "Day from 8 pm the evening before"),
        Quantity("temperature_mean_rh_over_90_from_8pm", "Mean temperature during RH ≥ 90%", "degC"),
    ),
    outputs=(
        Quantity("dsv", "Disease severity values", "index"),
        Quantity("dsv_14_day", "DSVs in the last 14 days", "index"),
        Quantity("dsv_total", "DSVs since emergence", "index"),
    ),
    risk=Risk(
        SEVERITY_LEVELS,
        "Very high: 21 or more DSVs in the last 14 days once the season total reaches 30. High: 14 or more in "
        "14 days once the total reaches 18. Moderate: a season total of 18 or more (the usual first-spray "
        "threshold). Low: any DSVs in the last 14 days. Very low: none.",
    ),
    explorer=(
        ExplorerInput("temperature", "Mean temperature during RH ≥ 90%", "degC", 0, 30, 0.5, 16),
        ExplorerInput("hours", "Hours with RH ≥ 90%", "hour", 0, 24, 1, 14),
    ),
    sweep={"temperature": tuple(float(t) for t in range(4, 30, 2)), "hours": tuple(float(h) for h in range(0, 25, 3))},
    region=(),
    season=("05-01", "09-30"),
    biofix=Biofix("05-15", "Crop emergence or the last fungicide application"),
    changelog=(
        Change(
            "1.0",
            "2026-10-28",
            "Ported from the Crop Risk Tool; humid hours and their temperature from "
            "the same window (the day from 8 pm).",
        ),
    ),
)


def dsv(temperature_c, hours) -> np.ndarray:
    """Wallin's daily DSV (0–4) from the mean temperature during RH ≥ 90% and the number of those hours."""
    t = np.asarray(temperature_c, dtype=float)
    h = np.asarray(hours, dtype=float)
    steps = np.select(
        [t < 7.2, t <= 11.6, t <= 15.0, t <= 26.6],
        [np.zeros_like(h), _over(h, 15, 18, 21), _over(h, 12, 15, 18, 21), _over(h, 9, 12, 15, 18)],
        0.0,
    )
    # No humid hours means no DSV (and no temperature to average); missing hours mean unknown
    return np.where(h == 0, 0.0, np.where(np.isnan(h) | np.isnan(t), np.nan, steps))


def _over(hours: np.ndarray, *thresholds: float) -> np.ndarray:
    """How many of the thresholds the hours exceed (booleans added in NumPy would OR, so count as numbers)."""
    return sum(((hours > x).astype(float) for x in thresholds), np.zeros_like(hours))


def outputs(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    values = dsv(inputs["temperature_mean_rh_over_90_from_8pm"], inputs["hours_rh_over_90_from_8pm"])
    return {"dsv": values, **_accumulated(values, 0)}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0) -> np.ndarray:
    totals = _accumulated(np.asarray(outputs["dsv"], dtype=float), biofix_index)
    total, recent = totals["dsv_total"], totals["dsv_14_day"]
    level = np.select(
        [(recent >= 21) & (total >= 30), (recent >= 14) & (total >= 18), total >= 18, recent >= 1], [4, 3, 2, 1], 0
    ).astype(float)
    level[:biofix_index] = np.nan
    return level


def explore(temperature: float, hours: float) -> dict[str, float]:
    return {"dsv": float(dsv(temperature, hours))}


def _accumulated(values: np.ndarray, start: int) -> dict[str, np.ndarray]:
    """Season total and 14-day total from `start`; a missing day adds nothing (NaN before `start`)."""
    counted = np.where(
        np.arange(values.shape[0]).reshape(-1, *([1] * (values.ndim - 1))) >= start, np.nan_to_num(values), 0
    )
    total = np.cumsum(counted, axis=0)
    recent = total - np.concatenate([np.zeros((14, *values.shape[1:])), total[:-14]])[: values.shape[0]]
    before = np.arange(values.shape[0]) < start
    total[before], recent[before] = np.nan, np.nan
    return {"dsv_total": total, "dsv_14_day": recent}
