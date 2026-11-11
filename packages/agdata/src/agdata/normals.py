"""Normal maps: each period's day-of-year statistics stored as maps (D85; PLAN.md Phase 6 D4).

A store per period, `data_dir/climate/normals/<period>.zarr`, an array per statistic, `<name>/<stat>`:

- **Daily variables** (`DAILY_NAMES`): `mean`, the pooled 15-day mean of D1 (`climatology.pooled`); the maximum
  and minimum also `p10` and `p90`. No mean temperature in `last30`: gridMET's years have none, and a normal of
  a third of the years would be another period's.
- **Running totals from January 1** (`RUNNING_NAMES`: every degree-day cube the archive keeps, precipitation and
  ET0): `mean` across years (D61: each year's own total, then averaged). Means are linear, so a single-sine pair's
  normal is the difference of its thresholds' (`dd_sine_41` − `dd_sine_86`) and a total from another start is a
  subtraction, and only the cubes are stored. `DECILE_NAMES` (modified 50/86, sine 41/86, precipitation) also keep
  `p10` … `p90` (not in `last5`, whose five years can't give deciles), for a percentile map among the years.
- **Freezes** at 32, 28 and 24 °F (`freeze_32`, …): `chance`, per day, the share of years with a freeze still to
  come (January–June: after the date) or already come (July–December: by the date); and single maps (slot 0 of
  their array) `spring_p10`, `spring_p50`, `spring_p90`, `fall_p10`, … (calendar slots, `climatology.slot`; a
  share of years falling among years with none is missing) and `season_p50` (days).

Every array is (366, ny, nx) int16 packed by its own `scale` (attrs), `FILL` missing, chunked a day per chunk over
`TILE` cells, so a normal map costs what a day of the daily store does. A store is built from the years' copies
laid out for points (`agdata.pastyears` for the archive's, `agdata.climatestore` for gridMET's), a 16 × 16 block
of cells at a time (a chunk a year), into a block-chunked scratch store that's then rechunked into maps, and marks
itself complete last. It's stale when its years, a year's copy, the gridMET fit or `VERSION` change (`status`).
"""

import shutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from zarr.codecs.numcodecs import PCodec
from zarr.errors import GroupNotFoundError

from agdata import climatestore, climatology, pastyears
from agdata.catalog import (
    CUMULATIVE_VARIABLES,
    DAILY_VARIABLES,
    DD_AVERAGE_SETTINGS_F,
    DD_MODIFIED_PAIRS_F,
    DD_SINE_THRESHOLDS_F,
    FILL,
    dd_name,
)
from agdata.cumulative import MAX_BRIDGE_DAYS
from agdata.grid import Window
from agdata.qc import fill_short_gaps
from agmodels.degree_days import degree_days_average, degree_days_modified, degree_days_sine

VERSION = 2  # bump when what's stored changes, and every period is built again (2: `enough_years`)
KIND = "climate/normals"
BLOCK = pastyears.CELLS  # cells a side per block: one chunk a year from the copies
TILE = 256  # cells a side per stored chunk
DAILY_NAMES = (
    "air_temperature_max",
    "air_temperature_min",
    "air_temperature_mean",
    "precipitation_sum",
    "relative_humidity_max",
    "relative_humidity_min",
    "shortwave_radiation_sum",
    "wind_speed_mean",
    "et0_sum",
)
SPREAD_NAMES = ("air_temperature_max", "air_temperature_min")  # with p10 and p90
SPREAD = (10.0, 90.0)
SINE = tuple(dd_name("sine", t) for t in DD_SINE_THRESHOLDS_F)
MODIFIED = tuple(dd_name("modified", b, u) for b, u in DD_MODIFIED_PAIRS_F)
AVERAGE = tuple(dd_name("average", b, u) for b, u in DD_AVERAGE_SETTINGS_F)
RUNNING_NAMES = (*SINE, *MODIFIED, *AVERAGE, "precipitation", "et0")
DECILE_NAMES = ("dd_modified_50_86", "dd_sine_41_86", "precipitation")
DECILES = tuple(float(p) for p in range(10, 100, 10))
FREEZE_F = (32, 28, 24)
FREEZE_QUANTILES = (0.1, 0.5, 0.9)
Progress = Callable[[int, int], None]


def path(data_dir: Path, period: str) -> Path:
    return Path(data_dir) / KIND / f"{period}.zarr"


@dataclass(frozen=True, kw_only=True)
class Stat:
    name: str  # `<name>/<stat>`
    scale: float
    single: bool = False  # a single map in slot 0, not one per day


def stats(period: str) -> list[Stat]:
    """What a period's store holds."""
    out = []
    for name in DAILY_NAMES:
        if name == "air_temperature_mean" and period == "last30":
            continue
        scale = DAILY_VARIABLES[name].scale
        out.append(Stat(name=f"{name}/mean", scale=scale))
        if name in SPREAD_NAMES:
            out += [Stat(name=f"{name}/p{p:g}", scale=scale) for p in SPREAD]
    for name in RUNNING_NAMES:
        out.append(Stat(name=f"{name}/mean", scale=CUMULATIVE_VARIABLES[name].scale))
    if period != "last5":
        for name in DECILE_NAMES:
            scale = CUMULATIVE_VARIABLES.get(name, CUMULATIVE_VARIABLES["dd_sine_41"]).scale
            out += [Stat(name=f"{name}/p{p:g}", scale=scale) for p in DECILES]
    for f in FREEZE_F:
        out.append(Stat(name=f"freeze_{f}/chance", scale=0.1))  # percent
        for season in ("spring", "fall"):
            out += [Stat(name=f"freeze_{f}/{season}_p{q * 100:g}", scale=1.0, single=True) for q in FREEZE_QUANTILES]
        out.append(Stat(name=f"freeze_{f}/season_p50", scale=1.0, single=True))
    return out


# --- Reading the years -----------------------------------------------------------------------------------------


@dataclass
class _Source:
    group: Any
    names: list[str]
    window: Window


def _open_year(data_dir: Path, year: int, archive: set[int]) -> _Source:
    layout = pastyears.PAST if year in archive else climatestore.LAYOUT
    where = layout.path(data_dir, year)
    try:
        group = zarr.open_group(where, mode="r")
    except (FileNotFoundError, GroupNotFoundError) as error:
        raise ValueError(f"{year} has no copy laid out for points ({where})") from error
    attrs: dict[str, Any] = dict(group.attrs)
    if not attrs.get("complete"):
        raise ValueError(f"{year}'s copy ({where}) is incomplete")
    w = attrs["window"]
    return _Source(group=group["values"], names=list(attrs["names"]), window=Window(**w))


def _read_block(source: _Source, block: Window, names: list[str], year: int) -> dict[str, np.ndarray]:
    """(366, by, bx) per name on the calendar slots, NaN for a name the year doesn't have."""
    w = source.window
    packed = np.asarray(source.group[:, :, block.j0 - w.j0 : block.j1 - w.j0, block.i0 - w.i0 : block.i1 - w.i0])
    out = {}
    for name in names:
        if name in source.names:
            days = DAILY_VARIABLES[name].decode(packed[source.names.index(name)], dtype=np.float32)
            out[name] = climatology.layout(days, year).astype(np.float32)
        else:
            out[name] = np.full((climatology.SLOTS, *block.shape), np.nan, dtype=np.float32)
    return out


# --- Statistics for a block --------------------------------------------------------------------------------------


def _daily_degree_days(tmin_c: np.ndarray, tmax_c: np.ndarray, year: int) -> dict[str, np.ndarray]:
    """A year's daily degree days per cube (366 slots, …), gaps of up to MAX_BRIDGE_DAYS bridged as the cumulative
    store bridges them (within the year), NaN where a day can't be estimated."""
    real = ~np.isnan(climatology.layout(np.zeros(366 if climatology._leap(year) else 365), year))
    lo, hi = tmin_c[real], tmax_c[real]
    known = np.isfinite(lo) & np.isfinite(hi)
    lo, _ = fill_short_gaps(np.where(known, lo, np.nan), MAX_BRIDGE_DAYS)
    hi, _ = fill_short_gaps(np.where(known, hi, np.nan), MAX_BRIDGE_DAYS)
    lo_f, hi_f = lo * 1.8 + 32, hi * 1.8 + 32
    usable = np.isfinite(lo_f) & np.isfinite(hi_f)
    days: dict[str, np.ndarray] = {}
    for t, name in zip(DD_SINE_THRESHOLDS_F, SINE, strict=True):
        days[name] = degree_days_sine(lo_f, hi_f, t)
    for (b, u), name in zip(DD_MODIFIED_PAIRS_F, MODIFIED, strict=True):
        days[name] = degree_days_modified(lo_f, hi_f, b, u)
    for (b, u), name in zip(DD_AVERAGE_SETTINGS_F, AVERAGE, strict=True):
        days[name] = degree_days_average(lo_f, hi_f, b, u)
    return {name: climatology.layout(np.where(usable, v, np.nan), year) for name, v in days.items()}


def block_stats(years: list[int], by_year: list[dict[str, np.ndarray]], period: str) -> dict[str, np.ndarray]:
    """Every `stats(period)` array over one block, (366, by, bx) float32, from each year's daily values on the
    calendar slots (`_read_block`)."""
    out: dict[str, np.ndarray] = {}
    shape = by_year[0]["air_temperature_max"].shape

    def stack(name: str) -> np.ndarray:
        return np.stack([y[name] for y in by_year])

    wanted = {s.name for s in stats(period)}
    for name in DAILY_NAMES:
        if f"{name}/mean" not in wanted:
            continue
        spread = SPREAD if name in SPREAD_NAMES else ()
        p = climatology.pooled(stack(name), years, percentiles=spread)
        out[f"{name}/mean"] = p.mean
        for q in spread:
            out[f"{name}/p{q:g}"] = p.percentiles[q]
    dd_daily = [
        _daily_degree_days(y["air_temperature_min"], y["air_temperature_max"], year)
        for y, year in zip(by_year, years, strict=True)
    ]
    daily_totals = {name: np.stack([d[name] for d in dd_daily]) for name in (*SINE, *MODIFIED, *AVERAGE)}
    daily_totals["precipitation"] = stack("precipitation_sum")
    daily_totals["et0"] = stack("et0_sum")
    daily_totals["dd_sine_41_86"] = daily_totals["dd_sine_41"] - daily_totals["dd_sine_86"]
    for name, daily in daily_totals.items():
        deciles = DECILES if name in DECILE_NAMES and period != "last5" else ()
        if name not in RUNNING_NAMES and not deciles:
            continue
        r = climatology.running(daily, years, percentiles=deciles)
        if name in RUNNING_NAMES:
            out[f"{name}/mean"] = r.mean
        for q in deciles:
            out[f"{name}/p{q:g}"] = r.percentiles[q]
    tmin = stack("air_temperature_min")
    spring_slots = slice(*climatology.SPRING)
    for f in FREEZE_F:
        fz = climatology.freezes(tmin, (f - 32) / 1.8)
        chance = fz.by_fall.copy()
        chance[spring_slots] = fz.after_spring[spring_slots]
        out[f"freeze_{f}/chance"] = chance * 100
        for q in FREEZE_QUANTILES:
            spring, fall = fz.dates(q)
            out[f"freeze_{f}/spring_p{q * 100:g}"] = _single(spring, shape)
            out[f"freeze_{f}/fall_p{q * 100:g}"] = _single(fall, shape)
        out[f"freeze_{f}/season_p50"] = _single(fz.season_length(0.5), shape)
    return {k: v.astype(np.float32) for k, v in out.items()}


def _single(values: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    out = np.full(shape, np.nan, dtype=np.float32)
    out[0] = values
    return out


# --- Building ----------------------------------------------------------------------------------------------------


def _blocks(window: Window, size: int) -> Iterator[Window]:
    for j in range(window.j0, window.j1, size):
        for i in range(window.i0, window.i1, size):
            yield Window(j0=j, j1=min(j + size, window.j1), i0=i, i1=min(i + size, window.i1))


def _encode(values: np.ndarray, scale: float) -> np.ndarray:
    packed = np.round(values / scale)
    return np.where(np.isfinite(packed), np.clip(packed, FILL + 1, np.iinfo(np.int16).max), FILL).astype(np.int16)


def _stamps(data_dir: Path, years: list[int], archive: set[int]) -> dict[str, Any]:
    """What a build read, to tell when it's stale: each archive year's copy stamp and the gridMET fit."""
    copies = {}
    for y in years:
        if y in archive:
            attrs = dict(zarr.open_group(pastyears.PAST.path(data_dir, y), mode="r").attrs)
            copies[str(y)] = attrs.get("daily_written")
        else:
            attrs = dict(zarr.open_group(climatestore.path(data_dir, y), mode="r").attrs)
            copies[str(y)] = attrs.get("fit")
    return {"copies": copies, "version": VERSION}


def build(
    data_dir: Path,
    period: str,
    years: list[int],
    archive: set[int],
    window: Window,
    progress: Progress | None = None,
    days_per_chunk: int = 1,
    stopping: Callable[[], bool] = lambda: False,
) -> list[str] | None:
    """Builds a period's store from `years` (the archive's where in `archive`, else gridMET's). Returns the arrays
    written. Built beside its path and renamed into place once whole. `days_per_chunk` is for tests: a chunk a day
    is ~30,000 chunk writes whatever the window. Checks `stopping` between blocks and arrays: a stopped build
    removes what it wrote, leaves the period's current store in place and returns None (a rerun starts over)."""
    if not years:
        raise ValueError(f"{period} has no years")
    sources = {y: _open_year(data_dir, y, archive) for y in years}
    for y, s in sources.items():
        inside = s.window.j0 <= window.j0 and window.j1 <= s.window.j1
        if not (inside and s.window.i0 <= window.i0 and window.i1 <= s.window.i1):
            raise ValueError(f"{y}'s copy covers {s.window}, not {window}")
    want = stats(period)
    names = list(dict.fromkeys(["air_temperature_max", "air_temperature_min", *DAILY_NAMES]))
    target = path(data_dir, period)
    scratch = target.with_name(target.name + ".blocks")
    building = target.with_name(target.name + ".part")
    for p in (scratch, building):
        if p.exists():
            shutil.rmtree(p)
    # Pass 1: a block at a time into block-shaped chunks
    blocks_group = zarr.open_group(scratch, mode="w")
    for s in want:
        blocks_group.create_array(
            s.name,
            shape=(climatology.SLOTS, *window.shape),
            chunks=(climatology.SLOTS, BLOCK, BLOCK),
            dtype="int16",
            fill_value=int(FILL),
            serializer=PCodec(level=4),
        )
    blocks = list(_blocks(window, BLOCK))
    steps = len(blocks) + len(want)
    for k, block in enumerate(blocks):
        if stopping():
            shutil.rmtree(scratch)
            return None
        by_year = [_read_block(sources[y], block, names, y) for y in years]
        found = block_stats(years, by_year, period)
        rows = slice(block.j0 - window.j0, block.j1 - window.j0)
        cols = slice(block.i0 - window.i0, block.i1 - window.i0)
        for s in want:
            blocks_group[s.name][:, rows, cols] = _encode(found[s.name], s.scale)  # type: ignore[index]
        if progress is not None:
            progress(k + 1, steps)
    # Pass 2: rechunked into maps, a day per chunk
    group = zarr.open_group(building, mode="w")
    for k, s in enumerate(want):
        if stopping():
            shutil.rmtree(scratch)
            shutil.rmtree(building)
            return None
        days = 1 if s.single else climatology.SLOTS
        array = group.create_array(
            s.name,
            shape=(days, *window.shape),
            chunks=(min(days_per_chunk, days), min(TILE, window.shape[0]), min(TILE, window.shape[1])),
            dtype="int16",
            fill_value=int(FILL),
            serializer=PCodec(level=8),
        )
        source = blocks_group[s.name]
        for tile in _blocks(window, TILE):
            rows = slice(tile.j0 - window.j0, tile.j1 - window.j0)
            cols = slice(tile.i0 - window.i0, tile.i1 - window.i0)
            array[:, rows, cols] = np.asarray(source[:days, rows, cols])  # type: ignore[index]
        array.attrs.update({"scale": s.scale, "single": s.single})
        if progress is not None:
            progress(len(blocks) + k + 1, steps)
    group.attrs.update(
        {
            "period": period,
            "years": years,
            "archive_years": sorted(y for y in years if y in archive),
            "window": {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1},
            "built": datetime.now(UTC).isoformat(timespec="seconds"),
            **_stamps(data_dir, years, archive),
            "complete": True,
        }
    )
    climatestore._swap(building, target)
    shutil.rmtree(scratch)
    return [s.name for s in want]


def status(data_dir: Path, period: str, years: list[int], archive: set[int]) -> str | None:
    """Why a period's store needs building, or None if it's current."""
    try:
        group = zarr.open_group(path(data_dir, period), mode="r")
    except (FileNotFoundError, GroupNotFoundError):
        return "missing"
    attrs: dict[str, Any] = dict(group.attrs)
    if not attrs.get("complete"):
        return "incomplete"
    if attrs.get("version") != VERSION:
        return "out of date: the code changed"
    if attrs.get("years") != years or attrs.get("archive_years") != sorted(y for y in years if y in archive):
        return "out of date: the period's years changed"
    try:
        if attrs.get("copies") != _stamps(data_dir, years, archive)["copies"]:
            return "out of date: a year's data changed"
    except (FileNotFoundError, GroupNotFoundError):
        return "out of date: a year's copy is missing"
    return None


# --- Reading -----------------------------------------------------------------------------------------------------


def read_map(
    data_dir: Path, period: str, name: str, day: date | None = None, window: Window | None = None
) -> np.ndarray:
    """A stored statistic (`<name>/<stat>`) for a calendar day (`day`'s slot; a single map takes None) over
    `window` (default the store's), float64 in its unit, NaN where missing. A KeyError for one the store lacks."""
    group = zarr.open_group(path(data_dir, period), mode="r")
    attrs: dict[str, Any] = dict(group.attrs)
    array = group[name]
    assert isinstance(array, zarr.Array)
    w = Window(**attrs["window"])
    window = window or w
    index = 0 if array.attrs.get("single") else climatology.slot(day or date(climatology.LEAP, 1, 1))
    packed = np.asarray(array[index, window.j0 - w.j0 : window.j1 - w.j0, window.i0 - w.i0 : window.i1 - w.i0])
    scale = float(array.attrs["scale"])  # type: ignore[arg-type]
    return np.where(packed == FILL, np.nan, packed.astype(np.float64) * scale)
