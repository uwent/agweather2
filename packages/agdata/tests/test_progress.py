import io
import json

import pytest

from agdata.progress import Reporter


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def reporter(quiet=False):
    out, err, clock = io.StringIO(), io.StringIO(), Clock()
    return Reporter(out=out, err=err, quiet=quiet, every_s=10, clock=clock, live=False), out, err, clock


def lines(stream):
    return [line[9:] if line[:2].isdigit() else line for line in stream.getvalue().splitlines()]  # no time stamps


def test_progress_is_throttled_and_says_how_long_is_left():
    report, out, _, clock = reporter()
    report.progress("months", 0, 4)
    clock.now = 5
    report.progress("months", 1, 4)  # within 10 s of the last line: skipped
    clock.now = 60
    report.progress("months", 2, 4)
    clock.now = 61
    report.progress("months", 4, 4)  # the last always shows
    assert lines(out) == ["months: 0/4 (0%), 0 s", "months: 2/4 (50%), 60 s, ~60 s left", "months: 4/4 (100%), 61 s"]


def test_quiet_keeps_steps_off_the_terminal_but_not_failures():
    report, out, err, clock = reporter(quiet=True)
    report.step("reading")
    report.warn("slow")
    report.fail("2025-01", RuntimeError("queue full"))
    clock.now = 200
    assert report.finish("1 of 2 written") is False
    assert out.getvalue() == ""
    assert lines(err) == [
        "warning: slow",
        "failed: 2025-01: RuntimeError('queue full')",
        "Done in 3 min: 1 of 2 written; 1 warning; 1 failed:",
        "  2025-01: RuntimeError('queue full')",
    ]


def test_a_clean_run_finishes_on_stdout_even_when_quiet():
    for quiet in (False, True):
        report, out, err, _ = reporter(quiet=quiet)
        report.step("working")
        assert report.finish() is True
        assert lines(out) == (["Done in 0 s"] if quiet else ["working", "Done in 0 s"]) and err.getvalue() == ""


def test_waiting_for_the_write_lock_names_its_holder():
    report, out, _, _ = reporter()
    report.waiting_for_lock("pid 4242 (backfill, since 11:59)")
    assert lines(out) == ["waiting for the write lock (held by pid 4242 (backfill, since 11:59))"]


def test_once_it_has_the_lock_the_step_before_the_wait_is_what_it_is_doing_again(tmp_path):
    path = tmp_path / "events.jsonl"
    clock = Clock()
    report = Reporter(out=io.StringIO(), err=io.StringIO(), live=False, clock=clock, events=path)
    report.got_lock()  # without a wait, nothing
    report.step("2025: building")
    report.waiting_for_lock("pid 4242 (backfill)")
    clock.now = 120
    report.waiting_for_lock("pid 4242 (backfill)")
    report.got_lock()
    report.close()
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert report.doing == "2025: building"
    assert [(e["kind"], e["message"]) for e in events[-2:]] == [
        ("detail", "got the write lock after 2 min"),
        ("resume", "2025: building"),
    ]


@pytest.mark.parametrize("seconds, said", [(45, "45 s"), (120, "2 min"), (89 * 60, "89 min"), (3 * 3600, "3.0 h")])
def test_durations_read_in_seconds_minutes_or_hours(seconds, said):
    report, _, _, clock = reporter()
    clock.now = seconds
    assert report.summary() == f"Done in {said}"


def test_details_are_text_lines_but_not_when_quiet():
    for quiet in (False, True):
        report, out, _, _ = reporter(quiet=quiet)
        report.detail("2023-06-01 05Z  ==> OK")
        assert lines(out) == ([] if quiet else ["2023-06-01 05Z  ==> OK"])


def test_file_reads_are_details_prefixed_with_the_activity_on_their_thread():
    import threading

    from agdata import progress

    report, out, _, _ = reporter()
    progress.file_read("https://x.s3.amazonaws.com/a/b.grb2", 7, 43_100_000, 13.7, 0.3)  # no active reporter
    with report.activate():

        def hour():
            with progress.activity("2023-06-01 05Z") as act:
                progress.file_opened("https://noaa-urma-pds.s3.amazonaws.com/urma2p5.20230601/f.grb2")
                assert act is not None and act.stage_text == "GET noaa-urma-pds/urma2p5.20230601/f.grb2"
                progress.file_read(
                    "https://noaa-urma-pds.s3.amazonaws.com/urma2p5.20230601/f.grb2", 7, 43_100_000, 13.7, 0.3
                )

        thread = threading.Thread(target=hour)
        thread.start()
        thread.join()
        progress.file_read("https://x.s3.amazonaws.com/p.grb2", 1, 500_000, 0.1, 0.0)  # this thread: no activity
    assert lines(out) == [
        "2023-06-01 05Z  GET noaa-urma-pds/urma2p5.20230601/f.grb2: 7 msgs, 43.1 MB in 13.7 s, decoded in 0.3 s",
        "GET x/p.grb2: 1 msg, 0.5 MB in 0.1 s, decoded in 0.0 s",
    ]
    assert progress.current() is None


def test_every_call_is_an_event_for_the_dashboard(tmp_path):
    import json

    path = tmp_path / "runs" / "1.events.jsonl"
    report = Reporter(out=io.StringIO(), err=io.StringIO(), live=False, events=path)
    report.step("planning")
    report.detail("a file")
    with report.activity("CDS 2024-12") as act:
        act.stage("queued")
    report.progress("hours", 1, 2)
    report.progress("hours", 2, 2)
    report.warn("slow")
    report.fail("2024-12", "CDS said no")
    report.finish()
    report.close()
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [e["kind"] for e in events] == [
        "step", "detail", "activity", "activity", "activity", "progress", "progress", "warn", "fail", "finish",
    ]  # fmt: skip
    assert [e.get("state") for e in events if e["kind"] == "activity"] == ["start", "stage", "end"]
    assert events[-1]["ok"] is False and "CDS said no" in events[-1]["message"]


def test_the_live_display_draws_bars_activities_and_details_and_keeps_steps():
    out = io.StringIO()
    report = Reporter(out=out, err=out, live=True)
    with report.activate():
        report.progress("hours", 3, 10)
        with report.activity("2023-06-01 05Z") as act:
            act.stage("GET noaa-urma-pds/f.grb2")
            report.detail("2023-06-01 04Z  ==> OK")
            from rich.console import Console

            console = Console(file=io.StringIO(), width=120)
            console.print(report._render())
            drawn = console.file.getvalue()  # type: ignore[attr-defined]
        report.step("a step stays")
    report.close()
    assert "hours" in drawn and "3/10" in drawn and "2023-06-01 05Z" in drawn and "GET noaa-urma-pds" in drawn
    assert "04Z  ==> OK" in drawn
    assert "a step stays" in out.getvalue()
