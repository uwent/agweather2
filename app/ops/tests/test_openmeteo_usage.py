"""Open-Meteo's use against the plan (D115, `ops.openmeteo_usage`)."""

import ast
import logging
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import requests
from django.contrib import admin
from django.contrib.messages import get_messages

from agdata.sources import openmeteo as source
from ops import openmeteo_usage as usage
from ops import status, tasks
from ops.admin import OpenMeteoUsageAdmin
from ops.models import OpenMeteoUsage

APP = Path(__file__).parents[2]
NOW = datetime(2026, 11, 24, 12, tzinfo=UTC)  # day 13 of the billing month November 12 to December 11
CELL = source.cell_for(36.12, -97.07)


@pytest.fixture
def plan(settings):
    settings.OPEN_METEO_MONTHLY_CALLS = 1000
    settings.OPEN_METEO_DAILY_CALLS = None
    settings.OPEN_METEO_BILLING_DAY = 12
    settings.OPEN_METEO_WARN_SHARE = 0.8
    return settings


def use(day: date, calls: float, endpoint: str = "forecast") -> None:
    OpenMeteoUsage.objects.create(day=day, endpoint=endpoint, requests=int(calls), calls=calls)


def call(endpoint: str = "forecast", calls: float = 1.0, ok: bool = True, status: int | None = 200) -> source.Call:
    return source.Call(endpoint=endpoint, calls=calls, status=status, ok=ok)


def test_the_billing_month_runs_from_the_billing_day_to_the_day_before_it_next_month():
    assert usage.billing_period(today=date(2026, 11, 24), billing_day=12) == (date(2026, 11, 12), date(2026, 12, 11))
    assert usage.billing_period(today=date(2026, 11, 12), billing_day=12) == (date(2026, 11, 12), date(2026, 12, 11))
    assert usage.billing_period(today=date(2026, 11, 11), billing_day=12) == (date(2026, 10, 12), date(2026, 11, 11))
    assert usage.billing_period(today=date(2027, 1, 5), billing_day=12) == (date(2026, 12, 12), date(2027, 1, 11))
    assert usage.billing_period(today=date(2026, 12, 31), billing_day=1) == (date(2026, 12, 1), date(2026, 12, 31))
    assert usage.period_text(date(2026, 11, 12), date(2026, 12, 11)) == "November 12 to December 11"


@pytest.mark.django_db
def test_a_tally_adds_to_its_days_rows():
    tally = usage.Tally()
    for c in (call(), call(ok=False, status=500), call(endpoint="historical", calls=2.5)):
        tally.add(c)
    usage.record(tally=tally, now=NOW)
    usage.record(tally=tally, now=NOW)
    usage.record(tally=usage.Tally(), now=NOW)  # nothing to add
    rows = {r.endpoint: (r.day, r.requests, r.calls, r.failed) for r in OpenMeteoUsage.objects.all()}
    assert rows == {"forecast": (NOW.date(), 4, 4.0, 2), "historical": (NOW.date(), 2, 5.0, 0)}


@pytest.mark.django_db
def test_a_fetch_is_counted_whether_it_succeeds_or_fails(monkeypatch):
    def fetch(endpoint, cell, first, last, session=None, api_key=None, timeout=None, tries=None, on_call=None):
        assert on_call is not None
        on_call(call(endpoint=endpoint, ok=False, status=503))
        if endpoint == "archive":
            raise requests.HTTPError("Open-Meteo 503")
        on_call(call(endpoint=endpoint))
        return source.Hours(start=NOW, values={"air_temperature": np.zeros(24)}), 1.0

    monkeypatch.setattr(source, "fetch", fetch)
    _, calls = usage.fetch_counted("forecast", CELL, NOW.date(), NOW.date(), now=NOW)
    assert calls == 1.0
    with pytest.raises(requests.HTTPError):
        usage.fetch_counted("archive", CELL, date(2020, 1, 1), date(2020, 1, 31), now=NOW)
    rows = {r.endpoint: (r.requests, r.calls, r.failed) for r in OpenMeteoUsage.objects.all()}
    assert rows == {"forecast": (2, 2.0, 1), "archive": (1, 1.0, 1)}


@pytest.mark.django_db
def test_a_database_failure_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setattr(usage, "RECORD", "INSERT INTO no_such_table VALUES (%s, %s, %s, %s, %s)")
    tally = usage.Tally()
    tally.add(call())
    with caplog.at_level(logging.ERROR, logger=usage.__name__):
        usage.record(tally=tally, now=NOW)
    assert "Open-Meteo usage not recorded" in caplog.text
    assert OpenMeteoUsage.objects.count() == 0  # and the transaction around it still works


@pytest.mark.django_db
def test_the_month_is_projected_at_the_last_weeks_pace(plan):
    use(date(2026, 11, 11), 500)  # the last billing month's, and before the last week
    for k in range(1, 7):
        use(NOW.date() - timedelta(days=k), 10)  # November 18–23
    use(NOW.date(), 5)
    use(NOW.date(), 1, endpoint="historical")
    u = usage.period_usage(NOW)
    assert (u.first, u.last, u.period) == (date(2026, 11, 12), date(2026, 12, 11), "November 12 to December 11")
    assert u.used == 66 and u.today == 6 and u.share == pytest.approx(0.066)
    pace = (6 * 10 + 0) / 7  # November 17 used nothing
    assert u.projected == pytest.approx(66 + pace * 17.5)  # 17.5 days to December 12 00Z
    assert usage.warnings_for(u) == []


@pytest.mark.django_db
def test_a_warning_at_80_percent_of_the_month_and_on_a_pace_to_pass_it(plan):
    use(date(2026, 11, 12), 790)
    u = usage.period_usage(NOW)
    assert usage.warnings_for(u) == []  # 79%, and nothing in the last week
    use(NOW.date(), 10)
    assert usage.warnings_for(usage.period_usage(NOW)) == [
        "Open-Meteo: 800 of the plan's 1,000 calls used November 12 to December 11 (80%)"
    ]
    OpenMeteoUsage.objects.all().delete()
    use(NOW.date() - timedelta(days=1), 70)  # 10 a day over the week, for 17.5 days more
    assert usage.warnings_for(usage.period_usage(NOW)) == []
    use(NOW.date() - timedelta(days=2), 400)
    assert usage.warnings_for(usage.period_usage(NOW)) == [
        "Open-Meteo: at the last week's pace, 1,645 calls by December 11, over the plan's 1,000 (470 used so far)"
    ]


@pytest.mark.django_db
def test_without_a_key_the_free_apis_daily_cap_is_watched_too(plan):
    plan.OPEN_METEO_DAILY_CALLS = 100
    use(NOW.date(), 85)
    assert usage.warnings_for(usage.period_usage(NOW)) == [
        "Open-Meteo: 85 of the day's 100 calls used today (UTC; 85%)"
    ]


@pytest.mark.django_db
def test_the_admin_says_where_the_month_stands_and_warns_past_the_threshold(plan, admin_client, settings):
    use(date(2026, 11, 20), 100)
    response = admin_client.get("/admin/ops/openmeteousage/")
    assert response.status_code == 200
    shown = [(m.level_tag, m.message) for m in get_messages(response.wsgi_request)]
    assert [level for level, _ in shown] == ["info"]
    assert "of the plan's 1,000 calls used" in shown[0][1]
    OpenMeteoUsage.objects.update(calls=900)
    response = admin_client.get("/admin/ops/openmeteousage/")
    shown = [(m.level_tag, m.message) for m in get_messages(response.wsgi_request)]
    assert [level for level, _ in shown] == ["info", "warning"]


def test_the_admin_is_read_only(rf):
    model_admin = OpenMeteoUsageAdmin(OpenMeteoUsage, admin.site)
    request = rf.get("/")
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request, obj=OpenMeteoUsage()) is False


@pytest.mark.django_db
def test_up_reports_the_month_and_is_degraded_past_the_threshold(client, plan, tmp_path):
    plan.DATA_DIR = tmp_path
    today = datetime.now(UTC).date()
    use(today, 100)
    body = client.get("/up").json()
    assert body["status"] == "ok"
    section = body["open_meteo"]
    assert (section["calls"], section["limit"], section["share"], section["today"], section["daily_limit"]) == (
        100,
        1000,
        0.1,
        100,
        None,
    )
    assert section["period_start"] <= today.isoformat() <= section["period_end"]
    from django.core.cache import cache

    cache.clear()
    OpenMeteoUsage.objects.update(calls=850)
    body = client.get("/up").json()
    assert body["status"] == "degraded"
    assert any(p.startswith("Open-Meteo: 850 of the plan's 1,000 calls") for p in body["problems"])


@pytest.mark.django_db
def test_jobs_status_has_a_line_for_the_month(plan, tmp_path):
    use(NOW.date(), 1_240)
    plan.OPEN_METEO_MONTHLY_CALLS = 5_000_000
    current = status.snapshot(tmp_path, NOW)
    lines = status.status_lines(current)
    assert "  open-meteo: 1.24k of 5M calls November 12 to December 11 (0%), projected 1.24k; today 1.24k" in lines


@pytest.mark.django_db
def test_housekeeping_keeps_two_years_and_warns_while_over(plan, caplog):
    use(NOW.date() - timedelta(days=2 * 365 + 1), 1)
    use(NOW.date() - timedelta(days=2 * 365), 1)
    use(NOW.date(), 900)
    with caplog.at_level(logging.INFO, logger=tasks.__name__):
        tasks.open_meteo_housekeeping(NOW)
    assert OpenMeteoUsage.objects.count() == 2
    logged = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == tasks.__name__]
    assert logged == [
        ("INFO", "Open-Meteo usage: 1 rows older than two years deleted"),
        ("WARNING", "Open-Meteo: 900 of the plan's 1,000 calls used November 12 to December 11 (90%)"),
    ]


def plan_settings(**env: str) -> str:
    """config.settings' Open-Meteo plan in a fresh Python with only these variables set ("": empty)."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith("OPEN_METEO_")}
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment.update({"DJANGO_ENV": "development", "OPEN_METEO_API_KEY": ""} | env)
    script = "import config.settings as s; print(s.OPEN_METEO_MONTHLY_CALLS, s.OPEN_METEO_DAILY_CALLS, s.OPEN_METEO_BILLING_DAY)"
    result = subprocess.run(
        [sys.executable, "-c", script], env=environment, cwd=APP, capture_output=True, text=True, timeout=60
    )
    return result.stdout.strip() or result.stderr.strip().splitlines()[-1]


def test_the_plan_defaults_to_the_customer_plan_with_a_key_and_the_free_apis_limits_without():
    assert plan_settings(OPEN_METEO_API_KEY="k") == "5000000 None 12"
    assert plan_settings() == "300000 10000 12"
    assert plan_settings(OPEN_METEO_MONTHLY_CALLS="1000000", OPEN_METEO_BILLING_DAY="3") == "1000000 10000 3"
    assert "OPEN_METEO_BILLING_DAY must be" in plan_settings(OPEN_METEO_BILLING_DAY="31")


def openmeteo_module_names(tree: ast.Module) -> set[str]:
    """The names a module binds to `agdata.sources.openmeteo`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "agdata.sources":
            names |= {a.asname or a.name for a in node.names if a.name == "openmeteo"}
        elif isinstance(node, ast.Import):
            names |= {a.asname for a in node.names if a.name == "agdata.sources.openmeteo" and a.asname}
    return names


def test_every_open_meteo_fetch_in_the_app_is_counted():
    """D115: the app fetches from Open-Meteo only through `fetch_counted`, so every call is counted against the plan.
    A new caller (the fallback when NBM is late, a job) uses it too."""
    allowed = APP / "ops" / "openmeteo_usage.py"
    found = []
    for path in sorted(APP.rglob("*.py")):
        if "tests" in path.parts or path == allowed:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        names = openmeteo_module_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "agdata.sources.openmeteo":
                found += [
                    f"{path.relative_to(APP)}:{node.lineno} imports {a.name}"
                    for a in node.names
                    if a.name in ("fetch", "_get")
                ]
            if (
                isinstance(node, ast.Attribute)
                and node.attr in ("fetch", "_get")
                and isinstance(node.value, ast.Name)
                and node.value.id in names
            ):
                found.append(f"{path.relative_to(APP)}:{node.lineno} uses openmeteo.{node.attr}")
            if (
                isinstance(node, ast.Attribute)
                and node.attr in ("fetch", "_get")
                and ast.unparse(node.value) == "agdata.sources.openmeteo"
            ):
                found.append(f"{path.relative_to(APP)}:{node.lineno} uses agdata.sources.openmeteo.{node.attr}")
    assert found == [], "fetch from Open-Meteo through ops.openmeteo_usage.fetch_counted"
    assert "fetch_counted(" in (APP / "ops" / "openmeteo.py").read_text()  # the guard sees the real caller
