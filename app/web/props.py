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
    settings: list["ModelSettings"] = Field(description="The models with settings, for the preferences panels.")


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
    settings: list["ModelSettings"] = Field(description="The models with settings, for the preferences panel.")


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
    # Not `status`: a page's props are merged over the shared ones, and `status` is the data's (SharedProps)
    model_status: Literal["beta", "stable", "retired"]
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


# --- A model at a site (web.sitemodel, track 3) ---------------------------------------------------------------


class ModelQuantity(Props):
    """An input or output of a model: its API column, label and stored unit (the API's run gives it in metric)."""

    name: str
    label: str
    unit: str
    description: str


class ModelChoice(Props):
    value: str
    label: str


class ModelOption(Props):
    """A choice that changes the model, sent to its run as a plain parameter (`maturity_group=2.5`)."""

    name: str
    label: str
    choices: list[ModelChoice] = Field(description="Empty for a value the reader types (a date, YYYY-MM-DD).")
    default: str
    date: bool = Field(description="Whether the value is a date (an option without choices named `…_date`).")


class SiteModelBiofix(Props):
    default: str = Field(description="MM-DD.")
    label: str = Field(description="What the date means to a grower.")
    stage: str | None = Field(description="The crop stage whose estimated date is the default instead, in words.")


class ModelPlanting(Props):
    """What a planting date adds: the crop's stages, a disease's susceptible window or a stage biofix (D64)."""

    crop: str = Field(description="The crop's name.")
    typical_dates: bool = Field(description="Whether `early`, `mid` and `late` typical dates exist for it.")
    options: list[ModelOption] = Field(description="The crop model's own options, sent to the run too.")


class ModelSettings(Props):
    """A model's settings as the preferences panels offer them (for all sites, a group or a site): the same fields as
    its page at a site, without the rest of its content."""

    id: str
    name: str
    group: str
    biofix: SiteModelBiofix | None
    planting: ModelPlanting | None
    options: list[ModelOption]


class CropStageInfo(Props):
    code: str
    name: str


class ModelTrained(Props):
    description: str
    years: list[int] = Field(description="The first and last year of its data.")
    states: list[str]


class SiteModelInfo(Props):
    """A model as its page at a site shows it (content from the registry, D117)."""

    id: str
    name: str
    group: str
    status: Literal["beta", "stable"]
    version: str
    summary: str
    crops: list[str] = Field(description="The crops' names.")
    inputs: list[ModelQuantity] = Field(description="The model's own inputs (not its crop model's).")
    outputs: list[ModelQuantity] = Field(description="Its outputs; the first is the primary one.")
    options: list[ModelOption]
    biofix: SiteModelBiofix | None = Field(description="None for a model without a biofix, or with one fixed.")
    planting: ModelPlanting | None = Field(description="None for a model that takes no planting date.")
    stages: list[CropStageInfo] = Field(description="A crop model's stages in order; empty for other models.")
    risk_levels: list[str] = Field(description="Its risk levels, lowest first; empty for a model without risk.")
    risk_criteria: str = Field(description="How its outputs become each level, in words; empty without risk.")
    risk_thresholds: list[float]
    susceptible: str | None = Field(description="The crop stages a disease affects, in words, or None.")
    season: list[str] | None = Field(description="MM-DD first and last day it runs, or None (all year).")
    region: list[str] = Field(description="State abbreviations where it's valid; empty: anywhere.")
    trained: ModelTrained | None
    guidance_html: str | None = Field(description="The model page's 'How to read it', as HTML; None without a page.")


class SiteModelProps(Props):
    """A model at a site (`/sites/{lat},{lng}/models/{id}`): the point, a shared link's name, the model's content and
    the years the archive holds. Its numbers the page fetches from the API (`/models/{id}/run`, D117)."""

    lat: float
    lng: float
    name: str | None = Field(default=None, description="The `?name=` of a shared link, trimmed; None without one.")
    model: SiteModelInfo
    years: list[int] = Field(description="The years with weather to run the model on, newest first.")


# --- Topic pages and the methods page (web.topicpages, web.methodspage, track 4) -----------------------------------


class TopicEntry(Props):
    """A topic as the index (`/topics`) lists it."""

    id: str
    title: str
    kind: Literal["disease", "insect", "crop", "agronomic", "weather"]
    scientific_name: str | None
    crops: list[str] = Field(description="Crop ids (`agmodels.croplist`); empty for a topic of no one crop.")


class TopicsIndexProps(Props):
    topics: list[TopicEntry] = Field(description="Every topic page, by title.")
    crops: list[NamedId] = Field(
        description="The crops some topic names, by category as `agmodels.croplist` orders them."
    )
    kinds: list[NamedId] = Field(description="The kinds in the order a crop lists them, with their public names.")


class TopicModel(Props):
    """A model that predicts the topic's pest, disease or crop (its spec's `topics`)."""

    id: str
    name: str
    summary: str
    model_status: Literal["beta", "stable", "retired"]
    map_layer: str | None = Field(description="Its layer on the map explorer (`/map?layer=`); None if it has none.")


class TopicPageProps(Props):
    """A topic page (`/topics/{id}`): its Markdown and front matter (`content/topics/<id>.md`) as content (D117)."""

    id: str
    title: str
    kind: Literal["disease", "insect", "crop", "agronomic", "weather"]
    kind_name: str = Field(description="The kind's public name, singular ('Disease').")
    scientific_name: str | None
    summary: str
    crops: list[NamedId]
    image_url: str | None = Field(description="The photo's static URL; None without one.")
    image_alt: str = Field(description="The credit's first sentence, which describes the photo.")
    image_credit: str
    draft: bool = Field(description="The page's text is a draft (its front matter's status).")
    updated: str | None = Field(description="When the page's text last changed (YYYY-MM-DD).")
    sections: list[ModelSection]
    sources: list[ModelSource] = Field(description="The page's keyed sources, numbered as the text cites them.")
    models: list[TopicModel] = Field(description="The models naming this topic, but retired ones, by name.")


class MethodsGrid(Props):
    """The grid and the days, from `agdata.grid.NDFD` and `agdata.timezones` (D74)."""

    name: str
    cell_km: float = Field(description="A cell's width, km.")
    day_zone: str = Field(description="The grid's days' time zone, in words ('Central Standard Time').")
    day_zone_abbreviation: str = Field(description="'CST'.")
    day_start_utc: int = Field(description="The UTC hour a grid day starts (6 for CST).")
    evening_hour: int = Field(description="The clock hour the day from 6 pm and the night start at (18).")
    overnight_hour: int = Field(description="The clock hour the overnight minimum's window starts at (12, noon).")
    interpolate_days: int = Field(description="The longest gap a model's daily input is interpolated across (D45).")
    bridge_days: int = Field(description="The longest gap a running total bridges with an estimate (D25).")


class MethodsSource(Props):
    """A source by use (`agdata.provenance.USES`)."""

    source: str
    name: str
    role: Literal["archive", "provisional", "forecast", "outside", "normals"]
    variables: list[str] = Field(description="Catalog names: hourly, or daily for the normals.")
    first: str | None = Field(description="YYYY-MM-DD; None: from the archive's first day.")
    last: str | None = Field(description="YYYY-MM-DD; None: still in use.")
    description: str
    url: str


class MethodsScore(Props):
    measure: str
    unit: str = Field(description="The stored unit's symbol (`agdata.units`); the page converts it.")
    before: float
    after: float
    tested: str


class MethodsCorrection(Props):
    """A correction (`agdata.corrections`), as `/api/v2/methods` serves it."""

    id: str
    title: str
    summary: str
    variables: list[str]
    version: str
    fitted: str | None = Field(description="YYYY-MM-DD the table was fitted; None without a fitted table.")
    scores: list[MethodsScore]
    evidence: list[str] = Field(description="Links to the validation reports on GitHub.")


class MethodsVariable(Props):
    """A variable of the catalog, as `/api/v2/variables` serves it."""

    name: str
    long_name: str
    kind: Literal["hourly", "daily", "cumulative"]
    unit: str
    notes: str
    statistic: str | None = Field(description="Daily: min, max, mean or sum of its hourly variable.")
    hourly_sources: list[str]
    computed_from: list[str]
    sources: list[str] = Field(description="Source ids (`MethodsSource.source`).")
    gap_fill: Literal["interpolate", "zero"] | None
    corrections: list[str] = Field(description="Correction ids.")


class MethodsProps(Props):
    """The methods page (`/methods`): generated from the code and data (D92), never written by hand."""

    grid: MethodsGrid
    sources: list[MethodsSource]
    corrections: list[MethodsCorrection]
    variables: list[MethodsVariable] = Field(description="Hourly, then daily, then running totals, as /variables.")
    api_methods_url: str


class SiteModelFeedProps(Props):
    """One model across your saved sites (`/sites/models/{id}`): the model's content. The sites are kept in the
    browser, which runs the model over them (`/models/{id}/run?points=`, D117)."""

    model: SiteModelInfo


# Stubs for the pages of tracks 5–7 (2026-11-26), so the waves' agents share one set of routes; each agent fills in its
# page's props.


class ToolsIndexProps(Props):
    """The tools (`/tools`, track 5)."""


class DegreeDaysToolProps(Props):
    """The degree-day calculator (`/tools/degree-days`, track 5)."""


class OakWiltToolProps(Props):
    """Oak wilt (`/tools/oak-wilt`, track 5)."""


class FreezeToolProps(Props):
    """Freeze dates and odds (`/tools/freeze`, track 5)."""


class CalendarProps(Props):
    """The day-of-year calendar (`/calendar`, track 5)."""


class ClimateProps(Props):
    """Climate (`/climate`, track 6)."""


class DataPageProps(Props):
    """Downloads (`/data`, track 7)."""


class StatusPageProps(Props):
    """Data status (`/status`, track 7)."""


class ContentPageProps(Props):
    """A page of text from `content/pages` (`/about`, `/accessibility`, `/contact`, track 7)."""

    title: str


class GlossaryProps(Props):
    """The glossary (`/glossary`, track 7)."""
