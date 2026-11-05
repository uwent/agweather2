"""Models' ingredients on the grid (PLAN.md Phase 5 F, D47, D66): the store a model map is finished from.

`agmodels.ingredients` splits a model into ingredients (daily, biofix- and option-free), accumulations from the
biofix and a day-by-day finish. This keeps the ingredients over the window, one store per year beside the daily
and cumulative ones (`data/ingredients/{year}.zarr`):

- each stored ingredient's daily values, under `{model_id}.{name}`, or its `shared` name for one kept once (the
  insects' freeze factor, the moving means three models use);
- for one that's accumulated, its running total from local January 1 (`….total`), and for one averaged, the
  running count of days with a value (`….known`), so a total, sum or mean over any days is `cum[d] − cum[b − 1]`.

Degree days and rye's rain aren't kept here: the cumulative store's running totals stand in (`degree_days`,
`cumulative` on the ingredient). The forecast run keeps its own in its directory, continuing the archive's.

An accumulated ingredient's daily values are kept at its total's step (P-days to 0.2; severity values and hour
counts are whole numbers, so exactly), so the total is exactly the sum of the stored days and an update continues
it from the stored day before: any day's update gives what building the year gives, and rounding never compounds.

Inputs are each daily variable's, gaps filled as the runner fills them (D45). An update from day `first` reads
LOOKBACK_DAYS of weather before it, recomputes from the earliest day a change can reach (cotton reads days ahead),
and continues the running totals, counts and minimums from the stored day before. It works in bands of the stores'
chunk rows (a daily chunk is read once and written whole) and blocks of days (BLOCK_CELL_DAYS), each continuing
the last.
"""

from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np

from agdata.catalog import DAILY_VARIABLES, GAP_FILL, Variable
from agdata.grid import Window
from agdata.store import DAILY, DEFAULT_CHUNKS, INGREDIENTS, GridStore
from agmodels.gaps import MAX_GAP_DAYS, fill_short_gaps, fill_zero
from agmodels.ingredients import LOOKBACK_DAYS, Ingredient
from agmodels.registry import all_models
from agmodels.spec import Model

# Cells × days computed at once: over Wisconsin (58,000 cells) blocks of 45 days, 2.8 GB at peak with the lookback;
# a band of more cells (the launch box's 256 rows) takes fewer days, down to MIN_BLOCK_DAYS
BLOCK_CELL_DAYS = 2_600_000
MIN_BLOCK_DAYS = 8

# Storage per unit: (scale, valid_min, valid_max) of daily values, and an accumulated one's step (its total's: a
# year of up to 24 h a day, or of an index up to ~16 a day, in int16)
_DAILY: dict[str, tuple[float, float, float]] = {
    "degC": (0.01, -80, 80),
    "delta_degC": (0.01, 0, 80),
    "percent": (0.01, 0, 100),
    "hour": (0.01, 0, 24),
    "day": (0.01, 0, 60),
    "m_s": (0.01, 0, 100),
    "mm": (0.02, 0, 650),
    "index": (0.001, 0, 32),
}
_TOTAL_STEP: dict[str, float] = {"hour": 0.5, "index": 0.2}


@dataclass(frozen=True, kw_only=True)
class Stored:
    """An ingredient kept in the store: its key, the declaration, the model that computes it (the first to declare
    a shared one), whether it's accumulated (its running total kept) and averaged (its known days counted)."""

    key: str
    ingredient: Ingredient
    model_id: str
    version: int
    total: bool
    known: bool

    def variables(self) -> list[Variable]:
        """The daily values, then the running total and count where kept."""
        unit = self.ingredient.unit
        if unit not in _DAILY:
            raise ValueError(f"{self.key}: no storage settled for unit {unit}")
        scale, low, high = _DAILY[unit]
        common: dict[str, Any] = {"derived": True, "version": self.version}
        if self.total:
            if unit not in _TOTAL_STEP:
                raise ValueError(f"{self.key}: no running total settled for unit {unit}")
            scale = _TOTAL_STEP[unit]
            high = min(high, 32000 * scale)
        out = [
            Variable(
                name=self.key,
                long_name=f"{self.key} (model ingredient)",
                unit=unit,
                scale=scale,
                valid_min=low,
                valid_max=high,
                **common,
            )
        ]
        if self.total:
            out.append(
                Variable(
                    name=f"{self.key}.total",
                    long_name=f"{self.key} since Jan 1",
                    unit=unit,
                    scale=scale,
                    valid_min=0,
                    valid_max=32000 * scale,
                    **common,
                )
            )
        if self.known:
            out.append(
                Variable(
                    name=f"{self.key}.known",
                    long_name=f"Days with {self.key} since Jan 1",
                    unit="day",
                    scale=1,
                    valid_min=0,
                    valid_max=366,
                    **common,
                )
            )
        return out


def key(model_id: str, ingredient: Ingredient) -> str:
    """Where an ingredient is kept: its shared name, or `{model_id}.{name}`."""
    return ingredient.shared or f"{model_id}.{ingredient.name}"


@cache
def stored() -> dict[str, Stored]:
    """Every ingredient the store keeps, by key (not those the cumulative store's totals stand in for)."""
    out: dict[str, Stored] = {}
    for model_id, m in all_models().items():
        accumulated = {a.of for a in m.SPEC.accumulations}
        averaged = {a.of for a in m.SPEC.accumulations if a.how == "mean"}
        for i in m.SPEC.ingredients:
            if i.degree_days is not None or i.cumulative is not None:
                continue
            k = key(model_id, i)
            if k in out and out[k].ingredient.unit != i.unit:
                raise ValueError(f"shared ingredient {k} has two units")
            out[k] = Stored(
                key=k,
                ingredient=i,
                model_id=out[k].model_id if k in out else model_id,
                version=i.version if i.shared else _version(m.SPEC.version),
                total=i.name in accumulated or (k in out and out[k].total),
                known=i.name in averaged or (k in out and out[k].known),
            )
    return out


# Crop models without ingredients (day-by-day state machines), stored instead as their outputs per planting tier
# (`agdata.croptiers`, D66): each output's storage (scale, valid_min, valid_max)
TIER_MODELS = ("soybean-stages", "spring-wheat-stages")
TIERS = ("early", "mid", "late")
_TIER_OUTPUTS: dict[str, tuple[float, float, float]] = {
    "stage": (1, -1, 100),
    "nodes": (0.01, 0, 60),
    "gdd_total": (0.5, 0, 16000),
    "gdd": (0.1, 0, 100),
}


def tier_key(model_id: str, output: str, tier: str) -> str:
    """Where a crop model's output for a planting tier is kept: `{model_id}.{output}.{tier}`."""
    return f"{model_id}.{output}.{tier}"


@cache
def tier_variables() -> list[Variable]:
    models = all_models()
    out = []
    for model_id in TIER_MODELS:
        spec = models[model_id].SPEC
        for q in spec.outputs:
            scale, low, high = _TIER_OUTPUTS[q.name]
            for tier in TIERS:
                out.append(
                    Variable(
                        name=tier_key(model_id, q.name, tier),
                        long_name=f"{spec.name}: {q.label} ({tier} planting)",
                        unit=q.unit,
                        scale=scale,
                        valid_min=low,
                        valid_max=high,
                        derived=True,
                        version=_version(spec.version),
                    )
                )
    return out


@cache
def variables() -> list[Variable]:
    return [v for s in stored().values() for v in s.variables()] + tier_variables()


def open_or_create(root: Path, year: int, window: Window) -> GridStore:
    try:
        store = GridStore.open(root, INGREDIENTS, year, variables(), add_missing=True)
    except FileNotFoundError:
        return GridStore.create(root, INGREDIENTS, year, window, variables())
    if store.window != window:
        raise ValueError(f"{store.path} covers {store.window}, not {window}; widening the box needs a rebuild")
    return store


def update(
    data_dir: Path,
    window: Window,
    first: date,
    last: date,
    run: Path | None = None,
    run_first: date | None = None,
    keys: Iterable[str] | None = None,
    lock: Callable[[], AbstractContextManager] | None = None,
    progress: Callable[[int, int], None] | None = None,
    not_before: date | None = None,
) -> tuple[date, date]:
    """Recomputes the ingredients a change to days first..last reaches and writes them; returns the days written.

    The archive's by default. With `run` (a forecast run's directory) the run's: weather from `run_first` on is the
    run's, the days before the archive's, and running totals continue from the archive's day before. Computing
    happens outside `lock` (a write-lock factory; default none: the caller holds it), writing inside it, so a
    year's build doesn't keep other writers waiting; `progress(done, total)` after each block. Nothing is written
    before `not_before` (a year's build leaves the year before alone)."""
    entries = [s for s in stored().values() if keys is None or s.key in set(keys)]
    ahead = max((s.ingredient.ahead_days for s in entries), default=0)
    write_from = first - timedelta(days=ahead)
    if run is not None and run_first is not None:
        write_from = max(write_from, run_first - timedelta(days=ahead))
    if not_before is not None:
        write_from = max(write_from, not_before)
    if run is None:
        write_from = _resume_from(data_dir, write_from, entries)
    root = run if run is not None else data_dir
    store_window = _store_window(root, data_dir, write_from.year, window)
    rows = _chunk_rows(store_window)
    block_days = max(MIN_BLOCK_DAYS, BLOCK_CELL_DAYS // (rows * window.shape[1]))
    blocks = []
    day = write_from
    while day <= last:
        blocks.append((day, min(last, day + timedelta(days=block_days - 1))))
        day = blocks[-1][1] + timedelta(days=1)
    work = [(b, j) for b in blocks for j in range(window.j0, window.j1, rows)]
    computing = _computing(entries)
    names = sorted({q.name for m, _ in computing for q in m.SPEC.inputs})
    for done, ((begin, end), j) in enumerate(work):
        band = Window(j0=j, j1=min(j + rows, window.j1), i0=window.i0, i1=window.i1)
        values = _compute(data_dir, run, run_first, band, begin, end, ahead, computing, names)
        with (lock or nullcontext)():
            _write(data_dir, root, band, begin, values, entries, run is not None)
        if progress is not None:
            progress(done + 1, len(work))
    return write_from, last


def build_year(data_dir: Path, window: Window, year: int, **kwargs) -> tuple[date, date] | None:
    """A year's ingredients from its daily store, January 1 through the last day rolled up; `kwargs` go to
    `update` (`lock`, `progress`). The year before isn't touched."""
    rolled = _rolled_days(data_dir, year)
    if rolled is None:
        return None
    first = date(year, 1, 1)
    return update(data_dir, window, first, first + timedelta(days=int(rolled[-1])), not_before=first, **kwargs)


def build(
    data_dir: Path,
    window: Window,
    year: int,
    lock: Callable[[], AbstractContextManager] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[date, date] | None:
    """A year's ingredients from January 1 and its crops' stages per planting tier (`agdata.croptiers`), marked
    current (D29), and the next year's January, whose windows reach back into this one."""
    from agdata import croptiers  # it uses this module

    tiers = {v.name for v in tier_variables()}
    reason = status(data_dir, year)
    if reason is not None and reason.endswith("stale variables"):
        stale = GridStore.stale_variables(data_dir, INGREDIENTS, year, variables())
        rolled = _rolled_days(data_dir, year)
        if stale <= tiers and rolled is not None:  # only the crops' tiers: the rest is current
            last = date(year, 1, 1) + timedelta(days=int(rolled[-1]))
            croptiers.update(data_dir, window, year, last, lock=lock)
            return date(year, 1, 1), last
    days = build_year(data_dir, window, year, lock=lock, progress=progress)
    if days is None:
        return None
    croptiers.update(data_dir, window, year, days[1], lock=lock)
    with (lock or nullcontext)():
        store = GridStore.open(data_dir, INGREDIENTS, year, variables(), add_missing=True)
        store.mark_current([v.name for v in variables()])
    if INGREDIENTS.path(data_dir, year + 1).exists():
        january = date(year + 1, 1, 1)
        update(data_dir, window, january, january + timedelta(days=LOOKBACK_DAYS), lock=lock)
    return days


def status(data_dir: Path, year: int) -> str | None:
    """Why a year's ingredients need building (not built, stale variables, days missing), or None."""
    rolled = _rolled_days(data_dir, year)
    if rolled is None:
        return None
    if not INGREDIENTS.path(data_dir, year).exists():
        return "not built"
    stale = GridStore.stale_variables(data_dir, INGREDIENTS, year, variables())
    if stale:
        return f"{len(stale)} stale variables"
    store = GridStore.open(data_dir, INGREDIENTS, year, variables())
    written = store.read_meta(f"{next(iter(stored()))}.source") > 0
    missing = rolled[~written[rolled]]
    if missing.size:
        return f"{missing.size} days missing (from {date(year, 1, 1) + timedelta(days=int(missing[0]))})"
    return None


def _rolled_days(data_dir: Path, year: int) -> np.ndarray | None:
    """The day indexes of a year rolled up in its daily store, or None (no store, nothing rolled up)."""
    try:
        daily = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
    except FileNotFoundError:
        return None
    rolled = np.flatnonzero(daily.read_meta("air_temperature_min.source") > 0)
    return rolled if rolled.size else None


def _resume_from(data_dir: Path, day: date, entries: list[Stored]) -> date:
    """`day`, or earlier in its year if the store lacks the day before for something continued from it (a running
    total, count or minimum): from the first day that's missing, or the year's first day of weather."""
    continued = [s.key for s in entries if s.total or s.ingredient.running_minimum]
    rolled = _rolled_days(data_dir, day.year)
    if not continued or rolled is None:
        return day
    start = date(day.year, 1, 1) + timedelta(days=int(rolled[0]))
    if day <= start:
        return day
    try:
        store = GridStore.open(data_dir, INGREDIENTS, day.year, variables(), add_missing=True)
    except FileNotFoundError:
        return start
    t0, t1 = store.index_of(start), store.index_of(day)
    have = np.all([store.has_data(k, t0, t1) for k in continued], axis=0)
    missing = np.flatnonzero(~have)
    return day if missing.size == 0 else start + timedelta(days=int(missing[0]))


def _version(text: str) -> int:
    """A model's version (0.2, 1.0) as the store's integer (2, 1000)."""
    major, minor = (int(p) for p in text.split("."))
    return major * 1000 + minor


def _chunk_rows(window: Window) -> int:
    """Rows per band: a daily chunk's (the whole window when it's smaller), so each chunk is read once per band."""
    return min(DEFAULT_CHUNKS["day"][1], window.shape[0])


def _computing(entries: list[Stored]) -> list[tuple[Model, list[Stored]]]:
    """The models to run and what each gives: a shared ingredient from its first model only."""
    by_model: dict[str, list[Stored]] = {}
    for s in entries:
        by_model.setdefault(s.model_id, []).append(s)
    models = all_models()
    return [(models[model_id], wanted) for model_id, wanted in by_model.items()]


def _compute(data_dir, run, run_first, band: Window, begin: date, end: date, ahead: int, computing, names) -> dict:
    """Each stored ingredient on days begin..end over a band, from weather LOOKBACK_DAYS before and `ahead` days
    after (what there is)."""
    read_from = begin - timedelta(days=LOOKBACK_DAYS)
    n = (end - read_from).days + 1 + ahead
    keep = slice(LOOKBACK_DAYS, LOOKBACK_DAYS + (end - begin).days + 1)
    dates = [read_from + timedelta(days=k) for k in range(n)]
    context = {
        "day_of_year": np.array([d.timetuple().tm_yday for d in dates], dtype=float),
        "year": np.array([d.year for d in dates], dtype=float),
    }
    inputs = {name: _filled(name, _read(data_dir, run, run_first, name, read_from, n, band)) for name in names}
    values: dict[str, np.ndarray] = {}
    for m, wanted in computing:
        out = m.ingredients({q.name: inputs[q.name] for q in m.SPEC.inputs} | context)  # type: ignore[attr-defined]
        for s in wanted:
            values[s.key] = np.asarray(out[s.ingredient.name], dtype=np.float32)[keep]
    return values


def _read(data_dir: Path, run: Path | None, run_first: date | None, name: str, first: date, n: int, window: Window):
    """Days first..first + n − 1 of a daily variable: the archive's, and the run's from `run_first` on."""
    out = np.full((n, *window.shape), np.nan, dtype=np.float32)
    days = [first + timedelta(days=k) for k in range(n)]

    def root_of(d: date) -> Path:
        return run if run is not None and run_first is not None and d >= run_first else data_dir

    groups: dict[tuple[Path, int], list[int]] = {}
    for k, d in enumerate(days):
        groups.setdefault((root_of(d), d.year), []).append(k)
    for (root, year), ks in groups.items():
        try:
            store = GridStore.open(root, DAILY, year, DAILY_VARIABLES.values(), add_missing=True)
        except FileNotFoundError:
            continue
        t0 = store.index_of(days[ks[0]])
        out[ks[0] : ks[-1] + 1] = store.read_steps(name, t0, t0 + len(ks), window)
    return out


def _filled(name: str, values: np.ndarray) -> np.ndarray:
    """The runner's gap estimate (D45), on the cells that have a gap."""
    method = GAP_FILL.get(name)
    if method is None:
        return values
    flat = values.reshape(values.shape[0], -1)
    gappy = np.flatnonzero(np.isnan(flat).any(axis=0))
    if gappy.size:
        fill: Callable = (lambda v: fill_short_gaps(v, MAX_GAP_DAYS)) if method == "interpolate" else fill_zero
        flat[:, gappy] = fill(flat[:, gappy])[0]
    return flat.reshape(values.shape)


def _write(data_dir, root, band, begin, values, entries, is_run) -> None:
    """Writes days from `begin` year by year: daily values as stored (an accumulated one at its total's step);
    minimums held, and totals and counts continued, from the stored day before (zero on January 1). A run continues
    the archive's."""
    n = next(iter(values.values())).shape[0] if values else 0
    dates = [begin + timedelta(days=k) for k in range(n)]
    for year in sorted({d.year for d in dates}):
        k0 = next(k for k, d in enumerate(dates) if d.year == year)
        k1 = max(k for k, d in enumerate(dates) if d.year == year) + 1
        first = dates[k0]
        day_before = first - timedelta(days=1)
        continuing = day_before.year == year
        store = open_or_create(root, year, _store_window(root, data_dir, year, band))
        out: dict[str, np.ndarray] = {}
        for s in entries:
            daily = s.variables()[0]
            v = values[s.key][k0:k1].astype(np.float64)
            if s.ingredient.running_minimum and continuing:
                held = _previous(data_dir, root, s.key, day_before, band, is_run)
                v = np.where(np.isnan(v), v, np.fmin(v, held))
            v = daily.decode(daily.encode(np.where(np.isnan(v), v, np.clip(v, daily.valid_min, daily.valid_max))))
            out[s.key] = v
            known = np.isfinite(v)
            if s.total:
                base = _previous(data_dir, root, f"{s.key}.total", day_before, band, is_run) if continuing else 0
                out[f"{s.key}.total"] = np.nan_to_num(base) + np.cumsum(np.where(known, v, 0.0), axis=0)
            if s.known:
                base = _previous(data_dir, root, f"{s.key}.known", day_before, band, is_run) if continuing else 0
                out[f"{s.key}.known"] = np.nan_to_num(base) + np.cumsum(known, axis=0)
        store.write(first, out, source="derived", window=band)


def _store_window(root: Path, data_dir: Path, year: int, band: Window) -> Window:
    """The window a store covers: the daily store's for that year (a band is only part of it)."""
    for path in (root, data_dir):
        for y in (year, year - 1, year + 1):
            try:
                return GridStore.open(path, DAILY, y, DAILY_VARIABLES.values(), add_missing=True).window
            except FileNotFoundError:
                continue
    return band


def _previous(data_dir: Path, root: Path, name: str, day: date, band: Window, is_run: bool) -> np.ndarray:
    """A stored value on `day` (a run's own, else the archive's); NaN where none."""
    for path in (root, data_dir) if is_run else (root,):
        try:
            store = GridStore.open(path, INGREDIENTS, day.year, variables(), add_missing=True)
        except FileNotFoundError:
            continue
        t = store.index_of(day)
        if store.has_data(name, t, t + 1)[0]:
            return store.read_steps(name, t, t + 1, band)[0]
    return np.full(band.shape, np.nan)
