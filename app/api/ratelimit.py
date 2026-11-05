"""Per-client rate limits on the API (D69).

Each client (an IPv4 address, or an IPv6 /64, which one household or server is given) has a budget of
`API_RATE_LIMIT` units a minute. A request costs 1 unit plus 1 for every `API_RATE_UNIT_MS` of server time it took,
so a kept tile or a 304 costs 1, a map computed afresh several, and every model at a point about ten: the cost
follows the work, with no table of costs per endpoint to keep. Counts are kept in Postgres (`ops.models.ApiUsage`),
shared by every web process: a request's first unit is recorded as it arrives (one query, and all a cheap request
costs), the rest after it's answered. A request is refused (429, with `Retry-After`) once the minute's budget is
spent, and still counted, so a client that keeps sending stays refused; the request that crosses the line is
answered, so a client can overrun by one request's cost.

Every API response says where the client stands: `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`
(seconds until the minute ends). If the database can't be reached the API answers without limits rather than fail.
The client's address is `REMOTE_ADDR`: in production uvicorn takes it from `X-Forwarded-For`, which Caddy sets
to the address it saw (it drops what a client sends), and only Caddy can reach uvicorn.
"""

import ipaddress
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.http import HttpRequest, HttpResponse

from api import envelope

logger = logging.getLogger(__name__)

ARRIVED = """
INSERT INTO ops_apiusage (client, minute, requests, cost) VALUES (%s, %s, 1, 1)
ON CONFLICT (client, minute)
DO UPDATE SET requests = ops_apiusage.requests + 1, cost = ops_apiusage.cost + 1
RETURNING cost
"""
# Counts lost in a crash don't matter: don't wait for the write to reach the disk (~2 ms a request)
NO_WAIT = "SET LOCAL synchronous_commit TO OFF"
MORE = "UPDATE ops_apiusage SET cost = cost + %s WHERE client = %s AND minute = %s RETURNING cost"


def client_key(address: str | None) -> str | None:
    """The client a request is counted against: its IPv4 address or IPv6 /64, or None if it is exempt
    (`API_RATE_EXEMPT`) or has no valid address."""
    try:
        ip = ipaddress.ip_address(address or "")
    except ValueError:
        return None
    if any(ip in ipaddress.ip_network(net) for net in settings.API_RATE_EXEMPT):
        return None
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


def cost_of(elapsed_ms: float) -> int:
    return 1 + int(elapsed_ms // settings.API_RATE_UNIT_MS)


def arrived(client: str, minute: datetime) -> int:
    """Count a request and its first unit in the client's minute; the minute's cost so far, this one included."""
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(NO_WAIT)
        cursor.execute(ARRIVED, [client, minute])
        row = cursor.fetchone()
    assert row is not None
    return int(row[0])


def charge_more(client: str, minute: datetime, units: int) -> int:
    """Add the units a request cost past its first; the minute's cost."""
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(NO_WAIT)
        cursor.execute(MORE, [units, client, minute])
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def refused(request: HttpRequest, limit: int, reset: int) -> HttpResponse:
    message = (
        f"This address has used its share of the API for this minute ({limit} units; see RateLimit-Limit). "
        f"Please wait {reset} seconds and try again."
    )
    response = envelope.error_response(request, [{"code": "rate_limited", "param": None, "message": message}], 429)
    response["Retry-After"] = str(reset)
    _headers(response, limit, 0, reset)
    return response


def _headers(response: HttpResponse, limit: int, remaining: int, reset: int) -> None:
    response["RateLimit-Limit"] = str(limit)
    response["RateLimit-Remaining"] = str(max(0, remaining))
    response["RateLimit-Reset"] = str(reset)


class RateLimitMiddleware:
    """Counts and limits `/api/` requests per client (module docstring). Off when `API_RATE_LIMIT` is None."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        limit = settings.API_RATE_LIMIT
        client = client_key(request.META.get("REMOTE_ADDR")) if request.path.startswith("/api/") else None
        if limit is None or client is None:
            return self.get_response(request)
        now = datetime.now(UTC)
        minute = now.replace(second=0, microsecond=0)
        reset = 60 - now.second
        try:
            total = arrived(client, minute)
        except DatabaseError:
            logger.exception("rate limit: couldn't count the request; answering without a limit")
            return self.get_response(request)
        if total > limit:
            return refused(request, limit, reset)
        started = time.perf_counter()
        response = self.get_response(request)
        more = cost_of((time.perf_counter() - started) * 1000) - 1
        if more:
            try:
                total = charge_more(client, minute, more)
            except DatabaseError:
                logger.exception("rate limit: couldn't record the request's cost")
        _headers(response, limit, limit - total, reset)
        return response
