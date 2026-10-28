"""The variable catalog: every gridded variable, its stored unit and encoding, and how it rolls up to days.

Stores keep each variable as int16 with a scale and offset (value = stored * scale + offset), which keeps
the archive small (PLAN.md §5.3); `encode`/`decode` do the packing, and the int16 minimum marks a missing
value. Scales are the stored precision (D21): coarser than URMA's 0.01, whose last digit is noise at the
analysis's accuracy and doesn't compress (docs/pilot.md). Units are symbols from `agdata.units` (SI, D18).
A variable's QC range is what's physically plausible in the service area; values outside it are treated as
missing by QC (Phase 2).
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
    fillable: bool = True  # short gaps may be interpolated in time (not for sums like precip, or directions)
    spike_c: float | None = None  # QC: a value this far from both neighbors in time, the same way, is a spike
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
            spike_c=12,
            scale=0.1,
            valid_min=-60,
            valid_max=60,
            daily=("min", "max", "mean"),
            sources={"urma": "TMP:2 m above ground"},
        ),
        Variable(
            "dew_point",
            "Dew point at 2 m",
            "degC",
            spike_c=12,
            scale=0.1,
            valid_min=-70,
            valid_max=40,
            daily=("min", "max", "mean"),
            sources={"urma": "DPT:2 m above ground"},
        ),
        Variable(
            "relative_humidity",
            "Relative humidity at 2 m",
            "percent",
            scale=1,
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
            scale=0.1,
            valid_min=0,
            valid_max=75,
            daily=("mean", "max"),
            sources={"urma": "WIND:10 m above ground"},
        ),
        Variable(
            "wind_gust",
            "Wind gust at 10 m",
            "m_s",
            scale=0.1,
            valid_min=0,
            valid_max=100,
            daily=("max",),
            sources={"urma": "GUST:10 m above ground"},
        ),
        Variable(
            "wind_direction",
            "Wind direction at 10 m, from",
            "deg",
            fillable=False,
            scale=1,
            valid_min=0,
            valid_max=360,
            notes="Daily means of directions need vector averaging, so there is no plain daily statistic",
            sources={"urma": "WDIR:10 m above ground"},
        ),
        Variable(
            "surface_pressure",
            "Surface pressure",
            "kPa",
            scale=0.1,
            valid_min=50,
            valid_max=110,
            daily=("mean",),
            sources={"urma": "PRES:surface"},
        ),
        Variable(
            "cloud_cover",
            "Total cloud cover",
            "percent",
            scale=1,
            valid_min=0,
            valid_max=100,
            daily=("mean",),
            sources={"urma": "TCDC:entire atmosphere (considered as a single layer)"},
        ),
        Variable(
            "precipitation",
            "Precipitation in the hour ending at the time",
            "mm",
            fillable=False,
            scale=0.1,
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
            notes="HRRR, mean of the hour's four 15-minute values, regridded (D7). Daily sums in MJ/m² (W/m² x 0.0036)",
            sources={"hrrr": "DSWRF:surface, wrfsubhf01"},
        ),
        Variable(
            "soil_temperature_4cm",
            "Soil temperature at 4 cm",
            "degC",
            scale=0.1,
            valid_min=-40,
            valid_max=60,
            daily=("min", "max", "mean"),
            notes="HRRR's land-surface model, regridded (D9); the potato model's 2 in depth",
            sources={"hrrr": "TSOIL:0.04-0.04 m below ground"},
        ),
        Variable(
            "soil_temperature_10cm",
            "Soil temperature at 10 cm",
            "degC",
            scale=0.1,
            valid_min=-40,
            valid_max=60,
            daily=("min", "max", "mean"),
            notes="HRRR's land-surface model, regridded (D9); the potato model's 4 in depth",
            sources={"hrrr": "TSOIL:0.1-0.1 m below ground"},
        ),
        Variable(
            "et0",
            "FAO-56 grass reference evapotranspiration in the hour",
            "mm",
            fillable=False,
            scale=0.001,
            valid_min=0,
            valid_max=3,
            daily=("sum",),
            derived=True,
            notes="Hourly FAO-56 Penman-Monteith (PLAN.md D8)",
        ),
    ]
}


# Daily statistics (PLAN.md §5.2): each hourly variable's `daily` stats over each cell's local calendar day.
# Min, max and mean keep the hourly unit and precision; sums have their own (shortwave's in MJ/m²).
DAILY_MIN_HOURS = 20  # min, max and mean need this many hours of the day; sums need every hour (D25)
_SUMS: dict[str, tuple[str, float, float, float]] = {
    # hourly name: (unit, factor from the hourly unit, scale, valid max)
    "precipitation": ("mm", 1.0, 0.1, 1000),
    "shortwave_radiation": ("MJ_m2", 0.0036, 0.01, 50),  # W/m² mean over an hour → MJ/m²
    "et0": ("mm", 1.0, 0.01, 20),
}


@dataclass(frozen=True)
class DailyStatistic:
    variable: Variable  # stored in the daily store
    hourly: str
    stat: DailyStat
    factor: float = 1.0  # hourly unit → daily unit


def _daily_statistic(v: Variable, stat: DailyStat) -> DailyStatistic:
    name = f"{v.name}_{stat}"
    if stat == "sum":
        unit_, factor, scale, high = _SUMS[v.name]
        long_name = f"{v.long_name}, daily total"
        daily = Variable(name, long_name, unit_, scale=scale, valid_min=0, valid_max=high)
        return DailyStatistic(daily, v.name, stat, factor)
    long_name = f"{v.long_name}, daily {stat}"
    daily = Variable(
        name, long_name, v.unit, scale=v.scale, offset=v.offset, valid_min=v.valid_min, valid_max=v.valid_max
    )
    return DailyStatistic(daily, v.name, stat)


DAILY_STATISTICS: dict[str, DailyStatistic] = {
    s.variable.name: s for v in VARIABLES.values() for s in (_daily_statistic(v, stat) for stat in v.daily)
}
DAILY_VARIABLES: dict[str, Variable] = {name: s.variable for name, s in DAILY_STATISTICS.items()}


# Running totals from local January 1 (D26, D27): any range is cum[end] - cum[start - 1]. Degree days are
# cubes per threshold: single sine is linear, so a sine pair is the difference of its two thresholds' cubes.
# Thresholds are those the planned models use (°F, D18); corn's modified average isn't linear, so it has its own.
DD_SINE_THRESHOLDS_F: tuple[float, ...] = (39.2, 41, 42.8, 45, 48, 50, 52, 55, 80.1, 86, 90, 92)
DD_MODIFIED_PAIRS_F: tuple[tuple[float, float], ...] = ((50, 86),)
_DD_RANGE = {"scale": 0.5, "valid_min": 0, "valid_max": 16000}  # a base-39.2 year in Florida is about 13,000


def dd_name(method: Literal["sine", "modified"], base: float, upper: float | None = None) -> str:
    """`dd_sine_39p2`, `dd_modified_50_86`: the legacy naming, with the method."""

    def f(t: float) -> str:
        return f"{t:g}".replace(".", "p")

    return f"dd_{method}_{f(base)}" + (f"_{f(upper)}" if upper is not None else "")


def _cumulative() -> list[Variable]:
    dd = [
        Variable(dd_name("sine", t), f"Single-sine degree days above {t:g} °F since Jan 1", "degF_day", **_DD_RANGE)
        for t in DD_SINE_THRESHOLDS_F
    ] + [
        Variable(
            dd_name("modified", base, upper),
            f"Modified-average degree days {base:g}/{upper:g} °F since Jan 1",
            "degF_day",
            **_DD_RANGE,
        )
        for base, upper in DD_MODIFIED_PAIRS_F
    ]
    totals = [
        Variable("precipitation", "Precipitation since Jan 1", "mm", scale=0.2, valid_min=0, valid_max=6000),
        Variable("et0", "FAO-56 grass reference ET since Jan 1", "mm", scale=0.1, valid_min=0, valid_max=3000),
    ]
    # Running counts of days in the totals that were estimated across a gap or left out (D25). Every DD cube
    # comes from the daily min and max temperature, so they share the temperature counts
    counts = [
        Variable(
            f"{basis}_{kind}_days", f"Days with {basis} {kind} since Jan 1", "day", scale=1, valid_min=0, valid_max=366
        )
        for basis, kinds in (
            ("temperature", ("estimated", "missing")),
            ("precipitation", ("missing",)),
            ("et0", ("estimated", "missing")),
        )
        for kind in kinds
    ]
    return dd + totals + counts


CUMULATIVE_VARIABLES: dict[str, Variable] = {v.name: v for v in _cumulative()}


def variable(name: str) -> Variable:
    try:
        return VARIABLES[name]
    except KeyError:
        raise ValueError(f"unknown variable {name!r}") from None
