"""The variable catalog: every gridded variable, its stored unit and encoding, and how it rolls up to days.

Stores keep each variable as int16 with a scale and offset (value = stored * scale + offset), which keeps
the archive small (docs/architecture.md §5.3); `encode`/`decode` do the packing, and the int16 minimum marks a missing
value. Scales are the stored precision (D21): coarser than URMA's 0.01, whose last digit is noise at the
analysis's accuracy and doesn't compress (docs/pilot.md). Units are symbols from `agdata.units` (SI, D18).
A variable's QC range is what's physically plausible in the service area; values outside it are treated as
missing by QC (Phase 2).
"""

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from agdata.units import unit
from agmodels import features
from agmodels.gaps import GapFill

DailyStat = Literal["min", "max", "mean", "sum"]

FILL = np.int16(np.iinfo(np.int16).min)  # missing
DECODE_PARALLEL = 100_000  # float32 decodes and encodes of more values than this go through Numba
_INT16_MAX = np.iinfo(np.int16).max


@dataclass(frozen=True, kw_only=True)
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
    version: int = 1  # of the code that computes it; bump when its output changes so stores rebuild it (D29)
    fillable: bool = True  # short gaps may be interpolated in time (not for sums like precip, or directions)
    gap_fill: GapFill | None = None  # daily: how a model's input estimates a missing day (D45, `agmodels.gaps`)
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
        """Floats in the stored unit → int16; NaN becomes FILL. Values must already be within the QC range. Many
        values are packed in one parallel pass (`agdata.fastdecode.encode_int16`), the same values."""
        values = np.asarray(values)
        if values.size > DECODE_PARALLEL:
            from agdata.fastdecode import encode_int16  # Numba: loaded only when a write is large

            packed, bad = encode_int16(values, self.scale, self.offset)
            if bad:
                raise ValueError(f"{self.name}: values outside what int16 can hold; run QC first")
            return packed
        values = np.asarray(values, dtype=np.float64)
        missing = ~np.isfinite(values)
        packed = np.round((np.where(missing, 0.0, values) - self.offset) / self.scale)
        if np.any((packed[~missing] <= FILL) | (packed[~missing] > _INT16_MAX)):
            raise ValueError(f"{self.name}: values outside what int16 can hold; run QC first")
        packed[missing] = FILL
        return packed.astype(np.int16)

    def decode(self, packed: np.ndarray, dtype: type = np.float64) -> np.ndarray:
        """int16 → `dtype` (float64, or float32 for a map's many days) in the stored unit; FILL becomes NaN. float32
        is float64's values rounded, decoded in one parallel pass (`agdata.fastdecode`) when there are many."""
        packed = np.asarray(packed)
        if dtype is np.float32 and packed.size > DECODE_PARALLEL:
            from agdata.fastdecode import decode_float32  # Numba: loaded only when a map needs it

            return decode_float32(packed, self.scale, self.offset)
        values = packed.astype(np.float64)
        values *= self.scale
        values += self.offset
        values[packed == FILL] = np.nan
        return values.astype(dtype, copy=False)


VARIABLES: dict[str, Variable] = {
    v.name: v
    for v in [
        Variable(
            name="air_temperature",
            long_name="Air temperature at 2 m",
            unit="degC",
            notes="The air temperature at 2 m (about 6.5 feet) above the ground, the height of a weather station's thermometer.",
            spike_c=12,
            scale=0.1,
            valid_min=-60,
            valid_max=60,
            daily=("min", "max", "mean"),
            sources={"urma": "TMP:2 m above ground"},
        ),
        Variable(
            name="dew_point",
            long_name="Dew point at 2 m",
            unit="degC",
            notes="The temperature to which the air would have to cool for dew to form. The closer it is to the air temperature, the more humid the air.",
            spike_c=12,
            scale=0.1,
            valid_min=-70,
            valid_max=40,
            daily=("min", "max", "mean"),
            sources={"urma": "DPT:2 m above ground"},
        ),
        Variable(
            name="relative_humidity",
            long_name="Relative humidity at 2 m",
            unit="percent",
            scale=1,
            valid_min=0,
            valid_max=100,
            daily=("min", "max", "mean"),
            derived=True,
            notes="How much water vapor the air holds, as a percentage of the most it could hold at its temperature. We compute it from the air temperature and dew point (the Magnus formula, over water).",
        ),
        Variable(
            name="wind_speed",
            long_name="Wind speed at 10 m",
            unit="m_s",
            notes="The wind's mean speed at 10 m (about 33 feet) above the ground, the standard height for wind measurements.",
            scale=0.1,
            valid_min=0,
            valid_max=75,
            daily=("mean", "max"),
            sources={"urma": "WIND:10 m above ground"},
        ),
        Variable(
            name="wind_gust",
            long_name="Wind gust at 10 m",
            unit="m_s",
            notes="The highest short burst of wind speed during the hour, at 10 m above the ground.",
            scale=0.1,
            valid_min=0,
            valid_max=100,
            daily=("max",),
            sources={"urma": "GUST:10 m above ground"},
        ),
        Variable(
            name="wind_direction",
            long_name="Wind direction at 10 m",
            unit="deg",
            fillable=False,
            scale=1,
            valid_min=0,
            valid_max=360,
            notes="The direction the wind blows from, in degrees clockwise from north (90 is from the east). A day's directions can't be averaged as numbers, so there is no daily value.",
            sources={"urma": "WDIR:10 m above ground"},
        ),
        Variable(
            name="surface_pressure",
            long_name="Surface pressure",
            unit="kPa",
            notes="The air pressure at the ground, not adjusted to sea level, so it is lower at higher elevations.",
            scale=0.1,
            valid_min=50,
            valid_max=110,
            daily=("mean",),
            sources={"urma": "PRES:surface"},
        ),
        Variable(
            name="cloud_cover",
            long_name="Total cloud cover",
            unit="percent",
            notes="The share of the sky covered by cloud at any height.",
            scale=1,
            valid_min=0,
            valid_max=100,
            daily=("mean",),
            sources={"urma": "TCDC:entire atmosphere (considered as a single layer)"},
        ),
        Variable(
            name="precipitation",
            long_name="Precipitation",
            unit="mm",
            fillable=False,
            scale=0.01,  # D28: at 0.1, light-snow hours under 0.05 mm round to 0 (January totals 6.6% low)
            valid_min=0,
            valid_max=300,
            daily=("sum",),
            notes="Rain and melted snow in the hour ending at the time shown.",
            sources={"urma": "APCP:surface, 1-hour accumulation"},
        ),
        Variable(
            name="shortwave_radiation_hrrr",
            long_name="Solar radiation from HRRR before our correction, mean over the hour",
            unit="W_m2",
            scale=0.1,
            valid_min=0,
            valid_max=1500,
            notes="The sunlight reaching the ground as NOAA's HRRR weather model gives it, before we correct it to measurements on the ground. It reads about 18% high.",
            sources={"hrrr": "DSWRF:surface, wrfsubhf01"},
        ),
        Variable(
            name="shortwave_radiation",
            long_name="Solar radiation, mean over the hour",
            unit="W_m2",
            scale=0.1,
            valid_min=0,
            valid_max=1500,
            daily=("sum",),
            derived=True,
            version=3,  # 1 + the correction table's version (`agdata.shortwave`; a test checks it)
            notes="The sunlight reaching the ground (downward shortwave radiation), corrected to measurements by instruments on the ground. Daily totals are in megajoules per square meter (MJ/m²).",
            sources={"hrrr": "shortwave_radiation_hrrr, corrected (agdata.shortwave)"},
        ),
        Variable(
            name="soil_temperature_4cm",
            long_name="Soil temperature at 4 cm",
            unit="degC",
            scale=0.1,
            valid_min=-40,
            valid_max=60,
            daily=("min", "max", "mean"),
            version=2,  # 2: ERA5-Land, not HRRR (D52)
            notes="Estimated by a weather model at 4 cm (about 1.5 inches), between the depths of its soil layers (0–7, 7–28 and 28–100 cm). The potato models use it for 2 inches.",
            sources={
                "era5land": "soil_temperature_level_1-3, at the depth (agdata.sources.era5land)",
                "ifs": "IFS HRES layers, at the depth (agdata.sources.ifs): provisional days and the forecast",
            },
        ),
        Variable(
            name="soil_temperature_10cm",
            long_name="Soil temperature at 10 cm",
            unit="degC",
            scale=0.1,
            valid_min=-40,
            valid_max=60,
            daily=("min", "max", "mean"),
            version=2,  # 2: ERA5-Land, not HRRR (D52)
            notes="Estimated by a weather model at 10 cm (about 4 inches), between the depths of its soil layers (0–7, 7–28 and 28–100 cm). The potato models use it for 4 inches.",
            sources={
                "era5land": "soil_temperature_level_1-3, at the depth (agdata.sources.era5land)",
                "ifs": "IFS HRES layers, at the depth (agdata.sources.ifs): provisional days and the forecast",
            },
        ),
        Variable(
            name="soil_temperature_30cm",
            long_name="Soil temperature at 30 cm",
            unit="degC",
            scale=0.1,
            valid_min=-40,
            valid_max=60,
            daily=("min", "max", "mean"),
            version=2,  # 2: ERA5-Land, not HRRR (D52)
            notes="Estimated by a weather model at 30 cm (about 12 inches), between the depths of its soil layers (0–7, 7–28 and 28–100 cm). The potato models take 8 inches between this depth and 10 cm.",
            sources={
                "era5land": "soil_temperature_level_1-3, at the depth (agdata.sources.era5land)",
                "ifs": "IFS HRES layers, at the depth (agdata.sources.ifs): provisional days and the forecast",
            },
        ),
        Variable(
            name="snow_depth",
            long_name="Snow depth",
            unit="cm",
            scale=0.1,
            valid_min=0,
            valid_max=1000,
            daily=("max", "mean"),
            notes="The depth of the snow on the ground, not its water content, as a weather model estimates it.",
            sources={
                "era5land": "snow_depth (agdata.sources.era5land)",
                "ifs": "snow_depth (agdata.sources.ifs): provisional days and the forecast",
            },
        ),
        *(
            Variable(
                name=f"soil_moisture_{top}_to_{bottom}cm",
                long_name=f"Soil moisture, {top} to {bottom} cm",
                unit="m3_m3",
                scale=0.001,
                valid_min=0,
                valid_max=1,
                daily=("mean",),
                notes=f"The volume of water in the soil from {top} to {bottom} cm, as a share of the soil's volume (0.30 is 30%). It is estimated by a weather model for its own soil, not a field's, and includes frozen water.",
                sources={
                    "era5land": f"volumetric_soil_water_layer_{layer} (agdata.sources.era5land)",
                    "ifs": f"IFS HRES soil_moisture_{top}_to_{bottom}cm (agdata.sources.ifs): provisional days and the forecast",
                },
            )
            for layer, (top, bottom) in enumerate(((0, 7), (7, 28), (28, 100)), start=1)
        ),
        Variable(
            name="et0",
            long_name="Reference evapotranspiration (FAO-56 grass)",
            unit="mm",
            fillable=False,
            scale=0.001,
            valid_min=0,
            valid_max=3,
            daily=("sum",),
            derived=True,
            version=2,  # 2: Rs/Rso held to 0.3–1 (ASCE-EWRI), so heavy cloud can't make net longwave a gain
            notes="The water a short, well-watered grass would lose to evaporation and transpiration, by the FAO-56 Penman–Monteith equation, computed each hour from temperature, humidity, wind and solar radiation.",
        ),
    ]
}


# Daily statistics (docs/architecture.md §5.2): each hourly variable's `daily` stats over each grid day (midnight to midnight CST in every cell, D74).
# Min, max and mean keep the hourly unit and precision; sums have their own (shortwave's in MJ/m²).
DAILY_MIN_HOURS = features.MIN_HOURS  # min, max and mean need this many hours of the day; sums need every hour (D25)
_SUMS: dict[str, tuple[str, float, float, float, float]] = {
    # hourly name: (unit, factor from the hourly unit, scale, offset, valid max)
    # Precip spends all of int16 on 0..1310 mm (offset) for 0.02 mm steps: at 0.1 mm, trace days rounded to 0 (D28)
    "precipitation": ("mm", 1.0, 0.02, 655.34, 1300),
    "shortwave_radiation": ("MJ_m2", 0.0036, 0.01, 0.0, 50),  # W/m² mean over an hour → MJ/m²
    "et0": ("mm", 1.0, 0.01, 0.0, 20),
}


_SUM_NAMES = {
    "precipitation": "Precipitation, daily total",
    "shortwave_radiation": "Solar radiation, daily total",
    "et0": "Reference evapotranspiration (FAO-56 grass), daily total",
}


@dataclass(frozen=True, kw_only=True)
class DailyStatistic:
    variable: Variable  # stored in the daily store
    hourly: str
    stat: DailyStat
    factor: float = 1.0  # hourly unit → daily unit


def _daily_statistic(v: Variable, stat: DailyStat) -> DailyStatistic:
    """A daily statistic of an hourly variable, with the hourly variable's version: when what's stored hourly
    changes (a new source or correction), the days computed from it are stale too and roll up again (D29)."""
    name = f"{v.name}_{stat}"
    if stat == "sum":
        unit_, factor, scale, offset, high = _SUMS[v.name]
        long_name = _SUM_NAMES[v.name]
        daily = Variable(
            name=name,
            long_name=long_name,
            unit=unit_,
            scale=scale,
            offset=offset,
            valid_min=0,
            valid_max=high,
            derived=True,
            gap_fill="zero" if v.name == "precipitation" else "interpolate",  # precip is never estimated
            version=v.version,
        )
        return DailyStatistic(variable=daily, hourly=v.name, stat=stat, factor=factor)
    long_name = f"{v.long_name}, daily {stat}"
    daily = Variable(
        name=name,
        long_name=long_name,
        unit=v.unit,
        scale=v.scale,
        offset=v.offset,
        valid_min=v.valid_min,
        valid_max=v.valid_max,
        derived=True,
        gap_fill="interpolate",
        version=v.version,
    )
    return DailyStatistic(variable=daily, hourly=v.name, stat=stat)


DAILY_STATISTICS: dict[str, DailyStatistic] = {
    s.variable.name: s for v in VARIABLES.values() for s in (_daily_statistic(v, stat) for stat in v.daily)
}
DAILY_VARIABLES: dict[str, Variable] = {name: s.variable for name, s in DAILY_STATISTICS.items()}
# Where a day's ET0 total is missing because some hours are, the total with those hours estimated
# (`agdata.gaps`), for running totals only; the raw `et0_sum` stays missing (D25)
DAILY_VARIABLES["et0_sum_estimate"] = Variable(
    name="et0_sum_estimate",
    long_name="Reference evapotranspiration (FAO-56 grass), daily total with missing hours estimated",
    notes="The day's total with any missing hours estimated, so that running totals can continue. It is used only for running totals; the daily total stays missing.",
    unit="mm",
    scale=0.01,
    valid_min=0,
    valid_max=20,
    derived=True,
    gap_fill="interpolate",
)


# Daily features the models read (`agmodels.features`, Phase 3 B; windows D74): counts of hours over the
# calendar day and over the day from 6 pm (readings 19:00 the evening before through 18:00), night hours (6 pm to
# 6 am, readings 19:00-06:00; tar spot's 7 pm to 6 am, 20:00-06:00), the mean temperature during humid hours, and the
# overnight minimum (noon to noon). Features that look across days (hot past 5 days, dry) and moving averages are
# computed on read. Bump a feature's version when `agmodels.features` changes what it computes (D29).
# Version 2 counts gridded RH at 88%, a station's 90% (D50, `agmodels.features.STATION_RH_90_AS_GRIDDED`)
_RH90 = "{} with relative humidity at or above 90% as a weather station counts it (88% on the grid)"
_HOURS = {"unit": "hour", "scale": 1, "valid_min": 0, "valid_max": 25, "derived": True, "gap_fill": "interpolate"}
_TEMPERATURE = {
    "unit": "degC",
    "scale": 0.1,
    "valid_min": -60,
    "valid_max": 60,
    "derived": True,
    "gap_fill": "interpolate",
}
_DEPRESSION = {**_TEMPERATURE, "unit": "delta_degC"}
_DEPRESSION_NOTE = "How far the air temperature is above the dew point. The smaller it is, the closer the air is to forming dew."  # a difference of temperatures: °F is ×1.8, no offset
# THI is unitless, about 1.8 T + 32 in humid air: −45 at −40 °C, 120 at 50 °C and saturated
_INDEX = {"unit": "index", "scale": 0.1, "valid_min": -80, "valid_max": 140, "derived": True, "gap_fill": "interpolate"}
# A missing day's scab period counts as none, as a missing day's rain does (D45); the runner flags the day estimated
_FLAG = {"unit": "index", "scale": 1, "valid_min": 0, "valid_max": 1, "derived": True, "gap_fill": "zero"}
_PERIOD_HOURS = {"unit": "hour", "scale": 1, "valid_min": 0, "valid_max": 130, "derived": True, "gap_fill": "zero"}
_RAIN = {
    "unit": "mm",
    "scale": 0.02,
    "offset": 655.34,
    "valid_min": 0,
    "valid_max": 1300,
    "derived": True,
    "gap_fill": "zero",
}
DAILY_FEATURES: dict[str, Variable] = {
    v.name: v
    for v in [
        Variable(name="hours_temperature_over_20c", long_name="Hours with temperature at or above 20 °C", **_HOURS),
        Variable(name="hours_temperature_over_30c", long_name="Hours with temperature at or above 30 °C", **_HOURS),
        Variable(name="hours_rh_under_70", long_name="Hours with relative humidity below 70%", **_HOURS),
        Variable(name="hours_rh_over_80", long_name="Hours with relative humidity at or above 80%", **_HOURS),
        Variable(name="hours_rh_over_90", long_name=_RH90.format("Hours"), version=2, **_HOURS),
        Variable(
            name="hours_rh_over_90_temperature_over_70f",
            long_name=_RH90.format("Hours") + " and at least 70 °F",
            version=2,  # counted at 88% since D100
            **_HOURS,
        ),
        Variable(
            name="hours_rh_over_80_from_6pm",
            long_name="Hours with relative humidity at or above 80%, day from 6 p.m.",
            **_HOURS,
        ),
        Variable(name="hours_rh_over_90_from_6pm", long_name=_RH90.format("Hours") + ", day from 6 p.m.", **_HOURS),
        # 2: 6 pm to 6 am (was 8 pm to 7 am, D74); 3 for RH ≥ 90%, after D50's 2
        Variable(
            name="hours_rh_over_80_night",
            long_name="Night hours (6 p.m. to 6 a.m.) with relative humidity at or above 80%",
            version=2,
            **_HOURS,
        ),
        Variable(
            name="hours_rh_over_90_night", long_name=_RH90.format("Night hours (6 p.m. to 6 a.m.)"), version=3, **_HOURS
        ),
        Variable(
            name="hours_rh_over_90_7pm_to_6am",
            long_name=_RH90.format("Hours from 7 p.m. to 6 a.m."),
            **_HOURS,
        ),
        Variable(
            name="hours_soil_4cm_below_27f",
            long_name="Hours with soil at 4 cm below 27 °F",
            version=2,  # 2: from ERA5-Land's soil (D52)
            **_HOURS,
        ),
        Variable(
            name="hours_soil_10cm_below_27f",
            long_name="Hours with soil at 10 cm below 27 °F",
            version=2,  # 2: from ERA5-Land's soil (D52)
            **_HOURS,
        ),
        Variable(
            name="hours_soil_8in_below_27f",
            long_name="Hours with soil at 8 inches below 27 °F",
            version=2,  # 2: from ERA5-Land's soil (D52)
            **_HOURS,
        ),
        Variable(
            name="dew_point_depression_min",
            long_name="Dew point depression, daily min",
            notes=_DEPRESSION_NOTE,
            **_DEPRESSION,
        ),
        Variable(
            name="dew_point_depression_mean",
            long_name="Dew point depression, daily mean",
            notes=_DEPRESSION_NOTE,
            **_DEPRESSION,
        ),
        Variable(
            name="dew_point_depression_max",
            long_name="Dew point depression, daily max",
            notes=_DEPRESSION_NOTE,
            **_DEPRESSION,
        ),
        Variable(
            name="temperature_mean_rh_over_80_from_6pm",
            long_name="Mean temperature of hours with relative humidity at or above 80%, day from 6 p.m.",
            **_TEMPERATURE,
        ),
        Variable(
            name="temperature_mean_rh_over_90_from_6pm",
            long_name=_RH90.format("Mean temperature of hours") + ", day from 6 p.m.",
            **_TEMPERATURE,
        ),
        Variable(
            name="air_temperature_min_overnight",
            long_name="Air temperature, overnight minimum",
            notes="The lowest air temperature from noon the day before to noon on the day, so a cold morning counts on its own day.",
            **_TEMPERATURE,
        ),
        # Winter chill (D76, `agmodels.chill`) and livestock heat stress (D77, `agmodels.livestock`), calendar days
        Variable(
            name="chill_hours",
            long_name="Chill hours (32–45 °F)",
            notes="Hours with the air temperature from 32 to 45 °F (0 to 7.2 °C), which fruit trees need through the winter to bloom well in spring.",
            **_HOURS,
        ),
        Variable(
            name="utah_chill_units",
            long_name="Utah chill units",
            notes="Winter chill by the Utah model: each hour counts as a full, half or no unit by its temperature, and warm hours count against the total.",
            unit="chill_units",
            scale=0.5,
            valid_min=-24,
            valid_max=24,
            derived=True,
            gap_fill="interpolate",
        ),
        Variable(name="thi_min", long_name="Temperature humidity index, daily min", **_INDEX),
        Variable(name="thi_mean", long_name="Temperature humidity index, daily mean", **_INDEX),
        Variable(name="thi_max", long_name="Temperature humidity index, daily max", **_INDEX),
        Variable(name="hours_thi_over_68", long_name="Hours with a temperature humidity index of 68 or more", **_HOURS),
        Variable(name="hours_thi_over_72", long_name="Hours with a temperature humidity index of 72 or more", **_HOURS),
        Variable(name="cci_max", long_name="Cattle comfort index, daily max", **_TEMPERATURE),
        # Apple scab (`agmodels.models.apple_scab`): wet periods found in the 120 hours to the day's end (D96), and
        # the day's and night's rain for ascospore release
        Variable(
            name="scab_infection",
            long_name="Apple scab infection period",
            notes="Whether a period of wet leaves ending on the day was long enough, at its temperature, for apple scab to infect, by the Revised Mills table.",
            **_FLAG,
        ),
        Variable(
            name="scab_wet_hours", long_name="Apple scab: wet hours of the day's latest wet period", **_PERIOD_HOURS
        ),
        Variable(
            name="scab_wet_temperature",
            long_name="Apple scab: mean temperature of the day's latest wet period",
            **_TEMPERATURE,
        ),
        Variable(
            name="scab_period_truncated",
            long_name="Apple scab: the day's wet period may have begun more than 120 hours earlier",
            **_FLAG,
        ),
        # Fire blight (`agmodels.models.fire_blight`), calendar days
        Variable(
            name="cougarblight_risk_values",
            long_name="Cougarblight's hourly temperature risk values, daily total",
            notes="The day's total of the fire blight Cougarblight model's risk values for each hour's temperature.",
            unit="index",
            scale=0.05,
            valid_min=0,
            valid_max=1500,
            derived=True,
            gap_fill="interpolate",
        ),
        Variable(
            name="degree_hours_over_65f",
            long_name="Degree hours above 65 °F (18.3 °C)",
            notes="Each hour's degrees above 65 °F, added up over the day. The MaryBlyt fire blight model reads them.",
            unit="degC_hour",
            scale=0.1,
            valid_min=0,
            valid_max=600,
            derived=True,
            gap_fill="interpolate",
        ),
        Variable(
            name="hours_wet",
            long_name="Hours estimated wet",
            notes="Hours with relative humidity at or above 90% or 0.01 inch of rain or more, which stand in for hours with wet leaves.",
            **_HOURS,
        ),
        Variable(name="precipitation_7am_to_7pm", long_name="Precipitation, 7 a.m. to 7 p.m.", **_RAIN),
        Variable(name="precipitation_8pm_to_6am", long_name="Precipitation, 8 p.m. the day before to 6 a.m.", **_RAIN),
        Variable(
            name="temperature_mean_rain_7am_to_7pm",
            long_name="Mean temperature of hours with 0.01 inch of rain or more, 7 a.m. to 7 p.m.",
            **_TEMPERATURE,
        ),
    ]
}
DAILY_VARIABLES.update(DAILY_FEATURES)
# How each daily variable's missing days are estimated as a model's input (D45)
GAP_FILL: dict[str, GapFill] = {name: v.gap_fill for name, v in DAILY_VARIABLES.items() if v.gap_fill is not None}


# Running totals from local January 1 (D26, D27): any range is cum[end] - cum[start - 1]. Degree days are
# cubes per threshold: single sine is linear, so a sine pair is the difference of its two thresholds' cubes.
# Thresholds are those the planned models use (°F, D18); corn's modified average isn't linear, so it has its own.
DD_SINE_THRESHOLDS_F: tuple[float, ...] = (32, 39.2, 41, 42.8, 43, 45, 48.2, 50, 52, 55, 80.1, 86, 90, 92, 95)
DD_MODIFIED_PAIRS_F: tuple[tuple[float, float], ...] = ((50, 86),)
# The simple average isn't linear in its thresholds either: seedcorn maggot's 39/84.2, potato's 39.2 (4 °C), and
# NEWA's 40 for the onion and cabbage maggots and 48 for alfalfa weevil (part H, D95)
DD_AVERAGE_SETTINGS_F: tuple[tuple[float, float | None], ...] = ((39, 84.2), (39.2, None), (40, None), (48, None))
_DD_RANGE = {
    "scale": 0.5,
    "valid_min": 0,
    "valid_max": 16000,
    "derived": True,
}  # a base-39.2 year in Florida is about 13,000


_COUNT_WORDS = {
    "temperature": "temperature",
    "precipitation": "precipitation",
    "et0": "reference evapotranspiration",
    "water_balance": "water balance",
}


def dd_name(method: Literal["sine", "modified", "average"], base: float, upper: float | None = None) -> str:
    """`dd_sine_39p2`, `dd_modified_50_86`, `dd_average_39_84p2`: the legacy naming, with the method."""

    def f(t: float) -> str:
        return f"{t:g}".replace(".", "p")

    return f"dd_{method}_{f(base)}" + (f"_{f(upper)}" if upper is not None else "")


_DD_NOTES = {
    "sine": "Degree days measure the warmth that drives crop and insect development. The single-sine method fits a sine curve through the day's low and high temperatures and counts the area above the base temperature.",
    "modified": "Degree days measure the warmth that drives crop and insect development. The modified-average method raises a low below the base to the base and lowers a high above the upper limit to the limit, then counts the day's mean above the base.",
    "average": "Degree days measure the warmth that drives crop and insect development. The simple-average method counts the day's mean of its low and high temperatures above the base.",
}


def _cumulative() -> list[Variable]:
    dd = (
        [
            Variable(
                name=dd_name("sine", t),
                long_name=f"Single-sine degree days above {t:g} °F since January 1",
                notes=_DD_NOTES["sine"],
                unit="degF_day",
                **_DD_RANGE,
            )
            for t in DD_SINE_THRESHOLDS_F
        ]
        + [
            Variable(
                name=dd_name("modified", base, upper),
                long_name=f"Modified-average degree days {base:g}/{upper:g} °F since January 1",
                notes=_DD_NOTES["modified"],
                unit="degF_day",
                **_DD_RANGE,
            )
            for base, upper in DD_MODIFIED_PAIRS_F
        ]
        + [
            Variable(
                name=dd_name("average", base, upper),
                long_name=f"Simple-average degree days above {base:g} °F"
                + (f", capped at {upper:g} °F" if upper is not None else "")
                + " since January 1",
                notes=_DD_NOTES["average"],
                unit="degF_day",
                **_DD_RANGE,
            )
            for base, upper in DD_AVERAGE_SETTINGS_F
        ]
    )
    totals = [
        Variable(
            name="precipitation",
            long_name="Precipitation since January 1",
            unit="mm",
            scale=0.2,
            valid_min=0,
            valid_max=6000,
            derived=True,
        ),
        Variable(
            name="et0",
            long_name="Reference evapotranspiration (FAO-56 grass) since January 1",
            unit="mm",
            scale=0.1,
            valid_min=0,
            valid_max=3000,
            derived=True,
        ),
        Variable(
            name="water_balance",
            long_name="Water balance (precipitation minus reference evapotranspiration) since January 1",
            unit="mm",
            scale=0.2,
            offset=1500,  # int16 at 0.2 holds −5050 to 8050 mm about this offset
            valid_min=-3000,
            valid_max=6000,
            derived=True,
            notes="A day without precipitation data counts as no rain, and a day without reference evapotranspiration is estimated as in its own running total. Either day counts as estimated.",
        ),
    ]
    # The Dynamic model's chill since October 1 (D76, `agdata.chillseason`), from hourly temperature: the portions,
    # the intermediate each day ends with (the next day starts from it), and the hours without a temperature
    chill = [
        Variable(
            name="chill_portions",
            long_name="Chill portions (the Dynamic model) since October 1",
            notes="Winter chill by the Dynamic model, which counts chill in portions that, once made, warm weather can't undo.",
            unit="chill_portions",
            scale=0.01,
            valid_min=0,
            valid_max=300,
            derived=True,
        ),
        Variable(
            name="chill_state",
            long_name="The Dynamic model's intermediate at the day's end",
            unit="index",
            scale=0.001,
            valid_min=0,
            valid_max=30,
            derived=True,
        ),
        Variable(
            name="chill_missing_hours",
            long_name="Hours without a temperature since October 1, left out of the chill portions",
            unit="hour",
            scale=1,
            valid_min=0,
            valid_max=8784,
            derived=True,
        ),
    ]
    # Running counts of days in the totals that were estimated across a gap or left out (D25). Every DD cube
    # comes from the daily min and max temperature, so they share the temperature counts
    counts = [
        Variable(
            name=f"{basis}_{kind}_days",
            long_name=f"Days with {_COUNT_WORDS[basis]} {kind} since January 1",
            unit="day",
            scale=1,
            valid_min=0,
            valid_max=366,
            derived=True,
        )
        for basis, kinds in (
            ("temperature", ("estimated", "missing")),
            ("precipitation", ("missing",)),
            ("et0", ("estimated", "missing")),
            ("water_balance", ("estimated", "missing")),
        )
        for kind in kinds
    ]
    return dd + totals + chill + counts


CUMULATIVE_VARIABLES: dict[str, Variable] = {v.name: v for v in _cumulative()}
# Kept in the store for the next day's computation, not served: the Dynamic model's carried intermediate
INTERNAL_TOTALS = frozenset({"chill_state"})


def variable(name: str) -> Variable:
    try:
        return VARIABLES[name]
    except KeyError:
        raise ValueError(f"unknown variable {name!r}") from None
