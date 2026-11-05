"""The data dashboard: `uv run app/manage.py` with no command (on a terminal), or `manage.py dashboard`.

One screen of what v1's console logging and `DataImport.check_statuses` told you, kept live:

- each year of the archive (`ops.archive.year_states`): hours, precip, shortwave, ERA5-Land, rolled up, past years;
- the write lock's holder and who's waiting; the worker and its jobs; the archive's and forecast's health;
- every data command running (`ops.runs`), started here or from any shell: its bars with the time left, a spinner
  per hour or request in flight, and its last step;
- the selected run's log: each file read, each block written (v1's `HOUR 05 ==> GET …`).

Keys start commands as detached runs (they carry on when the dashboard closes; reopening it picks them up) and stop
them. Everything here reads files and the database; nothing writes the archive.
"""

import contextlib
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from django.conf import settings
from rich.console import Group
from rich.progress_bar import ProgressBar
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Static

from ops import archive, locks, runs

EVENTS_S = 0.25  # how often running commands' events are read
YEARS_S = 15.0  # how often the years table is read again
STATUS_S = 30.0  # the lock, the worker and its jobs
USAGE_S = 2.0  # how often the runs' CPU, memory and read rate are sampled (and the table redrawn)
RUN_COLUMNS = [
    ("mark", ""),
    ("command", "command"),
    ("pid", "pid"),
    ("since", "since"),
    ("elapsed", "elapsed"),
    ("progress", "progress"),
    ("left", "left"),
    ("cpu", "CPU"),
    ("memory", "memory"),
    ("read", "read"),
    ("doing", "doing"),
]
RUN_MARKS = {"running": ("●", "green"), "done": ("✓", "green"), "failed": ("✗", "red"), "stopped": ("■", "yellow")}
CLOCK_TICKS = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE_BYTES = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


# The number pad's symbol keys under the kitty keyboard protocol (Windows Terminal, kitty, WezTerm …) arrive as named
# keys without a character, so an Input ignores them; the digits arrive as characters already
KEYPAD = {"subtract": "-", "add": "+", "decimal": ".", "divide": "/", "multiply": "*", "separator": ","}


class Prompt(ModalScreen[list[str] | None]):
    """Asks for a command's arguments; dismisses with the manage.py argv to launch, or None."""

    DEFAULT_CSS = """
    Prompt { align: center middle; }
    #box { width: 76; height: auto; border: round $accent; padding: 1 2; background: $surface; }
    #box Label { margin-bottom: 1; }
    #buttons { height: auto; margin-top: 1; }
    #buttons Button { margin-right: 2; }
    """

    def __init__(self, title: str, hint: str, placeholder: str, build):
        super().__init__()
        self.title_text, self.hint, self.placeholder, self.build = title, hint, placeholder, build

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(Text(self.title_text, style="bold"))
            yield Label(self.hint)
            yield Input(placeholder=self.placeholder, id="value")
            yield Label("", id="error")
            with Horizontal(id="buttons"):
                yield Button("Start in the background", variant="primary", id="go")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self) -> None:
        self._go()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "go":
            self._go()
        else:
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if (char := KEYPAD.get(event.key)) is not None and event.character is None:
            self.query_one(Input).insert_text_at_cursor(char)
            event.stop()
            event.prevent_default()

    def _go(self) -> None:
        try:
            argv = self.build(self.query_one(Input).value.strip())
        except ValueError as error:
            self.query_one("#error", Label).update(Text(str(error), style="red"))
            return
        self.dismiss(argv)


class Confirm(ModalScreen[bool]):
    DEFAULT_CSS = """
    Confirm { align: center middle; }
    #box { width: 70; height: auto; border: round $warning; padding: 1 2; background: $surface; }
    #buttons { height: auto; margin-top: 1; }
    #buttons Button { margin-right: 2; }
    """

    def __init__(self, question: str):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self.question)
            with Horizontal(id="buttons"):
                yield Button("Yes", variant="warning", id="yes")
                yield Button("No", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def key_escape(self) -> None:
        self.dismiss(False)


class Dashboard(App):
    TITLE = "AgWeather data"
    CSS = """
    #years { height: auto; max-height: 16; border: round $primary; }
    #years:focus, #runs:focus, #log:focus { border: heavy $accent; }
    #status { height: auto; padding: 0 1; }
    #runs { height: auto; max-height: 12; border: round $secondary; }
    #detail { height: auto; padding: 0 1; }
    #log { border: round $panel; }
    """
    BINDINGS: ClassVar = [
        Binding("f", "fill", "Fill years"),
        Binding("b", "backfill", "Backfill range"),
        Binding("e", "era5land", "ERA5-Land range"),
        Binding("r", "rebuild", "Rebuild stale"),
        Binding("p", "pastyears", "Past years"),
        Binding("i", "ingredients", "Ingredients"),
        Binding("s", "stop", "Stop run"),
        Binding("c", "clear", "Clear finished"),
        Binding("tab", "focus_next", "Next section", show=True),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, data_dir: Path):
        super().__init__()
        self.data_dir = data_dir
        self.run_list: list[runs.Run] = []
        self.offsets: dict[int, int] = {}  # pid -> bytes of its events read
        self.states: dict[int, runs.Latest] = {}
        self.selected: int | None = None  # pid whose log is shown
        self.lock_text = Text("")
        self.health_text = Text("")
        self.runs_drawn = Group()
        self.samples: dict[int, tuple[float, float, int]] = {}  # pid -> (when, CPU seconds, bytes read)
        self.usage: dict[int, tuple[str, str, str]] = {}  # pid -> (CPU, memory, read rate) as shown

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        table = DataTable(id="years", cursor_type="row", zebra_stripes=True)
        yield table
        yield Static(id="status")
        yield DataTable(id="runs", cursor_type="row", zebra_stripes=True)
        yield Static(id="detail")
        yield RichLog(id="log", max_lines=2000, wrap=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{self.data_dir} · {settings.SERVICE_BOX}"
        table = self.query_one("#years", DataTable)
        table.add_columns(
            "", "year", "hours", "URMA", "RTMA", "precip", "shortwave", "ERA5-Land", "rolled up", "past years"
        )
        runs_table = self.query_one("#runs", DataTable)
        for key, label in RUN_COLUMNS:
            runs_table.add_column(label, key=key)
        runs_table.border_title = "runs (click or ↑/↓ to pick one; s stops it, c clears finished)"
        self.load_years()
        self.load_status()
        self.poll_runs()
        self.set_interval(YEARS_S, self.load_years)
        self.set_interval(STATUS_S, self.load_status)
        self.set_interval(EVENTS_S, self.poll_runs)
        self.set_interval(1 / 8, self.draw_detail)  # the spinners
        self.set_interval(USAGE_S, self.sample_usage)

    # Years

    @work(thread=True, exclusive=True, group="years")
    def load_years(self) -> None:
        states = archive.year_states(self.data_dir)
        self.call_from_thread(self.show_years, states)

    def show_years(self, states: list[archive.YearState]) -> None:
        table = self.query_one("#years", DataTable)
        table.clear()
        for y in states:
            table.add_row(
                Text("✓", style="green") if y.complete else Text("·", style="yellow"),
                str(y.year),
                _frac(y.analysis, y.hours),
                f"{y.urma:,}",
                f"{y.rtma:,}",
                _pct(y.precip, y.hours),
                _pct(y.shortwave, y.hours),
                _frac(y.era5land_days, y.days),
                _frac(y.rolled_up, y.days),
                Text(
                    y.past_years + (f"  stale: {', '.join(y.stale)}" if y.stale else ""),
                    style="green" if y.past_years in ("current", "–") and not y.stale else "yellow",
                ),
            )

    # Lock, worker, health

    @work(thread=True, exclusive=True, group="status")
    def load_status(self) -> None:
        from django.db import close_old_connections

        from ops.status import snapshot

        lines = Text()
        try:
            status = snapshot(self.data_dir, datetime.now(UTC))
        except Exception as error:  # the database may be down; the files still say a lot
            lines.append(f"status unavailable: {error}\n", style="red")
            status = None
        finally:
            close_old_connections()
        workers = _worker_pids()
        lines.append("worker ", style="bold")
        lines.append(
            f"running (pid {', '.join(workers)})" if workers else "not running (bin/dev)",
            style="green" if workers else "red",
        )
        if status is not None:
            i = status.ingest
            lines.append("   archive ", style="bold")
            lines.append(f"newest hour {_ago(i.get('newest_hour'))}, URMA {_ago(i.get('newest_urma_hour'))}")
            f = status.forecast
            if f.get("cycle"):
                lines.append("   forecast ", style="bold")
                lines.append(f"run {_ago(f['cycle'])}")
            jobs = ", ".join(f"{j.name} {_ago(j.last_finished)}" for j in status.jobs if j.schedule and j.last_finished)
            lines.append("\njobs ", style="bold")
            lines.append(jobs or "none run yet")
            if status.problems:
                lines.append("\nproblems ", style="bold red")
                lines.append("; ".join(status.problems), style="red")
        self.health_text = lines
        self.call_from_thread(self.draw_status)

    def draw_status(self) -> None:
        holder = None
        with contextlib.suppress(Exception):
            from ops.status import lock_holder

            holder = lock_holder(self.data_dir)
        text = Text()
        text.append("lock ", style="bold")
        text.append(f"held by {holder}" if holder else "free", style="yellow" if holder else "green")
        for waiter in locks.waiting(self.data_dir):
            text.append(f"   waiting: {waiter}", style="dim")
        text.append("\n")
        text.append_text(self.health_text)
        self.query_one("#status", Static).update(text)

    # Runs

    def poll_runs(self) -> None:
        found = runs.runs(self.data_dir)
        active = [r for r in found if r.running]
        recent = [r for r in found if not r.running][:3]
        changed = [r.pid for r in active + recent] != [r.pid for r in self.run_list]
        self.run_list = active + recent
        if self.selected is None or self.selected not in {r.pid for r in self.run_list}:
            self.select(self.run_list[0].pid if self.run_list else None)
        if changed:
            self.show_runs()
        for run in active + [r for r in recent if r.pid == self.selected]:
            state = self.states.setdefault(run.pid, runs.Latest(bars={}, activities={}, details=[], problems=[]))
            if run.pid not in self.offsets:  # first sight: start from the tail, not the whole history
                size = Path(run.events).stat().st_size if Path(run.events).exists() else 0
                self.offsets[run.pid] = max(0, size - 256_000)
                if self.offsets[run.pid]:
                    events, offset = runs.events(run, self.offsets[run.pid])
                    events = events[1:]  # the first line may be cut
                else:
                    events, offset = runs.events(run, 0)
            else:
                events, offset = runs.events(run, self.offsets[run.pid])
            self.offsets[run.pid] = offset
            log = self.query_one("#log", RichLog)
            for event in events:
                runs.apply(state, event)
                if run.pid == self.selected and (line := _log_line(event)) is not None:
                    log.write(line)
        self.draw_status()

    def show_runs(self) -> None:
        """The runs table: rebuilt when runs come or go (the cursor stays on the picked run), else updated."""
        table = self.query_one("#runs", DataTable)
        pids = [str(r.pid) for r in self.run_list]
        rows = {run.pid: self.run_row(run) for run in self.run_list}
        if [key.value for key in table.rows] != pids:
            table.clear()
            for run in self.run_list:
                table.add_row(*rows[run.pid], key=str(run.pid))
            if self.selected is not None and str(self.selected) in pids:
                table.move_cursor(row=pids.index(str(self.selected)), animate=False)
            return
        for run in self.run_list:
            for (key, _), value in zip(RUN_COLUMNS, rows[run.pid], strict=True):
                table.update_cell(str(run.pid), key, value, update_width=True)

    def run_row(self, run: runs.Run) -> list:
        mark, style = RUN_MARKS[run.state]
        state = self.states.get(run.pid)
        progress = left = doing = Text("")
        if run.running and state is not None:
            if state.bars:
                label, (done, total, elapsed) = next(iter(state.bars.items()))
                progress = Text(f"{label}: {100 * done / max(total, 1):.0f}%")
                left = Text(f"~{_duration(elapsed / done * (total - done))}" if done else "", style="cyan")
            doing = Text((state.step or "").splitlines()[0] if state.step else "", style="dim")
        elif run.summary:
            doing = Text(run.summary.splitlines()[0], style="dim")
        cpu, memory, read = self.usage.get(run.pid, ("", "", "")) if run.running else ("", "", "")
        started = _local(run.started)
        end = _local(run.finished) if run.finished else datetime.now().astimezone()
        return [
            Text(mark, style=style),
            Text(run.label, style="bold", overflow="ellipsis", no_wrap=True),
            str(run.pid),
            f"{started:%m-%d %H:%M}",
            _duration((end - started).total_seconds()),
            progress,
            left,
            cpu,
            memory,
            read,
            doing,
        ]

    def sample_usage(self) -> None:
        """CPU, memory and bytes read per second of each running run, from /proc (bytes read include the network's,
        so for a backfill it's the download rate)."""
        now = time.monotonic()
        for run in self.run_list:
            if not run.running:
                continue
            found = _proc_usage(run.pid)
            if found is None:
                continue
            cpu_s, rss, read = found
            before = self.samples.get(run.pid)
            self.samples[run.pid] = (now, cpu_s, read)
            if before is None or now <= before[0]:
                continue
            span = now - before[0]
            self.usage[run.pid] = (
                f"{100 * (cpu_s - before[1]) / span:.0f}%",
                f"{rss / 1e9:.1f} GB" if rss >= 1e9 else f"{rss / 1e6:.0f} MB",
                f"{(read - before[2]) / span / 1e6:.1f} MB/s",
            )
        self.show_runs()

    def draw_detail(self) -> None:
        """The picked run: its bars with the time left, a spinner per activity in flight, its last step."""
        now = time.time()
        parts: list = []
        run = next((r for r in self.run_list if r.pid == self.selected), None)
        if run is None:
            parts.append(Text("Nothing running. f fills years; b, e, r and p start the other commands.", style="dim"))
        else:
            state = self.states.get(run.pid)
            head = Text()
            head.append(f"{run.label}", style="bold")
            head.append(f"   pid {run.pid}, {run.state}", style="dim")
            parts.append(head)
            if not run.running:
                if run.summary:
                    parts.append(Text(run.summary, style="dim"))
            elif state is not None:
                bars = Table.grid(padding=(0, 1))
                for label, (done, total, elapsed) in (state.bars or {}).items():
                    left = f"~{_duration(elapsed / done * (total - done))} left" if done else ""
                    bars.add_row(
                        Text(label, style="bold"),
                        ProgressBar(total=max(total, 1), completed=done, width=36),
                        Text(f"{done:,}/{total:,}"),
                        Text(f"{100 * done / max(total, 1):.0f}%"),
                        Text(left, style="cyan"),
                    )
                parts.append(bars)
                acts = sorted((state.activities or {}).items())
                grid = Table.grid(padding=(0, 1))
                for _, (label, stage, began) in acts[:10]:
                    grid.add_row(
                        Spinner("dots", style="cyan"),
                        Text(label, style="bold"),
                        Text(stage, no_wrap=True, overflow="ellipsis"),
                        Text(_duration(now - began), style="dim"),
                    )
                if len(acts) > 10:
                    grid.add_row("", Text(f"and {len(acts) - 10} more", style="dim"), "", "")
                parts.append(grid)
                if state.step:
                    parts.append(Text(state.step.splitlines()[0], style="dim", no_wrap=True, overflow="ellipsis"))
                for problem in (state.problems or [])[-3:]:
                    parts.append(Text(problem, style="red" if problem.startswith("failed") else "yellow"))
        self.runs_drawn = Group(*parts)
        self.query_one("#detail", Static).update(self.runs_drawn)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """A click or ↑/↓ in the runs table picks that run: its log shows below and s stops it."""
        if event.data_table.id != "runs" or event.row_key.value is None:
            return
        pid = int(event.row_key.value)
        if pid != self.selected:
            self.select(pid)

    def select(self, pid: int | None) -> None:
        self.selected = pid
        log = self.query_one("#log", RichLog)
        log.clear()
        run = next((r for r in self.run_list if r.pid == pid), None)
        if run is None:
            log.border_title = "log"
            return
        log.border_title = f"log: {run.label} (pid {run.pid})"
        if run.log and Path(run.log).exists():
            for line in runs.tail(Path(run.log), 300):
                log.write(Text(line))
            size = Path(run.events).stat().st_size if Path(run.events).exists() else 0
            self.offsets[run.pid] = size  # the log has what came before; follow the events from here
            return
        self.offsets.pop(run.pid, None)  # read its events' tail into the log on the next poll

    # Actions

    def launch(self, argv: list[str] | None) -> None:
        if not argv:
            return
        pid, _log = runs.launch(self.data_dir, argv)
        self.notify(f"Started {' '.join(argv)} (pid {pid})")
        self.selected = None  # select the new run once it has recorded itself
        self.set_timer(1.0, self.poll_runs)

    def action_fill(self) -> None:
        year = datetime.now(UTC).year

        def build(value: str) -> list[str]:
            first, _, last = value.partition("-")
            try:
                a, b = int(first), int(last or year - 1)
            except ValueError:
                raise ValueError("years as 2016-2024, or one year") from None
            if not 2016 <= a <= b <= year:
                raise ValueError(f"years from 2016 to {year}, the first first")
            return ["archive", "fill", "--from", str(a), "--to", str(b)]

        self.push_screen(
            Prompt(
                "Fill years",
                "Hours, December 31, ERA5-Land and past-years copies, newest year first. Resumes what's there.",
                f"2016-{year - 1}",
                build,
            ),
            self.launch,
        )

    def action_backfill(self) -> None:
        def build(value: str) -> list[str]:
            parts = value.split()
            if len(parts) != 2:
                raise ValueError("a start and an end date, YYYY-MM-DD YYYY-MM-DD (the end is the day after the last)")
            return ["backfill", "--start", parts[0], "--end", parts[1]]

        self.push_screen(
            Prompt("Backfill hours", "URMA/RTMA/HRRR hours for a date range (UTC).", "2023-06-01 2023-07-01", build),
            self.launch,
        )

    def action_era5land(self) -> None:
        def build(value: str) -> list[str]:
            parts = value.split()
            if len(parts) != 2:
                raise ValueError("a start and an end date, YYYY-MM-DD YYYY-MM-DD (the end is the day after the last)")
            return ["era5land", "--start", parts[0], "--end", parts[1]]

        self.push_screen(
            Prompt(
                "ERA5-Land soil and snow",
                "A month per CDS request; requests queue at the CDS.",
                "2023-01-01 2024-01-01",
                build,
            ),
            self.launch,
        )

    def action_rebuild(self) -> None:
        self.push_screen(
            Confirm("Recompute every stale derived variable (rebuild --stale)?"),
            lambda yes: self.launch(["rebuild", "--stale"] if yes else None),
        )

    def action_pastyears(self) -> None:
        self.push_screen(
            Confirm("Build the past-years copies that are missing or out of date (pastyears)?"),
            lambda yes: self.launch(["pastyears"] if yes else None),
        )

    def action_ingredients(self) -> None:
        self.push_screen(
            Confirm("Build the models' ingredients that are missing, stale or behind (ingredients)?"),
            lambda yes: self.launch(["ingredients"] if yes else None),
        )

    def action_clear(self) -> None:
        finished = [r for r in runs.runs(self.data_dir) if not r.running]
        if not finished:
            self.notify("No finished runs to clear")
            return

        def clear(yes: bool | None) -> None:
            if yes:
                removed = runs.clear(self.data_dir)
                for pid in [p for p in self.states if not any(r.pid == p for r in runs.running(self.data_dir))]:
                    self.states.pop(pid, None)
                self.notify(f"Cleared {removed} finished run{'s' * (removed != 1)}")
                self.poll_runs()

        self.push_screen(
            Confirm(f"Forget {len(finished)} finished or stopped run(s), with their logs? Running ones stay."), clear
        )

    def action_stop(self) -> None:
        run = next((r for r in self.run_list if r.pid == self.selected and r.running), None)
        if run is None:
            self.notify(
                "Pick a running run in the runs table first (click it, or Tab there and ↑/↓)", severity="warning"
            )
            return

        def stop(yes: bool | None) -> None:
            if yes and runs.stop(run):
                self.notify(f"Asked pid {run.pid} to stop after its current block (press s again to interrupt)")

        self.push_screen(Confirm(f"Stop {run.label} (pid {run.pid}) after its current block?"), stop)


def _log_line(event: dict) -> Text | None:
    kind = event.get("kind")
    if kind not in ("step", "detail", "warn", "fail", "finish"):
        return None
    when = datetime.fromtimestamp(event.get("t", 0)).astimezone()
    text = Text(f"{when:%H:%M:%S} ", style="dim")
    style = {"step": "bold", "detail": "", "warn": "yellow", "fail": "red", "finish": "bold green"}[kind]
    prefix = {"warn": "warning: ", "fail": "failed: "}.get(kind, "")
    text.append(prefix + event.get("message", ""), style=style)
    return text


def _proc_usage(pid: int) -> tuple[float, int, int] | None:
    """A process's CPU seconds (all its threads), resident memory and bytes read so far (files and sockets), from
    /proc; None if it's gone or not ours to read."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        cpu_s = (int(fields[11]) + int(fields[12])) / CLOCK_TICKS  # utime, stime (fields 14 and 15)
        rss = int(Path(f"/proc/{pid}/statm").read_text().split()[1]) * PAGE_BYTES
        io = dict(line.split(": ") for line in Path(f"/proc/{pid}/io").read_text().splitlines())
        return cpu_s, rss, int(io["rchar"])
    except (OSError, IndexError, KeyError, ValueError):
        return None


def _worker_pids() -> list[str]:
    """The Procrastinate worker's processes (`jobs start` becomes it), from /proc."""
    found = []
    for entry in Path("/proc").iterdir() if Path("/proc").exists() else []:
        if not entry.name.isdigit():
            continue
        with contextlib.suppress(OSError):
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            if "manage.py" in cmd and ("procrastinate worker" in cmd or "jobs start" in cmd) and "uv run" not in cmd:
                found.append(entry.name)
    return found


def _frac(done: int, total: int) -> Text:
    return Text(f"{done:,}/{total:,}", style="green" if total and done >= total else "yellow" if done else "dim")


def _pct(done: int, total: int) -> Text:
    if not total:
        return Text("–", style="dim")
    return Text(f"{100 * done / total:.0f}%", style="green" if done >= total else "yellow")


def _ago(value) -> str:
    if value is None:
        return "never"
    when = datetime.fromisoformat(value) if isinstance(value, str) else value
    return f"{_duration((datetime.now(UTC) - when).total_seconds())} ago"


def _local(iso: str) -> datetime:
    """A run's time; one without a zone is local (records always have one, but a hand-made one mustn't crash)."""
    when = datetime.fromisoformat(iso)
    return when if when.tzinfo else when.astimezone()


def _duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 90 * 60:
        return f"{seconds / 60:.0f} min"
    if seconds < 48 * 3600:
        return f"{seconds / 3600:.1f} h"
    return f"{seconds / 86400:.1f} days"


def main() -> None:
    Dashboard(Path(settings.DATA_DIR)).run()
