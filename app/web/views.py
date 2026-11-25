from django.http import HttpRequest
from django.urls import reverse

from web import home as home_content
from web.catalog import crop_entries, model_entries
from web.inertia import render
from web.middleware import grid_today
from web.props import HomeProps, SitesIndexProps


def home(request: HttpRequest):
    today = grid_today()
    return render(
        request,
        "Home",
        HomeProps(
            api_docs_url=reverse("api-v2:openapi-view"),
            maps=home_content.headline_maps(today),
            in_season=home_content.models_in_season(today),
        ),
    )


def sites(request: HttpRequest):
    """Your sites (track 3): kept in the browser (D120), so the page takes only the models and crops as props and
    each card fetches its own data from the API."""
    return render(request, "Sites/Index", SitesIndexProps(models=model_entries(), crops=crop_entries()))


def dev_map_demo(request: HttpRequest):
    """The map and chart demo (development only, routed when DEBUG): its data is made up in the page."""
    return render(request, "Dev/MapDemo")
