"""Carrot foliar blights (Alternaria and Cercospora): TOMCAST disease severity values over the last 7 days.

Each day earns 0–4 DSV from the hours of leaf wetness, taken as RH ≥ 90%, and the mean temperature meanwhile
(TOMCAST, Pitblado 1992, from Madden et al.'s FAST 1978). Risk is the last 7 days' total.

Ported from the Crop Risk Tool (`calc_alternaria_dsv`, `risk_for_alternaria`) with parity tests. Intended
difference, as for late blight: humid hours and their temperature both come from the day from 8 pm (the tool
counts the hours over the calendar day). Open question (PLAN.md Phase 3 D): the tool's lowest steps at 13–18 °C
(more than 7 h) and 18–21 °C (more than 4 h), and its band edges at 18 and 21 °C, against FAST's table.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import rolling_sum, running_total
from agmodels.lookup import level_reached, steps_over
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
    id="carrot-foliar-dsv",
    name="Carrot foliar blight disease severity values (TOMCAST)",
    group="disease",
    version="1.0",
    status="stable",
    summary="Daily disease severity values (0–4) from hours of leaf wetness and their temperature; the last "
    "7 days' total times fungicide sprays for Alternaria and Cercospora leaf blights of carrot.",
    topics=("carrot-alternaria-leaf-blight", "carrot-cercospora-leaf-blight"),
    crops=("Carrot",),
    citations=(
        Citation(
            "Pitblado, R. E. (1992). TOM-CAST: a weather-timed fungicide spray program for field tomatoes. "
            "Ridgetown College of Agricultural Technology, Ontario.",
            "https://atrium.lib.uoguelph.ca/server/api/core/bitstreams/5c7ec712-43ef-4b73-b8b8-e85c29d3d58b/content",
        ),
        Citation(
            "Madden, L., Pennypacker, S. P. and MacNab, A. A. (1978). FAST, a forecast system for Alternaria "
            "solani on tomato. Phytopathology 68, 1354–1358.",
            "https://www.apsnet.org/publications/phytopathology/backissues/Documents/1978Articles/Phyto68n09_1354.PDF",
        ),
        Citation(
            "UW Vegetable Pathology: Carrot Alternaria and Cercospora leaf blights.",
            "https://vegpath.plantpath.wisc.edu/diseases/carrot-alternaria-and-cercospora-leaf-blights/",
        ),
    ),
    inputs=(
        Quantity("hours_rh_over_90_from_8pm", "Hours with RH ≥ 90%", "hour", "Day from 8 pm the evening before"),
        Quantity("temperature_mean_rh_over_90_from_8pm", "Mean temperature during RH ≥ 90%", "degC"),
    ),
    outputs=(
        Quantity("dsv", "Disease severity values", "index"),
        Quantity("dsv_7_day", "DSVs in the last 7 days", "index"),
        Quantity("dsv_total", "DSVs since planting", "index"),
    ),
    risk=Risk(
        SEVERITY_LEVELS,
        "The last 7 days' DSVs: Very low below 5, Low from 5, Moderate from 10, High from 15, Very high from 20.",
    ),
    explorer=(
        ExplorerInput("temperature", "Mean temperature during RH ≥ 90%", "degC", 5, 35, 0.5, 20),
        ExplorerInput("hours", "Hours with RH ≥ 90%", "hour", 0, 24, 1, 10),
    ),
    sweep={"temperature": tuple(float(t) for t in range(10, 32, 2)), "hours": tuple(float(h) for h in range(0, 25, 3))},
    season=("06-01", "09-30"),
    biofix=Biofix("06-01", "Planting or the last fungicide application"),
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
    """TOMCAST's daily DSV (0–4) from the mean temperature during wetness and its hours."""
    t, h = np.asarray(temperature_c, dtype=float), np.asarray(hours, dtype=float)
    steps = np.select(
        [t < 13, t <= 18, t <= 21, t <= 26],
        [np.zeros_like(h), steps_over(h, 7, 15, 20), steps_over(h, 4, 8, 15, 22), steps_over(h, 2, 5, 12, 20)],
        steps_over(h, 3, 8, 15, 22),
    )
    return np.where(h == 0, 0.0, np.where(np.isnan(h) | np.isnan(t), np.nan, steps))


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    values = dsv(inputs["temperature_mean_rh_over_90_from_8pm"], inputs["hours_rh_over_90_from_8pm"])
    return {"dsv": values, **_accumulated(values, 0)}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    recent = _accumulated(np.asarray(outputs["dsv"], dtype=float), biofix_index)["dsv_7_day"]
    return level_reached(recent, 5, 10, 15, 20)


def explore(temperature: float, hours: float) -> dict[str, float]:
    return {"dsv": float(dsv(temperature, hours))}


def _accumulated(values: np.ndarray, start: int) -> dict[str, np.ndarray]:
    return {"dsv_7_day": rolling_sum(values, 7, start), "dsv_total": running_total(values, start)}
