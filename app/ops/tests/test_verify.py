"""The forecast's verification (D113): runs kept at publish, scored into ForecastScore, the job, the command and
`/up`."""

import json
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest
from django.contrib import admin
from django.core.management import call_command

from agdata import forecast, verification
from agdata.catalog import VARIABLES
from agdata.store import HOURLY, GridStore
from agdata.testing import WINDOW, fake_run, full, write_days
from ops import tasks
from ops.admin import ForecastScoreAdmin
from ops.forecast import refresh_forecast
from ops.models import ForecastScore
from ops.verification import keep_published, pooled, score, verification_health

CYCLE = datetime(2025, 7, 10, 13, tzinfo=UTC)
LATER = datetime(2025, 7, 11, 7, tzinfo=UTC)
DAY = date(2025, 7, 12)  # lead 2 of CYCLE, lead 1 of LATER
NOW = datetime(2025, 7, 14, 14, 25, tzinfo=UTC)
FORECAST = {
    "air_temperature_min": {DAY: full(11.0), DAY + timedelta(days=1): full(12.0)},
    "air_temperature_max": {DAY: full(22.0), DAY + timedelta(days=1): full(21.0)},
    "precipitation_sum": {DAY: full(1.0), DAY + timedelta(days=1): full(0.0)},
}


def observe_through(data_dir, last: datetime) -> None:
    """An hourly store with temperature through `last`: the archive's last observed hour."""
    store = GridStore.create(data_dir, HOURLY, last.year, WINDOW, [VARIABLES["air_temperature"]])
    store.write(last, {"air_temperature": full(20.0)}, source="urma")


def archive_day(data_dir, day: date, tmax: float = 20.0) -> None:
    write_days(
        data_dir,
        {
            "air_temperature_min": {day: full(10.0)},
            "air_temperature_max": {day: full(tmax)},
            "precipitation_sum": {day: full(0.0)},
        },
    )


@pytest.fixture
def kept(tmp_path):
    """Two kept runs holding DAY, and the archive observed through 07Z July 14 (DAY and the 13th closed), with DAY."""
    for cycle in (CYCLE, LATER):
        verification.keep(tmp_path, fake_run(tmp_path, cycle, FORECAST))
    observe_through(tmp_path, datetime(2025, 7, 14, 7, tzinfo=UTC))
    archive_day(tmp_path, DAY)
    return tmp_path


@pytest.mark.django_db
def test_due_days_are_scored_once_and_again_when_the_archive_rewrites_them(kept):
    done = score(kept, NOW)
    assert (done.days, done.rows) == (
        1,
        8,
    )  # DAY: two runs × min, max, precipitation, degree days; the 13th not archived
    rows = {(r.cycle, r.lead, r.variable): r for r in ForecastScore.objects.all()}
    tmax = rows[(CYCLE, 2, "air_temperature_max")]
    assert (tmax.valid_day, tmax.n, tmax.bias, tmax.mae, tmax.rmse) == (DAY, 6, 2.0, 2.0, 2.0)
    assert rows[(LATER, 1, "precipitation_sum")].false_alarms == 6
    assert score(kept, NOW).days == 0  # nothing new

    archive_day(kept, DAY, tmax=21.0)  # URMA replaces RTMA: a newer write
    done = score(kept, NOW)
    assert (done.days, done.rows) == (1, 8) and ForecastScore.objects.count() == 8
    assert ForecastScore.objects.get(cycle=CYCLE, lead=2, variable="air_temperature_max").bias == pytest.approx(1.0)
    assert score(kept, NOW, rescore=True).days == 1


@pytest.mark.django_db
def test_a_day_the_archive_hasnt_closed_waits(kept):
    archive_day(kept, DAY + timedelta(days=2))  # the 14th, still open at 07Z
    assert score(kept, NOW).days == 1
    assert not ForecastScore.objects.filter(valid_day=DAY + timedelta(days=2)).exists()


@pytest.mark.django_db
def test_scores_pool_weighted_by_cells(kept):
    score(kept, NOW)
    (row,) = pooled(since=DAY, variables=["air_temperature_max"], leads=[1, 2], by_cycle=True)[:1]
    assert (row["variable"], row["lead"], row["cycle_hour"], row["n"], row["scores"]) == (
        "air_temperature_max",
        1,
        7,
        6,
        1,
    )
    (precip,) = pooled(since=DAY, variables=["precipitation_sum"], leads=[2])
    assert (precip["hits"], precip["misses"], precip["false_alarms"]) == (0, 0, 6)


@pytest.mark.django_db
def test_verification_health_summarizes_and_alarms(kept):
    assert verification_health(kept.parent / "nothing", NOW) == (None, [])
    score(kept, NOW)
    body, problems = verification_health(kept, NOW)
    assert body is not None and body["runs_kept"] == 2 and body["last_scored_day"] == "2025-07-12"
    assert body["last_7_days"]["air_temperature_max"]["1"] == {"mae": 2.0, "bias": 2.0}
    assert problems == []

    archive_day(kept, DAY, tmax=16.0)  # lead 1's max off by 6 °C
    score(kept, NOW)
    _, problems = verification_health(kept, NOW)
    assert problems == ["forecast air_temperature_max lead-1 MAE 6.0 °C over 7 days"]

    _, problems = verification_health(kept, NOW + timedelta(days=12))  # days due long ago, none scored after DAY
    assert "no forecast day scored since 2025-07-12" in problems


@pytest.mark.django_db
def test_jobs_status_has_verifications_problems_as_up_does(kept):
    from ops import status

    archive_day(kept, DAY, tmax=16.0)
    score(kept, NOW)
    assert "forecast air_temperature_max lead-1 MAE 6.0 °C over 7 days" in status.snapshot(kept, NOW).problems


@pytest.mark.django_db
def test_up_shows_verification_once_there_is_some(kept, client, settings):
    settings.DATA_DIR = kept
    score(kept, datetime.now(UTC))
    body = client.get("/up").json()
    assert body["forecast"]["verification"]["runs_kept"] == 2


def test_a_real_published_run_is_kept_whole(archive_dir, tmp_path):
    """The fixture archive's run (`forecast.write_run`): every kept variable, leads 1-10, its values as published."""
    run = forecast.current_run(archive_dir)
    assert run is not None
    days = keep_published(tmp_path, run, NOW)
    assert days == [(date(2025, 7, 10) + timedelta(days=k)).isoformat() for k in range(1, 11)]
    (only,) = verification.kept_runs(tmp_path)
    assert set(only.versions) == set(verification.WEATHER) | set(verification.INGREDIENTS_KEPT)
    day = date(2025, 7, 13)
    kept = GridStore.open(only.path, verification.DAILY, 2025, verification.kept_variables())
    published = GridStore.open(run, verification.DAILY, 2025, [verification.kept_variable("air_temperature_max")])
    t = kept.index_of(day)
    np.testing.assert_array_equal(
        kept.read_steps("air_temperature_max", t, t + 1), published.read_steps("air_temperature_max", t, t + 1)
    )
    assert np.isfinite(kept.read_steps("late-blight-dsv.dsv", t, t + 1)).all()


def build_with_days(data_dir, window, cycle, soil=None):
    path = fake_run(data_dir, cycle, FORECAST, last_observed=cycle + timedelta(hours=1))
    info = json.loads((path / "run.json").read_text())
    first, last = cycle + timedelta(hours=1), cycle + timedelta(hours=264)
    (path / "run.json").write_text(json.dumps(info | {"first_hour": first.isoformat(), "last_hour": last.isoformat()}))
    return path


@pytest.mark.django_db
def test_publishing_keeps_the_run_and_a_failed_keep_still_publishes(tmp_path, monkeypatch):
    box = "43.05,-89.45,43.1,-89.4"
    record = refresh_forecast(tmp_path, box, NOW, find_cycle=lambda now: CYCLE, build=build_with_days)
    assert record is not None and record.sources["verified_days"] == [f"2025-07-{d}" for d in range(11, 21)]
    assert [k.cycle for k in verification.kept_runs(tmp_path)] == [CYCLE]

    def broken(*args):
        raise OSError("disk full")

    monkeypatch.setattr(verification, "keep", broken)
    record = refresh_forecast(tmp_path, box, NOW, find_cycle=lambda now: LATER, build=build_with_days)
    assert record is not None and record.status == "ok" and record.sources["verified_days"] is None
    assert forecast.current_run(tmp_path) == forecast.run_path(tmp_path, LATER).resolve()


@pytest.mark.django_db
def test_the_command_checks_scores_and_reports(kept, settings, capsys, monkeypatch):
    settings.DATA_DIR = kept
    monkeypatch.setattr("ops.management.commands.verify.clock", lambda: NOW)
    call_command("verify", "--check")
    out = capsys.readouterr().out
    assert "Kept runs: 2" in out and "Days due: 2025-07-12" in out
    call_command("verify")
    assert "1 days scored, 8 rows" in capsys.readouterr().out
    call_command("verify", "--report", "--days", "7")
    out = capsys.readouterr().out
    assert "air_temperature_max" in out and "hits 0, misses 0, false alarms 6" in out


def test_the_scoring_job_is_daily_and_in_the_catch_up():
    from procrastinate.contrib.django import app

    periodic = [p for p in app.periodic_registry.periodic_tasks.values() if p.task.name == tasks.score_forecasts.name]
    assert [p.cron for p in periodic] == ["25 14 * * *"]
    order = [t.name.rsplit(".", 1)[-1] for t in tasks.CATCH_UP]
    assert order.index("score_forecasts") == order.index("update_crop_tiers") + 1


def test_scores_are_read_only_in_the_admin(rf):
    model_admin = ForecastScoreAdmin(ForecastScore, admin.site)
    assert model_admin.has_add_permission(rf.get("/")) is False
    assert model_admin.has_change_permission(rf.get("/")) is False
