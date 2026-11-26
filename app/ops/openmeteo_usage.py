"""Open-Meteo's use against the plan (D115): every request the app makes is counted by UTC day and endpoint in
`OpenMeteoUsage`, failures and retries included (Open-Meteo counts what it receives), and the billing month's total
is set against `OPEN_METEO_MONTHLY_CALLS`. Past `OPEN_METEO_WARN_SHARE` of it, or of the free API's daily cap, or
when the last week's pace would pass the month's, the admin, `/up`, `jobs status` and the daily `housekeeping` log
say so. Nothing stops: the app keeps fetching, and the plan's own limits are Open-Meteo's to enforce.

Every Open-Meteo fetch in the app goes through `fetch_counted` (a test holds to it). Not counted: the IFS open-data
reads from S3 (not the API) and the development scripts' `agdata.clients.openmeteo_points`."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import requests
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.db.models import Sum

from agdata.sources import openmeteo

logger = logging.getLogger(__name__)

RECORD = """
INSERT INTO ops_openmeteousage (day, endpoint, requests, calls, failed) VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (day, endpoint)
DO UPDATE SET requests = ops_openmeteousage.requests + EXCLUDED.requests,
    calls = ops_openmeteousage.calls + EXCLUDED.calls,
    failed = ops_openmeteousage.failed + EXCLUDED.failed
"""
# Counts lost in a crash don't matter: don't wait for the write to reach the disk
NO_WAIT = "SET LOCAL synchronous_commit TO OFF"
PACE_DAYS = 7  # the complete days before today whose mean projects the month
DAY = timedelta(days=1)


@dataclass(kw_only=True)
class Tally:
    """What one fetch's attempts cost, by endpoint: [requests, calls, failed]."""

    by_endpoint: dict[str, list[float]] = field(default_factory=lambda: defaultdict(lambda: [0, 0.0, 0]))

    def add(self, call: openmeteo.Call) -> None:
        counts = self.by_endpoint[call.endpoint]
        counts[0] += 1
        counts[1] += call.calls
        counts[2] += 0 if call.ok else 1


def record(tally: Tally, now: datetime) -> None:
    """Adds a tally to its UTC day's rows. A database that fails here is logged, not raised: counting must never
    cost the request its answer."""
    if not tally.by_endpoint:
        return
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(NO_WAIT)
            for endpoint, (n, calls, failed) in tally.by_endpoint.items():
                cursor.execute(RECORD, [now.astimezone(UTC).date().isoformat(), endpoint, int(n), calls, int(failed)])
    except DatabaseError:
        logger.exception("Open-Meteo usage not recorded: %s", dict(tally.by_endpoint))


def fetch_counted(
    endpoint: str,
    cell: openmeteo.Cell,
    first: date,
    last: date,
    session: requests.Session | None = None,
    api_key: str | None = None,
    timeout: float = openmeteo.TIMEOUT,
    tries: int = openmeteo.TRIES,
    now: datetime | None = None,
) -> tuple[openmeteo.Hours, float]:
    """`openmeteo.fetch`, with every attempt it makes recorded against the plan, whether it succeeds or raises."""
    tally = Tally()
    try:
        return openmeteo.fetch(
            endpoint,
            cell,
            first,
            last,
            session=session,
            api_key=api_key,
            timeout=timeout,
            tries=tries,
            on_call=tally.add,
        )
    finally:
        record(tally=tally, now=now or datetime.now(UTC))


def billing_period(today: date, billing_day: int) -> tuple[date, date]:
    """The billing month holding `today`: from the billing day (1–28) to the day before it a month later."""
    first = today.replace(day=billing_day)
    if today < first:
        first = _months_later(first, -1)
    return first, _months_later(first, 1) - DAY


def _months_later(day: date, months: int) -> date:
    k = day.year * 12 + day.month - 1 + months
    return day.replace(year=k // 12, month=k % 12 + 1)


def period_text(first: date, last: date) -> str:
    """'November 12 to December 11'."""
    return f"{first:%B} {first.day} to {last:%B} {last.day}"


@dataclass(kw_only=True)
class PeriodUsage:
    first: date  # the billing month's first and last UTC days
    last: date
    used: float  # calls so far this billing month, today's included
    limit: int
    projected: float  # by the period's end, at the last PACE_DAYS complete days' mean
    today: float
    daily_limit: int | None

    @property
    def share(self) -> float:
        return self.used / self.limit

    @property
    def period(self) -> str:
        return period_text(self.first, self.last)


def period_usage(now: datetime) -> PeriodUsage:
    """The billing month's use so far and where the last week's pace takes it."""
    from ops.models import OpenMeteoUsage

    today = now.astimezone(UTC).date()
    first, last = billing_period(today=today, billing_day=settings.OPEN_METEO_BILLING_DAY)
    rows = OpenMeteoUsage.objects.filter(day__gte=min(first, today - PACE_DAYS * DAY), day__lte=today)
    by_day: dict[date, float] = defaultdict(float)
    for row in rows.values("day").annotate(calls=Sum("calls")):
        by_day[row["day"]] = row["calls"]
    used = sum(calls for day, calls in by_day.items() if day >= first)
    pace = sum(by_day[today - k * DAY] for k in range(1, PACE_DAYS + 1)) / PACE_DAYS  # days without rows used none
    end = datetime(last.year, last.month, last.day, tzinfo=UTC) + DAY
    left = max(0.0, (end - now) / DAY)
    return PeriodUsage(
        first=first,
        last=last,
        used=used,
        limit=settings.OPEN_METEO_MONTHLY_CALLS,
        projected=used + pace * left,
        today=by_day[today],
        daily_limit=settings.OPEN_METEO_DAILY_CALLS,
    )


def warnings_for(usage: PeriodUsage) -> list[str]:
    """What's worth a warning: the month or the day past OPEN_METEO_WARN_SHARE of the plan, or the month on pace to
    pass it."""
    share = settings.OPEN_METEO_WARN_SHARE
    out = []
    if usage.used >= share * usage.limit:
        out.append(
            f"Open-Meteo: {usage.used:,.0f} of the plan's {usage.limit:,} calls used {usage.period} ({usage.share:.0%})"
        )
    elif usage.projected >= usage.limit:
        out.append(
            f"Open-Meteo: at the last week's pace, {usage.projected:,.0f} calls by {usage.last:%B} {usage.last.day}, over the plan's {usage.limit:,} ({usage.used:,.0f} used so far)"
        )
    if usage.daily_limit is not None and usage.today >= share * usage.daily_limit:
        out.append(
            f"Open-Meteo: {usage.today:,.0f} of the day's {usage.daily_limit:,} calls used today (UTC; {usage.today / usage.daily_limit:.0%})"
        )
    return out


def summary(usage: PeriodUsage) -> str:
    """One sentence for the admin."""
    return f"Open-Meteo: {usage.used:,.0f} of the plan's {usage.limit:,} calls used {usage.period} ({usage.share:.0%}); at the last week's pace, about {usage.projected:,.0f} by {usage.last:%B} {usage.last.day}. Today (UTC): {usage.today:,.0f} calls."


def usage_health(now: datetime) -> tuple[dict, list[str]]:
    """`/up`'s `open_meteo` section and its problems, as `ingest_health` gives its own."""
    usage = period_usage(now)
    info = {
        "period_start": usage.first.isoformat(),
        "period_end": usage.last.isoformat(),
        "calls": round(usage.used),
        "limit": usage.limit,
        "share": round(usage.share, 3),
        "projected": round(usage.projected),
        "today": round(usage.today),
        "daily_limit": usage.daily_limit,
    }
    return info, warnings_for(usage)


def short_line(usage: PeriodUsage) -> str:
    """`jobs status`'s line: '1.24M of 5M calls November 12 to December 11 (25%), projected 3.1M; today 41k'."""
    return f"{_compact(usage.used)} of {_compact(usage.limit)} calls {usage.period} ({usage.share:.0%}), projected {_compact(usage.projected)}; today {_compact(usage.today)}"


def _compact(n: float) -> str:
    if n >= 1e6:
        return f"{n / 1e6:.3g}M"
    if n >= 1e3:
        return f"{n / 1e3:.3g}k"
    return f"{n:.0f}"
