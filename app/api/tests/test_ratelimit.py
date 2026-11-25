"""Per-client rate limits (`api.ratelimit`, D69)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from asgiref.sync import sync_to_async
from django.db import DatabaseError, connection
from django.test.client import AsyncClient

from api import ratelimit, timelimit
from ops.models import ApiUsage
from ops.tasks import housekeeping

pytestmark = pytest.mark.django_db
CLIENT = "203.0.113.5"


@pytest.fixture
def limited(settings):
    settings.API_RATE_LIMIT = 3
    settings.API_RATE_UNIT_MS = 100_000  # every test request costs 1
    return settings


def _get(client, path="/api/v2/status", address=CLIENT):
    return client.get(path, REMOTE_ADDR=address)


def test_a_client_is_an_ipv4_address_or_an_ipv6_64(settings):
    settings.API_RATE_EXEMPT = ["127.0.0.0/8", "::1/128"]
    assert ratelimit.client_key("203.0.113.5") == "203.0.113.5"
    assert ratelimit.client_key("2001:db8:1:2:aaaa::1") == "2001:db8:1:2::/64"
    assert ratelimit.client_key("2001:db8:1:2:bbbb::9") == "2001:db8:1:2::/64"
    assert ratelimit.client_key("127.0.0.1") is None
    assert ratelimit.client_key("::1") is None
    assert ratelimit.client_key("not an address") is None
    assert ratelimit.client_key(None) is None


def test_a_request_costs_one_plus_one_per_unit_of_server_time(settings):
    settings.API_RATE_UNIT_MS = 100
    assert [ratelimit.cost_of(ms) for ms in (0, 99.9, 100, 950)] == [1, 1, 2, 10]


def test_responses_say_what_is_left_and_the_limit_refuses_once_spent(client, limited):
    remaining = [_get(client)["RateLimit-Remaining"] for _ in range(3)]
    assert remaining == ["2", "1", "0"]
    refused = _get(client)
    assert refused.status_code == 429
    assert refused["RateLimit-Limit"] == "3"
    assert 1 <= int(refused["Retry-After"]) <= 60
    error = refused.json()["errors"][0]
    assert error["code"] == "rate_limited"
    assert error["message"].startswith("This address has used its share")
    usage = ApiUsage.objects.get(client=CLIENT)
    assert (usage.requests, usage.cost) == (
        4,
        4,
    )  # a refused request is counted: a client that keeps sending stays refused


def test_a_slow_request_costs_more(client, limited):
    limited.API_RATE_LIMIT = 100
    limited.API_RATE_UNIT_MS = 0.001  # any request takes thousands of units
    _get(client)
    assert ApiUsage.objects.get(client=CLIENT).cost > 10


def test_clients_are_counted_apart(client, limited):
    for _ in range(3):
        _get(client)
    assert _get(client).status_code == 429
    assert _get(client, address="198.51.100.7").status_code == 200


def test_exempt_addresses_and_other_paths_are_not_counted(client, limited):
    assert "RateLimit-Limit" not in _get(client, address="127.0.0.1")
    assert "RateLimit-Limit" not in _get(client, path="/up")
    assert not ApiUsage.objects.exists()


def test_off_without_a_limit(client, settings):
    settings.API_RATE_LIMIT = None
    assert "RateLimit-Limit" not in _get(client)


def test_the_api_answers_if_the_counts_cannot_be_read(client, limited, monkeypatch):
    def broken(*args):
        raise DatabaseError("down")

    monkeypatch.setattr(ratelimit, "arrived", broken)
    assert _get(client).status_code == 200


def test_usage_older_than_a_week_is_pruned():
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    ApiUsage.objects.create(client=CLIENT, minute=now - timedelta(days=8), requests=1, cost=1)
    ApiUsage.objects.create(client=CLIENT, minute=now, requests=1, cost=1)
    housekeeping.func(timestamp=0)
    assert list(ApiUsage.objects.values_list("minute", flat=True)) == [now]


def test_a_request_is_charged_in_the_minute_it_finishes(client, limited, monkeypatch):
    """A request running on past its minute's end charges its cost to the next minute, not the one already over."""
    limited.API_RATE_LIMIT = 100
    limited.API_RATE_UNIT_MS = 0.001  # any request takes thousands of units
    arrival = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    minutes = iter([(arrival, 1), (arrival + timedelta(minutes=1), 55)])
    monkeypatch.setattr(ratelimit, "_minute_now", lambda: next(minutes))
    response = _get(client)
    first = ApiUsage.objects.get(client=CLIENT, minute=arrival)
    later = ApiUsage.objects.get(client=CLIENT, minute=arrival + timedelta(minutes=1))
    assert (first.requests, first.cost) == (1, 1)
    assert later.requests == 0 and later.cost > 10
    assert response["RateLimit-Reset"] == "55"
    assert response["RateLimit-Remaining"] == "0"  # the finishing minute's cost


def test_a_charge_settled_twice_adds_only_the_time_since(settings, monkeypatch):
    settings.API_RATE_UNIT_MS = 100
    minute = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(ratelimit, "_minute_now", lambda: (minute, 30))
    ApiUsage.objects.create(client=CLIENT, minute=minute, requests=1, cost=1)
    clock = iter([100.25, 100.95, 101.0])
    monkeypatch.setattr(ratelimit.time, "perf_counter", lambda: next(clock))
    charge = ratelimit.Charge(client=CLIENT, minute=minute, total=1, started=100.0)
    assert charge.settle() == (3, 30)  # 250 ms: 2 more
    assert charge.settle() == (10, 30)  # 950 ms: 7 more
    assert charge.settle() == (11, 30)  # 1,000 ms: 1 more
    assert ApiUsage.objects.get(client=CLIENT).cost == 11


def _cost_of(client: str) -> int:
    try:
        return ApiUsage.objects.get(client=client).cost
    finally:
        connection.close()  # this thread's own


@pytest.mark.urls("api.tests.routes")
@pytest.mark.django_db(transaction=True)  # the charge as the limit passes is written from another thread
def test_a_request_past_the_time_limit_is_charged_as_the_limit_passes_and_again_when_it_finishes(settings):
    settings.API_RATE_LIMIT = None
    settings.API_RATE_UNIT_MS = 100
    local = "127.0.0.1"  # AsyncClient's address

    async def go():
        await AsyncClient().get("/api/test/sleep")  # warms the process (its first request imports the routes)
        settings.API_TIME_LIMIT = 0.3
        settings.API_RATE_LIMIT = 1000
        settings.API_RATE_EXEMPT = []
        response = await AsyncClient().get("/api/test/sleep?seconds=1.2")
        at_limit = await sync_to_async(_cost_of, thread_sensitive=False)(local)  # the view's thread is still busy
        for _ in range(100):
            if not timelimit.overrunning():
                break
            await asyncio.sleep(0.05)
        await sync_to_async(lambda: connection.close())()  # the view's thread's (the test client keeps it open)
        return response, at_limit

    response, at_limit = asyncio.run(go())
    assert response.status_code == 503
    assert 3 <= at_limit <= 6  # 1 on arrival, 2 or 3 for the time to the limit
    assert int(response["RateLimit-Remaining"]) == 1000 - at_limit
    assert 13 <= sum(ApiUsage.objects.values_list("cost", flat=True)) <= 16  # 1 plus 12 or so for its 1.2 s
