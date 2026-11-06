"""`ops.archive` and `manage.py archive`: each year's state from the stores' sources, and a fill of whole years in
order, with soil and the past-years copy alongside the next year's hours."""

import threading
from datetime import UTC, date, datetime
from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from agdata.daily import open_or_create_daily
from agdata.grid import service_window
from agdata.ingest import SOIL, open_or_create_hourly
from agdata.progress import Reporter
from ops import archive, backfill, runs

BOX = "43.05,-89.45,43.1,-89.4"
WINDOW = service_window(BOX)


def test_year_states_count_what_each_year_holds(tmp_path):
    hourly = open_or_create_hourly(tmp_path, 2023, WINDOW)
    start = datetime(2023, 1, 1, tzinfo=UTC)
    analysis: list[str | None] = [*(["urma"] * 40), *(["rtma"] * 8)]
    hourly.set_sources("air_temperature", start, analysis)
    hourly.set_sources("precipitation", start, ["urma"] * 48)
    hourly.set_sources("shortwave_radiation", start, ["hrrr"] * 24)
    soil: list[str | None] = [*(["era5land"] * 24), *(["ifs"] * 24)]
    hourly.set_sources(SOIL[0], start, soil)
    daily = open_or_create_daily(tmp_path, 2023, WINDOW)
    daily.set_sources("air_temperature_min", date(2023, 1, 1), ["urma"] * 3)
    (y,) = archive.year_states(tmp_path, now=datetime(2026, 11, 4, tzinfo=UTC))
    assert (y.year, y.hours, y.analysis, y.urma, y.rtma, y.precip, y.shortwave) == (2023, 8760, 48, 40, 8, 48, 24)
    assert (y.days, y.era5land_days, y.rolled_up, y.past_years) == (365, 1, 3, "missing")
    assert not y.complete


def test_this_year_counts_only_through_now(tmp_path):
    (y,) = archive.year_states(tmp_path, years=[2026], now=datetime(2026, 1, 3, 12, tzinfo=UTC))
    assert (y.hours, y.days, y.past_years) == (60, 2, "–")


@pytest.fixture
def fill_fakes(monkeypatch):
    log = SimpleNamespace(order=[], soil_threads=set())

    def run(**kwargs):
        log.order.append(("hours", kwargs["first"].year))
        return backfill.Result(fetched=kwargs["the_plan"].hours)

    def era5(**kwargs):
        log.order.append(("soil", kwargs["first"].year))
        log.soil_threads.add(threading.current_thread().name)
        return 12, 12

    monkeypatch.setattr(archive.backfill, "run", run)
    monkeypatch.setattr(archive, "backfill_era5land", era5)
    monkeypatch.setattr(archive.pastyears, "build", lambda data, year, progress: log.order.append(("past", year)))
    monkeypatch.setattr(
        archive, "update_days", lambda data, window, first, last, **kw: log.order.append(("dec31", first.year))
    )
    monkeypatch.setattr(archive.modelmaps, "status", lambda data, year: "not built")
    monkeypatch.setattr(
        archive.modelmaps, "build", lambda data, window, year, **kw: log.order.append(("ingredients", year))
    )
    return log


def plans(tmp_path, years):
    out = []
    for year in years:
        hours = backfill.Plan(blocks=[], stale={}, hours=100)
        out.append(
            archive.YearPlan(
                year=year, first=date(year, 1, 1), end=date(year + 1, 1, 1), hours=hours, era5land_days=365,
                past_years=True,
            )
        )  # fmt: skip
        (tmp_path / "hourly" / f"{year + 1}.zarr").mkdir(parents=True, exist_ok=True)
    return out


def report() -> Reporter:
    return Reporter(out=StringIO(), err=StringIO(), live=False)


class Lock:
    def __call__(self, **kwargs):
        return self

    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def test_a_fill_goes_newest_first_with_soil_and_past_years_beside_the_next_year(tmp_path, fill_fakes):
    result = archive.fill(
        data_dir=tmp_path, window=WINDOW, box=BOX, plans=plans(tmp_path, [2024, 2023]), report=report(),
        lock=Lock(), stopping=threading.Event(), workers=4, key="key",
    )  # fmt: skip
    hours = [step for step in fill_fakes.order if step[0] in ("hours", "dec31")]
    assert hours == [("hours", 2024), ("dec31", 2024), ("hours", 2023), ("dec31", 2023)]
    for year in (2024, 2023):  # each year's soil, its models' ingredients (soil feeds them), then its copy
        assert fill_fakes.order.index(("hours", year)) < fill_fakes.order.index(("soil", year))
        assert fill_fakes.order.index(("soil", year)) < fill_fakes.order.index(("ingredients", year))
        assert fill_fakes.order.index(("ingredients", year)) < fill_fakes.order.index(("past", year))
    assert fill_fakes.soil_threads == {"fill-soil"}  # not the hours' thread
    assert result.years == [2024, 2023] and result.fetched == 200 and not result.stopped


def test_a_fill_without_a_cds_key_warns_and_skips_soil(tmp_path, fill_fakes):
    reporter = report()
    archive.fill(
        data_dir=tmp_path, window=WINDOW, box=BOX, plans=plans(tmp_path, [2024]), report=reporter, lock=Lock(),
        stopping=threading.Event(), workers=4, key=None,
    )  # fmt: skip
    assert ("soil", 2024) not in fill_fakes.order and ("past", 2024) in fill_fakes.order
    assert any("COPERNICUS_API_KEY" in warning for warning in reporter.warnings)


def test_a_stopped_fill_starts_no_more_years(tmp_path, fill_fakes, monkeypatch):
    stopping = threading.Event()

    def run(**kwargs):
        fill_fakes.order.append(("hours", kwargs["first"].year))
        stopping.set()
        return backfill.Result(fetched=50, stopped=True)

    monkeypatch.setattr(archive.backfill, "run", run)
    result = archive.fill(
        data_dir=tmp_path, window=WINDOW, box=BOX, plans=plans(tmp_path, [2024, 2023]), report=report(),
        lock=Lock(), stopping=stopping, workers=4, key="key",
    )  # fmt: skip
    assert fill_fakes.order == [("hours", 2024)] and result.stopped and result.years == []


def test_the_estimate_counts_hours_and_only_the_last_years_soil(tmp_path):
    plan = plans(tmp_path, [2024, 2023])
    assert archive.estimate_s(plan, per_hour=5.0) == 200 * 5.0 + 365 / 30 * archive.ERA5LAND_MONTH_S


@pytest.mark.django_db
def test_the_archive_command_prints_each_year_and_whats_running(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    open_or_create_hourly(tmp_path, 2023, WINDOW).set_sources(
        "air_temperature", datetime(2023, 1, 1, tzinfo=UTC), ["urma"] * 24
    )
    run = runs.start(tmp_path, "backfill", ["--start", "2023-01-01"])
    (tmp_path / "runs" / f"{run.pid}.events.jsonl").write_text(
        '{"t": 1, "kind": "progress", "label": "hours", "done": 24, "total": 96, "elapsed": 60}\n'
    )
    out = StringIO()
    call_command("archive", stdout=out)
    text = out.getvalue()
    assert "2023            24/8,760" in text or "24/8,760" in text
    assert f"pid {run.pid}: backfill --start 2023-01-01" in text and "hours: 24/96 (25%), ~3 min left" in text
    assert "Lock: free" in text
    runs.finish(tmp_path, run, ok=True)
    assert not (tmp_path / "runs" / "archive").exists()


@pytest.mark.django_db
def test_archive_fill_dry_run_plans_and_estimates_without_fetching(settings, tmp_path, monkeypatch):
    settings.DATA_DIR = tmp_path
    monkeypatch.setattr(archive.backfill, "run", lambda **kwargs: pytest.fail("fetched"))
    out = StringIO()
    call_command("archive", "fill", "--from", "2024", "--to", "2024", "--box", BOX, "--dry-run", stdout=out)
    text = out.getvalue()
    assert "2024: 8,784 hours to fetch, 366 days of ERA5-Land, past-years copy to build" in text
    assert "About " in text and "dry run: nothing fetched" in text
    assert runs.runs(tmp_path) == []  # a dry run isn't recorded


def test_archive_stop_signals_each_running_run(settings, tmp_path, monkeypatch):
    settings.DATA_DIR = tmp_path
    run = runs.start(tmp_path, "backfill", [])
    runs.start(tmp_path, "job", ["ingest_recent"], id="job-7")  # the worker's (same pid here): never signalled
    stopped = []
    monkeypatch.setattr(runs, "stop", lambda r: stopped.append(r.key) or True)
    out = StringIO()
    call_command("archive", "stop", stdout=out)
    assert stopped == [run.key] and "to stop after its current block" in out.getvalue()


def test_a_stoppable_command_finishes_its_block_on_the_first_stop(settings, tmp_path, monkeypatch):
    import os
    import signal

    from ops.management.commands import rollup

    settings.DATA_DIR = tmp_path
    seen = {}

    def update_days(data, window, first, last):
        os.kill(os.getpid(), signal.SIGTERM)  # `archive stop` arrives mid-block
        seen["stopping"] = command.stopping.is_set()
        return [2025]

    monkeypatch.setattr(rollup, "update_days", update_days)
    command = rollup.Command(stdout=StringIO(), stderr=StringIO())
    command.stoppable = True
    call_command(command, "--start", "2025-07-01", "--end", "2025-07-01", "--box", BOX)
    assert seen == {"stopping": True}  # flagged, not interrupted
    (record,) = runs.runs(tmp_path)
    assert record.state == "done" and "stopped early" in record.summary


def test_background_starts_the_same_command_detached(settings, tmp_path, monkeypatch):
    from ops.management.commands import backfill as command

    settings.DATA_DIR = tmp_path
    launched = []
    monkeypatch.setattr(runs, "launch", lambda data, argv: launched.append(argv) or (4242, tmp_path / "x.log"))
    out = StringIO()
    instance = command.Command(stdout=out)
    instance.run_from_argv(["manage.py", "backfill", "--start", "2023-01-01", "--end", "2023-02-01", "--background"])
    assert launched == [["backfill", "--start", "2023-01-01", "--end", "2023-02-01"]]
    assert "pid 4242" in out.getvalue() and "archive stop 4242" in out.getvalue()


def test_background_works_with_no_other_arguments(settings, tmp_path, monkeypatch):
    from ops.management.commands import downloads as command

    settings.DATA_DIR = tmp_path
    launched = []
    monkeypatch.setattr(runs, "launch", lambda data, argv: launched.append(argv) or (4242, tmp_path / "x.log"))
    command.Command(stdout=StringIO()).run_from_argv(["manage.py", "downloads", "--background"])
    assert launched == [["downloads"]]


def test_jobs_is_not_recorded_as_a_run(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    call_command("jobs", "list", stdout=StringIO())
    assert runs.runs(tmp_path) == []


def test_the_ingredients_command_builds_what_isnt_current(settings, tmp_path, monkeypatch):
    from agdata import modelmaps

    settings.DATA_DIR = tmp_path
    (tmp_path / "daily" / "2025.zarr").mkdir(parents=True)
    (tmp_path / "daily" / "2024.zarr").mkdir(parents=True)
    monkeypatch.setattr(modelmaps, "status", lambda data, year: "not built" if year == 2025 else None)
    built = []

    def build(data, window, year, lock, progress):
        with lock():
            progress(1, 1)
        built.append(year)
        return date(year, 1, 1), date(year, 7, 1)

    monkeypatch.setattr(modelmaps, "build", build)
    monkeypatch.setattr(
        "ops.management.commands.ingredients.GridStore.open", lambda *a, **k: SimpleNamespace(window=WINDOW)
    )
    out = StringIO()
    call_command("ingredients", "--check", stdout=out)
    assert "2025: not built" in out.getvalue() and "2024" not in out.getvalue()
    call_command("ingredients", stdout=StringIO())
    assert built == [2025]
    call_command("ingredients", "--year", "2024", stdout=StringIO())
    assert built == [2025, 2024]


def test_the_archive_table_says_how_to_rebuild_a_past_years_copy_only_for_a_whole_year():
    from types import SimpleNamespace

    from agdata import pastyears
    from ops.management.commands.archive import _rebuildable

    def year(past, rolled):
        return SimpleNamespace(past_years=past, rolled_up=rolled, days=365)

    assert _rebuildable(year(pastyears.OUT_OF_DATE_DATA, 365))
    assert _rebuildable(year("missing", 365))
    assert not _rebuildable(year("missing", 190))  # still being filled: `archive fill` builds it when done
    assert not _rebuildable(year("current", 365))
