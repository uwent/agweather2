from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.utils import timezone

from ops.forecast import forecast_health
from ops.health import ingest_health


def up(request: HttpRequest) -> JsonResponse:
    """Public health check for the uptime monitor: down (503) when the database doesn't answer; degraded (still 200)
    when ingest or the forecast is behind or jobs failed, with the reasons."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        database = "down"
    if database == "down":
        body = {"status": "down", "version": settings.APP_VERSION, "database": database}
        return JsonResponse(body, status=503)
    now = timezone.now()
    ingest, problems = ingest_health(settings.DATA_DIR, now)
    forecast, forecast_problems = forecast_health(settings.DATA_DIR, now)
    problems = problems + forecast_problems
    body = {
        "status": "degraded" if problems else "ok",
        "version": settings.APP_VERSION,
        "database": database,
        "ingest": ingest,
        "forecast": forecast,
        "problems": problems,
    }
    return JsonResponse(body)
