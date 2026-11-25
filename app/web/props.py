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


# --- The model catalog and model pages (web.modelpages, track 4) ---------------------------------------------------


class NamedId(Props):
    id: str
    name: str


class CatalogModel(Props):
    """A model as the catalog (`/models`) lists it."""

    id: str
    name: str
    group: Literal["disease", "insect", "crop", "agronomic", "degree_days"]
    summary: str
    status: Literal["beta", "stable", "retired"]
    crops: list[str] = Field(description="Crop ids (`agmodels.croplist`); empty for a model of no one crop.")


class ModelsIndexProps(Props):
    models: list[CatalogModel] = Field(
        description="Every model but retired ones and the degree-day calculator, by name."
    )
    crops: list[NamedId] = Field(
        description="The crops some model names, by category as `agmodels.croplist` orders them."
    )
    groups: list[NamedId] = Field(description="The groups in the order a crop lists them, with their public names.")


class ModelSection(Props):
    """A `##` section of the model's Markdown page, rendered with raw HTML off (safe for `{@html}`)."""

    id: str
    title: str = Field(description="The heading; empty for text before the first heading.")
    html: str


class ModelSource(Props):
    """A keyed source of the model's page, which the text cites by number (`[^key]`)."""

    key: str
    number: int
    text: str
    url: str | None


class ModelRisk(Props):
    levels: list[str] = Field(description="The risk levels' words, lowest first.")
    criteria: str = Field(description="How the outputs become each level, in words.")


class ModelOutput(Props):
    label: str
    unit: str = Field(description="The stored unit's symbol (`agdata.units`).")
    description: str


class ModelInput(Props):
    name: str
    label: str
    unit: str
    description: str = Field(description="How the model takes it (a moving average, a window of hours).")
    definition: str = Field(description="The variable's description in the catalog (`/variables`' long_name).")


class ModelBiofix(Props):
    default: str = Field(description="MM-DD.")
    label: str
    fixed: bool = Field(description="Always the default: the model takes no date of yours.")
    stage_model: NamedId | None = Field(description="The crop model whose predicted stage is the default instead.")
    stage: str | None


class ModelSusceptibility(Props):
    crop_model: NamedId
    first: str
    last: str
    source: str
    note: str


class ModelTrainingArea(Props):
    """Where the model's data came from (D101)."""

    description: str = Field(description="Completes 'fitted to …'.")
    years: list[int]
    states: list[str] = Field(description="State names.")
    counties: list[str] = Field(description="'Adams County, WI'.")
    calendar_curve: bool = Field(description="The model also has a calendar curve (the `clock` option).")


class ModelChange(Props):
    version: str
    date: str
    note: str


class ModelCitation(Props):
    text: str
    doi: str | None
    url: str | None = Field(description="The DOI's link where there's a DOI, else a copy or a source without one.")


class ModelCheck(Props):
    kind: Literal["published", "system", "observations"]
    against: str
    result: str
    report_url: str = Field(description="The validation report's section on GitHub.")


class ModelPageProps(Props):
    """A model's page (`/models/{id}`): its spec and its Markdown page as content (D117)."""

    id: str
    name: str
    group: Literal["disease", "insect", "crop", "agronomic", "degree_days"]
    group_name: str
    status: Literal["beta", "stable", "retired"]
    version: str
    summary: str
    crops: list[NamedId]
    sections: list[ModelSection]
    draft: bool = Field(description="The page's text is a draft (its front matter's status).")
    updated: str | None = Field(description="When the page's text last changed (YYYY-MM-DD).")
    acknowledgments: str | None = Field(description="The front matter's acknowledgments, rendered; None without.")
    sources: list[ModelSource] = Field(description="The page's keyed sources, numbered as the text cites them.")
    risk: ModelRisk | None
    outputs: list[ModelOutput] = Field(description="The first is the one the map and risk colors show.")
    inputs: list[ModelInput]
    region: list[NamedId] = Field(description="States where it's valid (postal code, name); empty: anywhere.")
    season: list[str] | None = Field(description="[first, last] day it's shown, MM-DD; None: all year.")
    seasonal_appears: str | None = Field(description="A once-a-season map's first day, MM-DD; None: a daily model.")
    biofix: ModelBiofix | None
    susceptible: ModelSusceptibility | None
    trained: ModelTrainingArea | None
    changelog: list[ModelChange] = Field(description="Newest first.")
    citations: list[ModelCitation]
    checks: list[ModelCheck]
    report_url: str = Field(description="The model's validation report on GitHub (D98).")
    map_layer: str | None = Field(description="Its layer on the map explorer (`/map?layer=`); None if it has none.")
