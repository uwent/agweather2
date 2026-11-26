"""The home page's content: three headline maps chosen by the month, and the models in season by crop.

The maps are the API's static images (`/api/v2/maps/{layer}.png`, D60), which show the latest day when given no date,
so the page needs no data request of its own. Each month shows what matters then: degree days and the week's
precipitation through the growing season with a disease or insect that's active, and cold, snow and soil in winter
and early spring.
"""

from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlencode

from django.conf import settings

from agdata import seasonopens
from agmodels import croplist, seasons
from agmodels.spec import ModelSpec
from web.catalog import specs
from web.props import CropModels, HeadlineMap, ModelLink

# A model valid only in some states (cotton, pecan) shows only if one of them is in the launch coverage (D105): the
# 12 Midwest states and Kentucky
COVERED_STATES = {"IA", "IL", "IN", "KS", "KY", "MI", "MN", "MO", "ND", "NE", "OH", "SD", "WI"}
IMAGE_WIDTH = 640  # pixels: the API's maps take 400 to 2000


@dataclass(frozen=True, kw_only=True)
class Headline:
    layer: str  # an id in `agdata.layers.LAYERS`
    title: str
    alt: str
    params: dict[str, str | int] = field(default_factory=dict)


GDD = Headline(
    layer="dd_modified_50_86",
    title="Growing degree days since January 1",
    alt="Map of growing degree days (modified method, 50 to 86 °F) since January 1 across the region, through the latest day.",
)
PRECIP_WEEK = Headline(
    layer="precipitation_sum",
    params={"days": 7, "stat": "sum"},
    title="Precipitation in the past 7 days",
    alt="Map of total precipitation over the past 7 days across the region.",
)
LOW = Headline(
    layer="air_temperature_min",
    title="Low temperature",
    alt="Map of the daily low air temperature across the region on the latest day.",
)
SNOW = Headline(
    layer="snow_depth_max",
    title="Snow depth",
    alt="Map of snow depth across the region on the latest day.",
)
SOIL = Headline(
    layer="soil_temperature_10cm_mean",
    title="Soil temperature at 4 inches",
    alt="Map of the daily mean soil temperature at 10 cm (4 inches) across the region on the latest day.",
)
ALFALFA_WEEVIL = Headline(
    layer="alfalfa-weevil",
    title="Alfalfa weevil",
    alt="Map of alfalfa weevil risk across the region on the latest day.",
)
LATE_BLIGHT = Headline(
    layer="late-blight-dsv",
    title="Late blight",
    alt="Map of potato and tomato late blight risk from disease severity values across the region on the latest day.",
)
TAR_SPOT = Headline(
    layer="tar-spot",
    title="Tar spot of corn",
    alt="Map of corn tar spot risk across the region on the latest day.",
)
POTATO_VOLUNTEER = Headline(
    layer="potato-volunteer",
    title="Potato volunteer survival",
    alt="Map of the risk that potato tubers left in the field survive the winter, across the region, on the latest day.",
)

BY_MONTH: dict[int, tuple[Headline, Headline, Headline]] = {
    1: (LOW, SNOW, POTATO_VOLUNTEER),
    2: (LOW, SNOW, POTATO_VOLUNTEER),
    3: (LOW, SOIL, PRECIP_WEEK),
    4: (GDD, SOIL, PRECIP_WEEK),
    5: (GDD, PRECIP_WEEK, ALFALFA_WEEVIL),
    6: (GDD, PRECIP_WEEK, LATE_BLIGHT),
    7: (GDD, PRECIP_WEEK, TAR_SPOT),
    8: (GDD, PRECIP_WEEK, LATE_BLIGHT),
    9: (GDD, PRECIP_WEEK, LATE_BLIGHT),
    10: (GDD, PRECIP_WEEK, LOW),
    11: (LOW, PRECIP_WEEK, POTATO_VOLUNTEER),
    12: (LOW, SNOW, POTATO_VOLUNTEER),
}


def headline_maps(today: date) -> list[HeadlineMap]:
    return [
        HeadlineMap(
            layer=h.layer,
            title=h.title,
            alt=h.alt,
            image_url=f"/api/v2/maps/{h.layer}.png?{urlencode({**h.params, 'width': IMAGE_WIDTH})}",
            map_url=f"/map?{urlencode({'layer': h.layer})}",
        )
        for h in BY_MONTH[today.month]
    ]


def models_in_season(today: date) -> list[CropModels]:
    """The models in season today under each crop they name (a model naming several shows under each), the crops in
    the catalog's order (by category, then name) and each crop's models by name."""
    by_crop: dict[str, list[ModelSpec]] = {}
    for spec in specs():
        if spec.region and not (set(spec.region) & COVERED_STATES):
            continue
        # The rule /risk lists models by (at a place, also the weather's end); an insect's season opens on the
        # region's day (D128: when it's open on a tenth of the farmland)
        if seasons.in_season(spec, today, opens=seasonopens.region(settings.DATA_DIR, spec)):
            for crop in spec.crops:
                by_crop.setdefault(crop, []).append(spec)
    order = list(croplist.CATEGORIES)
    crops = sorted(by_crop, key=lambda c: (order.index(croplist.CROPS[c].category), croplist.CROPS[c].name))
    return [
        CropModels(
            crop=crop,
            name=croplist.CROPS[crop].name,
            models=[
                ModelLink(id=s.id, name=s.name, group=s.group, url=f"/models/{s.id}")
                for s in sorted(by_crop[crop], key=lambda s: s.name.lower())
            ],
        )
        for crop in crops
    ]
