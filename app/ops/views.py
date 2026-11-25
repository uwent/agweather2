import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.http.response import HttpResponseBase
from django.utils import timezone
from django.views.static import serve

from ops.forecast import forecast_health
from ops.health import ingest_health
from ops.openmeteo_usage import usage_health
from ops.verification import verification_health

logger = logging.getLogger(__name__)
CACHE_S = 30  # the checks open every store's metadata; a monitor (or anyone) polling /up reuses them this long


def up(request: HttpRequest) -> JsonResponse:
    """Public health check for the uptime monitor: down (503) when the database doesn't answer; degraded (still 200)
    when ingest or the forecast is behind, jobs failed or Open-Meteo's use nears the plan (D115), with the reasons."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        logger.exception("/up: the database didn't answer")
        database = "down"
    if database == "down":
        body = {"status": "down", "version": settings.APP_VERSION, "database": database}
        return JsonResponse(body, status=503)
    key = f"up:{settings.DATA_DIR}"
    checked = cache.get(key)
    if checked is None:
        now = timezone.now()
        ingest, problems = ingest_health(settings.DATA_DIR, now)
        forecast, forecast_problems = forecast_health(settings.DATA_DIR, now)
        verified, verification_problems = verification_health(settings.DATA_DIR, now)
        if verified is not None:  # nothing kept or scored yet: left out
            forecast = {**forecast, "verification": verified}
        open_meteo, open_meteo_problems = usage_health(now)  # D115
        checked = (
            ingest,
            forecast,
            open_meteo,
            problems + forecast_problems + verification_problems + open_meteo_problems,
        )
        cache.set(key, checked, CACHE_S)
    ingest, forecast, open_meteo, problems = checked
    body = {
        "status": "degraded" if problems else "ok",
        "version": settings.APP_VERSION,
        "database": database,
        "ingest": ingest,
        "forecast": forecast,
        "open_meteo": open_meteo,
        "problems": problems,
    }
    return JsonResponse(body)


def download(request: HttpRequest, path: str) -> HttpResponseBase:
    """A yearly download (`ops.downloads`) in development and tests, from the data folder as it is now; Caddy serves
    them in production."""
    from ops import downloads

    return serve(request, path, document_root=str(downloads.folder(settings.DATA_DIR)))
