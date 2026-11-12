"""Mappable layers (PLAN.md Phase 5 E, docs/api.md "Grids"): what `/layers` lists and `/grids/{layer}` reads.

A layer is a catalog variable on the grid with a time axis: a daily variable (local days, `agdata.daily`), an
hourly one (hours by their UTC end), either of them computed when read from stored ones (`agdata.computed`), a
running total from January 1 (`agdata.cumulative`), degree days for any setting (`degree_days`, computed from each
day's minimum and maximum, the same way as at points), or a model's outputs (`model`, finished from its ingredients
by `agdata.modelgrid`; the layer's id is the model's).

Climate (D86): a layer whose normal the stored normal maps hold (`agdata.normals`, D85) takes `climate=normal`,
`departure` or `percentile` (`Layer.climate` lists which), from the same layer rather than a copy of it; the
freeze layers come from those maps alone (`freeze_chance` by day of year, `freeze_dates` with no time at all), and
`elevation` from the terrain store (D6), with no time either. Their statistics are `outputs`, as a model's are.

A model layer's value is one of the model's outputs (`output=`): by default its risk level (an index into the
spec's levels), or a crop model's stage; `risk_value` is a continuous risk (the insects' summed activity) before it
becomes a level; `susceptibility` is a stage-gated disease's crop stage window (D33: 0 not susceptible, 1 within
the crop model's margin, 2 susceptible), from each place's typical planting.

`stats` are the statistics a range of steps can be reduced to: mean, min and max for any level, and sum where the
values add up (precipitation, ET0, shortwave, hour counts, degree days). A running total has none: each day is
already a total. `use` names what a layer's map looks like (`agdata.palettes.USES`: a palette and default
domains, served by `/layers` and `/palettes`); layers of one kind share it, so a legend means the same thing on
every map that uses it.
"""

from dataclasses import dataclass
from typing import Literal

from agdata.catalog import (
    CUMULATIVE_VARIABLES,
    DAILY_VARIABLES,
    DD_AVERAGE_SETTINGS_F,
    DD_MODIFIED_PAIRS_F,
    DD_SINE_THRESHOLDS_F,
    INTERNAL_TOTALS,
    VARIABLES,
    Variable,
    dd_name,
)
from agdata.computed import DAILY_COMPUTED, HOURLY_COMPUTED, adds_up

# What the normal maps hold (`agdata.normals`; not imported, which would load zarr and the models for the catalog)
NORMAL_DAILY = (
    "air_temperature_max",
    "air_temperature_min",
    "air_temperature_mean",
    "precipitation_sum",
    "relative_humidity_max",
    "relative_humidity_min",
    "shortwave_radiation_sum",
    "wind_speed_mean",
    "et0_sum",
)
NORMAL_DECILES = ("dd_modified_50_86", "dd_sine_41_86", "precipitation")
NORMAL_RUNNING = (
    *(dd_name("sine", t) for t in DD_SINE_THRESHOLDS_F),
    *(dd_name("modified", b, u) for b, u in DD_MODIFIED_PAIRS_F),
    *(dd_name("average", b, u) for b, u in DD_AVERAGE_SETTINGS_F),
    "precipitation",
    "et0",
)

TimeAxis = Literal["day", "hour", "day_of_year", "none"]
Source = Literal["daily", "hourly", "cumulative", "degree_days", "model", "normals", "terrain"]
Climate = Literal["normal", "departure", "percentile"]
Stat = Literal["sum", "mean", "min", "max"]
LEVEL_STATS: tuple[Stat, ...] = ("mean", "min", "max")
SUM_STATS: tuple[Stat, ...] = ("sum", "mean", "min", "max")
DEGREE_DAYS = "degree_days"
DD_STEP = 0.1  # °F·d: daily values from temperatures stored to 0.1 °C


@dataclass(frozen=True, kw_only=True)
class LayerOutput:
    """One output a model layer can show."""

    name: str
    label: str
    unit: str
    step: float
    use: str  # the colors its map uses (`agdata.palettes.USES`)


@dataclass(frozen=True, kw_only=True)
class Layer:
    id: str
    name: str
    group: Literal["weather", "running_total", "degree_days", "model", "climate", "terrain"]  # for pickers
    time_axis: TimeAxis
    source: Source
    variable: str | None  # the catalog variable read; None for degree days (computed from min and max)
    unit: str
    step: float  # the stored precision, in `unit`
    use: str  # the colors its map uses (`agdata.palettes.USES`): a palette and default domains
    stats: tuple[Stat, ...]
    description: str = ""
    outputs: tuple[LayerOutput, ...] = ()  # a model layer's, the default first
    planting: bool = False  # a model layer that takes a planting tier (`planting=early|mid|late`)
    climate: tuple[Climate, ...] = ()  # what `climate=` it takes (D86)
    threshold: bool = False  # takes a freeze `threshold=` (the freeze layers)

    @property
    def summable(self) -> bool:
        return "sum" in self.stats


# The colors each variable's map uses (`agdata.palettes.USES`), by name: the first prefix that matches wins
_USES = (
    ("dd_", "degree_days"),
    ("chill", "chill"),
    ("utah_chill", "chill"),
    ("thi", "heat_stress"),
    ("cci", "temperature"),  # an apparent temperature
    ("water_balance", "water_balance"),
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


def use_for(name: str) -> str:
    """The palette use (`agdata.palettes.USES`) of a variable's or model output's map."""
    return next((use for prefix, use in _USES if name.startswith(prefix)), "default")


def _daily_stats(v: Variable) -> tuple[Stat, ...]:
    return SUM_STATS if adds_up(v.name) else LEVEL_STATS  # a computed one with each input's gaps filled (D75)


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
            use=use_for(v.name),
            stats=_daily_stats(v),
            climate=("normal", "departure") if v.name in NORMAL_DAILY else (),
        )
        for v in [*DAILY_VARIABLES.values(), *(c.variable for c in DAILY_COMPUTED.values())]
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
            use=use_for(v.name),
            stats=_hourly_stats(v),
        )
        for v in [*VARIABLES.values(), *(c.variable for c in HOURLY_COMPUTED.values())]
        if v.name not in _LEFT_OUT
    ]
    found += [
        Layer(
            id=v.name if v.name.startswith(("dd_", "chill_")) else f"{v.name}_total",
            name=v.long_name,
            group="running_total",
            time_axis="day",
            source="cumulative",
            variable=v.name,
            unit=v.unit,
            step=v.scale,
            use=use_for(v.name),
            stats=(),
            climate=_running_climate(v.name),
        )
        for v in CUMULATIVE_VARIABLES.values()
        if not v.name.endswith(("_days", "_hours")) and v.name not in INTERNAL_TOTALS
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
            use="degree_days",
            stats=SUM_STATS,
            description="Each day's degree days for `dd=method_base[_upper]` (sine, average or modified), from the "
            "day's minimum and maximum temperature; `stat=sum` over start..end is the running total from start",
            climate=("normal", "departure", "percentile"),
        )
    )
    return found


def _running_climate(name: str) -> tuple[Climate, ...]:
    if name not in NORMAL_RUNNING:
        return ()
    return ("normal", "departure", "percentile") if name in NORMAL_DECILES else ("normal", "departure")


FREEZE_DATE_OUTPUTS = (
    ("last_spring_p10", "Last spring freeze, 10% of years by", "spring_p10"),
    ("last_spring_p50", "Last spring freeze, median date", "spring_p50"),
    ("last_spring_p90", "Last spring freeze, 90% of years by", "spring_p90"),
    ("first_fall_p10", "First fall freeze, 10% of years by", "fall_p10"),
    ("first_fall_p50", "First fall freeze, median date", "fall_p50"),
    ("first_fall_p90", "First fall freeze, 90% of years by", "fall_p90"),
    ("season_days_p50", "Frost-free season, median length", "season_p50"),
)
ELEVATION_OUTPUTS = (
    ("mean", "Mean elevation", "elevation_mean"),
    ("min", "Lowest elevation", "elevation_min"),
    ("max", "Highest elevation", "elevation_max"),
    ("spread", "Spread of elevation (standard deviation)", "elevation_std"),
)


def _climate_layers() -> list[Layer]:
    """The freeze layers (from the normal maps, D85) and elevation (the terrain store, D6)."""
    dates = tuple(
        LayerOutput(
            name=name,
            label=label,
            unit="day" if name.startswith("season") else "date",
            step=1,
            use="season_length" if name.startswith("season") else "date",
        )
        for name, label, _ in FREEZE_DATE_OUTPUTS
    )
    return [
        Layer(
            id="freeze_chance",
            name="Chance of a freeze",
            group="climate",
            time_axis="day_of_year",
            source="normals",
            variable=None,
            unit="percent",
            step=0.1,
            use="chance",
            stats=(),
            description="The share of the period's years with a freeze (a minimum at or below `threshold`) after the "
            "date (January–June) or on or before it (July–December)",
            threshold=True,
        ),
        Layer(
            id="freeze_dates",
            name="Freeze dates and season length",
            group="climate",
            time_axis="none",
            source="normals",
            variable=None,
            unit="date",
            step=1,
            use="date",
            stats=(),
            description="The last spring and first fall freeze (a minimum at or below `threshold`) by the share of "
            "the period's years, and the frost-free season's median length",
            outputs=dates,
            threshold=True,
        ),
        Layer(
            id="elevation",
            name="Elevation",
            group="terrain",
            time_axis="none",
            source="terrain",
            variable=None,
            unit="m",
            step=0.1,
            use="elevation",
            stats=(),
            description="Each grid cell's elevation from the National Elevation Dataset (30 m, in NHDPlus V2): its "
            "mean, lowest, highest, or spread",
            outputs=tuple(
                LayerOutput(name=name, label=label, unit="m", step=0.1, use="elevation")
                for name, label, _ in ELEVATION_OUTPUTS
            ),
        ),
    ]


RISK_LEVEL, RISK_VALUE, SUSCEPTIBILITY = "risk_level", "risk_value", "susceptibility"


def _model_layers() -> list[Layer]:
    from agdata.modelgrid import OUTPUT_STEPS, mapped, tiered  # imports every model

    found = []
    models = mapped()
    for m in models.values():
        spec = m.SPEC
        outputs = [
            LayerOutput(
                name=q.name,
                label=q.label,
                unit=q.unit,
                step=1 if q.name == "stage" else OUTPUT_STEPS[q.unit],
                use="crop_stage" if q.name == "stage" else use_for(q.name),
            )
            for q in spec.outputs
        ]
        if spec.risk is not None:
            levels = f"risk_{len(spec.risk.levels)}"
            risk = [LayerOutput(name=RISK_LEVEL, label="Risk level", unit="index", step=1, use=levels)]
            if spec.risk.thresholds:
                risk.append(LayerOutput(name=RISK_VALUE, label="Risk", unit="index", step=0.001, use="risk_value"))
            outputs = [*risk, *outputs]
        if spec.susceptible is not None and spec.susceptible.crop in models:
            outputs.append(
                LayerOutput(
                    name=SUSCEPTIBILITY, label="Crop susceptibility", unit="index", step=1, use="susceptibility"
                )
            )
        default = outputs[0] if spec.risk is not None else next((o for o in outputs if o.name == "stage"), outputs[0])
        outputs = [default, *(o for o in outputs if o is not default)]
        if spec.seasonal is not None:
            outputs += _projected_outputs(outputs, spec.risk.levels if spec.risk is not None else ())
        found.append(
            Layer(
                id=spec.id,
                name=spec.name,
                group="model",
                time_axis="day",
                source="model",
                variable=None,
                unit=default.unit,
                step=default.step,
                use=default.use,
                stats=LEVEL_STATS,
                description=spec.summary,
                outputs=tuple(outputs),
                planting=tiered(spec.id) is not None,
            )
        )
    return found


def _projected_outputs(outputs: list[LayerOutput], levels: tuple[str, ...]) -> list[LayerOutput]:
    """A seasonal product's season end projected on the earlier seasons (`agdata.seasonal`): each output's and the
    risk level's median, and the percent of seasons ending at each risk level."""
    from agdata.seasonal import CHANCE, PROJECTED, level_key

    medians = [
        LayerOutput(
            name=f"{PROJECTED}{o.name}",
            label=f"{o.label}, projected to the season's end (median)",
            unit=o.unit,
            step=o.step,
            use=o.use,
        )
        for o in outputs
        if o.name not in (RISK_VALUE, SUSCEPTIBILITY)
    ]
    chances = [
        LayerOutput(
            name=f"{CHANCE}{level_key(level)}",
            label=f"Chance the season ends at {level} risk",
            unit="percent",
            step=1,
            use="chance",
        )
        for level in levels
    ]
    return medians + chances


LAYERS: dict[str, Layer] = {layer.id: layer for layer in [*_layers(), *_climate_layers(), *_model_layers()]}
