"""Potato volunteer survival: hours of killing soil cold (below 27 °F) at 2, 4 and 8 in since October 1.

Tubers left after harvest survive the winter, sprout as volunteers and can carry late blight and insect pests into
the next season, unless the soil around them freezes hard enough. Kirk and Wharton's rule (Michigan State
University): count the hours with soil below 27 °F at 2 and 4 in over the winter; more than 120 at both depths makes
survival unlikely, at neither likely. The Wisconsin potato volunteer tool adds 8 in: each depth reaching 120 hours
lowers the risk a level, from Very high (none) to Low (all three). Here 2 and 4 in are HRRR's 4 and 10 cm levels
(D9), and 8 in is interpolated between 10 and 30 cm, all counted from hourly values as daily features.

Ported from the tool (`calc_vol_risk`, on Wisconet stations), with its season and threshold (Ben): a full year from
October 1, so the count catches the winter's freeze and its risk carries through the next growing season, with the
soil temperatures shown alongside (their daily minimums are in the inputs layer, for the chart); and at least 120
hours. MSU counts November 1 through March 31, but soil doesn't fall below 27 °F in a Wisconsin October, so the
counts are the same there. A day missing an hour adds nothing to the counts (D25), which leans the risk high where
data are short.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.ingredients import Accumulation, Ingredient, finished, with_accumulations
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, Input, ModelSpec, Quantity, Risk

KILLING_HOURS = 120  # this many at a depth kills the tubers there (the tool's; MSU says more than 120)
DEPTHS = {"4cm": "2 in (4 cm)", "10cm": "4 in (10 cm)", "8in": "8 in (10–30 cm interpolated)"}

SPEC = ModelSpec(
    id="potato-volunteer",
    name="Potato volunteer survival",
    group="agronomic",
    version="0.1",
    status="beta",
    summary="Whether potato tubers left in the field are likely to survive the winter, from the hours of soil "
    "below 27 °F at 2, 4 and 8 in; surviving volunteers can carry late blight and insect pests into the next season.",
    topics=("potato-volunteers",),
    crops=("Potato",),
    citations=(
        Citation(
            text="Kirk, W. and Wharton, P. Potential survival of potato volunteers in Michigan. Michigan State "
            "University Extension.",
            url="https://www.canr.msu.edu/news/potential_survival_of_potato_volunteers_in_mich",
        ),
        Citation(
            text="UW Vegetable Pathology (2025). Deep frost this winter limits risk of potato volunteers.",
            url="https://vegpath.plantpath.wisc.edu/2025/04/22/potato-volunteer-risk/",
        ),
    ),
    inputs=(
        Input(name="hours_soil_4cm_below_27f", label=f"Hours with soil at {DEPTHS['4cm']} below 27 °F", unit="hour"),
        Input(name="hours_soil_10cm_below_27f", label=f"Hours with soil at {DEPTHS['10cm']} below 27 °F", unit="hour"),
        Input(name="hours_soil_8in_below_27f", label=f"Hours with soil at {DEPTHS['8in']} below 27 °F", unit="hour"),
        Input(
            name="soil_temperature_4cm_min",
            label="Minimum soil temperature at 4 cm",
            unit="degC",
            description="Shown, not used",
        ),
        Input(
            name="soil_temperature_10cm_min",
            label="Minimum soil temperature at 10 cm",
            unit="degC",
            description="Shown, not used",
        ),
        Input(
            name="soil_temperature_30cm_min",
            label="Minimum soil temperature at 30 cm",
            unit="degC",
            description="Shown, not used",
        ),
    ),
    outputs=tuple(
        Quantity(name=f"killing_hours_{d}", label=f"Hours below 27 °F at {label} since October 1", unit="hour")
        for d, label in DEPTHS.items()
    ),
    risk=Risk(
        levels=("Low", "Moderate", "High", "Very high"),
        criteria="The chance tubers survive, by the depths (2, 4 and 8 in) with at least 120 hours below 27 °F since "
        "October 1: Low at all three, Moderate at two, High at one, Very high at none.",
    ),
    explorer=tuple(
        ExplorerInput(
            name=f"killing_hours_{d}",
            label=f"Hours below 27 °F at {label}",
            unit="hour",
            minimum=0,
            maximum=500,
            step=1,
            default=60,
        )
        for d, label in DEPTHS.items()
    ),
    explorer_outputs=(
        Quantity(name="risk", label="Risk level", unit="index", description="Index into the risk levels"),
    ),
    sweep={f"killing_hours_{d}": (0.0, 60.0, 119.0, 120.0, 240.0) for d in DEPTHS},
    season=("10-01", "09-30"),
    biofix=Biofix(
        default="10-01", label="October 1, the start of the season (the winter's count carries through the next summer)"
    ),
    ingredients=tuple(Ingredient(name=f"hours_below_27f_{d}", unit="hour") for d in DEPTHS),
    accumulations=tuple(Accumulation(name=f"killing_hours_{d}", of=f"hours_below_27f_{d}") for d in DEPTHS),
    changelog=(Change(version="0.1", date="2026-10-28", note="Ported from the Wisconsin potato volunteer tool."),),
)


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {f"hours_below_27f_{d}": np.asarray(inputs[f"hours_soil_{d}_below_27f"], dtype=float) for d in DEPTHS}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    return {f"killing_hours_{d}": values[f"killing_hours_{d}"] for d in DEPTHS}


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
    totals = [np.asarray(values[f"killing_hours_{d}"], dtype=float) for d in DEPTHS]
    killed = sum(((t >= KILLING_HOURS).astype(float) for t in totals), np.zeros_like(totals[0]))
    unknown = np.any([np.isnan(t) for t in totals], axis=0)
    return np.where(unknown, np.nan, len(DEPTHS) - killed)


def explore(killing_hours_4cm: float, killing_hours_10cm: float, killing_hours_8in: float) -> dict[str, float]:
    totals = {"killing_hours_4cm": killing_hours_4cm, "killing_hours_10cm": killing_hours_10cm}
    totals["killing_hours_8in"] = killing_hours_8in
    return {"risk": float(risk({k: np.array([v]) for k, v in totals.items()})[0])}
