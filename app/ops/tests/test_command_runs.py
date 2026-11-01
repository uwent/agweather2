"""The data commands run end to end with fakes in place of the archive and the network: what they print (and not,
with --quiet), what they hand their helpers, and that a failure ends in a CommandError after the summary."""

import threading
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from agdata.ingest import BlockReport
from agdata.rebuild import StaleReport
from ops.locks import hold_write_lock
from ops.models import IngestRecord

BOX = "43.05,-89.45,43.1,-89.4"


def run(*args: str) -> tuple[str, str]:
    """(stdout, stderr) of a command; a CommandError propagates after the output is captured by the caller."""
    out, err = StringIO(), StringIO()
    call_command(*args, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


def run_failing(*args: str) -> tuple[CommandError, str, str]:
    out, err = StringIO(), StringIO()
    with pytest.raises(CommandError) as raised:
        call_command(*args, stdout=out, stderr=err)
    return raised.value, out.getvalue(), err.getvalue()


@pytest.fixture
def data_dir(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    return tmp_path


# --- the shared base ---------------------------------------------------------------------------------------------


def test_a_command_waits_for_a_held_lock_and_says_whose_it_is(data_dir, monkeypatch):
    from ops.management.commands import rollup

    monkeypatch.setattr(rollup, "update_days", lambda *args: [2025])
    monkeypatch.setattr("ops.locks.time.sleep", lambda seconds: threading.Event().wait(0.05))
    holder = hold_write_lock(data_dir)
    timer = threading.Timer(0.3, holder.close)
    timer.start()
    out, _ = run("rollup", "--start", "2025-07-01", "--end", "2025-07-01")
    timer.join()
    assert f"waiting for the write lock (held by pid {holder_pid()})" in out
    assert "rolled up 2025-07-01 to 2025-07-01" in out


def holder_pid() -> int:
    import os

    return os.getpid()  # the test process holds the lock


def test_a_command_gives_up_when_the_lock_stays_held(data_dir, monkeypatch):
    from ops.management import base
    from ops.management.commands import rollup

    monkeypatch.setattr(base, "LOCK_WAIT_S", 0.1)
    monkeypatch.setattr(rollup, "update_days", lambda *args: pytest.fail("ran without the lock"))
    holder = hold_write_lock(data_dir)
    try:
        with pytest.raises(CommandError, match="another job or command is writing"):
            call_command("rollup", "--start", "2025-07-01", "--end", "2025-07-01", stdout=StringIO(), stderr=StringIO())
    finally:
        holder.close()


# --- rollup ------------------------------------------------------------------------------------------------------


def test_rollup_includes_its_end_day_and_reports_the_years_rebuilt(data_dir, monkeypatch):
    from ops.management.commands import rollup

    calls = []
    monkeypatch.setattr(
        rollup, "update_days", lambda data, window, first, last: calls.append((data, first, last)) or [2024, 2025]
    )
    out, err = run("rollup", "--start", "2024-12-30", "--end", "2025-01-02", "--box", BOX)
    assert calls == [(data_dir, date(2024, 12, 30), date(2025, 1, 2))]  # the end is a day rolled up, not a bound
    assert "Rolling up 2024-12-30 to 2025-01-02 (4 days)" in out
    assert "rebuilt the running totals of [2024, 2025]" in out
    assert err == ""


def test_rollup_of_a_single_day_is_allowed(data_dir, monkeypatch):
    from ops.management.commands import rollup

    calls = []
    monkeypatch.setattr(rollup, "update_days", lambda data, window, first, last: calls.append((first, last)) or [])
    out, _ = run("rollup", "--start", "2025-07-01", "--end", "2025-07-01", "--box", BOX)
    assert calls == [(date(2025, 7, 1), date(2025, 7, 1))]
    assert "(1 days)" in out and "no years" in out


def test_quiet_keeps_steps_off_stdout(data_dir, monkeypatch):
    from ops.management.commands import rollup

    monkeypatch.setattr(rollup, "update_days", lambda *args: [2025])
    out, err = run("rollup", "--start", "2025-07-01", "--end", "2025-07-02", "--box", BOX, "--quiet")
    # Steps stay off the terminal; the summary is the one line left
    assert "Rolling up" not in out and len(out.splitlines()) == 1 and "Done in" in out
    assert err == ""


# --- rebuild -----------------------------------------------------------------------------------------------------


def test_rebuild_check_lists_stale_variables_without_rebuilding(data_dir, monkeypatch):
    from ops.management.commands import rebuild

    monkeypatch.setattr(rebuild, "find_stale", lambda data: StaleReport(stale={"daily/2025": ["gdd", "et0"]}))
    monkeypatch.setattr(rebuild, "rebuild_stale", lambda *args, **kwargs: pytest.fail("--check is read-only"))
    out, _ = run("rebuild", "--check")
    assert out == "daily/2025: gdd, et0\n"


def test_rebuild_without_a_flag_says_what_to_pass(data_dir):
    with pytest.raises(CommandError, match=r"--stale.*--check"):
        call_command("rebuild")


def test_rebuild_stale_with_nothing_stale_just_finishes(data_dir, monkeypatch):
    from ops.management.commands import rebuild

    seen = []
    monkeypatch.setattr(rebuild, "rebuild_stale", lambda data, window, log: seen.append(data) or StaleReport())
    out, err = run("rebuild", "--stale")
    assert seen == [data_dir]
    assert "Done in" in out and "warning" not in err and "failed" not in out


def test_rebuild_stale_warns_about_what_a_rebuild_cannot_fix(data_dir, monkeypatch):
    from ops.management.commands import rebuild

    monkeypatch.setattr(
        rebuild, "rebuild_stale", lambda data, window, log: StaleReport(stale={"hourly/2025": ["precipitation"]})
    )
    out, err = run("rebuild", "--stale")
    assert "still stale" in err and "hourly/2025: precipitation" in err
    assert "1 warning" in out


# --- forecast ----------------------------------------------------------------------------------------------------


def record(status, **fields) -> IngestRecord:
    when = datetime(2025, 7, 1, 12, tzinfo=UTC)
    defaults = {
        "kind": IngestRecord.Kind.FORECAST,
        "status": status,
        "box": BOX,
        "first_hour": when,
        "hours": 264,
        "started_at": when,
        "finished_at": when + timedelta(minutes=5),
    }
    return IngestRecord(**{**defaults, **fields})


def test_forecast_publishes_and_reports_the_run(data_dir, monkeypatch):
    from ops.management.commands import forecast

    calls = []

    def refresh(data, box, now, retry_failed):
        calls.append((data, box, now, retry_failed))
        return record(IngestRecord.Status.OK)

    monkeypatch.setattr(forecast, "refresh_forecast", refresh)
    out, _ = run("forecast", "--before", "2025-07-01T18", "--box", BOX)
    assert calls == [(data_dir, BOX, datetime(2025, 7, 1, 18, tzinfo=UTC), True)]  # a command retries failed cycles
    assert "before 2025-07-01 18Z" in out and "forecast 2025-07-01 12Z +264 h: ok" in out


def test_forecast_with_nothing_new_says_so(data_dir, monkeypatch):
    from ops.management.commands import forecast

    monkeypatch.setattr(forecast, "refresh_forecast", lambda *args, **kwargs: None)
    out, _ = run("forecast")
    assert "nothing new" in out


def test_forecast_partial_run_warns_about_failed_hours_and_exits_cleanly(data_dir, monkeypatch):
    from ops.management.commands import forecast

    rec = record(IngestRecord.Status.PARTIAL, failed_hours=["2025-07-02T00:00:00+00:00"])
    monkeypatch.setattr(forecast, "refresh_forecast", lambda *args, **kwargs: rec)
    out, err = run("forecast")
    assert "1 hours failed to fetch" in err and "1 warning" in out


def test_a_failed_forecast_build_prints_the_summary_then_raises(data_dir, monkeypatch):
    from ops.management.commands import forecast

    rec = record(IngestRecord.Status.FAILED, error="RuntimeError('GRIB truncated')")
    monkeypatch.setattr(forecast, "refresh_forecast", lambda *args, **kwargs: rec)
    error, out, err = run_failing("forecast", "--quiet")
    assert "1 failed" in str(error)
    assert "GRIB truncated" in err and "Done in" in err  # failures reach stderr even when quiet
    assert out == ""


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("--before", "2025-07-01T18:00+02:00"), "leave the offset off"),
        (("--before", "tomorrow"), "expected YYYY-MM-DDTHH"),
        (("--box", "nowhere"), "--box"),
    ],
)
def test_forecast_refuses_bad_arguments_before_building(data_dir, monkeypatch, args, message):
    from ops.management.commands import forecast

    monkeypatch.setattr(forecast, "refresh_forecast", lambda *a, **k: pytest.fail("built"))
    with pytest.raises(CommandError, match=message):
        call_command("forecast", *args)


# --- refetch_precip ----------------------------------------------------------------------------------------------


@pytest.fixture
def precip(data_dir, monkeypatch):
    """refetch_precip with the archive faked: the blocks refetched and the days rolled up are recorded."""
    from ops.management.commands import refetch_precip

    log = SimpleNamespace()
    log.refetched, log.rolled, log.rescaled = [], [], []
    monkeypatch.setattr(refetch_precip, "open_or_create_hourly", lambda data, year, window: ("store", year))
    monkeypatch.setattr(
        refetch_precip,
        "refetch_precipitation",
        lambda store, start, hours: log.refetched.append((start, hours)) or hours // 2,
    )
    monkeypatch.setattr(
        refetch_precip, "update_days", lambda data, window, first, last: log.rolled.append((first, last)) or [2025]
    )
    monkeypatch.setattr(
        refetch_precip.GridStore, "rescale", classmethod(lambda cls, data, layout, year, var: log.rescaled.append(year))
    )
    return log


def test_refetch_precip_rolls_up_from_the_day_before_start(precip):
    out, _ = run("refetch_precip", "--start", "2025-07-05", "--end", "2025-07-08", "--box", BOX)
    assert precip.refetched == [(datetime(2025, 7, 5, tzinfo=UTC), 72)]
    # a UTC day's first hours belong to the previous local day; the last day is the day before --end
    assert precip.rolled == [(date(2025, 7, 4), date(2025, 7, 7))]
    assert "36 of 72 hours replaced" in out
    assert precip.rescaled == []


def test_refetch_precip_works_in_blocks_of_ten_days_and_months(precip):
    out, _ = run("refetch_precip", "--start", "2025-06-28", "--end", "2025-07-03", "--box", BOX)
    assert [start for start, _ in precip.refetched] == [
        datetime(2025, 6, 28, tzinfo=UTC),
        datetime(2025, 7, 1, tzinfo=UTC),
    ]
    assert sum(hours for _, hours in precip.refetched) == 5 * 24
    assert "2 blocks" in out


def test_refetch_precip_rescale_repacks_each_year_first(precip):
    run("refetch_precip", "--start", "2024-12-30", "--end", "2025-01-02", "--box", BOX, "--rescale")
    assert precip.rescaled == [2024, 2025]
    assert precip.rolled == [(date(2024, 12, 29), date(2025, 1, 1))]


def test_refetch_precip_refuses_an_empty_range(precip):
    with pytest.raises(CommandError, match="must be after"):
        call_command("refetch_precip", "--start", "2025-07-05", "--end", "2025-07-05")
    assert precip.refetched == []


# --- backfill ----------------------------------------------------------------------------------------------------


@pytest.fixture
def backfill_fakes(data_dir, monkeypatch):
    from ops.management.commands import backfill

    log = SimpleNamespace()
    log.blocks, log.records, log.rolled, log.stale_asked = [], [], [], []
    log.failed = []
    log.stale = None  # None: every hour of the block is stale
    monkeypatch.setattr(backfill, "open_or_create_hourly", lambda data, year, window: "store")

    def stale_hours(data, window, start, stop, urma_published):
        log.stale_asked.append((start, stop))
        return (
            log.stale(start, stop)
            if log.stale
            else [start + timedelta(hours=h) for h in range(int((stop - start) / timedelta(hours=1)))]
        )

    def ingest_block(store, start, hours, workers, progress):
        log.blocks.append((start, hours, workers))
        progress(hours)
        return BlockReport(
            start=start,
            hours=hours,
            missing={"air_temperature": 0},
            out_of_range={},
            spikes={},
            failed=list(log.failed),
        )

    monkeypatch.setattr(backfill, "stale_hours", stale_hours)
    monkeypatch.setattr(backfill, "ingest_block", ingest_block)
    monkeypatch.setattr(backfill, "record_run", lambda *args: log.records.append(args))
    monkeypatch.setattr(
        backfill, "update_days", lambda data, window, first, last: log.rolled.append((first, last)) or [first.year]
    )
    monkeypatch.setattr(backfill, "_rolled_up", lambda *args: False)
    return log


def test_backfill_redo_refetches_the_whole_block_without_asking_what_is_stale(backfill_fakes):
    run("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX, "--redo", "--workers", "2")
    assert backfill_fakes.stale_asked == []
    assert backfill_fakes.blocks == [(datetime(2025, 7, 1, tzinfo=UTC), 72, 2)]
    (args,) = backfill_fakes.records
    assert args[0] == IngestRecord.Kind.BACKFILL and args[1] == BOX and args[6].failed == []


def test_backfill_rolls_up_the_days_a_block_finished(backfill_fakes):
    out, _ = run("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX)
    # not the day before the first block (outside the range) and not the last UTC day (it runs into the next block)
    assert backfill_fakes.rolled == [(date(2025, 7, 1), date(2025, 7, 2))]
    assert "72 hours fetched, 0 failed" in out
    assert "rolled up 2025-07-01 to 2025-07-02" in out


def test_backfill_second_block_also_rolls_up_the_day_before_it(backfill_fakes):
    run("backfill", "--start", "2025-07-01", "--end", "2025-07-08", "--box", BOX, "--block-days", "5")
    assert [start for start, _, _ in backfill_fakes.blocks] == [
        datetime(2025, 7, 1, tzinfo=UTC),
        datetime(2025, 7, 6, tzinfo=UTC),
    ]
    assert backfill_fakes.rolled == [(date(2025, 7, 1), date(2025, 7, 4)), (date(2025, 7, 5), date(2025, 7, 6))]


def test_backfill_with_a_complete_block_fetches_nothing(backfill_fakes):
    backfill_fakes.stale = lambda start, stop: []
    out, _ = run("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX)
    assert backfill_fakes.blocks == [] and backfill_fakes.records == []
    assert "complete" in out and "0 hours fetched" in out


def test_backfill_with_failed_hours_exits_nonzero_after_the_summary(backfill_fakes):
    backfill_fakes.failed = [datetime(2025, 7, 1, 5, tzinfo=UTC), datetime(2025, 7, 1, 6, tzinfo=UTC)]
    error, _out, err = run_failing("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX)
    assert "1 failed" in str(error)
    assert "2 hours not fetched (rerun to retry)" in err
    assert "1 failed:" in err  # one failure per block, the hours counted in its message
    assert "72 hours fetched, 2 failed" in err  # the summary still lists what was done
    assert backfill_fakes.rolled  # the block was still rolled up


def test_backfill_records_a_block_that_raises_and_stops(backfill_fakes, monkeypatch):
    from ops.management.commands import backfill

    def broken(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(backfill, "ingest_block", broken)
    with pytest.raises(RuntimeError, match="disk full"):
        call_command("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX, stdout=StringIO())
    (args,) = backfill_fakes.records
    assert args[6] is None and "disk full" in args[7]  # no report, the error recorded as a failed run
    assert backfill_fakes.rolled == []


def test_backfill_holds_the_lock_one_block_at_a_time(backfill_fakes, data_dir):
    seen = []
    original = backfill_fakes.stale_asked

    class Spy(list):
        def append(self, item):
            original.append(item)
            try:
                hold_write_lock(data_dir)
            except CommandError:
                seen.append("locked")

    backfill_fakes.stale_asked = Spy()
    run("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX)
    assert seen == ["locked"]
    hold_write_lock(data_dir).close()  # released at the end


# --- era5land ----------------------------------------------------------------------------------------------------


@pytest.fixture
def cds(data_dir, settings, monkeypatch):
    """era5land with the CDS and the archive faked: a month's request fails when its first day is in `fail`."""
    from agdata.sources import era5land as source
    from ops.management.commands import era5land as command

    settings.COPERNICUS_API_KEY = "key"
    log = SimpleNamespace()
    log.requests, log.written, log.rolled, log.fail, log.files_seen = [], [], [], set(), []
    log.days = [date(2025, 5, 30), date(2025, 5, 31), date(2025, 6, 1), date(2025, 6, 2)]

    monkeypatch.setattr(
        command, "missing_days", lambda data, window, first, last: [d for d in log.days if first <= d <= last]
    )
    monkeypatch.setattr(command, "land_mask", lambda data, window, key: "land")

    def retrieve(first, last, window, path, key):
        log.requests.append((first, last))
        if first in log.fail:
            raise RuntimeError("CDS request failed")
        path.write_bytes(b"grib")
        log.files_seen.append(path)
        return path

    def write_file(data, window, path, land):
        assert path.read_bytes() == b"grib" and land == "land"
        log.written.append(path.name)
        return (date.fromisoformat(path.stem.split("_")[0]), date.fromisoformat(path.stem.split("_")[1]))

    monkeypatch.setattr(source, "retrieve", retrieve)
    monkeypatch.setattr(command, "write_file", write_file)
    monkeypatch.setattr(command, "roll_up", lambda data, window, first, last: log.rolled.append((first, last)))
    return log


def test_era5land_needs_its_api_key(cds, settings):
    settings.COPERNICUS_API_KEY = None
    with pytest.raises(CommandError, match="COPERNICUS_API_KEY"):
        call_command("era5land", "--start", "2025-05-30", "--end", "2025-06-03")


def test_era5land_writes_each_span_rolls_it_up_and_deletes_the_download(cds, data_dir):
    out, err = run("era5land", "--start", "2025-05-30", "--end", "2025-06-03", "--box", BOX)
    assert sorted(cds.requests) == [(date(2025, 5, 30), date(2025, 5, 31)), (date(2025, 6, 1), date(2025, 6, 2))]
    assert sorted(cds.rolled) == [(date(2025, 5, 30), date(2025, 5, 31)), (date(2025, 6, 1), date(2025, 6, 2))]
    assert "4 days to fetch in 2 requests" in out and "2 of 2 requests written" in out
    assert err == ""
    assert not any(path.exists() for path in cds.files_seen)


def test_one_failing_span_is_reported_the_other_is_written_and_the_exit_is_nonzero(cds, data_dir):
    cds.fail = {date(2025, 5, 30)}
    error, _out, err = run_failing("era5land", "--start", "2025-05-30", "--end", "2025-06-03", "--box", BOX)
    assert "1 failed" in str(error)
    assert "failed: 2025-05-30..2025-05-31" in err and "CDS request failed" in err
    assert "1 of 2 requests written" in err
    assert cds.written == ["2025-06-01_2025-06-02.grib"]
    assert cds.rolled == [(date(2025, 6, 1), date(2025, 6, 2))]


def test_a_failure_while_writing_is_reported_and_the_file_is_still_removed(cds, monkeypatch):
    from ops.management.commands import era5land as command

    def broken(data, window, path, land):
        cds.files_seen.append(path)
        raise OSError("disk full")

    monkeypatch.setattr(command, "write_file", broken)
    _error, _out, err = run_failing("era5land", "--start", "2025-06-01", "--end", "2025-06-03", "--box", BOX)
    assert "disk full" in err
    assert cds.rolled == [] and cds.files_seen
    assert not any(path.exists() for path in cds.files_seen)


def test_era5land_keeps_downloads_in_a_folder_it_is_given(cds, tmp_path):
    keep = tmp_path / "keep"
    run("era5land", "--start", "2025-06-01", "--end", "2025-06-03", "--box", BOX, "--downloads", str(keep))
    assert [p.name for p in keep.iterdir()] == ["2025-06-01_2025-06-02.grib"]


def test_era5land_redo_fetches_every_day_of_the_range(cds, monkeypatch):
    from ops.management.commands import era5land as command

    monkeypatch.setattr(command, "missing_days", lambda *args: pytest.fail("--redo doesn't ask what's missing"))
    out, _ = run("era5land", "--start", "2025-06-01", "--end", "2025-06-04", "--box", BOX, "--redo")
    assert cds.requests == [(date(2025, 6, 1), date(2025, 6, 3))]
    assert "3 days to fetch in 1 requests" in out


def test_era5land_with_nothing_missing_downloads_nothing(cds):
    cds.days = []
    out, _ = run("era5land", "--start", "2025-06-01", "--end", "2025-06-04", "--box", BOX)
    assert cds.requests == [] and "nothing to fetch" in out


def test_era5land_quiet_prints_only_the_summary(cds):
    out, _err = run("era5land", "--start", "2025-06-01", "--end", "2025-06-03", "--box", BOX, "--quiet")
    assert "downloaded in" not in out and "Requests:" not in out  # nothing but the summary
    assert len(out.splitlines()) == 1 and "Done in" in out


def test_era5land_refuses_bad_arguments_before_asking_the_cds(cds):
    with pytest.raises(CommandError, match="--concurrent must be at least 1"):
        call_command("era5land", "--start", "2025-06-01", "--end", "2025-06-03", "--concurrent", "0")
    with pytest.raises(CommandError, match="must be after"):
        call_command("era5land", "--start", "2025-06-03", "--end", "2025-06-03")
    assert cds.requests == []


def test_era5land_default_downloads_folder_is_under_the_data_dir(cds, data_dir):
    run("era5land", "--start", "2025-06-01", "--end", "2025-06-03", "--box", BOX)
    assert all(Path(p).parent == data_dir / "tmp" / "era5land" for p in cds.files_seen)


def test_backfill_skips_the_rollup_of_a_complete_block_whose_days_are_already_in(backfill_fakes, monkeypatch):
    from ops.management.commands import backfill

    backfill_fakes.stale = lambda start, stop: []
    monkeypatch.setattr(backfill, "_rolled_up", lambda *args: True)
    run("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", BOX)
    assert backfill_fakes.rolled == []


def test_rolled_up_means_every_day_has_a_daily_minimum_temperature_across_a_year_end(data_dir):
    import numpy as np

    from agdata.daily import open_or_create_daily
    from agdata.grid import service_window
    from ops.management.commands.backfill import _rolled_up

    window = service_window(BOX)
    assert not _rolled_up(data_dir, window, date(2025, 12, 30), date(2026, 1, 1))  # nothing written
    for year, first, days in ((2025, date(2025, 12, 30), 2), (2026, date(2026, 1, 1), 1)):
        store = open_or_create_daily(data_dir, year, window)
        store.write(first, {"air_temperature_min": np.zeros((days, *window.shape))}, source="urma")
    assert _rolled_up(data_dir, window, date(2025, 12, 30), date(2026, 1, 1))
    assert not _rolled_up(data_dir, window, date(2025, 12, 30), date(2026, 1, 2))  # the 2nd isn't in


def test_era5land_says_so_while_requests_sit_in_the_queue(cds, monkeypatch):
    from ops.management.commands import era5land as command

    monkeypatch.setattr(command, "HEARTBEAT_S", 0.05)
    original = cds.fail
    release = threading.Event()
    from agdata.sources import era5land as source

    real = source.retrieve

    def slow(first, last, window, path, key):
        release.wait(0.4)
        return real(first, last, window, path, key)

    monkeypatch.setattr(source, "retrieve", slow)
    out, _ = run("era5land", "--start", "2025-06-01", "--end", "2025-06-03", "--box", BOX)
    assert "1 requests still queued or downloading at the CDS" in out
    assert original == set() and "1 of 1 requests written" in out
