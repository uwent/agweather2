from django.conf import settings
from django.http import Http404, HttpRequest
from django.urls import reverse

from agdata.series import archive_years
from agmodels import croplist
from agmodels.registry import all_models
from web import home as home_content
from web import methodspage, modelpages, topicpages
from web.catalog import crop_entries, model_entries
from web.content import topics
from web.inertia import render
from web.middleware import grid_today
from web.props import HomeProps, MapExplorerProps, SiteCrop, SiteModel, SiteModelProps, SiteProps, SitesIndexProps
from web.sitemodel import model_info, shown_spec

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
    latitude, longitude = _point(lat, lng)
    name = _name(request)
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


def models_index(request: HttpRequest):
    """The model catalog (track 4): every model by crop, then group, from the registry (content, D117)."""
    return render(request, "Models/Index", modelpages.index_props())


def model_page(request: HttpRequest, model_id: str):
    """A model's page (track 4): sections from its spec and its Markdown page; 404 for unknown and retired ids."""
    spec = modelpages.page_spec(model_id)
    if spec is None:
        raise Http404("No such model")
    return render(request, "Models/Show", modelpages.page_props(spec))


def _point(lat: str, lng: str) -> tuple[float, float]:
    latitude, longitude = float(lat), float(lng)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise Http404("No such location")
    return latitude, longitude


def _name(request: HttpRequest) -> str | None:
    return " ".join(request.GET.get("name", "").split())[:NAME_LENGTH] or None


def site_model(request: HttpRequest, lat: str, lng: str, model_id: str):
    """A model at a site (track 3 step 6): its content as props, its run from the API in the browser. Not found for
    a model we don't have or have retired."""
    latitude, longitude = _point(lat, lng)
    spec = shown_spec(model_id)
    if spec is None:
        raise Http404("No such model")
    this_year = grid_today().year
    years = sorted((y for y in archive_years(settings.DATA_DIR) if y <= this_year), reverse=True)
    if this_year not in years:
        years.insert(0, this_year)
    return render(
        request,
        "Sites/Model",
        SiteModelProps(lat=latitude, lng=longitude, name=_name(request), model=model_info(spec), years=years),
    )


def topics_index(request: HttpRequest):
    """The pests and diseases (track 4): every topic page by crop, then kind, from `content/topics` (D117)."""
    return render(request, "Topics/Index", topicpages.index_props())


def topic_page(request: HttpRequest, topic_id: str):
    """A topic page (track 4): its Markdown and front matter, and the models that name it; 404 for unknown ids."""
    page = topics().get(topic_id)
    if page is None:
        raise Http404("No such topic")
    return render(request, "Topics/Show", topicpages.page_props(page))


def methods(request: HttpRequest):
    """How the data is made (track 4): generated from the code and data (D92), the same as `/api/v2/methods`."""
    return render(request, "Methods", methodspage.methods_props())
