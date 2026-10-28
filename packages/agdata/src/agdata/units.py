"""Units: the one place conversion factors live in Python (PLAN.md D18).

Stores hold SI (°C, mm, m/s, kPa, W/m², MJ/m²) except degree days, which stay in the unit each model is
defined in (mostly °F·d). Values are converted only at the edges: source adapters convert into the stored
unit, and the API converts out to what a request asks for. `frontend/lib/units.ts` mirrors this table for
display, and both are tested against `tests/fixtures/units_cases.json` so they can't drift.

Every unit is affine to its dimension's base unit: base = value * factor + offset.
"""

from dataclasses import dataclass
from typing import Literal, overload

import numpy as np

System = Literal["metric", "imperial"]


@dataclass(frozen=True)
class Unit:
    symbol: str
    label: str
    dimension: str
    factor: float = 1.0
    offset: float = 0.0
    digits: int = 1  # decimals shown by default


UNITS: dict[str, Unit] = {
    unit.symbol: unit
    for unit in [
        # temperature (base °C)
        Unit("degC", "°C", "temperature", digits=1),
        Unit("degF", "°F", "temperature", factor=5 / 9, offset=-32 * 5 / 9, digits=0),
        Unit("K", "K", "temperature", offset=-273.15, digits=1),
        # degree days and other temperature-time sums (base °C·d)
        Unit("degC_day", "°C·d", "degree_days", digits=0),
        Unit("degF_day", "°F·d", "degree_days", factor=5 / 9, digits=0),
        # depth of water: precipitation, ET (base mm; kg/m² of water is 1 mm)
        Unit("mm", "mm", "depth", digits=1),
        Unit("kg_m2", "kg/m²", "depth", digits=1),
        Unit("cm", "cm", "depth", factor=10, digits=1),
        Unit("in", "in", "depth", factor=25.4, digits=2),
        # speed (base m/s)
        Unit("m_s", "m/s", "speed", digits=1),
        Unit("km_h", "km/h", "speed", factor=1 / 3.6, digits=0),
        Unit("mph", "mph", "speed", factor=0.44704, digits=0),
        Unit("kn", "kn", "speed", factor=1852 / 3600, digits=0),
        # pressure (base kPa)
        Unit("kPa", "kPa", "pressure", digits=1),
        Unit("Pa", "Pa", "pressure", factor=0.001, digits=0),
        Unit("hPa", "hPa", "pressure", factor=0.1, digits=0),
        Unit("inHg", "inHg", "pressure", factor=3.386389, digits=2),
        # irradiance, a rate (base W/m²)
        Unit("W_m2", "W/m²", "irradiance", digits=0),
        # radiant exposure, a sum over time (base MJ/m²)
        Unit("MJ_m2", "MJ/m²", "radiant_exposure", digits=1),
        Unit("kWh_m2", "kWh/m²", "radiant_exposure", factor=3.6, digits=2),
        Unit("ly", "ly", "radiant_exposure", factor=0.041868, digits=0),
        # fractions and angles (no conversion)
        Unit("percent", "%", "fraction", digits=0),
        Unit("deg", "°", "angle", digits=0),
    ]
}

# The unit each display system shows for a dimension; dimensions not listed show as stored
DISPLAY: dict[System, dict[str, str]] = {
    "metric": {
        "temperature": "degC",
        "degree_days": "degC_day",
        "depth": "mm",
        "speed": "km_h",
        "pressure": "kPa",
        "radiant_exposure": "MJ_m2",
    },
    "imperial": {
        "temperature": "degF",
        "degree_days": "degF_day",
        "depth": "in",
        "speed": "mph",
        "pressure": "inHg",
        "radiant_exposure": "MJ_m2",
    },
}


def unit(symbol: str) -> Unit:
    try:
        return UNITS[symbol]
    except KeyError:
        raise ValueError(f"unknown unit {symbol!r}") from None


@overload
def convert(value: None, from_unit: str, to_unit: str) -> None: ...
@overload
def convert(value: float, from_unit: str, to_unit: str) -> float: ...
@overload
def convert(value: np.ndarray, from_unit: str, to_unit: str) -> np.ndarray: ...
def convert(value, from_unit: str, to_unit: str):
    """Converts a number or array between units of one dimension. NaN stays NaN; None stays None."""
    if value is None or from_unit == to_unit:
        return value
    source, target = unit(from_unit), unit(to_unit)
    if source.dimension != target.dimension:
        raise ValueError(f"can't convert {source.label} ({source.dimension}) to {target.label} ({target.dimension})")
    base = np.asarray(value, dtype=float) * source.factor + source.offset
    result = (base - target.offset) / target.factor
    return float(result) if np.ndim(result) == 0 else result


def display_unit(stored_unit: str, system: System) -> str:
    """The unit a value stored in `stored_unit` is shown in for a display system."""
    return DISPLAY[system].get(unit(stored_unit).dimension, stored_unit)


def to_display(value, stored_unit: str, system: System):
    return convert(value, stored_unit, display_unit(stored_unit, system))
