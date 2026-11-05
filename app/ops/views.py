import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.static import serve

from ops.forecast import forecast_health
from ops.health import ingest_health

logger = logging.getLogger(__name__)
CACHE_S = 30  # the checks open every store's metadata; a monitor (or anyone) polling /up reuses them this long


def up(request: HttpRequest) -> JsonResponse:
    """Public health check for the uptime monitor: down (503) when the database doesn't answer; degraded (still 200)
    when ingest or the forecast is behind or jobs failed, with the reasons."""
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
        checked = (ingest, forecast, problems + forecast_problems)
        cache.set(key, checked, CACHE_S)
    ingest, forecast, problems = checked
    body = {
        "status": "degraded" if problems else "ok",
        "version": settings.APP_VERSION,
        "database": database,
        "ingest": ingest,
        "forecast": forecast,
        "problems": problems,
    }
    return JsonResponse(body)


def download(request: HttpRequest, path: str) -> HttpResponse:
    """A yearly download (`ops.downloads`) in development and tests, from the data folder as it is now; Caddy serves
    them in production."""
    from ops import downloads

    return serve(request, path, document_root=str(downloads.folder(settings.DATA_DIR)))
