from django.http import Http404, HttpRequest
from django.urls import reverse

from agmodels import croplist
from agmodels.registry import all_models
from web import home as home_content
from web.catalog import crop_entries, model_entries
from web.inertia import render
from web.middleware import grid_today
from web.props import HomeProps, MapExplorerProps, SiteCrop, SiteModel, SiteProps, SitesIndexProps

# The longest `?name=` a site page shows from a link
NAME_LENGTH = 80


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


def map_explorer(request: HttpRequest):
    """The map explorer (Phase 7 track 2): its layers, tiles and values come from the API in the browser (D117)."""
    return render(request, "Map/Explorer", MapExplorerProps())


def site(request: HttpRequest, lat: str, lng: str):
    """A site's page, saved or not (F1): any point by its coordinates, which the URL pattern takes as numbers only."""
    latitude, longitude = float(lat), float(lng)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise Http404("No such location")
    name = " ".join(request.GET.get("name", "").split())[:NAME_LENGTH] or None
    specs = sorted((m.SPEC for m in all_models().values() if m.SPEC.status != "retired"), key=lambda s: s.name.lower())
    models = [
        SiteModel(
            id=s.id,
            name=s.name,
            group=s.group,
            crops=list(s.crops),
            status=s.status,
            risk_levels=list(s.risk.levels) if s.risk else [],
        )
        for s in specs
    ]
    crops = [SiteCrop(id=c.id, name=c.name) for c in croplist.CROPS.values()]
    return render(request, "Sites/Show", SiteProps(lat=latitude, lng=longitude, name=name, models=models, crops=crops))
