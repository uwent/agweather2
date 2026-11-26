from django.conf import settings
from django.contrib import admin
from django.templatetags.static import static
from django.urls import path, re_path
from django.views.generic import RedirectView

from api import views as api_views
from api.api import api
from ops import views as ops
from updates import views as updates
from updates.feeds import ChangelogFeed
from web import legacy
from web import views as web

urlpatterns = [
    path("", web.home, name="home"),
    path("up", ops.up, name="up"),
    path("map", web.map_explorer, name="map"),
    path("sites", web.sites, name="sites"),
    path("models", web.models_index, name="models"),
    path("models/<str:model_id>", web.model_page, name="model"),
    path("topics", web.topics_index, name="topics"),
    path("topics/<str:topic_id>", web.topic_page, name="topic"),
    path("methods", web.methods, name="methods"),
    path("tools", web.tools_index, name="tools"),
    path("tools/degree-days", web.degree_days_tool, name="tool-degree-days"),
    path("tools/oak-wilt", web.oak_wilt_tool, name="tool-oak-wilt"),
    path("tools/freeze", web.freeze_tool, name="tool-freeze"),
    path("tools/crop-gdd", web.crop_gdd_tool, name="tool-crop-gdd"),
    path("tools/alfalfa", web.alfalfa_tool, name="tool-alfalfa"),
    path("tools/potato-volunteer", web.potato_volunteer_tool, name="tool-potato-volunteer"),
    path("calendar", web.calendar, name="calendar"),
    path("climate", web.climate, name="climate"),
    path("data", web.data, name="data"),
    path("status", web.status, name="status"),
    path("about", web.content_page, {"page": "about"}, name="about"),
    path("accessibility", web.content_page, {"page": "accessibility"}, name="accessibility"),
    path("contact", web.content_page, {"page": "contact"}, name="contact"),
    path("glossary", web.glossary, name="glossary"),
    path("changelog", updates.changelog, name="changelog"),
    path("changelog.atom", ChangelogFeed(), name="changelog-feed"),
    path("api-use", updates.api_use, name="api-use"),
    # One model across your saved sites (the feed, track 3 step 9): before the numbers-only site routes
    path("sites/models/<str:model_id>", web.site_model_feed, name="sites-model-feed"),
    # A site's page: numbers only, so other pages under /sites/ (/sites/models/{id}) can't collide (F1)
    re_path(r"^sites/(?P<lat>-?\d{1,2}(?:\.\d+)?),(?P<lng>-?\d{1,3}(?:\.\d+)?)$", web.site, name="site"),
    # A model at a site: the same numbers, then a model's id (kebab-case)
    re_path(
        r"^sites/(?P<lat>-?\d{1,2}(?:\.\d+)?),(?P<lng>-?\d{1,3}(?:\.\d+)?)/models/(?P<model_id>[a-z0-9]+(?:-[a-z0-9]+)*)$",
        web.site_model,
        name="site-model",
    ),
    # Browsers ask for /favicon.ico wherever a page doesn't link an icon (the API docs, a JSON answer); Caddy serves
    # it in production, so this is for development
    path("favicon.ico", RedirectView.as_view(url=static("favicon.ico"), permanent=False)),
    # The API's root is its documentation (a temporary redirect, so the root could become an index later)
    path("api/v2/", RedirectView.as_view(url="/api/v2/docs", permanent=False), name="api-root"),
    path("api/v2/", api.urls),
    re_path(r"^api/v2/(?P<rest>.*)$", api_views.not_found),  # after the API's own routes
    path("admin/", admin.site.urls),
    # v1's and VDIFN's URLs (D62, web.legacy): last, so every v2 route above keeps its own (/sites, /sites/{lat},{lng})
    re_path(rf"^(?P<path>{legacy.PREFIXES})$", web.legacy_redirect),
]

if settings.DEBUG or settings.TESTING:
    # The yearly downloads (ops.downloads); in production Caddy serves them from the data volume
    urlpatterns.append(re_path(r"^downloads/(?P<path>.+)$", ops.download, name="downloads"))
