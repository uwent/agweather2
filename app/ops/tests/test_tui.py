"""The dashboard (`ops.tui`) driven headless: it shows the years, a running command's bars and activities and its
log, and its keys launch commands in the background."""

import asyncio
import json
from datetime import UTC, datetime
from io import StringIO

from rich.console import Console

from agdata.grid import service_window
from agdata.ingest import open_or_create_hourly
from ops import runs, tui

BOX = "43.05,-89.45,43.1,-89.4"


def test_the_dashboard_shows_years_runs_and_logs_and_launches_commands(settings, tmp_path, monkeypatch):
    settings.DATA_DIR = tmp_path
    open_or_create_hourly(tmp_path, 2023, service_window(BOX)).set_sources(
        "air_temperature", datetime(2023, 1, 1, tzinfo=UTC), ["urma"] * 24
    )
    run = runs.start(tmp_path, "archive", ["fill", "--from", "2016"])
    events = [
        {"t": 1, "kind": "step", "message": "2023: 8,736 hours to fetch"},
        {"t": 2, "kind": "progress", "label": "hours 2016–2024", "done": 24, "total": 96, "elapsed": 60},
        {"t": 3, "kind": "activity", "id": 1, "label": "2023-06-01 05Z", "stage": "GET noaa-urma-pds/f",
         "state": "start"},
        {"t": 4, "kind": "detail", "message": "2023-06-01 04Z  ==> OK in 3.1 s"},
    ]  # fmt: skip
    (tmp_path / "runs" / f"{run.pid}.events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    monkeypatch.setattr(tui, "_worker_pids", lambda: [])
    launched = []
    monkeypatch.setattr(runs, "launch", lambda data, argv: launched.append(argv) or (4242, tmp_path / "x.log"))

    async def drive():
        app = tui.Dashboard(tmp_path)
        async with app.run_test(size=(140, 48)) as pilot:
            await pilot.pause(1.0)
            years = app.query_one("#years", tui.DataTable)
            assert years.row_count == 1
            console = Console(file=StringIO(), width=140)
            console.print(app.runs_drawn)
            drawn = console.file.getvalue()  # type: ignore[attr-defined]
            log = "\n".join(str(line.text) for line in app.query_one("#log", tui.RichLog).lines)
            await pilot.press("f")
            await pilot.pause(0.2)
            for key in ("2", "0", "2", "3", "subtract", "2", "0", "2", "4"):  # the number pad's minus
                await pilot.press(key)
            await pilot.press("enter")
            await pilot.pause(0.2)
            return drawn, log

    drawn, log = asyncio.run(drive())
    assert "archive fill --from 2016" in drawn and "hours 2016–2024" in drawn and "24/96" in drawn
    assert "2023-06-01 05Z" in drawn and "GET noaa-urma-pds/f" in drawn
    assert "2023-06-01 04Z  ==> OK in 3.1 s" in log
    assert launched == [["archive", "fill", "--from", "2023", "--to", "2024"]]


def test_a_click_or_the_arrows_pick_a_run_in_the_runs_table_and_s_stops_it(settings, tmp_path, monkeypatch):
    import os

    settings.DATA_DIR = tmp_path
    first = runs.start(tmp_path, "backfill", ["--start", "2023-01-01"])
    second = runs.Run(**{**first.__dict__, "pid": os.getppid(), "command": "era5land", "started": "2000-01-01T00:00"})
    (tmp_path / "runs" / f"{second.pid}.json").write_text(json.dumps(second.__dict__))  # an older run, also alive
    monkeypatch.setattr(tui, "_worker_pids", lambda: [])
    stopped = []
    monkeypatch.setattr(runs, "stop", lambda run: stopped.append(run.pid) or True)

    async def drive():
        app = tui.Dashboard(tmp_path)
        async with app.run_test(size=(160, 48)) as pilot:
            await pilot.pause(0.5)
            focused = []
            for _ in range(3):
                focused.append(app.focused.id if app.focused else None)
                await pilot.press("tab")
            assert app.selected == first.pid  # the newest is picked to begin with
            table = app.query_one("#runs", tui.DataTable)
            assert [key.value for key in table.rows] == [str(first.pid), str(second.pid)]
            await pilot.click("#runs", offset=(10, 3))  # the border, the header, then the second row
            await pilot.pause(0.2)
            clicked = app.selected
            await pilot.press("up")  # the table has focus now: the arrows move the pick
            await pilot.pause(0.2)
            arrowed = app.selected
            await pilot.press("down")
            await pilot.pause(0.2)
            await pilot.press("s")
            await pilot.pause(0.2)
            await pilot.click("#yes")
            await pilot.pause(0.2)
            return focused, (clicked, arrowed, app.selected)

    focused, (clicked, arrowed, picked) = asyncio.run(drive())
    assert set(focused) == {"years", "runs", "log"}  # Tab goes through all three
    assert (clicked, arrowed, picked) == (second.pid, first.pid, second.pid)
    assert stopped == [second.pid]


def test_a_processs_usage_comes_from_proc():
    import os

    cpu_s, rss, read = tui._proc_usage(os.getpid()) or (0, 0, 0)
    assert cpu_s > 0 and rss > 10_000_000 and read > 0
    assert tui._proc_usage(999_999_999) is None
