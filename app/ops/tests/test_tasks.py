"""The jobs in ops.tasks: each waits a while for the write lock (the download jobs longer), labels it with its name,
and skips a turn (a warning) when it doesn't come."""

import logging
from datetime import UTC, datetime

import pytest

from ops import tasks
from ops.locks import WriteLocked

NOW = int(datetime(2025, 7, 1, 12, tzinfo=UTC).timestamp())


@pytest.fixture
def lock_calls(monkeypatch, settings, tmp_path):
    """tasks.write_lock replaced by one that records its arguments and never blocks."""
    settings.DATA_DIR = tmp_path
    settings.COPERNICUS_API_KEY = "key"
    calls = []

    class Free:
        def __enter__(self):
            return None

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(tasks, "write_lock", lambda data_dir, **kwargs: calls.append(kwargs) or Free())
    return calls


def locked(*args, **kwargs):
    raise WriteLocked("another job or command is writing (pid 7)", holder="7")


def warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and r.name == tasks.__name__]


@pytest.mark.parametrize(
    ("job", "refresh"),
    [
        (tasks.ingest_recent, "refresh_recent"),
        (tasks.ingest_forecast, "refresh_forecast"),
        (tasks.ingest_era5land, "refresh_era5land"),
        (tasks.ingest_ifs, "refresh_ifs"),
    ],
)
def test_each_job_skips_with_a_warning_when_the_lock_is_held(job, refresh, lock_calls, monkeypatch, caplog):
    monkeypatch.setattr(tasks, refresh, locked)
    if refresh in ("refresh_recent", "refresh_forecast"):
        monkeypatch.setattr(tasks, "write_lock", locked)  # these take the lock themselves
    with caplog.at_level(logging.WARNING, logger=tasks.__name__):
        job(NOW)  # returns, doesn't raise
    (message,) = warnings(caplog)
    assert f"{job.name.rsplit('.', 1)[-1]} skipped" in message and "pid 7" in message


def test_the_download_jobs_wait_for_the_lock_in_the_refresh_and_the_restitch(lock_calls, monkeypatch):
    stitched = []
    seen = {}

    def refresh_era5land(*args, lock, **kwargs):
        seen["era5land"] = lock
        return [("a span",)]

    def refresh_ifs(*args, lock, **kwargs):
        seen["ifs"] = lock
        return True

    monkeypatch.setattr(tasks, "refresh_era5land", refresh_era5land)
    monkeypatch.setattr(tasks, "refresh_ifs", refresh_ifs)
    monkeypatch.setattr(tasks, "restitch_current", lambda data_dir, box: stitched.append(box))
    tasks.ingest_era5land(NOW)
    tasks.ingest_ifs(NOW)
    assert stitched == [tasks.settings.SERVICE_BOX] * 2
    lock_calls.clear()
    for name in ("era5land", "ifs"):
        with seen[name]():  # what the refresh function enters when it writes
            pass
    assert [c["wait"] for c in lock_calls] == [tasks.DOWNLOAD_LOCK_WAIT_S] * 2
    assert [c["label"] for c in lock_calls] == ["job ingest_era5land", "job ingest_ifs"]
    assert tasks.DOWNLOAD_LOCK_WAIT_S >= 60


def test_the_download_jobs_restitch_waits_for_the_lock_too(lock_calls, monkeypatch):
    monkeypatch.setattr(tasks, "refresh_era5land", lambda *args, **kwargs: [("a span",)])
    monkeypatch.setattr(tasks, "restitch_current", lambda data_dir, box: None)
    tasks.ingest_era5land(NOW)
    assert lock_calls == [{"wait": tasks.DOWNLOAD_LOCK_WAIT_S, "label": "job ingest_era5land"}]


def test_nothing_new_from_era5land_or_ifs_does_not_restitch(lock_calls, monkeypatch):
    monkeypatch.setattr(tasks, "refresh_era5land", lambda *args, **kwargs: [])
    monkeypatch.setattr(tasks, "refresh_ifs", lambda *args, **kwargs: False)
    monkeypatch.setattr(tasks, "restitch_current", lambda *args: pytest.fail("restitched with nothing new"))
    tasks.ingest_era5land(NOW)
    tasks.ingest_ifs(NOW)
    assert lock_calls == []


def test_a_restitch_that_cannot_get_the_lock_is_a_skip_not_a_failure(lock_calls, monkeypatch, caplog):
    monkeypatch.setattr(tasks, "refresh_ifs", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "write_lock", locked)
    with caplog.at_level(logging.WARNING, logger=tasks.__name__):
        tasks.ingest_ifs(NOW)
    assert "ingest_ifs skipped" in warnings(caplog)[0]


def test_the_era5land_job_does_nothing_without_a_cds_key(lock_calls, settings, monkeypatch):
    settings.COPERNICUS_API_KEY = None
    monkeypatch.setattr(tasks, "refresh_era5land", lambda *args, **kwargs: pytest.fail("ran without a key"))
    tasks.ingest_era5land(NOW)
    assert lock_calls == []


def test_the_ifs_job_passes_the_key_to_the_refresh_even_when_it_is_unset(lock_calls, settings, monkeypatch):
    settings.COPERNICUS_API_KEY = None
    keys = []
    monkeypatch.setattr(tasks, "refresh_ifs", lambda data_dir, box, now, key, lock: keys.append(key) or False)
    tasks.ingest_ifs(NOW)
    assert keys == [None]  # IFS needs the key only for a first land mask; the refresh decides


def test_the_forecast_job_builds_with_the_service_box_and_the_job_time(lock_calls, settings, monkeypatch):
    seen = []
    monkeypatch.setattr(tasks, "refresh_forecast", lambda data_dir, box, now: seen.append((data_dir, box, now)))
    tasks.ingest_forecast(NOW)
    assert seen == [(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(NOW, UTC))]
    # the hourly and forecast jobs wait less: a backfill lets them in between its blocks
    assert lock_calls == [{"wait": tasks.JOB_LOCK_WAIT_S, "label": "job ingest_forecast"}]


# --- the maintenance jobs (Phase 5) ------------------------------------------------------------------------------


def test_the_past_years_job_builds_each_stale_year_and_warns_about_one_it_cant(lock_calls, monkeypatch, caplog):
    built = []

    def build(data_dir, year):
        if year == 2023:
            raise ValueError("2023 has no complete daily store")
        built.append(year)

    monkeypatch.setattr(tasks.pastyears, "stale_years", lambda data_dir, before: {2023: "missing", 2024: "stale"})
    monkeypatch.setattr(tasks.pastyears, "build", build)
    with caplog.at_level(logging.WARNING, logger=tasks.__name__):
        tasks.build_past_years(NOW)
    assert built == [2024]
    assert warnings(caplog) == ["past-years copy of 2023 not built: 2023 has no complete daily store"]
    assert lock_calls == []  # it only reads the daily stores


@pytest.fixture
def daily_store(settings, tmp_path):
    """An archive of one daily store over the test window: what the crop tiers job reads its window from."""
    from agdata.catalog import DAILY_VARIABLES
    from agdata.store import DAILY, GridStore
    from agdata.testing import WINDOW

    settings.DATA_DIR = tmp_path
    GridStore.create(tmp_path, DAILY, 2025, WINDOW, [DAILY_VARIABLES["air_temperature_min"]])
    return WINDOW


def test_the_crop_tiers_job_refreshes_the_archives_window_through_the_jobs_day(daily_store, monkeypatch):
    seen = []

    def refresh(data_dir, window, today, lock):
        seen.append((window, today))
        return {"archive": ["corn-stages.mid"]}

    monkeypatch.setattr(tasks.croptiers, "refresh", refresh)
    tasks.update_crop_tiers(NOW)
    assert seen == [(daily_store, datetime.fromtimestamp(NOW, UTC).date())]


def test_the_crop_tiers_job_skips_an_empty_archive_and_a_held_lock(daily_store, monkeypatch, caplog):
    def refresh(*args, **kwargs):
        raise WriteLocked("another job or command is writing (pid 7)", holder="7")

    monkeypatch.setattr(tasks.croptiers, "refresh", refresh)
    with caplog.at_level(logging.WARNING, logger=tasks.__name__):
        tasks.update_crop_tiers(NOW)
    assert "update_crop_tiers skipped" in warnings(caplog)[0]
    caplog.clear()
    monkeypatch.setattr(tasks.series, "archive_years", lambda data_dir: [])
    tasks.update_crop_tiers(NOW)  # nothing to do, and no warning
    assert warnings(caplog) == []


@pytest.mark.django_db
def test_the_maps_and_downloads_jobs_log_what_they_did(monkeypatch, caplog, settings, tmp_path):
    from types import SimpleNamespace

    from api.routes import maps
    from ops import downloads

    settings.DATA_DIR = tmp_path
    monkeypatch.setattr(maps, "prune_stale", lambda: 3)
    monkeypatch.setattr(downloads, "build_wanted", lambda data_dir, now: [SimpleNamespace(bytes=3e6)] * 2)
    with caplog.at_level(logging.INFO, logger=tasks.__name__):
        tasks.housekeeping(NOW)
        tasks.build_downloads(NOW)
    logged = [r.getMessage() for r in caplog.records if r.name == tasks.__name__]
    assert logged == ["maps: 3 unused images deleted", "downloads: 2 files built (6 MB)"]


def test_update_climatology_runs_only_when_the_plan_has_work(monkeypatch, settings, tmp_path, caplog):
    from ops import climatology

    settings.DATA_DIR = tmp_path
    settings.SERVICE_BOX = "wisconsin"
    ran = []
    monkeypatch.setattr(climatology, "run", lambda *a, **k: ran.append(k) or 0)
    with caplog.at_level(logging.INFO, logger=tasks.__name__):
        monkeypatch.setattr(climatology, "plan", lambda *a, **k: climatology.Plan(period=(), normal=[], overlap=[]))
        tasks.update_climatology(NOW)
        assert ran == []
        monkeypatch.setattr(
            climatology,
            "plan",
            lambda *a, **k: climatology.Plan(period=(1995,), normal=[1995], overlap=[], fetch=[("pr", 1995)]),
        )
        tasks.update_climatology(NOW)
    assert len(ran) == 1
    logged = [r.getMessage() for r in caplog.records if r.name == tasks.__name__]
    assert logged[-1] == "climatology: 1 files fetched, 0 years derived"
