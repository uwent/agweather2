"""Cercospora leaf spot of beet: daily infection values (DIV) and their 2- and 7-day means.

Each day earns 0–7 DIV from the hours with RH ≥ 90% and their mean temperature, read from Windels et al.'s
(1998) table, which is in °F. Risk follows the Crop Risk Tool: the higher of the last 2 days' and last 7 days'
mean DIV.

Ported from the Crop Risk Tool (`calc_cercospora_div`, `risk_for_cercospora`) with parity tests. Intended
difference, as for late blight: humid hours and their temperature both come from the day from 6 pm.

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
    id="cercospora-beet-div",
    name="Cercospora leaf spot daily infection values",
    group="disease",
    version="0.3",
    status="stable",
    summary="Daily infection values (0–7) from hours of high humidity and their temperature; their 2- and "
    "7-day means time fungicide sprays for Cercospora leaf spot of table and sugar beet.",
    topics=("beet-cercospora-leaf-spot",),
    crops=("Beet",),
    citations=(
        Citation(
            text="Windels, C. E., Lamey, H. A., Hilde, D., Widner, J. and Knudsen, T. (1998). A Cercospora leaf spot "
            "model for sugar beet: in practice by an industry. Plant Disease 82, 716–726.",
            doi="10.1094/PDIS.1998.82.7.716",
        ),
        Citation(
            text="Cornell Vegetables: Cercospora leaf spot of table beet.",
            url="https://www.vegetables.cornell.edu/pest-management/disease-factsheets/cercospora-leaf-spot-of-table-beet/",
        ),
    ),
    inputs=(
        Input(
            name="hours_rh_over_90_from_6pm",
            label="Hours with RH ≥ 90%",
            unit="hour",
            description="Day from 6 pm the evening before",
        ),
        Input(name="temperature_mean_rh_over_90_from_6pm", label="Mean temperature during RH ≥ 90%", unit="degC"),
    ),
    outputs=(
        Quantity(name="div", label="Daily infection value", unit="index"),
        Quantity(name="div_2_day_mean", label="Mean DIV, last 2 days", unit="index"),
        Quantity(name="div_7_day_mean", label="Mean DIV, last 7 days", unit="index"),
        Quantity(name="div_total", label="DIVs since planting", unit="index"),
    ),
    risk=Risk(
        levels=SEVERITY_LEVELS,
        criteria="Very high when the last 7 days average 5 or more DIV or the last 2 days 5.5; High from 3 (7 days) or "
        "3.5 (2 days); Moderate from 1.5 or 2; Low from 0.5 or 1; Very low below those.",
    ),
    explorer=(
        ExplorerInput(
            name="temperature",
            label="Mean temperature during RH ≥ 90%",
            unit="degC",
            minimum=10,
            maximum=35,
            step=0.5,
            default=24,
        ),
        ExplorerInput(
            name="hours", label="Hours with RH ≥ 90%", unit="hour", minimum=0, maximum=24, step=1, default=12
        ),
    ),
    sweep={"temperature": tuple(t / 2 for t in range(28, 66)), "hours": tuple(float(h) for h in range(25))},
    season=("06-01", "09-30"),
    biofix=Biofix(default="06-01", label="Planting"),
    ingredients=(Ingredient(name="div", unit="index"),),
    accumulations=(
        Accumulation(name="div_2_day_mean", of="div", how="mean", days=2),
        Accumulation(name="div_7_day_mean", of="div", how="mean", days=7),
        Accumulation(name="div_total", of="div"),
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
            note="DIV totals count from the biofix, as the risk does (were from the first day read).",
        ),
        Change(
            version="0.3",
            date="2026-11-06",
            note="Humid hours and their temperature from the day from 6 pm CST (was 8 pm local, the Crop Risk "
            "Tool's), and days on CST all year (D74).",
        ),
    ),
)

# Windels et al.'s table: (upper bound of the °F band, DIV floor, hours each further DIV needs more than)
_TABLE_F: tuple[tuple[float, float, tuple[float, ...]], ...] = (
    (60, 0, ()),
    (61, 0, (21,)),
    (62, 0, (19, 22)),
    (63, 0, (16, 19, 21)),
    (64, 0, (13, 15, 18, 20, 23)),
    (65, 0, (6, 8, 12, 18, 21)),
    (71, 0, (3, 6, 10, 14, 18, 21)),
    (72, 0, (2, 6, 9, 13, 17, 20)),
    (73, 0, (1, 6, 9, 12, 16, 19)),
    (76, 1, (5, 9, 11, 16, 18, 23)),
    (77, 1, (5, 8, 12, 15, 18, 22)),
    (78, 1, (5, 8, 11, 14, 17, 20)),
    (79, 1, (4, 7, 9, 12, 14, 17)),
    (80, 1, (3, 6, 8, 10, 12, 15)),
    (81, 1, (2, 4, 6, 7, 9, 11)),
    (82, 1, (2, 4, 5, 7, 8, 10)),
    (np.inf, 1, (2, 4, 5, 7, 8, 9)),
)


def div(temperature_c, hours) -> np.ndarray:
    """Windels' daily infection value (0–7) from the mean temperature during RH ≥ 90% and those hours."""
    t = np.asarray(temperature_c, dtype=float) * 1.8 + 32
    h = np.asarray(hours, dtype=float)
    conditions, values, lower = [], [], -np.inf
    for upper, floor, steps in _TABLE_F:
        conditions.append((t > lower) & (t <= upper))
        values.append(floor + steps_over(h, *steps))
        lower = upper
    table = np.select(conditions, values, 0.0)
    return np.where(h == 0, 0.0, np.where(np.isnan(h) | np.isnan(t), np.nan, table))


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {"div": div(inputs["temperature_mean_rh_over_90_from_6pm"], inputs["hours_rh_over_90_from_6pm"])}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    return {name: values[name] for name in ("div", "div_2_day_mean", "div_7_day_mean", "div_total")}


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
    a = with_accumulations(outputs, SPEC.accumulations, biofix_index)
    week, two = a["div_7_day_mean"], a["div_2_day_mean"]
    level = np.select(
        [
            (week >= 5) | (two >= 5.5),
            (week >= 3) | (two >= 3.5),
            (week >= 1.5) | (two >= 2),
            (week >= 0.5) | (two >= 1),
        ],
        [4, 3, 2, 1],
        0,
    ).astype(float)
    return np.where(np.isnan(a["div_total"]), np.nan, level)


def explore(temperature: float, hours: float) -> dict[str, float]:
    return {"div": float(div(temperature, hours))}
