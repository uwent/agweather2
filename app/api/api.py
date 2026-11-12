"""API v2 (docs/api.md): the NinjaAPI, its error handlers, and a router per area under `api.routes`."""

from typing import Any

from ninja import NinjaAPI
from ninja.operation import Operation

from api import docs, errors, strict
from api.params import QueryParser
from api.routes import climate, degree_days, discovery, grids, maps, models, summaries, tiles, weather


class AgWeatherAPI(NinjaAPI):
    """Ninja's API with operation ids named by area and function (`weather_daily`), and the public text from
    `api.docs` in its OpenAPI schema."""

    def get_openapi_operation_id(self, operation: Operation) -> str:
        area = operation.view_func.__module__.rpartition(".")[2]
        return f"{area}_{operation.view_func.__name__}"

    def get_openapi_schema(self, *, path_prefix: str | None = None, path_params: dict[str, Any] | None = None):
        schema = super().get_openapi_schema(path_prefix=path_prefix, path_params=path_params)
        docs.apply(schema)
        return schema


api = AgWeatherAPI(
    title="AgWeather API",
    version="2",
    urls_namespace="api-v2",
    parser=QueryParser(),
)
errors.install(api)
api.add_router("/", models.router)  # before discovery: /models/run isn't a model id
api.add_router("/", discovery.router)
api.add_router("/", weather.router)
api.add_router("/", degree_days.router)
api.add_router("/", grids.router)
api.add_router("/", summaries.router)
api.add_router("/", tiles.router)
api.add_router("/", maps.router)
api.add_router("/", climate.router)
strict.install(api)  # after the routers: every operation's query is checked
