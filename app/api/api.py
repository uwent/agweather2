"""API v2 (docs/api.md): the NinjaAPI, its error handlers, and a router per area under `api.routes`."""

from ninja import NinjaAPI

from api import errors
from api.params import QueryParser
from api.routes import discovery

api = NinjaAPI(
    title="AgWeather API",
    version="2",
    description="Hourly and daily weather, degree days, and crop disease and insect models for the Upper Midwest.",
    urls_namespace="api-v2",
    parser=QueryParser(),
)
errors.install(api)
api.add_router("/", discovery.router)
