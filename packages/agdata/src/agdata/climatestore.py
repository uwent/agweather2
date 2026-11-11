"""gridMET's years on the 2.5 km grid, on the archive's basis: the 30-year normal's years before the archive (D82,
D84; PLAN.md Phase 6 D3).

Derived from the files gridMET's adapter keeps (`agdata.sources.gridmet`): each variable regridded by the cubic
B-spline with the coast rule, then adjusted to the archive by the overlap's fit (`fit`, D84), clamped to what the
variable can hold, and packed as the daily store packs it. A store a year, `data_dir/climate/gridmet/<year>.zarr`,
laid out as the past-years copies are (`agdata.pastyears`: variables × days × 16 × 16 cells, so a cell's year of
everything is one chunk), and read by the same `pastyears.Reader`. A store marks itself complete last.

**The fit** (`fit`, `data_dir/climate/gridmet-fit.zarr`): per daily variable, by cell and calendar slot, from the
years both sources have (2016–2025 at first), pairing days by their label (gridMET's 12Z day by its start date):

- `add` (temperatures, RH): the mean of archive − gridMET over the slot's pooled window (`POOL_DAYS`, wider than
  the normals' 15 days because ten years of differences are noisy);
- `ratio` (precipitation, shortwave, wind, ET0): archive total ÷ gridMET total over the same pairs, capped to
  `RATIO_LIMITS`, 1 where gridMET's pooled total is under `RATIO_MIN_TOTAL` of the variable (a dry spell's ratio is
  noise);
- then smoothed across `SMOOTH` × `SMOOTH` cells (a mean of those with a value), so a cell's adjustment isn't one
  cell's sampling noise. A slot with under `FIT_COVERAGE` of its possible pairs takes its neighbours' through the
  smoothing, or none.

Every variable gridMET gives is adjusted (D84). Wind and ET0 joined once the archive's wind was checked against
anemometers (`docs/validation-wind.md`: within 3% of 70 airport stations at 10 m, where gridMET's is 1.5×). Changing
`ADJUST` asks for a new fit (`ops.climatology.plan`); a new fit makes every year out of date (`status`), and
`derive` writes it again from the kept files, without a download.
"""

import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import zarr
from zarr.codecs.numcodecs import PCodec
from zarr.errors import GroupNotFoundError

from agdata import pastyears
from agdata.catalog import DAILY_VARIABLES, FILL
from agdata.climatology import SLOTS, layout
from agdata.grid import Window
from agdata.sources import gridmet
from agdata.store import DAILY, GridStore, StoreLayout

LAYOUT = StoreLayout(kind="climate/gridmet", step="day")
VERSION = 1  # of `derive`: bump when its output changes, and every year is derived again
FIT_VERSION = 1  # of `fit`'s method
Kind = Literal["add", "ratio"]
ADJUST: dict[str, Kind] = {
    "air_temperature_max": "add",
    "air_temperature_min": "add",
    "relative_humidity_max": "add",
    "relative_humidity_min": "add",
    "precipitation_sum": "ratio",
    "shortwave_radiation_sum": "ratio",
    "wind_speed_mean": "ratio",
    "et0_sum": "ratio",
}
POOL_DAYS = 31
SMOOTH = 5  # cells a side
FIT_COVERAGE = 0.5
RATIO_LIMITS = (0.5, 2.0)
# gridMET's total over a pooled window (every overlap year's days) below which a ratio is noise: mm, MJ/m², m/s, mm
RATIO_MIN_TOTAL = {
    "precipitation_sum": 25.0,
    "shortwave_radiation_sum": 100.0,
    "wind_speed_mean": 50.0,
    "et0_sum": 25.0,
}
Progress = Callable[[int, int], None]


def path(data_dir: Path, year: int) -> Path:
    return LAYOUT.path(data_dir, year)


def fit_path(data_dir: Path) -> Path:
    return Path(data_dir) / "climate" / "gridmet-fit.zarr"


def years(data_dir: Path) -> list[int]:
    return pastyears.years_on_disk(data_dir, LAYOUT)


def kept_years(data_dir: Path) -> dict[int, list[str]]:
    """Each year with kept gridMET files (netCDF-4), and which variables."""
    found: dict[int, list[str]] = {}
    for source in gridmet.SOURCES:
        folder = Path(data_dir) / gridmet.KIND / source.name
        for file in sorted(folder.glob("*.nc")) if folder.exists() else ():
            if file.stem.isdigit() and gridmet.kept(file):
                found.setdefault(int(file.stem), []).append(source.name)
    return dict(sorted(found.items()))


# --- The fit ---------------------------------------------------------------------------------------------------


def _pooled(values: np.ndarray) -> np.ndarray:
    """(366, …) → each slot's sum over its centered POOL_DAYS window, wrapping the year."""
    before = POOL_DAYS // 2
    padded = np.concatenate([values[-before:], values, values[: POOL_DAYS - 1 - before]])
    sums = np.cumsum(padded, axis=0, dtype=np.float64)
    sums = np.concatenate([np.zeros((1, *values.shape[1:])), sums])
    return sums[POOL_DAYS:] - sums[:-POOL_DAYS]


def smooth(values: np.ndarray, size: int = SMOOTH) -> np.ndarray:
    """(…, ny, nx) → the mean of each cell's size × size neighbourhood over the cells with a value (NaN where none
    has one); edges use what's there."""
    ok = np.isfinite(values)
    filled = np.where(ok, values, 0.0)

    def box(a: np.ndarray) -> np.ndarray:
        half = size // 2
        pad = [(0, 0)] * (a.ndim - 2) + [(half + 1, half), (half + 1, half)]
        s = np.pad(a, pad).cumsum(axis=-2).cumsum(axis=-1)
        return s[..., size:, size:] - s[..., :-size, size:] - s[..., size:, :-size] + s[..., :-size, :-size]

    total, count = box(filled), box(ok.astype(np.float64))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, total / count, np.nan)


def fit_one(
    name: str,
    archive: Callable[[int], np.ndarray],
    gridmet_days: Callable[[int], np.ndarray],
    overlap: list[int],
    progress: Progress | None = None,
) -> np.ndarray:
    """One variable's adjustment (366, ny, nx) from the overlap's years: `archive(year)` and `gridmet_days(year)`
    give a year's days on the same window, (days, ny, nx). Sums accumulate a year at a time, so memory holds three
    (366, ny, nx) arrays whatever the years."""
    kind = ADJUST[name]
    sum_a = sum_g = count = possible = None
    for k, year in enumerate(overlap):
        a, g = layout(archive(year), year), layout(gridmet_days(year), year)
        both = np.isfinite(a) & np.isfinite(g)
        if sum_a is None:
            sum_a, sum_g, count = np.zeros(a.shape), np.zeros(a.shape), np.zeros(a.shape)
            possible = np.zeros(SLOTS)
        assert sum_a is not None and sum_g is not None and count is not None and possible is not None
        sum_a += np.where(both, a, 0.0)
        sum_g += np.where(both, g, 0.0)
        count += both
        possible += ~np.isnan(layout(np.zeros(366 if _leap(year) else 365), year))
        if progress is not None:
            progress(k + 1, len(overlap))
    if sum_a is None or sum_g is None or count is None or possible is None:
        raise ValueError(f"{name}: no overlap years to fit")
    pa, pg, pn = _pooled(sum_a), _pooled(sum_g), _pooled(count)
    enough = pn >= FIT_COVERAGE * _pooled(possible)[:, None, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        if kind == "add":
            raw = np.where(enough, (pa - pg) / pn, np.nan)
        else:
            raw = np.where(enough & (pg >= RATIO_MIN_TOTAL[name]), pa / pg, np.where(enough, 1.0, np.nan))
            raw = np.clip(raw, *RATIO_LIMITS)
    return smooth(raw).astype(np.float32)


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def fit(data_dir: Path, window: Window, overlap: list[int], report: Callable[[str], None] | None = None,
        progress: Callable[[str, int, int], None] | None = None) -> None:  # fmt: skip
    """Fits every `ADJUST` variable over `overlap` (years with both a daily store and kept gridMET files) and writes
    `gridmet-fit.zarr`, replacing the last fit once whole."""
    target = fit_path(data_dir)
    building = target.with_name(target.name + ".part")
    if building.exists():
        shutil.rmtree(building)
    group = zarr.open_group(building, mode="w")
    by_daily = {s.daily: s for s in gridmet.SOURCES}
    for name, kind in ADJUST.items():
        if report is not None:
            report(f"fitting {name} ({kind}) over {overlap[0]}–{overlap[-1]}")
        source = by_daily[name]

        def archive(year: int, name: str = name) -> np.ndarray:
            store = GridStore.open(data_dir, DAILY, year, [DAILY_VARIABLES[name]])
            return store.read_steps(name, 0, store.length, window, dtype=np.float32)

        def from_gridmet(year: int, source: gridmet.Source = source) -> np.ndarray:
            found = gridmet.read(gridmet.path(data_dir, source.name, year), source.name)
            _whole_year(found, year)
            return gridmet.regrid(found, window)

        values = fit_one(
            name,
            archive,
            from_gridmet,
            overlap,
            progress=None if progress is None else lambda d, t, n=name: progress(n, d, t),
        )
        array = group.create_array(name, shape=values.shape, chunks=(SLOTS, 64, 64), dtype="float32", fill_value=np.nan)
        array[:] = values
        array.attrs["kind"] = kind
    group.attrs.update(
        {
            "version": FIT_VERSION,
            "fitted": datetime.now(UTC).isoformat(timespec="microseconds"),  # two fits a second apart differ
            "years": overlap,
            "window": _window_attrs(window),
            "pool_days": POOL_DAYS,
            "smooth": SMOOTH,
            "names": sorted(ADJUST),
            "complete": True,
        }
    )
    _swap(building, target)


def fit_attrs(data_dir: Path) -> dict[str, Any] | None:
    try:
        group = zarr.open_group(fit_path(data_dir), mode="r")
    except (FileNotFoundError, GroupNotFoundError):
        return None
    attrs = dict(group.attrs)
    return attrs if attrs.get("complete") else None


def _fit_stamp(attrs: dict[str, Any] | None) -> str | None:
    return None if attrs is None else f"{attrs['version']}@{attrs['fitted']}"


# --- Deriving a year -------------------------------------------------------------------------------------------


def adjust(name: str, values: np.ndarray, year: int, table: np.ndarray | None) -> np.ndarray:
    """A year's days (days, ny, nx) put on the archive's basis by `table` (366, ny, nx; None: as they are), then
    clamped to the variable's valid range."""
    out = values.astype(np.float32, copy=True)
    if table is not None:
        slots = np.flatnonzero(~np.isnan(layout(np.zeros(values.shape[0]), year)))
        t = table[slots]
        out = out + np.nan_to_num(t, nan=0.0) if ADJUST[name] == "add" else out * np.nan_to_num(t, nan=1.0)
    v = DAILY_VARIABLES[name]
    return np.clip(out, v.valid_min, v.valid_max)


def _pairs(days: dict[str, np.ndarray]) -> None:
    """In place: a day's minimum no higher than its maximum, for temperature and RH (each adjusted on its own)."""
    for low, high in (
        ("air_temperature_min", "air_temperature_max"),
        ("relative_humidity_min", "relative_humidity_max"),
    ):
        if low in days and high in days:
            days[low] = np.fmin(days[low], days[high])


def status(data_dir: Path, year: int) -> str | None:
    """Why a year needs deriving, or None if it's current: missing, incomplete, a kept file fetched since, the fit
    or `ADJUST` changed, or `derive`'s code changed."""
    target = path(data_dir, year)
    try:
        group = zarr.open_group(target, mode="r")
    except (FileNotFoundError, GroupNotFoundError):
        return "missing"
    attrs: dict[str, Any] = dict(group.attrs)
    if not attrs.get("complete") or not (target / "values" / "zarr.json").exists():
        return "incomplete"
    if attrs.get("version") != VERSION:
        return "out of date: the code changed"
    if attrs.get("fit") != _fit_stamp(fit_attrs(data_dir)):
        return "out of date: the fit changed"
    if attrs.get("files") != _files(data_dir, year):
        return "out of date: gridMET's files changed"
    return None


def _files(data_dir: Path, year: int) -> dict[str, float]:
    found = {}
    for s in gridmet.SOURCES:
        file = gridmet.path(data_dir, s.name, year)
        if gridmet.kept(file):
            found[s.name] = round(file.stat().st_mtime, 3)
    return found


def derive(data_dir: Path, year: int, window: Window, progress: Progress | None = None) -> list[str]:
    """Writes a year's store from its kept files (every `gridmet.SOURCES` variable it has), adjusted by the current
    fit where there is one. Returns the daily variables written. Built beside its path and renamed into place."""
    present = [s for s in gridmet.SOURCES if gridmet.kept(gridmet.path(data_dir, s.name, year))]
    if not present:
        raise ValueError(f"no gridMET files kept for {year}")
    attrs = fit_attrs(data_dir)
    table_group = zarr.open_group(fit_path(data_dir), mode="r") if attrs is not None else None
    days: dict[str, np.ndarray] = {}
    adjusted: list[str] = []
    for k, source in enumerate(present):
        found = gridmet.read(gridmet.path(data_dir, source.name, year), source.name)
        _whole_year(found, year)
        table = None
        if table_group is not None and source.daily in ADJUST and source.daily in table_group:
            if attrs is not None and attrs["window"] != _window_attrs(window):
                raise ValueError("the fit was made over another window: fit again (`climatology --refit`)")
            array = table_group[source.daily]
            assert isinstance(array, zarr.Array)
            table = np.asarray(array[...])
        if table is not None:
            adjusted.append(source.daily)
        days[source.daily] = adjust(source.daily, gridmet.regrid(found, window), year, table)
        if progress is not None:
            progress(k + 1, len(present) + 1)
    _pairs(days)
    names = list(days)
    target = path(data_dir, year)
    building = target.with_name(target.name + ".part")
    if building.exists():
        shutil.rmtree(building)
    group = zarr.open_group(building, mode="w")
    n = next(iter(days.values())).shape[0]
    values = group.create_array(
        "values",
        shape=(len(names), n, *window.shape),
        chunks=(len(names), n, min(pastyears.CELLS, window.shape[0]), min(pastyears.CELLS, window.shape[1])),
        dtype="int16",
        fill_value=int(FILL),
        serializer=PCodec(level=8),
    )
    values[:] = np.stack([DAILY_VARIABLES[name].encode(days[name]) for name in names])
    group.attrs.update(
        {
            "year": year,
            "window": _window_attrs(window),
            "names": names,
            "version": VERSION,
            "fit": _fit_stamp(attrs),
            "adjusted": sorted(adjusted),
            "files": _files(data_dir, year),
            "complete": True,
        }
    )
    _swap(building, target)
    if progress is not None:
        progress(len(present) + 1, len(present) + 1)
    return names


def _whole_year(found: gridmet.Year, year: int) -> None:
    """A kept file must hold every day of its year (gridMET's current year grows a day at a time)."""
    expected = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    if len(found.days) != expected or found.days[0] != date(year, 1, 1):
        raise ValueError(f"{found.source.name} {year}: {len(found.days)} days from {found.days[0]}, not the whole year")


def _window_attrs(window: Window) -> dict[str, int]:
    return {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1}


def _swap(building: Path, target: Path) -> None:
    old = target.with_name(target.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        target.rename(old)
    building.rename(target)
    if old.exists():
        shutil.rmtree(old)


def reader(data_dir: Path) -> pastyears.Reader:
    """Reads a cell's days from the derived years, as `pastyears.Reader` does the archive's."""
    return pastyears.Reader(data_dir=data_dir, layout=LAYOUT)


def drop(data_dir: Path, year: int) -> None:
    """Deletes a derived year (one no longer in the period)."""
    target = path(data_dir, year)
    if target.exists():
        shutil.rmtree(target)
