"""Per-client rate limits on the API (D69).

Each client (an IPv4 address, or an IPv6 /64, which one household or server is given) has a budget of
`API_RATE_LIMIT` units a minute. A request costs 1 unit plus 1 for every `API_RATE_UNIT_MS` of server time it took,
so a kept tile or a 304 costs 1, a map computed afresh several, and every model at a point about ten: the cost
follows the work, with no table of costs per endpoint to keep. Counts are kept in Postgres (`ops.models.ApiUsage`),
shared by every web process: a request's first unit is recorded as it arrives (one query, and all a cheap request
costs), the rest after it's answered, in the minute it finishes in (a request that ran on past a minute's end would
otherwise charge a minute already over, and cost nothing more). A request past the time limit (`api.timelimit`) is
charged its time so far when the limit passes, and the rest when it finishes, so a client can't start many long
requests within one minute's budget. A request is refused (429, with `Retry-After`) once the minute's budget is
spent, and still counted, so a client that keeps sending stays refused; the request that crosses the line is
answered, so a client can overrun by one request's cost.

Every API response says where the client stands: `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`
(seconds until the minute ends). If the database can't be reached the API answers without limits rather than fail.
The client's address is `REMOTE_ADDR`: in production uvicorn takes it from `X-Forwarded-For`, which Caddy sets
to the address it saw (it drops what a client sends), and only Caddy can reach uvicorn.
"""

import ipaddress
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
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
# A request's cost past its first unit, in the minute it's charged in: a row of its own if the client has none there
MORE = """
INSERT INTO ops_apiusage (client, minute, requests, cost) VALUES (%s, %s, 0, %s)
ON CONFLICT (client, minute) DO UPDATE SET cost = ops_apiusage.cost + EXCLUDED.cost
RETURNING cost
"""


def address_key(address: str | None) -> str | None:
    """An address as one client: IPv4 as is, IPv6 as its /64; None if it isn't a valid address."""
    try:
        ip = ipaddress.ip_address(address or "")
    except ValueError:
        return None
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else str(ip)


def client_key(address: str | None) -> str | None:
    """The client a request is counted against: its IPv4 address or IPv6 /64, or None if it is exempt
    (`API_RATE_EXEMPT`) or has no valid address."""
    key = address_key(address)
    if key is None or any(
        ipaddress.ip_address(address or "") in ipaddress.ip_network(net) for net in settings.API_RATE_EXEMPT
    ):
        return None
    return key


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
    """Add units a request cost past its first to the client's `minute`; the minute's cost."""
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(NO_WAIT)
        cursor.execute(MORE, [client, minute, units])
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def _minute_now() -> tuple[datetime, int]:
    """The current minute and the seconds until it ends."""
    now = datetime.now(UTC)
    return now.replace(second=0, microsecond=0), 60 - now.second


@dataclass(kw_only=True)
class Charge:
    """A request's cost as charged so far: its first unit on arrival, then the rest by `settle`, which the request
    calls when it finishes and `api.timelimit` when it passes the time limit (from another thread)."""

    client: str
    minute: datetime  # the minute it arrived in, whose cost so far is `total`
    total: int
    started: float = field(default_factory=time.perf_counter)
    charged: int = 0  # units charged past the first
    lock: threading.Lock = field(default_factory=threading.Lock)

    def settle(self) -> tuple[int, int]:
        """Charges the units the request has cost so far and not been charged, to the current minute; that minute's
        cost (with nothing to charge, the last minute charged's: no write) and the seconds until the minute ends."""
        with self.lock:
            minute, reset = _minute_now()
            more = cost_of((time.perf_counter() - self.started) * 1000) - 1 - self.charged
            if more > 0:
                self.total = charge_more(self.client, minute, more)
                self.minute = minute
                self.charged += more
            return self.total, reset


def charge_overrun(request: HttpRequest, response: HttpResponse) -> None:
    """For `api.timelimit`, on a thread of its own as the time limit passes: charges the request its time so far and
    says where the client stands on `response` (the timeout). The thread's own database connection is closed after."""
    charge: Charge | None = getattr(request, "api_charge", None)
    if charge is None:
        return
    try:
        total, reset = charge.settle()
    except DatabaseError:
        logger.exception("rate limit: couldn't charge a request past the time limit")
        return
    finally:
        connection.close()
    limit = settings.API_RATE_LIMIT
    if limit is not None:
        _headers(response, limit, limit - total, reset)


def refused(request: HttpRequest, limit: int, reset: int) -> HttpResponse:
    message = f"This address has used its share of the API for this minute ({limit} units; see RateLimit-Limit). Please wait {reset} seconds and try again."
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
        minute, reset = _minute_now()
        try:
            total = arrived(client, minute)
        except DatabaseError:
            logger.exception("rate limit: couldn't count the request; answering without a limit")
            return self.get_response(request)
        if total > limit:
            return refused(request, limit, reset)
        charge = Charge(client=client, minute=minute, total=total)
        request.api_charge = charge  # pyright: ignore[reportAttributeAccessIssue]
        response = self.get_response(request)
        try:
            total, reset = charge.settle()
        except DatabaseError:
            logger.exception("rate limit: couldn't record the request's cost")
        _headers(response, limit, limit - total, reset)
        return response
