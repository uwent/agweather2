from django.contrib import admin
from django.urls import path

from api.api import api
from ops import views as ops
from web import views as web

urlpatterns = [
    path("", web.home, name="home"),
    path("up", ops.up, name="up"),
    path("api/v2/", api.urls),
    path("admin/", admin.site.urls),
]
