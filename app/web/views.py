from django.http import Http404, HttpRequest
from django.urls import reverse

from agmodels import croplist
from agmodels.registry import all_models
from web.inertia import render
from web.props import HomeProps, SiteCrop, SiteModel, SiteProps

# The longest `?name=` a site page shows from a link
NAME_LENGTH = 80


def home(request: HttpRequest):
    return render(request, "Home", HomeProps(api_docs_url=reverse("api-v2:openapi-view")))


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


def dev_map_demo(request: HttpRequest):
    """The map and chart demo (development only, routed when DEBUG): its data is made up in the page."""
    return render(request, "Dev/MapDemo")
