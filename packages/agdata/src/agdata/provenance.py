"""Where each hourly variable comes from, by date and use: the sources by date for the methods page and `/methods`
(PLAN.md Phase 6 step 2, "Methods derived from the code").

One entry per source and use. `first` and `last` bound the dates a source fills, taken from the source modules'
own constants where a source changes; None is open: from the archive's first day, or still in use. The text is
public (CLAUDE.md's "Writing for the public"); a test checks every stored hourly variable has a source for the
archive from its first day.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from agdata.climatestore import ADJUST
from agdata.sources.urma import HOURLY_PRECIP_FROM

Role = Literal["archive", "provisional", "forecast", "outside", "normals"]

_ANALYSIS = (
    "air_temperature",
    "dew_point",
    "wind_speed",
    "wind_gust",
    "wind_direction",
    "surface_pressure",
    "cloud_cover",
)
_SOIL_AND_SNOW = ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm", "snow_depth")


@dataclass(kw_only=True, frozen=True)
class SourceUse:
    source: str  # id: the archive's source code where it has one (`agdata.store.SOURCES`)
    name: str  # public
    role: Role
    variables: tuple[str, ...]  # catalog names: hourly, or daily for the normals
    first: date | None = None  # None: from the archive's first day
    last: date | None = None  # None: still in use
    description: str  # public
    url: str


URMA_NAME = "URMA (Unrestricted Mesoscale Analysis), NOAA"
RTMA_NAME = "RTMA (Real-Time Mesoscale Analysis), NOAA"
URMA_URL = "https://www.nco.ncep.noaa.gov/pmb/products/rtma/"
IFS_NAME = "ECMWF IFS (Integrated Forecasting System), through Open-Meteo"
IFS_URL = "https://www.ecmwf.int/en/forecasts/documentation-and-support"

USES: tuple[SourceUse, ...] = (
    SourceUse(
        source="urma",
        name=URMA_NAME,
        role="archive",
        variables=_ANALYSIS,
        description="NOAA's hourly analysis of weather near the ground on a 2.5 km grid, which combines weather station observations with a short forecast. It is published about 6 hours after the hour.",
        url=URMA_URL,
    ),
    SourceUse(
        source="urma",
        name=URMA_NAME,
        role="archive",
        variables=("precipitation",),
        first=HOURLY_PRECIP_FROM,
        description="URMA's hourly precipitation, from radar and rain gauges, from the day it began.",
        url=URMA_URL,
    ),
    SourceUse(
        source="rtma",
        name=RTMA_NAME,
        role="archive",
        variables=("precipitation",),
        last=HOURLY_PRECIP_FROM - timedelta(days=1),
        description="Before URMA published hourly precipitation, its real-time counterpart RTMA did, so the archive's hourly precipitation comes from RTMA until then.",
        url=URMA_URL,
    ),
    SourceUse(
        source="rtma",
        name=RTMA_NAME,
        role="provisional",
        variables=(*_ANALYSIS, "precipitation"),
        description="RTMA is published about an hour after the hour. It fills the newest hours until URMA's arrive and replace them.",
        url=URMA_URL,
    ),
    SourceUse(
        source="hrrr",
        name="HRRR (High-Resolution Rapid Refresh), NOAA",
        role="archive",
        variables=("shortwave_radiation",),
        description="Solar radiation from NOAA's hourly weather model on its 3 km grid, taken to our grid, as the mean of each hour's four 15-minute values (in 2016, values at each quarter hour rather than means over it), and corrected to pyranometers on the ground.",
        url="https://rapidrefresh.noaa.gov/hrrr/",
    ),
    SourceUse(
        source="era5land",
        name="ERA5-Land, ECMWF (Copernicus Climate Change Service)",
        role="archive",
        variables=_SOIL_AND_SNOW,
        description="ECMWF's reanalysis of the land surface on a 9 km grid, taken to our grid and to each depth. It is published about 5 days behind.",
        url="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land",
    ),
    SourceUse(
        source="ifs",
        name=IFS_NAME,
        role="provisional",
        variables=_SOIL_AND_SNOW,
        description="ECMWF's forecast model fills soil temperature and snow depth for the days since ERA5-Land's last, adjusted to meet it, until ERA5-Land's values arrive and replace them.",
        url=IFS_URL,
    ),
    SourceUse(
        source="nbm",
        name="NBM (National Blend of Models), NOAA",
        role="forecast",
        variables=(
            "air_temperature",
            "dew_point",
            "wind_speed",
            "wind_gust",
            "wind_direction",
            "cloud_cover",
            "precipitation",
            "shortwave_radiation",
        ),
        description="NOAA's forecast blended from many weather models, on the same 2.5 km grid, for the next 11 days. We correct its daily highs, overnight lows, humidity and solar radiation against the archive.",
        url="https://vlab.noaa.gov/web/mdl/nbm",
    ),
    SourceUse(
        source="ifs",
        name=IFS_NAME,
        role="forecast",
        variables=_SOIL_AND_SNOW,
        description="Soil temperature and snow depth in the forecast, adjusted to meet the archive's.",
        url=IFS_URL,
    ),
    SourceUse(
        source="openmeteo",
        name="Open-Meteo",
        role="outside",
        variables=(*_ANALYSIS, "precipitation", "shortwave_radiation", *_SOIL_AND_SNOW),
        description="For locations outside the area our maps cover, and for dates before our archive, we read weather for the location from Open-Meteo: NBM where it has it, then its best match of weather models, with ERA5 and ERA5-Land for earlier years and ECMWF IFS for soil and snow. We correct its solar radiation and humidity against Wisconsin's stations and the archive.",
        url="https://open-meteo.com/",
    ),
    SourceUse(
        source="gridmet",
        name="gridMET, Climatology Lab",
        role="normals",
        variables=tuple(ADJUST),
        description="A gridded daily weather dataset on a 4 km grid. The 30-year normal takes from it the years before our archive begins, adjusted to the archive cell by cell.",
        url="https://www.climatologylab.org/gridmet.html",
    ),
)
