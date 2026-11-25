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
