from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse


def up(request: HttpRequest) -> JsonResponse:
    """Public health check for the uptime monitor: ok, or down when the database doesn't answer."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        database = "down"
    status = "ok" if database == "ok" else "down"
    return JsonResponse(
        {"status": status, "version": settings.APP_VERSION, "database": database},
        status=200 if status == "ok" else 503,
    )
