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
from web import views as web

urlpatterns = [
    path("", web.home, name="home"),
    path("up", ops.up, name="up"),
    path("changelog", updates.changelog, name="changelog"),
    path("changelog.atom", ChangelogFeed(), name="changelog-feed"),
    path("api-use", updates.api_use, name="api-use"),
    # A site's page: numbers only, so other pages under /sites/ (/sites/models/{id}) can't collide (F1)
    re_path(r"^sites/(?P<lat>-?\d{1,2}(?:\.\d+)?),(?P<lng>-?\d{1,3}(?:\.\d+)?)$", web.site, name="site"),
    # Browsers ask for /favicon.ico wherever a page doesn't link an icon (the API docs, a JSON answer); Caddy serves
    # it in production, so this is for development
    path("favicon.ico", RedirectView.as_view(url=static("favicon.ico"), permanent=False)),
    # The API's root is its documentation (a temporary redirect, so the root could become an index later)
    path("api/v2/", RedirectView.as_view(url="/api/v2/docs", permanent=False), name="api-root"),
    path("api/v2/", api.urls),
    re_path(r"^api/v2/(?P<rest>.*)$", api_views.not_found),  # after the API's own routes
    path("admin/", admin.site.urls),
]

if settings.DEBUG or settings.TESTING:
    # The yearly downloads (ops.downloads); in production Caddy serves them from the data volume
    urlpatterns.append(re_path(r"^downloads/(?P<path>.+)$", ops.download, name="downloads"))

if settings.DEBUG:
    # A page for reviewing the map and chart parts ported from WISP 3 (Phase 7 wave 1); wave 2 replaces it
    urlpatterns.append(path("dev/map", web.dev_map_demo, name="dev-map-demo"))
