from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.utils import timezone

from ops.health import ingest_health


def up(request: HttpRequest) -> JsonResponse:
    """Public health check for the uptime monitor: down (503) when the database doesn't answer; degraded (still 200)
    when ingest is behind or jobs failed, with the reasons."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        database = "down"
    if database == "down":
        body = {"status": "down", "version": settings.APP_VERSION, "database": database}
        return JsonResponse(body, status=503)
    ingest, problems = ingest_health(settings.DATA_DIR, timezone.now())
    body = {
        "status": "degraded" if problems else "ok",
        "version": settings.APP_VERSION,
        "database": database,
        "ingest": ingest,
        "problems": problems,
    }
    return JsonResponse(body)
