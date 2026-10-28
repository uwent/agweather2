"""Custom degree days: any base and upper threshold, method, unit and biofix.

The same functions as every other model (`agmodels.degree_days`): single sine with a horizontal cutoff
(Baskerville and Emin 1969), simple average, or modified average (the corn GDD method). Thresholds are given in the
unit chosen (°F, as the legacy models are, or °C); degree days are linear in the temperature scale for all three
methods, so they're computed in °F with the thresholds converted and always come out in °F·d, the declared unit
(°C·d are 5/9 of them, converted for display like any other value). In the box, a sine
pair whose thresholds both have cubes is the difference of two cubes (D26); any other is computed from the daily
minimum and maximum on the fly.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.accumulate import running_total
from agmodels.crops import number_option
from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Option, Quantity

METHOD = Option(
    "method",
    "Method",
    (("sine", "Single sine"), ("average", "Simple average"), ("modified", "Modified average (corn GDD)")),
    "sine",
)
UNIT = Option("unit", "Unit of the thresholds", (("F", "°F"), ("C", "°C")), "F")
BASE = Option("base", "Base (lower threshold)", (("41", "41"), ("50", "50"), ("10", "10")), "50")
UPPER = Option("upper", "Upper threshold (none for no cutoff)", (("none", "None"), ("86", "86"), ("30", "30")), "86")

SPEC = ModelSpec(
    id="degree-days",
    name="Custom degree days",
    group="degree_days",
    version="1.0",
    status="stable",
    summary="Degree days since a biofix, with any base and upper threshold, method and unit.",
    topics=("degree-days",),
    crops=(),
    citations=(
        Citation(
            "Baskerville, G. L. and Emin, P. (1969). Rapid estimation of heat accumulation from maximum and minimum "
            "temperatures. Ecology 50, 514–517.",
            doi="10.2307/1933912",
        ),
    ),
    inputs=(
        Quantity("air_temperature_min", "Minimum temperature", "degC"),
        Quantity("air_temperature_max", "Maximum temperature", "degC"),
    ),
    outputs=(
        Quantity("dd_total", "Degree days since the biofix", "degF_day"),
        Quantity("dd", "Degree days", "degF_day"),
    ),
    risk=None,
    explorer=(
        ExplorerInput("min_temp", "Minimum temperature", "degF", -20, 100, 1, 50),
        ExplorerInput("max_temp", "Maximum temperature", "degF", -10, 115, 1, 80),
    ),
    sweep={
        "min_temp": tuple(float(t) for t in range(30, 91, 5)),
        "max_temp": tuple(float(t) for t in range(40, 111, 5)),
    },
    options=(METHOD, UNIT, BASE, UPPER),
    biofix=Biofix("01-01", "January 1, or any date (planting, an insect's first catch)"),
    changelog=(Change("1.0", "2026-10-28", "First version."),),
)


def daily(min_temp, max_temp, method: str, base: float, upper: float | None) -> np.ndarray:
    """One day's degree days, thresholds and temperatures in one unit."""
    if method == "sine":
        return degree_days_sine(min_temp, max_temp, base, upper)
    if method == "modified":
        return degree_days_modified(min_temp, max_temp, base, upper)
    if method == "average":
        if upper is not None:
            raise ValueError("the simple average has no upper threshold; use the modified average")
        return degree_days_average(min_temp, max_temp, base)
    raise ValueError(f"unknown method {method!r}")


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    lo, hi = (np.asarray(inputs[k], dtype=float) * 1.8 + 32 for k in ("air_temperature_min", "air_temperature_max"))
    to_f = (lambda t: t) if options.get(UNIT.name, UNIT.default) == "F" else (lambda t: t * 1.8 + 32)
    upper = options.get(UPPER.name, UPPER.default)
    dd = daily(
        lo,
        hi,
        options.get(METHOD.name, METHOD.default),
        to_f(number_option(options, BASE)),
        None if upper == "none" else to_f(number_option(options, UPPER)),
    )
    return {"dd_total": running_total(dd, biofix_index), "dd": dd}


def explore(min_temp: float, max_temp: float) -> dict[str, float]:
    """Each method's degree days at base 50 °F and upper 86 °F (none for the simple average)."""
    lo, hi = np.asarray(min_temp), np.asarray(max_temp)
    return {
        "sine": float(daily(lo, hi, "sine", 50, 86)),
        "modified": float(daily(lo, hi, "modified", 50, 86)),
        "average": float(daily(lo, hi, "average", 50, None)),
    }
