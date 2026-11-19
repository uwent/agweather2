"""Custom degree days: any base and upper threshold, method, unit and biofix.

The same functions as every other model (`agmodels.degree_days`): single sine with a horizontal cutoff
(Baskerville and Emin 1969), simple average, or modified average (the corn GDD method). An upper threshold caps
the minimum and maximum before averaging in both averages, as the API's calculator does; the modified average also
raises a minimum below the base to it. Thresholds are given in the
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
from agmodels.spec import Biofix, Change, Check, Citation, ExplorerInput, Input, ModelSpec, Option, Quantity

METHOD = Option(
    name="method",
    label="Method",
    choices=(("sine", "Single sine"), ("average", "Simple average"), ("modified", "Modified average (corn GDD)")),
    default="sine",
)
UNIT = Option(name="unit", label="Unit of the thresholds", choices=(("F", "°F"), ("C", "°C")), default="F")
BASE = Option(
    name="base", label="Base (lower threshold)", choices=(("41", "41"), ("50", "50"), ("10", "10")), default="50"
)
UPPER = Option(
    name="upper",
    label="Upper threshold (none for no cutoff)",
    choices=(("none", "None"), ("86", "86"), ("30", "30")),
    default="86",
)

SPEC = ModelSpec(
    id="custom-degree-days",
    name="Custom degree days",
    group="degree_days",
    version="0.2",
    checks=(
        Check(
            kind="published",
            against="Baskerville and Emin's single-sine method (1969), worked numerically and by hand",
            result="Our single-sine degree days agree with a numerical integral of the method's own temperature curve within 0.0002 degree days in 8 test cases.",
            report="docs/validation/models/custom-degree-days.md#against-the-method-and-the-old-api",
        ),
        Check(
            kind="system",
            against="The old AgWeather service's degree-day calculator, which AgWeather replaces",
            result="All three methods match the old calculator within 0.000001 degree days in 11,781 combinations of thresholds and temperatures.",
            report="docs/validation/models/custom-degree-days.md#against-the-method-and-the-old-api",
        ),
        Check(
            kind="system",
            against="The old AgWeather service at Waunakee, Wisconsin, each on its own weather data",
            result="From January 1 to October 31, 2026, our single-sine total (base 50 °F, upper 86 °F) was 3,184 degree days against the old service's 3,203, 0.6% lower.",
            report="docs/validation/models/custom-degree-days.md#on-the-archives-weather",
        ),
    ),
    status="beta",
    summary="Degree days since a biofix, with any base and upper threshold, method and unit.",
    topics=("degree-days",),
    crops=(),
    citations=(
        Citation(
            text="Baskerville, G. L. and Emin, P. (1969). Rapid estimation of heat accumulation from maximum and minimum temperatures. Ecology 50, 514–517.",
            doi="10.2307/1933912",
        ),
    ),
    inputs=(
        Input(name="air_temperature_min", label="Minimum temperature", unit="degC"),
        Input(name="air_temperature_max", label="Maximum temperature", unit="degC"),
    ),
    outputs=(
        Quantity(name="dd_total", label="Degree days since the biofix", unit="degF_day"),
        Quantity(name="dd", label="Degree days", unit="degF_day"),
    ),
    risk=None,
    explorer=(
        ExplorerInput(
            name="min_temp", label="Minimum temperature", unit="degF", minimum=-20, maximum=100, step=1, default=50
        ),
        ExplorerInput(
            name="max_temp", label="Maximum temperature", unit="degF", minimum=-10, maximum=115, step=1, default=80
        ),
    ),
    explorer_outputs=(
        Quantity(name="sine", label="Single sine degree days (base 50 °F, upper 86 °F)", unit="degF_day"),
        Quantity(name="modified", label="Modified degree days (base 50 °F, upper 86 °F)", unit="degF_day"),
        Quantity(name="average", label="Simple average degree days (base 50 °F)", unit="degF_day"),
    ),
    sweep={
        "min_temp": tuple(float(t) for t in range(30, 91, 5)),
        "max_temp": tuple(float(t) for t in range(40, 111, 5)),
    },
    options=(METHOD, UNIT, BASE, UPPER),
    biofix=Biofix(default="01-01", label="January 1, or any date (planting, an insect's first catch)"),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="First version."),
        Change(
            version="0.2",
            date="2026-11-19",
            note="The simple average takes an upper threshold (both temperatures capped at it before averaging), as the API's degree-day calculator does; it was refused, so the model's default upper of 86 °F made the simple average fail.",
        ),
    ),
)


def daily(min_temp, max_temp, method: str, base: float, upper: float | None) -> np.ndarray:
    """One day's degree days, thresholds and temperatures in one unit."""
    if method == "sine":
        return degree_days_sine(min_temp, max_temp, base, upper)
    if method == "modified":
        return degree_days_modified(min_temp, max_temp, base, upper)
    if method == "average":
        return degree_days_average(min_temp, max_temp, base, upper)
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
