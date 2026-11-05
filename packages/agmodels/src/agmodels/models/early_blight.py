"""Early blight of potato: physiological days (P-days) accumulated from crop emergence.

P-days measure potato development from daily minimum and maximum temperature: each day weighs a development
rate P(T) (0 below 7 °C and above 30 °C, 10 at 21 °C) at four points between the min and max (Sands, Hackett and
Nix 1979). Early blight risk rises once 300 P-days have accrued since emergence (Pscheidt and Stevenson 1986,
1988); after 400 the risk follows the recent rate.

Ported from the Crop Risk Tool (`calc_pdays`, `risk_for_early_blight`) with parity tests. Intended difference:
the tool and the old API weigh P(Tmin) in the last term; Sands et al. weigh P(Tmax) (`5 P(Tmin) + 8 P(...) +
8 P(...) + 3 P(Tmax)`), which v2 follows (see PLAN.md Phase 3 D). A day without its min or max has no P-days.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.ingredients import Accumulation, Ingredient, finished, with_accumulations
from agmodels.lookup import level_reached
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
    id="early-blight-pdays",
    name="Early blight P-days",
    group="disease",
    version="0.2",
    status="stable",
    summary="Potato physiological days from daily minimum and maximum temperature, accumulated from emergence "
    "to time the first fungicide spray for early blight (about 300 P-days).",
    topics=("early-blight",),
    crops=("Potato",),
    citations=(
        Citation(
            text="Sands, P. J., Hackett, C. and Nix, H. A. (1979). A model of the development and bulking of potatoes "
            "(Solanum tuberosum L.). I. Derivation from well-managed field crops. Field Crops Research 2, 309–331.",
            doi="10.1016/0378-4290(79)90031-5",
        ),
        Citation(
            text="Pscheidt, J. W. and Stevenson, W. R. (1988). The critical period for control of early blight "
            "(Alternaria solani) of potato. American Potato Journal 65, 425–438.",
            doi="10.1007/BF02854357",
        ),
        Citation(
            text="UW Vegetable Pathology: Potato early blight.",
            url="https://vegpath.plantpath.wisc.edu/diseases/potato-early-blight/",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="pdays", label="P-days", unit="index"),
        Quantity(name="pdays_total", label="P-days since emergence", unit="index"),
        Quantity(name="pdays_7_day_mean", label="Mean P-days, last 7 days", unit="index"),
    ),
    risk=Risk(
        levels=SEVERITY_LEVELS,
        criteria="Until 400 P-days since emergence, the total sets the risk: Low from 200, Moderate from 250, High "
        "from 300 (the usual first-spray threshold) and Very high from 350. From 400, the last 7 days' mean does: Very "
        "low below 1 a day, Low from 1, Moderate from 3, High from 5 and Very high from 9.",
    ),
    explorer=(
        ExplorerInput(
            name="tmin", label="Minimum temperature", unit="degC", minimum=-5, maximum=35, step=0.5, default=12
        ),
        ExplorerInput(
            name="tmax", label="Maximum temperature", unit="degC", minimum=-5, maximum=40, step=0.5, default=26
        ),
    ),
    sweep={"tmin": tuple(float(t) for t in range(-2, 34)), "tmax": tuple(float(t) for t in range(4, 40))},
    season=("05-01", "09-30"),
    biofix=Biofix(default="05-15", label="Crop emergence"),
    biofix_stage=("potato-stages", "EM"),  # emergence from a planting date, when one is given
    ingredients=(Ingredient(name="pdays", unit="index"),),
    accumulations=(
        Accumulation(name="pdays_total", of="pdays"),
        Accumulation(name="pdays_7_day_mean", of="pdays", how="mean", days=7),
    ),
    changelog=(
        Change(
            version="0.1",
            date="2026-10-28",
            note="Ported from the Crop Risk Tool; the last term weighs P(Tmax), as Sands et al.",
        ),
        Change(
            version="0.2",
            date="2026-11-03",
            note="P-day totals and their 7-day mean count from the biofix, as the risk does "
            "(were from the first day read).",
        ),
    ),
)


def development_rate(temperature_c) -> np.ndarray:
    """P(T): 0 below 7 °C, rising to 10 at 21 °C, falling to 0 at 30 °C."""
    t = np.asarray(temperature_c, dtype=float)
    rising = 10 * (1 - (t - 21) ** 2 / 196)  # (21 - 7)²
    falling = 10 * (1 - (t - 21) ** 2 / 81)  # (30 - 21)²
    p = np.where((t >= 7) & (t <= 21), rising, np.where((t > 21) & (t <= 30), falling, 0.0))
    return np.where(np.isnan(t), np.nan, p)


def pdays(tmin_c, tmax_c, last_term: str = "tmax") -> np.ndarray:
    """A day's P-days (0 to 10). `last_term="tmin"` reproduces the Crop Risk Tool and the old API."""
    lo, hi = np.asarray(tmin_c, dtype=float), np.asarray(tmax_c, dtype=float)
    p = development_rate
    last = p(hi) if last_term == "tmax" else p(lo)
    return (5 * p(lo) + 8 * p(2 * lo / 3 + hi / 3) + 8 * p(2 * hi / 3 + lo / 3) + 3 * last) / 24


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {"pdays": pdays(inputs["air_temperature_min"], inputs["air_temperature_max"])}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    return {name: values[name] for name in ("pdays", "pdays_total", "pdays_7_day_mean")}


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
    totals = with_accumulations(outputs, SPEC.accumulations, biofix_index)
    total, recent = totals["pdays_total"], totals["pdays_7_day_mean"]
    by_total, by_rate = level_reached(total, 200, 250, 300, 350), level_reached(recent, 1, 3, 5, 9)
    return np.where(total >= 400, by_rate, by_total)


def explore(tmin: float, tmax: float) -> dict[str, float]:
    return {"pdays": float(pdays(tmin, tmax))}
