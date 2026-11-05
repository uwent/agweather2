"""Per-client rate limits (`api.ratelimit`, D69)."""

from datetime import UTC, datetime, timedelta

import pytest
from django.db import DatabaseError

from api import ratelimit
from ops.models import ApiUsage
from ops.tasks import prune_api_usage

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
    prune_api_usage.func(timestamp=0)
    assert list(ApiUsage.objects.values_list("minute", flat=True)) == [now]
