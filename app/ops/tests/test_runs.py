"""Run records (`ops.runs`): what the dashboard and `archive` read about the data commands running and done."""

import json
import os
import time

from ops import runs


def test_a_run_is_recorded_while_it_runs_and_finished_after(tmp_path):
    run = runs.start(tmp_path, "backfill", ["--start", "2023-01-01", "--end", "2024-01-01"])
    assert run.pid == os.getpid() and run.label == "backfill --start 2023-01-01 --end 2024-01-01"
    (found,) = runs.runs(tmp_path)
    assert found.running and found.state == "running"
    assert [r.pid for r in runs.running(tmp_path)] == [os.getpid()]
    runs.finish(tmp_path, run, ok=False, summary="Done in 3 min; 1 failed")
    (found,) = runs.runs(tmp_path)
    assert not found.running and found.state == "failed" and found.summary.startswith("Done")


def test_a_run_whose_process_is_gone_is_stopped(tmp_path):
    run = runs.start(tmp_path, "era5land", [])
    data = json.loads((tmp_path / "runs" / f"{run.pid}.json").read_text())
    data["pid"] = 999_999_999
    (tmp_path / "runs" / "999999999.json").write_text(json.dumps(data))
    states = {r.pid: r.state for r in runs.runs(tmp_path)}
    assert states[999_999_999] == "stopped"


def test_events_are_read_from_an_offset_and_a_partial_line_waits(tmp_path):
    run = runs.start(tmp_path, "backfill", [])
    path = tmp_path / "runs" / f"{run.pid}.events.jsonl"
    path.write_text('{"t": 1, "kind": "step", "message": "a"}\n{"t": 2, "kind": "ste')
    events, offset = runs.events(run)
    assert [e["message"] for e in events] == ["a"]
    with open(path, "a") as handle:
        handle.write('p", "message": "b"}\n')
    events, _ = runs.events(run, offset)
    assert [e["message"] for e in events] == ["b"]


def test_latest_folds_events_into_bars_activities_and_the_last_step(tmp_path):
    run = runs.start(tmp_path, "archive", ["fill"])
    lines = [
        {"t": 1, "kind": "step", "message": "2023: 8760 hours to fetch"},
        {"t": 2, "kind": "progress", "label": "hours 2016–2024", "done": 10, "total": 100, "elapsed": 50.0},
        {"t": 3, "kind": "activity", "id": 1, "label": "2023-06-01 05Z", "stage": "", "state": "start"},
        {"t": 4, "kind": "activity", "id": 1, "label": "2023-06-01 05Z", "stage": "GET f", "state": "stage"},
        {"t": 5, "kind": "activity", "id": 2, "label": "CDS 2024-12", "stage": "", "state": "start"},
        {"t": 6, "kind": "activity", "id": 2, "label": "CDS 2024-12", "stage": "", "state": "end"},
        {"t": 7, "kind": "progress", "label": "ERA5-Land 2024", "done": 12, "total": 12, "elapsed": 9.0},
        {"t": 8, "kind": "warn", "message": "slow"},
        {"t": 9, "kind": "detail", "message": "block written"},
    ]
    (tmp_path / "runs" / f"{run.pid}.events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in lines))
    state = runs.latest(run)
    assert state.step == "2023: 8760 hours to fetch"
    assert state.bars == {"hours 2016–2024": (10, 100, 50.0)}  # a finished bar is gone
    assert state.activities == {1: ("2023-06-01 05Z", "GET f", 3)}
    assert state.problems == ["warning: slow"] and state.details == ["block written"]


def test_launch_starts_a_detached_command_with_its_output_in_a_log(tmp_path):
    pid, log = runs.launch(tmp_path, ["help", "archive"])
    deadline = time.monotonic() + 60
    while runs._alive(pid) and time.monotonic() < deadline:
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            break
        time.sleep(0.1)
    assert log.parent == tmp_path / "runs" and log.name.endswith("-help.log")
    assert "manage.py archive" in log.read_text()


def test_clear_forgets_finished_runs_and_their_files_but_not_running_ones(tmp_path):
    running = runs.start(tmp_path, "archive", ["fill"])
    done = runs.Run(**{**running.__dict__, "pid": 999_999_998, "log": str(tmp_path / "runs" / "old.log")})
    (tmp_path / "runs" / "old.log").write_text("a log")
    (tmp_path / "runs" / "999999998.events.jsonl").write_text("")
    done.events = str(tmp_path / "runs" / "999999998.events.jsonl")
    runs.finish(tmp_path, done, ok=False, summary=runs.INTERRUPTED)
    assert {r.pid: r.state for r in runs.runs(tmp_path)}[999_999_998] == "stopped"  # interrupted isn't failed
    assert runs.clear(tmp_path) == 1
    assert [r.pid for r in runs.runs(tmp_path)] == [running.pid]
    assert not (tmp_path / "runs" / "old.log").exists() and not (tmp_path / "runs" / "999999998.events.jsonl").exists()
