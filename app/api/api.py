from django.conf import settings
from django.http import HttpRequest
from ninja import NinjaAPI, Schema

api = NinjaAPI(
    title="AgWeather API",
    version="2",
    description="Hourly and daily weather, degree days, and crop disease and insect models for the Upper Midwest.",
    urls_namespace="api-v2",
)


class Status(Schema):
    service: str
    version: str
    service_box: str


@api.get("/status", response=Status, summary="Service status")
def status(request: HttpRequest):
    return Status(service="agweather", version=settings.APP_VERSION, service_box=settings.SERVICE_BOX)
