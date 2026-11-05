"""Mappable layers (PLAN.md Phase 5 E, docs/api.md "Grids"): what `/layers` lists and `/grids/{layer}` reads.

A layer is a catalog variable on the grid with a time axis: a daily variable (local days, `agdata.daily`), an
hourly one (hours by their UTC end), a running total from January 1 (`agdata.cumulative`), or degree days for any
setting (`degree_days`, computed from each day's minimum and maximum, the same way as at points). Model outputs
(Phase 5 F) and normals and departures (Phase 6, time axis `day_of_year`) join the list later without changing
what's here.

`stats` are the statistics a range of steps can be reduced to: mean, min and max for any level, and sum where the
values add up (precipitation, ET0, shortwave, hour counts, degree days). A running total has none: each day is
already a total. `palette` names a color scale the frontend owns (Phase 6); layers of one kind share it, so a
legend means the same thing on every map that uses it.
"""

from dataclasses import dataclass
from typing import Literal

from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_STATISTICS, DAILY_VARIABLES, VARIABLES, Variable

TimeAxis = Literal["day", "hour", "day_of_year"]
Source = Literal["daily", "hourly", "cumulative", "degree_days"]
Stat = Literal["sum", "mean", "min", "max"]
LEVEL_STATS: tuple[Stat, ...] = ("mean", "min", "max")
SUM_STATS: tuple[Stat, ...] = ("sum", "mean", "min", "max")
DEGREE_DAYS = "degree_days"
DD_STEP = 0.1  # °F·d: daily values from temperatures stored to 0.1 °C


@dataclass(frozen=True, kw_only=True)
class Layer:
    id: str
    name: str
    group: Literal["weather", "running_total", "degree_days"]  # for pickers
    time_axis: TimeAxis
    source: Source
    variable: str | None  # the catalog variable read; None for degree days (computed from min and max)
    unit: str
    step: float  # the stored precision, in `unit`
    palette: str
    stats: tuple[Stat, ...]
    description: str = ""

    @property
    def summable(self) -> bool:
        return "sum" in self.stats


# Palettes by name: the first prefix that matches wins
_PALETTES = (
    ("dd_", "degree_days"),
    ("dew_point_depression", "dew_point_depression"),
    ("soil_temperature", "soil_temperature"),
    ("air_temperature", "temperature"),
    ("dew_point", "temperature"),
    ("temperature_", "temperature"),
    ("relative_humidity", "humidity"),
    ("wind_direction", "direction"),
    ("wind", "wind"),
    ("surface_pressure", "pressure"),
    ("cloud_cover", "cloud"),
    ("precipitation", "precipitation"),
    ("shortwave", "radiation"),
    ("snow", "snow"),
    ("et0", "evapotranspiration"),
    ("hours_", "hours"),
)
# Internal variables that aren't layers: HRRR's shortwave before correction, the daily ET0 estimate the running
# totals use for days missing hours, and the running counts of estimated and missing days
_LEFT_OUT = {"shortwave_radiation_hrrr", "et0_sum_estimate"}


def palette_for(name: str) -> str:
    return next((palette for prefix, palette in _PALETTES if name.startswith(prefix)), "default")


def _daily_stats(v: Variable) -> tuple[Stat, ...]:
    s = DAILY_STATISTICS.get(v.name)
    return SUM_STATS if (s is not None and s.stat == "sum") or v.unit == "hour" else LEVEL_STATS


def _hourly_stats(v: Variable) -> tuple[Stat, ...]:
    if v.name == "wind_direction":
        return ()  # an angle's mean isn't the mean of its numbers
    return SUM_STATS if v.name in ("precipitation", "et0") else LEVEL_STATS


def _layers() -> list[Layer]:
    found = [
        Layer(
            id=v.name,
            name=v.long_name,
            group="weather",
            time_axis="day",
            source="daily",
            variable=v.name,
            unit=v.unit,
            step=v.scale,
            palette=palette_for(v.name),
            stats=_daily_stats(v),
        )
        for v in DAILY_VARIABLES.values()
        if v.name not in _LEFT_OUT
    ]
    found += [
        Layer(
            id=f"{v.name}_hourly",
            name=f"{v.long_name} (hourly)",
            group="weather",
            time_axis="hour",
            source="hourly",
            variable=v.name,
            unit=v.unit,
            step=v.scale,
            palette=palette_for(v.name),
            stats=_hourly_stats(v),
        )
        for v in VARIABLES.values()
        if v.name not in _LEFT_OUT
    ]
    found += [
        Layer(
            id=v.name if v.name.startswith("dd_") else f"{v.name}_total",
            name=v.long_name,
            group="running_total",
            time_axis="day",
            source="cumulative",
            variable=v.name,
            unit=v.unit,
            step=v.scale,
            palette=palette_for(v.name),
            stats=(),
        )
        for v in CUMULATIVE_VARIABLES.values()
        if not v.name.endswith("_days")
    ]
    found.append(
        Layer(
            id=DEGREE_DAYS,
            name="Degree days for any setting",
            group="degree_days",
            time_axis="day",
            source="degree_days",
            variable=None,
            unit="degF_day",
            step=DD_STEP,
            palette="degree_days",
            stats=SUM_STATS,
            description="Each day's degree days for `dd=method_base[_upper]` (sine, average or modified), from the "
            "day's minimum and maximum temperature; `stat=sum` over start..end is the running total from start",
        )
    )
    return found


LAYERS: dict[str, Layer] = {layer.id: layer for layer in _layers()}
