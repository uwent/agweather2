"""Botrytis leaf blight of onion: BOTCAST's disease severity index (DSI), accumulated from emergence.

Two steps a day (Sutton et al. 1986): whether inoculum is likely present (none after a hot spell, with too few
humid hours, or after a dry day without enough humid hours to recover), and how favorable the day's wet period
was for infection (0–2 from its length and temperature). Their product is the day's DSI; risk follows the
season total.

Ported from the Crop Risk Tool (`botcast_dinov`, `botcast_dinfv`, `calc_botrytis_dsi`, `risk_for_botrytis`)
with parity tests. Intended differences: humid hours and their temperature both come from the day from 8 pm (as
for late blight), and a day whose deciding inputs are missing has no DSI (R's `case_when` treats a missing
condition as false, so the tool can score such a day 1). Leaf wetness is taken as RH ≥ 90%.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import running_total
from agmodels.features import across_days
from agmodels.lookup import steps_over
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
    id="botrytis-onion-botcast",
    name="Botrytis leaf blight (BOTCAST)",
    group="disease",
    version="1.0",
    status="stable",
    summary="BOTCAST's daily disease severity index from inoculum and infection conditions, accumulated from "
    "emergence to time fungicide sprays for Botrytis leaf blight of onion.",
    topics=("onion-botrytis-leaf-blight",),
    crops=("Onion",),
    citations=(
        Citation(
            "Sutton, J. C., James, T. D. W. and Rowell, P. M. (1986). BOTCAST: a forecasting system to time the "
            "initial fungicide spray for managing Botrytis leaf blight of onions. Agriculture, Ecosystems and "
            "Environment 18, 123–143.",
            doi="10.1016/0167-8809(86)90136-2",
        ),
        Citation(
            "UW Vegetable Pathology: Onion Botrytis leaf blight.",
            "https://vegpath.plantpath.wisc.edu/diseases/onion-botrytis/",
        ),
    ),
    inputs=(
        Quantity("hours_rh_over_90_from_8pm", "Hours with RH ≥ 90%", "hour", "Day from 8 pm the evening before"),
        Quantity("temperature_mean_rh_over_90_from_8pm", "Mean temperature during RH ≥ 90%", "degC"),
        Quantity(
            "hours_temperature_over_30c",
            "Hours at or above 30 °C",
            "hour",
            "Four or more on any of the last 5 days makes inoculum unlikely",
        ),
        Quantity(
            "hours_rh_under_70", "Hours with RH below 70%", "hour", "With under 1 mm of rain, 6 or more make a dry day"
        ),
        Quantity("precipitation_sum", "Precipitation", "mm"),
    ),
    outputs=(
        Quantity("dsi", "Disease severity index", "index"),
        Quantity("inoculum", "Inoculum value (0 or 1)", "index"),
        Quantity("infection", "Infection value (0–2)", "index"),
        Quantity("dsi_total", "DSI since emergence", "index"),
    ),
    risk=Risk(
        SEVERITY_LEVELS,
        "The season's DSI total: Very low up to 10, Low above 10, Moderate above 20, High above 30, "
        "Very high above 40.",
    ),
    explorer=(
        ExplorerInput("temperature", "Mean temperature during RH ≥ 90%", "degC", 0, 32, 0.5, 15),
        ExplorerInput("hours", "Hours with RH ≥ 90%", "hour", 0, 24, 1, 12),
        ExplorerInput("hot", "Hot spell in the last 5 days (0 or 1)", "index", 0, 1, 1, 0),
        ExplorerInput("dry_yesterday", "Yesterday was dry (0 or 1)", "index", 0, 1, 1, 0),
    ),
    sweep={
        "temperature": tuple(float(t) for t in range(0, 33)),
        "hours": tuple(float(h) for h in range(25)),
        "hot": (0.0, 1.0),
        "dry_yesterday": (0.0, 1.0),
    },
    season=("05-15", "09-15"),
    biofix=Biofix("05-15", "Crop emergence"),
    changelog=(
        Change(
            "1.0",
            "2026-10-28",
            "Ported from the Crop Risk Tool; humid hours and their temperature from "
            "the same window; missing inputs give no DSI.",
        ),
    ),
)


def inoculum(hot, dry_yesterday, hours) -> np.ndarray:
    """BOTCAST's daily inoculum value: 0 or 1, in the order Sutton et al. test the conditions."""
    hot, dry, h = (np.asarray(x, dtype=float) for x in (hot, dry_yesterday, hours))
    return np.select(
        [np.isnan(h), hot == 1, h < 5, np.isnan(hot), h > 12, np.isnan(dry), dry == 1],
        [np.nan, 0, 0, np.nan, 1, np.nan, 0],
        1,
    )


def infection(temperature_c, hours) -> np.ndarray:
    """BOTCAST's daily infection value (0–2) from the wet period's length and mean temperature."""
    t, h = np.asarray(temperature_c, dtype=float), np.asarray(hours, dtype=float)
    return np.select(
        [
            np.isnan(h),
            h <= 6,
            np.isnan(t),
            (t < 6) | (t > 28),
            (h <= 12) & (t < 9),
            t <= 8,
            (h <= 15) & (t >= 27),
            (h <= 7) & (t >= 24),
            (h >= 15) & (t >= 8) & (t <= 25),
            (h >= 14) & (t >= 11) & (t <= 16.5),
            (h >= 11) & (t >= 13.5) & (t <= 16.5),
            h - 12 <= 9 - t,
        ],
        [np.nan, 0, np.nan, 0, 0, np.where(h <= 12, 0, np.where(h <= 22, 1, 2)), 0, 0, 2, 2, 2, 0],
        1,
    )


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    days = across_days(inputs)
    dry = np.asarray(days["dry"], dtype=float)
    dry_yesterday = np.concatenate([np.zeros((1, *dry.shape[1:])), dry[:-1]])  # before the first day: not dry
    hours = inputs["hours_rh_over_90_from_8pm"]
    inoc = inoculum(days["hot_past_5_days"], dry_yesterday, hours)
    infect = infection(inputs["temperature_mean_rh_over_90_from_8pm"], hours)
    dsi = inoc * infect
    return {"dsi": dsi, "inoculum": inoc, "infection": infect, "dsi_total": running_total(dsi, 0)}


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    total = running_total(np.asarray(outputs["dsi"], dtype=float), biofix_index)
    return np.where(np.isnan(total), np.nan, steps_over(total, 10, 20, 30, 40))


def explore(temperature: float, hours: float, hot: float, dry_yesterday: float) -> dict[str, float]:
    inoc, infect = float(inoculum(hot, dry_yesterday, hours)), float(infection(temperature, hours))
    return {"dsi": inoc * infect, "inoculum": inoc, "infection": infect}
