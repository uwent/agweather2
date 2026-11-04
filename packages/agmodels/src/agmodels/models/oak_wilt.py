"""Oak wilt: the risk of transmission by its sap beetle vectors (Colopterus truncatus, then Carpophilus sayi).

Vector flight from degree days (base 41 °F, from January 1; Jagemann et al. 2018), with risk reduced from July
15 as the wounds that let beetles carry the fungus become rare (two levels down, at most Low, and one more a week
later). Ported from VDIFN (`app/models/insects/oak_wilt.rb`) with parity tests; VDIFN's freeze reduction (from
November) never applies, since risk is already Very low by then.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import running_total
from agmodels.degree_days import degree_days_sine
from agmodels.spec import SEVERITY_LEVELS, Biofix, Change, Citation, ExplorerInput, ModelSpec, Quantity, Risk

# Degree-day bounds of each flight level (C. truncatus, C. sayi)
FLIGHT = ((180, 0), (231, 1), (283, 2), (388, 3), (913, 4), (1792, 3), (2172, 2), (np.inf, 1))
JULY_15, JULY_22 = 196, 203  # day of year in a common year (a leap year's are one later)

SPEC = ModelSpec(
    id="oak-wilt-vectors",
    name="Oak wilt vector flight",
    group="insect",
    version="0.2",
    status="stable",
    summary="The risk of oak wilt spreading by its beetle vectors, from their flight timed by degree days (base "
    "41 °F) and the season (wounding before mid-July).",
    topics=("oak-wilt",),
    crops=("Oak",),
    citations=(
        Citation(
            text="Jagemann, S. M., Juzwik, J., Tobin, P. C. and Raffa, K. F. (2018). Seasonal and regional "
            "distributions, degree-day models, and phoresy rates of the major sap beetle (Coleoptera: Nitidulidae) "
            "vectors of the oak wilt fungus, Bretziella fagacearum, in Wisconsin. Environmental Entomology 47, "
            "1152–1164.",
            doi="10.1093/ee/nvy080",
        ),
    ),
    inputs=(
        Quantity(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Quantity(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="dd_total", label="Degree days since January 1 (base 41 °F)", unit="degF_day"),
        Quantity(name="dd", label="Degree days", unit="degF_day"),
        Quantity(name="flight", label="Vector flight level", unit="index"),
    ),
    risk=Risk(
        levels=SEVERITY_LEVELS,
        criteria="Vector flight by degree days: Low from 180 (under 5% of C. truncatus flying), Moderate from 231, "
        "High from 283, Very high from 388 to 913 (peak flight), then High to 1,792, Moderate to 2,172 and Low after. "
        "From July 15 two levels lower and at most Low; from July 22 one lower again.",
    ),
    explorer=(
        ExplorerInput(
            name="dd_total",
            label="Degree days since January 1",
            unit="degF_day",
            minimum=0,
            maximum=3000,
            step=10,
            default=500,
        ),
        ExplorerInput(
            name="day_of_year", label="Day of the year", unit="day", minimum=1, maximum=365, step=1, default=150
        ),
    ),
    explorer_outputs=(
        Quantity(name="risk", label="Risk level", unit="index", description="Index into the risk levels"),
    ),
    sweep={"dd_total": tuple(float(d) for d in range(0, 3001, 100)), "day_of_year": (120.0, 196.0, 203.0)},
    context=("day_of_year", "year"),
    season=("03-01", "07-31"),
    biofix=Biofix(default="01-01", label="January 1"),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from VDIFN."),
        Change(
            version="0.2",
            date="2026-11-01",
            note="The July 15 and July 22 reductions apply to runs, not only the explorer (the spec didn't ask the "
            "runner for the day of the year), and fall on those dates in leap years too.",
        ),
    ),
)


def flight_level(dd_total) -> np.ndarray:
    total = np.asarray(dd_total, dtype=float)
    level = np.select([total < bound for bound, _ in FLIGHT], [lvl for _, lvl in FLIGHT], 1).astype(float)
    return np.where(np.isnan(total), np.nan, level)


def seasonal(level, day_of_year, year=None) -> np.ndarray:
    """The flight level lowered for the season: at most Low from July 15 (two levels down), one more from July 22
    (wounds made after mid-July rarely lead to infection). `year` (optional) puts the dates right in leap years."""
    level = np.asarray(level, dtype=float)
    shape = (-1, *([1] * (level.ndim - 1))) if level.ndim else ()
    doy = np.asarray(day_of_year, dtype=float).reshape(shape) if level.ndim else np.asarray(day_of_year, dtype=float)
    leap = 0.0
    if year is not None:
        y = np.asarray(year, dtype=float)
        y = y.reshape(shape) if level.ndim else y
        leap = ((y % 4 == 0) & ((y % 100 != 0) | (y % 400 == 0))).astype(float)
    after = np.where(doy >= JULY_15 + leap, np.minimum(level - 2, 1), level)
    after = np.where(doy >= JULY_22 + leap, after - 1, after)
    return np.where(np.isnan(level), np.nan, np.maximum(after, 0))


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
    dd = degree_days_sine(lo, hi, 41)
    total = running_total(dd, biofix_index)
    flight = flight_level(total)
    out = {"dd_total": total, "dd": dd, "flight": flight}
    if "day_of_year" in inputs:
        out["seasonal"] = seasonal(flight, inputs["day_of_year"], inputs.get("year"))
    return out


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    return np.asarray(outputs.get("seasonal", outputs["flight"]), dtype=float)


def explore(dd_total: float, day_of_year: float) -> dict[str, float]:
    return {"risk": float(seasonal(flight_level(dd_total), day_of_year))}
