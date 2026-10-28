"""The variable catalog: every gridded variable, its stored unit and encoding, and how it rolls up to days.

Stores keep each variable as int16 with a scale and offset (value = stored * scale + offset), which keeps
the archive small (PLAN.md §5.3); `encode`/`decode` do the packing, and the int16 minimum marks a missing
value. Units are symbols from `agdata.units` (SI, PLAN.md D18). A variable's QC range is what's physically
plausible in the service area; values outside it are treated as missing by QC (Phase 2).
"""

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from agdata.units import unit

DailyStat = Literal["min", "max", "mean", "sum"]

FILL = np.int16(np.iinfo(np.int16).min)  # missing
_INT16_MAX = np.iinfo(np.int16).max


@dataclass(frozen=True)
class Variable:
    name: str
    long_name: str
    unit: str
    scale: float
    offset: float = 0.0
    valid_min: float = -np.inf
    valid_max: float = np.inf
    daily: tuple[DailyStat, ...] = ()
    derived: bool = False  # computed from other variables at ingest, not read from a source
    notes: str = ""
    sources: dict[str, str] = field(default_factory=dict)  # source name → what it reads

    def __post_init__(self):
        unit(self.unit)  # a known unit
        lowest, highest = self.decode(np.array([FILL + 1, _INT16_MAX], dtype=np.int16))
        if lowest > self.valid_min or highest < self.valid_max:
            raise ValueError(
                f"{self.name}: int16 * {self.scale} + {self.offset} can't hold {self.valid_min}..{self.valid_max}"
            )

    def encode(self, values: np.ndarray) -> np.ndarray:
        """Floats in the stored unit → int16; NaN becomes FILL. Values must already be within the QC range."""
        values = np.asarray(values, dtype=np.float64)
        missing = ~np.isfinite(values)
        packed = np.round((np.where(missing, 0.0, values) - self.offset) / self.scale)
        if np.any((packed[~missing] <= FILL) | (packed[~missing] > _INT16_MAX)):
            raise ValueError(f"{self.name}: values outside what int16 can hold; run QC first")
        packed[missing] = FILL
        return packed.astype(np.int16)

    def decode(self, packed: np.ndarray) -> np.ndarray:
        """int16 → float64 in the stored unit; FILL becomes NaN."""
        packed = np.asarray(packed)
        values = packed.astype(np.float64) * self.scale + self.offset
        values[packed == FILL] = np.nan
        return values


VARIABLES: dict[str, Variable] = {
    v.name: v
    for v in [
        Variable(
            "air_temperature",
            "Air temperature at 2 m",
            "degC",
            scale=0.01,
            valid_min=-60,
            valid_max=60,
            daily=("min", "max", "mean"),
            sources={"urma": "TMP:2 m above ground"},
        ),
        Variable(
            "dew_point",
            "Dew point at 2 m",
            "degC",
            scale=0.01,
            valid_min=-70,
            valid_max=40,
            daily=("min", "max", "mean"),
            sources={"urma": "DPT:2 m above ground"},
        ),
        Variable(
            "relative_humidity",
            "Relative humidity at 2 m",
            "percent",
            scale=0.01,
            valid_min=0,
            valid_max=100,
            daily=("min", "max", "mean"),
            derived=True,
            notes="From air temperature and dew point (Magnus formula over water)",
        ),
        Variable(
            "wind_speed",
            "Wind speed at 10 m",
            "m_s",
            scale=0.01,
            valid_min=0,
            valid_max=75,
            daily=("mean", "max"),
            sources={"urma": "WIND:10 m above ground"},
        ),
        Variable(
            "wind_gust",
            "Wind gust at 10 m",
            "m_s",
            scale=0.01,
            valid_min=0,
            valid_max=100,
            daily=("max",),
            sources={"urma": "GUST:10 m above ground"},
        ),
        Variable(
            "wind_direction",
            "Wind direction at 10 m, from",
            "deg",
            scale=0.1,
            valid_min=0,
            valid_max=360,
            notes="Daily means of directions need vector averaging, so there is no plain daily statistic",
            sources={"urma": "WDIR:10 m above ground"},
        ),
        Variable(
            "surface_pressure",
            "Surface pressure",
            "kPa",
            scale=0.01,
            offset=80,
            valid_min=50,
            valid_max=110,
            daily=("mean",),
            sources={"urma": "PRES:surface"},
        ),
        Variable(
            "cloud_cover",
            "Total cloud cover",
            "percent",
            scale=0.01,
            valid_min=0,
            valid_max=100,
            daily=("mean",),
            sources={"urma": "TCDC:entire atmosphere (considered as a single layer)"},
        ),
        Variable(
            "precipitation",
            "Precipitation in the hour ending at the time",
            "mm",
            scale=0.01,
            valid_min=0,
            valid_max=300,
            daily=("sum",),
            notes="URMA hourly from 2017-12-05; before that only 6-hour totals (PLAN.md D6)",
            sources={"urma": "APCP:surface, 1-hour accumulation"},
        ),
        Variable(
            "shortwave_radiation",
            "Downward shortwave radiation at the surface, mean over the hour",
            "W_m2",
            scale=0.1,
            valid_min=0,
            valid_max=1500,
            daily=("sum",),
            notes="HRRR analysis, regridded (PLAN.md D7). The daily sum is in MJ/m² (W/m² x 3600 s / 1e6 per hour)",
            sources={"hrrr": "DSWRF:surface"},
        ),
        Variable(
            "et0",
            "FAO-56 grass reference evapotranspiration in the hour",
            "mm",
            scale=0.001,
            valid_min=0,
            valid_max=3,
            daily=("sum",),
            derived=True,
            notes="Hourly FAO-56 Penman-Monteith (PLAN.md D8)",
        ),
    ]
}


def variable(name: str) -> Variable:
    try:
        return VARIABLES[name]
    except KeyError:
        raise ValueError(f"unknown variable {name!r}") from None
