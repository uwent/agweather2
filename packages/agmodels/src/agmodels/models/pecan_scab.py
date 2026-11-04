"""Pecan scab hours: hours with RH at or above 90% and temperature at or above 70 °F, since March 1 or the last spray.

The Oklahoma Mesonet's Pecan Scab Advisor (March 1 to August 31): spraying is recommended once 10 scab hours have
accumulated for highly susceptible varieties, 20 for moderately and 30 for low susceptibility, and it has been 30 days
since March 1 or 5 to 14 days since the last fungicide application. Risk here is the tool's: Low below 10 hours,
Moderate from 10 (the highly susceptible varieties' threshold), High from 20, Very high from 30 (every variety's).
Scab hours are counted from hourly values as a daily feature (`hours_rh_over_90_temperature_over_70f`, the calendar
day), so the model itself reads days.

Ported from the Crop Risk Tool (`build_pecan_scab`), whose code counts RH at or above 92% and temperature above
21.1 °C, where its docs and the Mesonet say 90% and 70 °F: v2 follows the Mesonet (intended difference). Southern,
beta: run at points through Open-Meteo until the box reaches the South.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import rolling_sum, running_total
from agmodels.lookup import level_reached
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk

THRESHOLDS = (10, 20, 30)  # highly, moderately and low susceptible varieties' spray thresholds (scab hours)
PECAN_STATES = ("AL", "AR", "AZ", "CA", "FL", "GA", "KS", "LA", "MO", "MS", "NC", "NM", "OK", "SC", "TN", "TX")

SPEC = ModelSpec(
    id="pecan-scab",
    name="Pecan scab hours",
    group="disease",
    version="0.1",
    status="beta",
    summary="Hours warm (70 °F or more) and humid (RH 90% or more) since March 1 or the last fungicide spray, "
    "against the spray thresholds for highly, moderately and low susceptible pecan varieties.",
    topics=("pecan-scab",),
    crops=("Pecan",),
    citations=(
        Citation(
            text="Oklahoma Mesonet: Pecan Scab Advisor.",
            url="https://www.mesonet.org/agriculture/horticulture/pecan/pecan-scab-advisor",
        ),
        Citation(text="University of Arkansas: Pecan scab.", url="https://pecanscab.uada.edu/"),
    ),
    inputs=(
        Quantity(
            name="hours_rh_over_90_temperature_over_70f",
            label="Scab hours (RH ≥ 90% and ≥ 70 °F)",
            unit="hour",
            description="Calendar day",
        ),
    ),
    outputs=(
        Quantity(name="scab_hours_total", label="Scab hours since March 1 or the last spray", unit="hour"),
        Quantity(name="scab_hours", label="Scab hours", unit="hour"),
        Quantity(name="scab_hours_14_day", label="Scab hours in the last 14 days", unit="hour"),
    ),
    risk=Risk(
        levels=("Low", "Moderate", "High", "Very high"),
        criteria="Scab hours since March 1 or the last spray: Low below 10, Moderate from 10 (spray highly susceptible "
        "varieties such as Desirable, Pawnee and Wichita), High from 20 (moderately susceptible, such as Caddo, "
        "Kiowa and Stuart), Very high from 30 (low susceptibility, such as Excel, Kanza and Lakota). The Mesonet also "
        "waits 30 days after March 1, or 5 to 14 days after the last spray.",
    ),
    explorer=(
        ExplorerInput(
            name="scab_hours_total",
            label="Scab hours since March 1 or the last spray",
            unit="hour",
            minimum=0,
            maximum=60,
            step=1,
            default=10,
        ),
    ),
    explorer_outputs=(
        Quantity(name="risk", label="Risk level", unit="index", description="Index into the risk levels"),
    ),
    sweep={"scab_hours_total": tuple(float(h) for h in range(0, 41))},
    region=PECAN_STATES,
    season=("03-01", "08-31"),
    biofix=Biofix(default="03-01", label="March 1, or the last fungicide application"),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool, with the Mesonet's thresholds."),
    ),
)


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    hours = np.asarray(inputs["hours_rh_over_90_temperature_over_70f"], dtype=float)
    return {
        "scab_hours_total": running_total(hours, biofix_index),
        "scab_hours": hours,
        "scab_hours_14_day": rolling_sum(hours, 14, biofix_index),
    }


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return level_reached(outputs["scab_hours_total"], *THRESHOLDS)


def explore(scab_hours_total: float) -> dict[str, float]:
    return {"risk": float(level_reached(scab_hours_total, *THRESHOLDS))}
