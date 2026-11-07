"""Variables computed when they're read, from stored variables on the same time axis (PLAN.md Phase 6 C step 1).

Some variables are simple formulas of what the archive stores: water balance (precipitation minus ET0) is the
first. Storing them would add a copy to every store and a rebuild whenever their formula changed, for values that
cost one array operation to make. So they live here, not in `agdata.catalog`'s stored variables (which ingest,
rebuild, the stores and the downloads go through), and every reader computes them from their inputs:

- a point's days (`agdata.point.daily_at_point`) and hours (`agdata.series.cells_hours`);
- a map's steps (`agdata.series.combine`, called by `api.layermaps` on each input's read);
- `/variables`, `/layers`, the weather endpoints' `vars` and the API's units, which list them beside the stored ones.

A computed value is missing wherever any input is (D45: a raw value shows as missing). How a range of them is
totalled is the variable's own rule, given where it's used (water balance's, D75, at Phase 6 C step 3).

A formula takes its inputs as keyword arrays in their stored units, of any shape, and returns the value in the
variable's unit. A computed variable's `version` is its formula's: an ETag already carries the code's version, so
nothing is rebuilt when it changes, but the methods page names it.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np

from agdata.catalog import DAILY_VARIABLES, VARIABLES, Variable

Axis = Literal["day", "hour"]


@dataclass(frozen=True, kw_only=True)
class Computed:
    variable: Variable  # its name, long name, unit and shown precision (`scale`); never stored, so never encoded
    axis: Axis
    inputs: tuple[str, ...]  # stored variables on the same axis: daily catalog names for "day", hourly for "hour"
    formula: Callable[..., np.ndarray]  # inputs by name (stored units) → the value

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


def _water_balance(precipitation_sum: np.ndarray, et0_sum: np.ndarray) -> np.ndarray:
    return precipitation_sum - et0_sum


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
    ),
]

DAILY_COMPUTED: dict[str, Computed] = {c.name: c for c in _ALL if c.axis == "day"}
HOURLY_COMPUTED: dict[str, Computed] = {c.name: c for c in _ALL if c.axis == "hour"}


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
