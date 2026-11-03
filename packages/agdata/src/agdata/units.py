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


@dataclass(frozen=True, kw_only=True)
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
        Unit(symbol="degC", label="°C", dimension="temperature", digits=1),
        Unit(symbol="degF", label="°F", dimension="temperature", factor=5 / 9, offset=-32 * 5 / 9, digits=0),
        Unit(symbol="K", label="K", dimension="temperature", offset=-273.15, digits=1),
        # temperature differences (dew point depression, a day's range): no offset (base °C)
        Unit(symbol="delta_degC", label="°C", dimension="temperature_difference", digits=1),
        Unit(symbol="delta_degF", label="°F", dimension="temperature_difference", factor=5 / 9, digits=0),
        # degree days and other temperature-time sums (base °C·d)
        Unit(symbol="degC_day", label="°C·d", dimension="degree_days", digits=0),
        Unit(symbol="degF_day", label="°F·d", dimension="degree_days", factor=5 / 9, digits=0),
        # depth of water: precipitation, ET (base mm; kg/m² of water is 1 mm)
        Unit(symbol="mm", label="mm", dimension="depth", digits=1),
        Unit(symbol="kg_m2", label="kg/m²", dimension="depth", digits=1),
        Unit(symbol="cm", label="cm", dimension="depth", factor=10, digits=1),
        Unit(symbol="in", label="in", dimension="depth", factor=25.4, digits=2),
        # speed (base m/s)
        Unit(symbol="m_s", label="m/s", dimension="speed", digits=1),
        Unit(symbol="km_h", label="km/h", dimension="speed", factor=1 / 3.6, digits=0),
        Unit(symbol="mph", label="mph", dimension="speed", factor=0.44704, digits=0),
        Unit(symbol="kn", label="kn", dimension="speed", factor=1852 / 3600, digits=0),
        # pressure (base kPa)
        Unit(symbol="kPa", label="kPa", dimension="pressure", digits=1),
        Unit(symbol="Pa", label="Pa", dimension="pressure", factor=0.001, digits=0),
        Unit(symbol="hPa", label="hPa", dimension="pressure", factor=0.1, digits=0),
        Unit(symbol="inHg", label="inHg", dimension="pressure", factor=3.386389, digits=2),
        # irradiance, a rate (base W/m²)
        Unit(symbol="W_m2", label="W/m²", dimension="irradiance", digits=0),
        # radiant exposure, a sum over time (base MJ/m²)
        Unit(symbol="MJ_m2", label="MJ/m²", dimension="radiant_exposure", digits=1),
        Unit(symbol="kWh_m2", label="kWh/m²", dimension="radiant_exposure", factor=3.6, digits=2),
        Unit(symbol="ly", label="ly", dimension="radiant_exposure", factor=0.041868, digits=0),
        # mass per area: biomass, yield (base kg/ha); a pound per acre is 0.45359237 kg per 0.40468564224 ha
        Unit(symbol="kg_ha", label="kg/ha", dimension="areal_mass", digits=0),
        Unit(symbol="lb_ac", label="lb/ac", dimension="areal_mass", factor=0.45359237 / 0.40468564224, digits=0),
        # fractions and angles (no conversion)
        Unit(symbol="percent", label="%", dimension="fraction", digits=0),
        Unit(symbol="deg", label="°", dimension="angle", digits=0),
        # counts
        Unit(symbol="day", label="d", dimension="duration", digits=0),
        Unit(symbol="hour", label="h", dimension="duration", factor=1 / 24, digits=0),
        Unit(symbol="index", label="", dimension="index", digits=1),  # model indices (DSVs, P-days): no conversion
    ]
}

# The unit each display system shows for a dimension; dimensions not listed show as stored
DISPLAY: dict[System, dict[str, str]] = {
    "metric": {
        "temperature": "degC",
        "temperature_difference": "delta_degC",
        "degree_days": "degC_day",
        "depth": "mm",
        "speed": "km_h",
        "pressure": "kPa",
        "radiant_exposure": "MJ_m2",
        "areal_mass": "kg_ha",
    },
    "imperial": {
        "temperature": "degF",
        "temperature_difference": "delta_degF",
        "degree_days": "degF_day",
        "depth": "in",
        "speed": "mph",
        "pressure": "inHg",
        "radiant_exposure": "MJ_m2",
        "areal_mass": "lb_ac",
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
