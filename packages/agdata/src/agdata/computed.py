"""Variables computed when they're read, from stored variables on the same time axis (PLAN.md Phase 6 C step 1).

Some variables are simple formulas of what the archive stores: water balance (precipitation minus ET0) is the
first. Storing them would add a copy to every store and a rebuild whenever their formula changed, for values that
cost one array operation to make. So they live here, not in `agdata.catalog`'s stored variables (which ingest,
rebuild, the stores and the downloads go through), and every reader computes them from their inputs:

- a point's days (`agdata.point.daily_at_point`) and hours (`agdata.series.cells_hours`);
- a map's steps (`agdata.series.combine`, called by `api.layermaps` on each input's read);
- `/variables`, `/layers`, the weather endpoints' `vars` and the API's units, which list them beside the stored ones.

A computed value is missing wherever any input is (D45: a raw value shows as missing). One that `adds_up` can be
summed over a range, and its total bridges gaps as each input's own does (`for_total`): water balance takes a day
without rain data as no rain and bridges ET0 across short gaps, each such day counted as estimated (D75). Its
running total from January 1 is stored with the others (`agdata.cumulative`).

A formula takes its inputs as keyword arrays in their stored units, of any shape, and returns the value in the
variable's unit. A computed variable's `version` is its formula's: an ETag already carries the code's version, so
nothing is rebuilt when it changes, but the methods page names it.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np

from agdata.catalog import DAILY_STATISTICS, DAILY_VARIABLES, GAP_FILL, VARIABLES, Variable
from agmodels import livestock

Axis = Literal["day", "hour"]


@dataclass(frozen=True, kw_only=True)
class Computed:
    variable: Variable  # its name, long name, unit and shown precision (`scale`); never stored, so never encoded
    axis: Axis
    inputs: tuple[str, ...]  # stored variables on the same axis: daily catalog names for "day", hourly for "hour"
    formula: Callable[..., np.ndarray]  # inputs by name (stored units) → the value
    adds_up: bool = False  # a range of it can be summed (a depth such as water balance; not a level)

    def __post_init__(self):
        stored = DAILY_VARIABLES if self.axis == "day" else VARIABLES
        unknown = [name for name in self.inputs if name not in stored]
        if unknown:
            raise ValueError(f"{self.variable.name}: {', '.join(unknown)} aren't stored {self.axis} variables")
        if self.variable.name in stored:
            raise ValueError(f"{self.variable.name} is a stored variable already")

    @property
    def name(self) -> str:
        return self.variable.name

    def compute(self, inputs: Mapping[str, np.ndarray]) -> np.ndarray:
        """The value from its inputs' arrays (all the same shape); NaN wherever any input is."""
        arrays = {name: np.asarray(inputs[name], dtype=np.float64) for name in self.inputs}
        with np.errstate(invalid="ignore"):
            value = np.asarray(self.formula(**arrays), dtype=np.float64)
        missing = np.zeros(value.shape, dtype=bool)
        for values in arrays.values():
            missing |= ~np.isfinite(values)
        value[missing] = np.nan
        return value

    def for_total(self, inputs: Mapping[str, np.ndarray], gaps: str = "estimate") -> tuple[np.ndarray, np.ndarray]:
        """Each step's value as a total adds it (steps on axis 0), and the steps estimated: each input's gaps
        filled by its own method (`agdata.catalog.GAP_FILL`: precipitation as none, the others bridged across up to
        `MAX_GAP_DAYS`), unless `gaps="missing"`. A step still missing an input is missing."""
        from agdata.grids import fill_cells  # Numba's kernels load with it: only when a total is asked

        filled: dict[str, np.ndarray] = {}
        estimated: np.ndarray | None = None
        for name in self.inputs:
            values = np.asarray(inputs[name], dtype=np.float64)
            method = GAP_FILL.get(name)
            if gaps == "estimate" and method is not None:
                values, mask = fill_cells(values, method=method)
            else:
                mask = np.zeros(values.shape, dtype=bool)
            filled[name] = values
            estimated = mask if estimated is None else estimated | mask
        value = self.compute(filled)
        assert estimated is not None
        return value, estimated & np.isfinite(value)


def _water_balance(precipitation_sum: np.ndarray, et0_sum: np.ndarray) -> np.ndarray:
    return precipitation_sum - et0_sum


def _thi(air_temperature, relative_humidity):
    return livestock.thi(air_temperature, relative_humidity)


def _cci(air_temperature, relative_humidity, wind_speed, shortwave_radiation):
    return livestock.cci(air_temperature, relative_humidity, wind_speed, shortwave_radiation)


_ALL = [
    Computed(
        variable=Variable(
            name="water_balance",
            long_name="Water balance (precipitation minus reference evapotranspiration), daily",
            unit="mm",
            scale=0.02,  # precipitation's daily precision; ET0's is 0.01
            offset=634,  # int16 at 0.02 holds −20 to 1290 mm about this offset (the check every Variable makes)
            valid_min=-20,
            valid_max=1280,
            derived=True,
            notes="Daily precipitation minus daily FAO-56 grass reference ET0, computed when read. Positive where "
            "rain exceeded the demand of a well-watered grass reference crop, negative where it fell short",
        ),
        axis="day",
        inputs=("precipitation_sum", "et0_sum"),
        formula=_water_balance,
        adds_up=True,
    ),
    Computed(
        variable=Variable(
            name="thi",
            long_name="Temperature humidity index",
            unit="index",
            scale=0.1,
            valid_min=-80,
            valid_max=140,
            derived=True,
            notes="The NRC (1971) temperature humidity index from air temperature and relative humidity "
            "(`agmodels.livestock`). Dairy cattle's milk yield begins to fall from 68; 72 is commonly taken as stress",
        ),
        axis="hour",
        inputs=("air_temperature", "relative_humidity"),
        formula=_thi,
    ),
    Computed(
        variable=Variable(
            name="cci",
            long_name="Cattle comfort index",
            unit="degC",
            scale=0.1,
            valid_min=-80,
            valid_max=90,
            derived=True,
            notes="Mader, Johnson and Gaughan's (2010) comprehensive climate index: air temperature adjusted for "
            "humidity, wind (brought from 10 m to 2 m) and solar radiation, as an apparent temperature "
            "(`agmodels.livestock`)",
        ),
        axis="hour",
        inputs=("air_temperature", "relative_humidity", "wind_speed", "shortwave_radiation"),
        formula=_cci,
    ),
]

DAILY_COMPUTED: dict[str, Computed] = {c.name: c for c in _ALL if c.axis == "day"}
HOURLY_COMPUTED: dict[str, Computed] = {c.name: c for c in _ALL if c.axis == "hour"}


def adds_up(name: str) -> bool:
    """Whether a daily variable's days can be summed over a range: daily sums (precipitation, ET0, sunlight), hour
    counts, Utah chill units (a day's sum of hourly weights) and a computed one that adds up (water balance)."""
    if name in DAILY_COMPUTED:
        return DAILY_COMPUTED[name].adds_up
    s = DAILY_STATISTICS.get(name)
    return (s is not None and s.stat == "sum") or DAILY_VARIABLES[name].unit in ("hour", "chill_units")


def computed(name: str) -> Computed | None:
    """The computed variable of that name, daily or hourly, or None if it's stored or unknown."""
    return DAILY_COMPUTED.get(name) or HOURLY_COMPUTED.get(name)


def expand(names, table: Mapping[str, Computed]) -> list[str]:
    """`names` with each computed one (of `table`'s axis) replaced by its inputs, stored names kept, in first-seen
    order without repeats: what to read for them."""
    out: dict[str, None] = {}
    for name in names:
        c = table.get(name)
        for each in c.inputs if c is not None else (name,):
            out[each] = None
    return list(out)


def complete(values: dict[str, np.ndarray], names, table: Mapping[str, Computed]) -> dict[str, np.ndarray]:
    """`values` (read for `expand(names, table)`) with each computed name in `names` added, and only `names` kept."""
    for name in names:
        c = table.get(name)
        if c is not None:
            values[name] = c.compute(values)
    return {name: values[name] for name in names if name in values}
