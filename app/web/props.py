"""Props shared with every page, and the home page's. Types: frontend/types/generated/props.ts."""

from web.inertia import Props


class AppInfo(Props):
    version: str
    service_box: str


class SharedProps(Props):
    app: AppInfo


class HomeProps(Props):
    api_docs_url: str
