"""The forecast's verification archive (Phase 4 B, Phase 6 step 5, D113): each published run's lead days kept as
published, and scored against the archive's days as they arrive.

A run's daily store is restitched while it's current (`forecast.stitch` copies observed hours over its forecast), so
its days are the forecast only at publish: `keep` copies them then, into a directory of its own,

    {data_dir}/forecast/verify/{YYYYMMDDHH}/daily/{year}.zarr   the kept days (one store per year they touch)
    {data_dir}/forecast/verify/{YYYYMMDDHH}/verify.json         cycle, its grid day, day → lead, versions, written last

and `prune` deletes them after KEEP_DAYS. Lead k is the grid day k days after the one the cycle falls in (01Z
belongs to the day before, in CST); leads 1 to 10 are kept, and only days that start after the run's last
observed hour, so a kept day is wholly the forecast's (lead 0, today, mixes observed and forecast hours, and isn't
kept). A window that reaches into the evening before (the 6 pm features the disease severity values read) can
take an observed hour or two of that evening into lead 1, as the published forecast did.

Kept per day: WEATHER (11 daily variables) and INGREDIENTS (5 disease models' daily values), packed as stored (an
exact copy, no decoding). Degree days aren't kept: `score_day` computes them from the kept minimum and maximum, the
same way on both sides. Soil and snow are IFS's, not NBM's, and aren't scored.

`score_day` compares every kept run holding a day with the archive's day over the covered cells: cells where both
are known, the error forecast − observed in the catalog's units, and for precipitation the wet-day counts. The
caller (`ops.verification`) decides which days are due and keeps the scores.
"""

import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from agdata import coverage, modelmaps
from agdata.catalog import DAILY_VARIABLES, Variable
from agdata.forecast import forecast_dir, run_info
from agdata.grid import Window
from agdata.store import DAILY, INGREDIENTS, GridStore, StoreLayout
from agdata.timezones import GRID_ZONE, day_bounds
from agmodels.degree_days import degree_days_sine

WEATHER = (
    "air_temperature_min",
    "air_temperature_max",
    "dew_point_mean",
    "relative_humidity_mean",
    "precipitation_sum",
    "et0_sum",
    "shortwave_radiation_sum",
    "wind_speed_mean",
    "hours_rh_over_90",
    "hours_rh_over_90_night",
    "hours_wet",
)
INGREDIENTS_KEPT = (
    "late-blight-dsv.dsv",
    "carrot-foliar-dsv.dsv",
    "cercospora-beet-div.div",
    "early-blight-pdays.pdays",
    "botrytis-onion-botcast.dsi",
)
DEGREE_DAYS = "dd_sine_50_86"  # °F·d, single sine 50/86 °F from the day's minimum and maximum
SCORED = (*WEATHER, *INGREDIENTS_KEPT, DEGREE_DAYS)
UNITS = {**{name: DAILY_VARIABLES[name].unit for name in WEATHER}, DEGREE_DAYS: "degF_day"}
LEADS = range(1, 11)
KEEP_DAYS = 45
CHUNKS = (16, 256, 256)  # a run's 10 days in one or two chunks a block: ~450 files a run, not ~2,200 at a chunk a day
WET_DAY_MM = 0.254  # a wet day: 0.01 in or more, the least a gauge reports
INCOMPLETE_AFTER = timedelta(hours=1)  # a kept directory without verify.json this old is a keep that crashed
INFO = "verify.json"


def root(data_dir: Path) -> Path:
    return forecast_dir(data_dir) / "verify"


def kept_path(data_dir: Path, cycle: datetime) -> Path:
    return root(data_dir) / f"{cycle.astimezone(UTC):%Y%m%d%H}"


def cycle_day(cycle: datetime) -> date:
    """The grid day the cycle falls in: the day of the reading stamped at the cycle (CST, readings 01:00 … 24:00)."""
    return (cycle - timedelta(hours=1)).astimezone(ZoneInfo(GRID_ZONE)).date()


def lead_days(cycle: datetime, last_observed: datetime | None) -> dict[date, int]:
    """The run's days kept, with their leads: leads 1 to 10 whose first reading is after the last observed hour."""
    base = cycle_day(cycle)
    days = {base + timedelta(days=k): k for k in LEADS}
    if last_observed is None:
        return days
    return {day: k for day, k in days.items() if day_bounds(day, GRID_ZONE)[0] > last_observed}


def kept_variables() -> list[Variable]:
    """The kept store's variables: the weather's, then the ingredients' daily values, as their stores pack them."""
    return [DAILY_VARIABLES[name] for name in WEATHER] + [_ingredient(key) for key in INGREDIENTS_KEPT]


def _ingredient(key: str) -> Variable:
    return modelmaps.stored()[key].variables()[0]


def kept_variable(name: str) -> Variable:
    return DAILY_VARIABLES[name] if name in DAILY_VARIABLES else _ingredient(name)


def _layout(name: str) -> StoreLayout:
    return DAILY if name in DAILY_VARIABLES else INGREDIENTS


@dataclass(frozen=True, kw_only=True)
class Kept:
    """A kept run: its directory, cycle, days with their leads, and the version each variable was kept at."""

    path: Path
    cycle: datetime
    leads: dict[date, int]
    versions: dict[str, int]
    last_observed: datetime | None
    failed_leads: list[int] = field(default_factory=list)


def keep(data_dir: Path, run: Path) -> dict[date, int]:
    """Copies a published run's lead days (`lead_days`) into the verification archive, replacing any earlier copy of
    its cycle; returns the days kept with their leads. Call it right after `forecast.publish`, before the run is
    restitched. A variable the run lacks, or holds from older code (D29), isn't kept; a year's store it lacks drops
    that year's days."""
    info = run_info(run)
    cycle = datetime.fromisoformat(info["cycle"])
    observed = info.get("last_observed")
    leads = lead_days(cycle, datetime.fromisoformat(observed) if observed else None)
    path = kept_path(data_dir, cycle)
    if path.exists():
        shutil.rmtree(path)
    kept: dict[date, int] = {}
    versions: dict[str, int] = {}
    for year in sorted({day.year for day in leads}):
        days = sorted(day for day in leads if day.year == year)
        sources = _run_stores(run, year)
        if DAILY not in sources:
            continue
        window = sources[DAILY].window
        store = GridStore.create(path, DAILY, year, window, kept_variables(), chunks=CHUNKS)
        part = coverage.extent(window)
        for name in (*WEATHER, *INGREDIENTS_KEPT):
            source = sources.get(_layout(name))
            if source is None or name not in source.variables or name in source.stale or source.window != window:
                continue
            t0 = source.index_of(days[0])
            store.write_packed(days[0], name, source.read_packed(name, t0, t0 + len(days), window=part), window=part)
            versions[name] = source.variables[name].version
        kept |= {day: leads[day] for day in days}
    if not kept:
        return {}
    body = {
        "cycle": cycle.isoformat(),
        "cycle_day": cycle_day(cycle).isoformat(),
        "leads": {day.isoformat(): lead for day, lead in sorted(kept.items())},
        "last_observed": observed,
        "failed_leads": info.get("failed_leads", []),
        "versions": versions,
        "kept_at": datetime.now(UTC).isoformat(),
    }
    part_file = path / f"{INFO}.part"
    part_file.write_text(json.dumps(body, indent=2))
    part_file.replace(path / INFO)  # last: a directory without it is incomplete
    return kept


def _run_stores(run: Path, year: int) -> dict[StoreLayout, GridStore]:
    """A run's daily and ingredients stores for `year` opened for the kept variables each has (read only: nothing
    is added to them)."""
    out = {}
    for layout, names in ((DAILY, WEATHER), (INGREDIENTS, INGREDIENTS_KEPT)):
        path = layout.path(run, year)
        present = [kept_variable(name) for name in names if (path / name / "zarr.json").exists()]
        if not present:
            continue
        try:
            out[layout] = GridStore.open(run, layout, year, present)
        except (FileNotFoundError, KeyError, ValueError):
            continue
    return out


def kept_runs(data_dir: Path) -> list[Kept]:
    """The complete kept runs (with verify.json), oldest cycle first."""
    folder = root(data_dir)
    if not folder.exists():
        return []
    out = []
    for path in sorted(folder.iterdir()):
        info_file = path / INFO
        if not info_file.exists():
            continue
        info = json.loads(info_file.read_text())
        observed = info.get("last_observed")
        out.append(
            Kept(
                path=path,
                cycle=datetime.fromisoformat(info["cycle"]),
                leads={date.fromisoformat(day): int(lead) for day, lead in info["leads"].items()},
                versions={name: int(v) for name, v in info.get("versions", {}).items()},
                last_observed=datetime.fromisoformat(observed) if observed else None,
                failed_leads=list(info.get("failed_leads", [])),
            )
        )
    return out


def prune(data_dir: Path, now: datetime, keep_days: int = KEEP_DAYS) -> int:
    """Deletes kept runs whose cycle is more than `keep_days` before `now`, and keeps that crashed (no verify.json,
    untouched for INCOMPLETE_AFTER); returns how many."""
    folder = root(data_dir)
    if not folder.exists():
        return 0
    cutoff = now - timedelta(days=keep_days)
    deleted = 0
    for path in sorted(folder.iterdir()):
        try:
            cycle = datetime.strptime(path.name, "%Y%m%d%H").replace(tzinfo=UTC)
        except ValueError:
            continue  # not ours
        incomplete = (
            not (path / INFO).exists() and time.time() - path.stat().st_mtime > INCOMPLETE_AFTER.total_seconds()
        )
        if cycle < cutoff or incomplete:
            shutil.rmtree(path)
            deleted += 1
    return deleted


@dataclass(frozen=True, kw_only=True)
class Score:
    """One run's forecast of one variable on one day against the archive's, over the cells where both are known:
    the error forecast − observed in the catalog's unit (bias its mean, MAE its mean size, RMSE its root mean
    square); for precipitation, wet days (WET_DAY_MM) forecast and observed (hits), observed only (misses) and
    forecast only (false alarms). No cells: n 0 and the statistics None."""

    cycle: datetime
    lead: int
    variable: str
    n: int
    bias: float | None
    mae: float | None
    rmse: float | None
    hits: int | None = None
    misses: int | None = None
    false_alarms: int | None = None


@dataclass(frozen=True, kw_only=True)
class DayScores:
    """A day's scores; when the archive last wrote any of the day's values (epoch seconds, None: never); and what
    wasn't scored and why."""

    day: date
    observed_written: float | None
    scores: list[Score]
    skipped: list[str]


def observed_written(data_dir: Path, day: date) -> float | None:
    """When the archive last wrote any of a day's scored values (epoch seconds), or None if it holds none: a day is
    scored again when this is newer than its scores' (URMA replacing RTMA, a rebuild, a backfill)."""
    stamps = []
    for layout, names in ((DAILY, WEATHER), (INGREDIENTS, INGREDIENTS_KEPT)):
        store = _archive_store(data_dir, layout, day.year, names)
        if store is None:
            continue
        t = store.index_of(day)
        stamps += [s for name in store.variables if (s := store.written(name, t, t + 1)) is not None]
    return max(stamps) if stamps else None


def _archive_store(data_dir: Path, layout: StoreLayout, year: int, names) -> GridStore | None:
    """The archive's store for `year` opened for those of `names` it holds (read only: nothing added)."""
    path = layout.path(data_dir, year)
    present = [kept_variable(name) for name in names if (path / name / "zarr.json").exists()]
    if not present:
        return None
    try:
        return GridStore.open(data_dir, layout, year, present)
    except (FileNotFoundError, KeyError, ValueError):
        return None


def score_day(data_dir: Path, day: date, runs: list[Kept] | None = None) -> DayScores:
    """Scores every kept run holding `day` (of `runs`, default all kept) against the archive's day.

    The archive's day is read once over the covered cells (`coverage.extent`, ~4 MB a variable over the launch box)
    and each run's day from its kept store, all in this process: a day's read is a chunk per block and variable, too
    little to be worth `agdata.blocks`' pool. A variable kept or archived from older code than the catalog's (D29) is
    skipped, as is degree days when either temperature is."""
    runs = kept_runs(data_dir) if runs is None else runs
    holding = [k for k in runs if day in k.leads]
    skipped: list[str] = []
    stamp = observed_written(data_dir, day)
    if not holding or stamp is None:
        return DayScores(day=day, observed_written=stamp, scores=[], skipped=skipped)
    observed: dict[str, np.ndarray] = {}
    window: Window | None = None
    for layout, names in ((DAILY, WEATHER), (INGREDIENTS, INGREDIENTS_KEPT)):
        store = _archive_store(data_dir, layout, day.year, names)
        if store is None:
            continue
        window = window or store.window
        if store.window != window:
            skipped.append(f"the archive's {layout.kind} store for {day.year} covers another window")
            continue
        t = store.index_of(day)
        for name in store.variables:
            if name in store.stale:
                skipped.append(f"{name}: the archive's is from older code (rebuild pending)")
                continue
            observed[name] = store.read_steps(name, t, t + 1, coverage.extent(window))[0]
    if window is None:
        return DayScores(day=day, observed_written=stamp, scores=[], skipped=skipped)
    part = coverage.extent(window)
    _add_degree_days(observed)
    scores: list[Score] = []
    for kept in holding:
        forecast = _kept_day(kept, day, window, part, skipped)
        _add_degree_days(forecast)
        for name in SCORED:
            if name in forecast and name in observed:
                scores.append(_score(kept.cycle, kept.leads[day], name, forecast[name], observed[name]))
    return DayScores(day=day, observed_written=stamp, scores=scores, skipped=skipped)


def _kept_day(kept: Kept, day: date, window: Window, part: Window, skipped: list[str]) -> dict[str, np.ndarray]:
    """A kept run's values on `day`, of the variables kept at the catalog's version."""
    out: dict[str, np.ndarray] = {}
    label = f"{kept.cycle:%Y-%m-%d %H}Z"
    for name in (*WEATHER, *INGREDIENTS_KEPT):
        v = kept_variable(name)
        if name not in kept.versions:
            continue
        if kept.versions[name] != v.version:
            skipped.append(f"{name}: the {label} run's is from older code")
            continue
        try:
            store = GridStore.open(kept.path, DAILY, day.year, [v])
        except (FileNotFoundError, KeyError, ValueError) as error:
            skipped.append(f"{name}: the {label} run's can't be read ({error})")
            continue
        if store.window != window:
            skipped.append(f"the {label} run covers another window than the archive")
            return {}
        t = store.index_of(day)
        out[name] = store.read_steps(name, t, t + 1, part)[0]
    return out


def _add_degree_days(values: dict[str, np.ndarray]) -> None:
    if "air_temperature_min" in values and "air_temperature_max" in values:
        lo = values["air_temperature_min"] * 1.8 + 32
        hi = values["air_temperature_max"] * 1.8 + 32
        with np.errstate(invalid="ignore"):
            values[DEGREE_DAYS] = degree_days_sine(lo, hi, 50.0, 86.0)


def _score(cycle: datetime, lead: int, name: str, forecast: np.ndarray, observed: np.ndarray) -> Score:
    both = np.isfinite(forecast) & np.isfinite(observed)
    f, o = forecast[both].astype(np.float64), observed[both].astype(np.float64)
    n = int(both.sum())
    counts: dict[str, int | None] = {}
    if name == "precipitation_sum":
        wet_f, wet_o = f >= WET_DAY_MM, o >= WET_DAY_MM
        counts = {
            "hits": int((wet_f & wet_o).sum()),
            "misses": int((~wet_f & wet_o).sum()),
            "false_alarms": int((wet_f & ~wet_o).sum()),
        }
    if n == 0:
        return Score(cycle=cycle, lead=lead, variable=name, n=0, bias=None, mae=None, rmse=None, **counts)
    error = f - o
    return Score(
        cycle=cycle,
        lead=lead,
        variable=name,
        n=n,
        bias=float(error.mean()),
        mae=float(np.abs(error).mean()),
        rmse=float(np.sqrt((error**2).mean())),
        **counts,
    )
