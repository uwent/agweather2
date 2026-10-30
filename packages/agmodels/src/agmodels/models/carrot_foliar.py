"""Carrot foliar blights (Alternaria and Cercospora): TOMCAST disease severity values over the last 7 days.

Each day earns 0–4 DSV from the hours of leaf wetness, taken as RH ≥ 90%, and the mean temperature meanwhile
(TOMCAST, Pitblado 1992, from Madden et al.'s FAST 1978). Risk is the last 7 days' total.

The table is FAST's (Madden et al. 1978, Table 1). Its bands are whole degrees (13–17, 18–20, 21–25, 26–29 °C), read
here as [13, 18), [18, 21), [21, 26) and from 26 up (TOMCAST keeps the last row above 29); below 13 °C a day earns
nothing.

Ported from the Crop Risk Tool (`calc_alternaria_dsv`, `risk_for_alternaria`) with parity tests. Intended
differences: humid hours and their temperature both come from the day from 8 pm, as for late blight (the tool
counts the hours over the calendar day); and the table follows FAST where the tool's is off by one, its first step
at 13–17 °C (from 8 h; FAST 7) and 18–20 °C (from 5 h; FAST 4) and its band edges (18, 21 and 26 °C in the band
below).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import rolling_sum, running_total
from agmodels.lookup import level_reached
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
    version="0.2",
    status="stable",
    summary="Daily disease severity values (0–4) from hours of leaf wetness and their temperature; the last "
    "7 days' total times fungicide sprays for Alternaria and Cercospora leaf blights of carrot.",
    topics=("carrot-alternaria-leaf-blight", "carrot-cercospora-leaf-blight"),
    crops=("Carrot",),
    citations=(
        Citation(
            text="Pitblado, R. E. (1992). TOM-CAST: a weather-timed fungicide spray program for field tomatoes. "
            "Ridgetown College of Agricultural Technology, Ontario.",
            url="https://atrium.lib.uoguelph.ca/server/api/core/bitstreams/5c7ec712-43ef-4b73-b8b8-e85c29d3d58b/content",
        ),
        Citation(
            text="Madden, L., Pennypacker, S. P. and MacNab, A. A. (1978). FAST, a forecast system for Alternaria "
            "solani on tomato. Phytopathology 68, 1354–1358.",
            url="https://www.apsnet.org/publications/phytopathology/backissues/Documents/1978Articles/Phyto68n09_1354.PDF",
            doi="10.1094/Phyto-68-1354",
        ),
        Citation(
            text="UW Vegetable Pathology: Carrot Alternaria and Cercospora leaf blights.",
            url="https://vegpath.plantpath.wisc.edu/diseases/carrot-alternaria-and-cercospora-leaf-blights/",
        ),
    ),
    inputs=(
        Quantity(
            name="hours_rh_over_90_from_8pm",
            label="Hours with RH ≥ 90%",
            unit="hour",
            description="Day from 8 pm the evening before",
        ),
        Quantity(name="temperature_mean_rh_over_90_from_8pm", label="Mean temperature during RH ≥ 90%", unit="degC"),
    ),
    outputs=(
        Quantity(name="dsv", label="Disease severity values", unit="index"),
        Quantity(name="dsv_7_day", label="DSVs in the last 7 days", unit="index"),
        Quantity(name="dsv_total", label="DSVs since planting", unit="index"),
    ),
    risk=Risk(
        levels=SEVERITY_LEVELS,
        criteria="The last 7 days' DSVs: Very low below 5, Low from 5, Moderate from 10, High from 15, Very high "
        "from 20.",
    ),
    explorer=(
        ExplorerInput(
            name="temperature",
            label="Mean temperature during RH ≥ 90%",
            unit="degC",
            minimum=5,
            maximum=35,
            step=0.5,
            default=20,
        ),
        ExplorerInput(
            name="hours", label="Hours with RH ≥ 90%", unit="hour", minimum=0, maximum=24, step=1, default=10
        ),
    ),
    sweep={"temperature": tuple(float(t) for t in range(8, 35)), "hours": tuple(float(h) for h in range(25))},
    season=("06-01", "09-30"),
    biofix=Biofix(default="06-01", label="Planting or the last fungicide application"),
    changelog=(
        Change(
            version="0.1",
            date="2026-10-28",
            note="Ported from the Crop Risk Tool; humid hours and their temperature from "
            "the same window (the day from 8 pm).",
        ),
        Change(
            version="0.2",
            date="2026-10-28",
            note="FAST's table (Madden et al. 1978): the first step at 13–17 °C from 7 h and at 18–20 °C from 4 h, and "
            "18, 21 and 26 °C in the band above.",
        ),
    ),
)


def dsv(temperature_c, hours) -> np.ndarray:
    """TOMCAST's daily DSV (0–4) from the mean temperature during wetness and its hours."""
    t, h = np.asarray(temperature_c, dtype=float), np.asarray(hours, dtype=float)
    # The hours at which each band's DSV steps up, as FAST's table gives them (13–17 °C: 0–6 h earn 0, 7–15 h 1, …)
    steps = np.select(
        [t < 13, t < 18, t < 21, t < 26],
        [np.zeros_like(h), level_reached(h, 7, 16, 21), level_reached(h, 4, 9, 16, 23), level_reached(h, 3, 6, 13, 21)],
        level_reached(h, 4, 9, 16, 23),
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
