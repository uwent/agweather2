from django.http import HttpRequest, HttpResponse

from api.envelope import error_response


def not_found(request: HttpRequest, rest: str = "") -> HttpResponse:
    """Any path under /api/v2 no endpoint matches: the error envelope, not Django's HTML page."""
    item = {
        "code": "not_found",
        "param": None,
        "message": f"There's no endpoint at {request.path}. The API's endpoints are listed at /api/v2/docs.",
    }
    return error_response(request, [item], status=404)
