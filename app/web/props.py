"""Props shared with every page, and the home page's. Types: frontend/types/generated/props.ts."""

from datetime import date

from pydantic import Field

from web.inertia import Props


class AppInfo(Props):
    version: str
    service_box: str


class SharedProps(Props):
    app: AppInfo
    today: date = Field(
        description="The grid's current day: midnight to midnight Central Standard Time all year (D74)."
    )


class HomeProps(Props):
    api_docs_url: str


class SiteModel(Props):
    """A model in the site page's short catalog: what it's called and which crops it's for."""

    id: str
    name: str
    group: str
    crops: list[str]
    status: str


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
