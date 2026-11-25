from django.http import HttpRequest
from django.urls import reverse

from web.inertia import render
from web.props import HomeProps


def home(request: HttpRequest):
    return render(request, "Home", HomeProps(api_docs_url=reverse("api-v2:openapi-view")))


def dev_map_demo(request: HttpRequest):
    """The map and chart demo (development only, routed when DEBUG): its data is made up in the page."""
    return render(request, "Dev/MapDemo")
