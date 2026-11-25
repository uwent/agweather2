"""Props shared with every page, and the home and sites pages'. Types: frontend/types/generated/props.ts."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from web.inertia import Props


class AppInfo(Props):
    version: str
    service_box: str


Behind = Literal["observed", "forecast"]


class DataStatus(Props):
    """How current the data are (`web.status`): every page's "data through" line and the stale-data banner."""

    observed_through: datetime | None = Field(
        description="The newest observed hour in the archive (its UTC end), or None before the first."
    )
    daily_through: date | None = Field(description="The last whole day rolled up (grid days, D74).")
    forecast_cycle: datetime | None = Field(description="The forecast run in use (its cycle, UTC).")
    forecast_through: datetime | None = Field(description="The forecast's last hour (UTC end).")
    forecast_fallback: Literal["openmeteo"] | None = Field(
        description="Where points in the box take their forecast from while ours is out of date (D114), or None."
    )
    behind: list[Behind] = Field(
        description="What's late: 'observed' when the newest hour is more than 6 hours old, 'forecast' when the run is too old to use."
    )
    stale_sources: list[str] = Field(description="Sources of observed hours later than they normally run.")


class SharedProps(Props):
    app: AppInfo
    today: date = Field(
        description="The grid's current day: midnight to midnight Central Standard Time all year (D74)."
    )
    status: DataStatus | None = Field(description="None until the archive's status has first been read.")


class ModelEntry(Props):
    """A model as the site pages list it (`web.catalog`)."""

    id: str
    name: str
    group: Literal["disease", "insect", "crop", "agronomic", "degree_days"]
    crops: list[str]
    status: Literal["beta", "stable", "retired"]
    risk_levels: list[str] = Field(description="Its risk levels, lowest first; empty for a model without risk.")
    season: tuple[str, str] | None = Field(description="MM-DD first and last day it's shown, or None.")


class CropEntry(Props):
    id: str
    name: str
    category: str


class ModelLink(Props):
    id: str
    name: str
    group: str
    url: str


class CropModels(Props):
    crop: str
    name: str
    models: list[ModelLink]


class HeadlineMap(Props):
    layer: str
    title: str
    alt: str
    image_url: str = Field(description="The API's static map (`/api/v2/maps/{layer}.png`).")
    map_url: str = Field(description="The map explorer on this layer.")


class HomeProps(Props):
    api_docs_url: str
    maps: list[HeadlineMap]
    in_season: list[CropModels]


class SitesIndexProps(Props):
    models: list[ModelEntry]
    crops: list[CropEntry]


class MapExplorerProps(Props):
    """The map explorer's props: none yet. Its layers, palettes, models and crops come from the API (D117)."""


class SiteModel(Props):
    """A model in the site page's short catalog: what it's called and which crops it's for."""

    id: str
    name: str
    group: str
    crops: list[str]
    status: str
    risk_levels: list[str] = Field(
        description="The words for its risk levels, lowest first; empty for a model without risk (crop stages)."
    )


class SiteCrop(Props):
    id: str
    name: str


class SiteProps(Props):
    """A site's page (`/sites/{lat},{lng}`): the point as given, a name from a shared link, and the catalog the
    tabs name models and crops from. Its weather and risk the page fetches from the API (D117)."""

    lat: float
    lng: float
    name: str | None = Field(default=None, description="The `?name=` of a shared link, trimmed; None without one.")
    models: list[SiteModel]
    crops: list[SiteCrop]
