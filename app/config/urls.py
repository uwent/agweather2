from django.contrib import admin
from django.urls import path, re_path

from api import views as api_views
from api.api import api
from ops import views as ops
from web import views as web

urlpatterns = [
    path("", web.home, name="home"),
    path("up", ops.up, name="up"),
    path("api/v2/", api.urls),
    re_path(r"^api/v2/(?P<rest>.*)$", api_views.not_found),  # after the API's own routes
    path("admin/", admin.site.urls),
]
