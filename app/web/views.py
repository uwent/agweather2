from django.http import HttpRequest
from django.urls import reverse

from web.inertia import render
from web.props import HomeProps, MapExplorerProps


def home(request: HttpRequest):
    return render(request, "Home", HomeProps(api_docs_url=reverse("api-v2:openapi-view")))


def map_explorer(request: HttpRequest):
    """The map explorer (Phase 7 track 2): its layers, tiles and values come from the API in the browser (D117)."""
    return render(request, "Map/Explorer", MapExplorerProps())
