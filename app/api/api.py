from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI, Schema

from api import errors
from api.envelope import Result, respond
from api.params import QueryParser
from api.schemas import Meta, responses

api = NinjaAPI(
    title="AgWeather API",
    version="2",
    description="Hourly and daily weather, degree days, and crop disease and insect models for the Upper Midwest.",
    urls_namespace="api-v2",
    parser=QueryParser(),
)
errors.install(api)


class StatusData(Schema):
    service: str
    version: str
    service_box: str


class StatusResponse(Schema):
    meta: Meta
    data: StatusData


@api.get("/status", response=responses(StatusResponse), summary="Service status")
def status(request: HttpRequest) -> HttpResponse:
    data = StatusData(service="agweather", version=settings.APP_VERSION, service_box=settings.SERVICE_BOX)
    return respond(request, Result(request={}, data=data.model_dump()))
