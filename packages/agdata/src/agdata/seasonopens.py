"""The day an insect's season opens, at each cell and over the region, from the 30-year normal (D128).

Every insect has one rule (`ModelSpec.opens`):

- **Degree days** (`OpensOnDegreeDays`): a week before the day the area's normal degree days reach its first activity.
  The normal running totals from January 1 (`agdata.normals`' `last30`, the degree-day cubes the archive keeps, with
  the insect's own method, thresholds and start) give each cell the first day its total from the start reaches the
  first activity; that day is averaged over the land within 50 km, center-weighted, as the area's spring freeze is
  (`agdata.springfreeze.smooth`, D127), so a frost pocket or a lake-cooled cell doesn't open its own season. European
  corn borer's one-flight form opens on its own first activity where its normal is below the bound, as the model runs.
  Western bean cutworm's method (the day's mean capped at 75 °F, less 38 °F) isn't a stored cube: its days come from
  the normal daily minimum and maximum's means, which leave out the warm days of a cool spell (its first activity comes
  in July, when the mean is above 38 °F nearly every day, so it matters little).
- **A crop stage** (`OpensOnCropStage`): the day the crop typically reaches it on the same normal, by the crop model's
  degree days counted from its typical planting tier (`agdata.potatoplanting`, itself the area's spring freeze) or from
  January 1 for apple, averaged over the area the same way.
- **The calendar** (`OpensOnCalendar`): the season's first day everywhere, for migrants.

Days are calendar slots (`climatology.slot`: a leap year's day of year from 0); a cell the normal never brings to the
event opens at `NEVER` (past the year: not in season). A cell without the normal (outside its area, or before
`last30` is built) has none, and a place there falls back on the season's calendar first day with a warning.

Region-wide (the home page's list, a map's warnings), one day per insect: the 10th percentile of the cells' days,
each cell weighted by its cultivated share (`agdata.cropland`, D116; equal weights where the store isn't built), so
the season is open for the region once it's open on a tenth of its farmland.

The maps of every insect are computed together, once per build of the normals (and of the terrain store, which
decides the water left out), over the normals store's window, and cut to each request, so a point reads exactly its map
cell's day.
"""

import hashlib
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from agdata import climatology, cropland, normals, potatoplanting, regions, springfreeze
from agdata.catalog import dd_name
from agdata.grid import NDFD, Window
from agmodels import registry
from agmodels.degree_days import degree_days_average_capped_mean
from agmodels.ingredients import DegreeDays
from agmodels.spec import ModelSpec, OpensOnCalendar, OpensOnCropStage, OpensOnDegreeDays

PERIOD = "last30"
VERSION = 1  # bump when how the maps are computed changes, and the built file is built again
NEVER = float(climatology.SLOTS)  # a cell the normal never brings to the event: past every day of the year
REGION_PERCENTILE = 10.0
BLOCK_SLOTS = 32  # the normal's days read at once (a statistic's 32 days over the launch extent: ~75 MB)
# The insect's degree days as the stored running totals' sum: (cube name, sign); None for a method no cube keeps
Cubes = tuple[tuple[str, int], ...]


def cubes(method: str, base_f: float, upper_f: float | None) -> Cubes | None:
    """The stored normal running totals (`normals.RUNNING_NAMES`) whose sum is a method's degree days: a single sine's
    with an upper is its base's less its upper's (both linear, D61); None where no cube keeps it."""
    if method == "sine":
        found = ((dd_name("sine", base_f), 1),) + (() if upper_f is None else ((dd_name("sine", upper_f), -1),))
    elif method in ("modified", "average"):
        found = ((dd_name(method, base_f, upper_f), 1),)
    else:
        return None
    return found if all(name in normals.RUNNING_NAMES for name, _ in found) else None


def crop_stage_dd(rule: OpensOnCropStage) -> tuple[DegreeDays, float]:
    """The crop model's degree-day setting and its degree days (°F) to the stage, from its module's stage table."""
    crop = registry.model(rule.crop)
    setting = crop.SPEC.ingredients[0].degree_days
    if setting is None:
        raise ValueError(f"{rule.crop} isn't timed by degree days")
    codes = [s.code for s in crop.stages()]  # type: ignore[attr-defined]
    dd = float(np.asarray(crop.THRESHOLDS)[codes.index(rule.stage)])  # type: ignore[attr-defined]
    if crop.SPEC.ingredients[0].unit == "degC_day":
        dd *= 1.8
    return setting, dd


def opening_specs() -> list[ModelSpec]:
    """Every model whose season opens by the normal (degree days or a crop stage)."""
    return [
        m.SPEC for m in registry.all_models().values() if isinstance(m.SPEC.opens, OpensOnDegreeDays | OpensOnCropStage)
    ]


# --- At a cell and over a window -----------------------------------------------------------------------------------


def slots(data_dir: Path, spec: ModelSpec, window: Window) -> np.ndarray:
    """The day the model's season opens over `window` as calendar slots, float (y, x): NaN where the normal is
    missing (past its area, or everywhere if it isn't built); the calendar's first day everywhere for a model without
    a rule or opening on the calendar."""
    rule = spec.opens
    if rule is None or isinstance(rule, OpensOnCalendar):
        first = spec.season[0] if spec.season is not None else "01-01"
        return np.full(window.shape, float(_slot(first)))
    whole = _whole(Path(data_dir), *_stamps(data_dir))
    out = np.full(window.shape, np.nan)
    if whole is None:
        return out
    maps, w = whole
    values = maps[spec.id]
    j0, j1 = max(window.j0, w.j0), min(window.j1, w.j1)
    i0, i1 = max(window.i0, w.i0), min(window.i1, w.i1)
    if j0 < j1 and i0 < i1:
        out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = values[
            j0 - w.j0 : j1 - w.j0, i0 - w.i0 : i1 - w.i0
        ]
    return out


def at(data_dir: Path | None, spec: ModelSpec, cell: tuple[int, int] | None) -> str | None:
    """The day the season opens at a grid cell (j, i) as MM-DD, "12-31" past it where the normal never gets there;
    None where there's no normal (off the grid, outside its area, no data folder): the caller then uses the season's
    calendar first day and says so (`MISSING`)."""
    if spec.opens is None or isinstance(spec.opens, OpensOnCalendar):
        return None
    if data_dir is None or cell is None:
        return None
    j, i = cell
    value = float(slots(data_dir, spec, Window(j0=j, j1=j + 1, i0=i, i1=i + 1))[0, 0])
    return None if np.isnan(value) else slot_text(value)


# Public text: the warning where a place has no normal to open an insect's season by (the same for every insect, so
# a list of them says it once)
MISSING = "An insect's season opens when the 30-year normal temperatures bring its first activity or its crop's stage. We don't have those normals for this location, so insect seasons here start on fixed dates set for Wisconsin."


def at_point(
    data_dir: Path | None, spec: ModelSpec, latitude: float, longitude: float
) -> tuple[str | None, str | None]:
    """The day the season opens at a point's cell (MM-DD; None: the calendar's first day) and the warning to give
    with it (`MISSING`, where the rule needs a normal the place doesn't have), for the runner (`runner.run`'s
    `season_opens`)."""
    if spec.opens is None or isinstance(spec.opens, OpensOnCalendar):
        return None, None
    cell = NDFD.cell_of(latitude, longitude) if data_dir is not None else None
    found = at(data_dir, spec, cell)
    return found, None if found is not None else MISSING


def how(spec: ModelSpec) -> str:
    """Public text: when the season opens, completing "It opens …"."""
    rule = spec.opens
    if isinstance(rule, OpensOnDegreeDays):
        return f"about a week before {rule.event} in a typical year"
    if isinstance(rule, OpensOnCropStage):
        return f"on the day {rule.event} in a typical year"
    assert spec.season is not None
    return f"on {_day_text(spec.season[0])}"


def map_warning(spec: ModelSpec, opens: np.ndarray, dates: list[date], land: np.ndarray) -> str | None:
    """Public text for a map whose last day comes before the season opens at some of its land cells (`opens`, the
    cells' slots), which are blank; None where it's open everywhere."""
    with np.errstate(invalid="ignore"):
        closed = land & (climatology.slot(dates[-1]) < opens)
    if not closed.any():
        return None
    return f"Blank areas are where the season for {spec.name.lower()} hasn't opened yet. It opens {how(spec)}."


def region(data_dir: Path | None, spec: ModelSpec) -> str | None:
    """The day the season opens over the region (MM-DD): the 10th percentile of the cells' days over the normals'
    area, each cell weighted by its cultivated share; the calendar's first day for a model opening on it; None where
    the normal isn't built (the caller uses the calendar's)."""
    rule = spec.opens
    if rule is None or isinstance(rule, OpensOnCalendar):
        return spec.season[0] if spec.season is not None else None
    if data_dir is None:
        return None
    found = _region(Path(data_dir), spec.id, *_stamps(data_dir), _cropland_stamp(data_dir))
    return None if found is None else slot_text(found)


def weighted_percentile(values: np.ndarray, weights: np.ndarray, percentile: float) -> float | None:
    """The smallest value at or below which `percentile` of the weight lies (values and weights flat, finite and
    positive weights only); None with no weight."""
    use = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    v, w = values[use], weights[use]
    if not v.size:
        return None
    order = np.argsort(v, kind="stable")
    total = np.cumsum(w[order])
    k = int(np.searchsorted(total, percentile / 100 * total[-1], side="left"))
    return float(v[order][min(k, v.size - 1)])


def slot_text(slot: float) -> str:
    """A calendar slot as MM-DD; one past the year (`NEVER`) as 12-31's day after, which no season reaches."""
    if slot >= climatology.SLOTS:
        return "12-31"  # never: no insect's season runs to December 31, so it never opens
    return (date(climatology.LEAP, 1, 1) + timedelta(days=int(slot))).strftime("%m-%d")


def _slot(mmdd: str) -> int:
    month, day = (int(p) for p in mmdd.split("-"))
    return climatology.slot(date(climatology.LEAP, month, day))


def _day_text(mmdd: str) -> str:
    month, day = (int(p) for p in mmdd.split("-"))
    return f"{date(2001, month, day):%B} {day}"


# --- Computing the maps --------------------------------------------------------------------------------------------


def _stamps(data_dir: Path) -> tuple[str | None, float | None]:
    return normals.stamp(data_dir, PERIOD), regions._water_stamp()


def _cropland_stamp(data_dir: Path) -> float | None:
    found = cropland.load(Path(data_dir))
    return None if found is None else found.stamp


@lru_cache(maxsize=2)
def _whole(data_dir: Path, stamp: str | None, water_stamp: float | None) -> tuple[dict[str, np.ndarray], Window] | None:
    """Every rule's map over the normals store's window (read-only) and that window; None if it isn't built. Read
    from the built file (`build`) when it's current, else computed here (a minute or two over the launch extent).
    Keyed by the stamps, so a rebuilt store is read again."""
    attrs = normals.info(data_dir, PERIOD)
    if stamp is None or attrs is None:
        return None
    w = Window(**attrs["window"])
    maps = _saved(data_dir, _key(stamp, water_stamp))
    if maps is None:
        maps = compute(data_dir, opening_specs(), w)
    for values in maps.values():
        values.flags.writeable = False
    return maps, w


# --- The built file: the maps kept beside the normals, so a process reads them rather than computing ------------


def path(data_dir: Path) -> Path:
    """The built maps: `climate/normals/last30-season-opens.npz`."""
    return normals.path(data_dir, PERIOD).with_name(f"{PERIOD}-season-opens.npz")


def _key(stamp: str | None, water_stamp: float | None) -> str:
    """What the maps depend on: this code's version, the normals' and the water mask's builds, and every rule (and
    potato's planting offsets, which crop rules count from)."""
    rules = repr(sorted((s.id, repr(s.opens), s.season) for s in opening_specs()))
    extra = repr((potatoplanting.OFFSETS, springfreeze.RADIUS_KM))
    digest = hashlib.sha256((rules + extra).encode()).hexdigest()[:16]
    return f"{VERSION}:{stamp}:{water_stamp}:{digest}"


def _saved(data_dir: Path, key: str) -> dict[str, np.ndarray] | None:
    try:
        with np.load(path(data_dir), allow_pickle=False) as found:
            if str(found["key"]) != key:
                return None
            return {name.removeprefix("opens/"): found[name] for name in found.files if name.startswith("opens/")}
    except (FileNotFoundError, KeyError, ValueError, OSError):
        return None


def status(data_dir: Path) -> str | None:
    """Why the built maps need building (`build`), or None when they're current or there's no normal to build them
    from."""
    stamps = _stamps(data_dir)
    if stamps[0] is None:
        return None
    if not path(data_dir).exists():
        return "none yet"
    return None if _saved(data_dir, _key(*stamps)) is not None else "the normals, the water mask or a rule changed"


def build(data_dir: Path) -> int:
    """Computes every rule's map over the normals' window and writes them beside the normals (written to a temporary
    name and renamed into place); returns how many. Nothing to do without the normals."""
    stamps = _stamps(data_dir)
    attrs = normals.info(data_dir, PERIOD)
    if stamps[0] is None or attrs is None:
        return 0
    maps = compute(data_dir, opening_specs(), Window(**attrs["window"]))
    target = path(data_dir)
    temporary = target.with_name(f".{target.name}.building.npz")
    np.savez(temporary, key=np.array(_key(*stamps)), **{f"opens/{k}": v.astype(np.float32) for k, v in maps.items()})
    temporary.replace(target)
    _whole.cache_clear()
    _region.cache_clear()
    return len(maps)


@lru_cache(maxsize=64)
def _region(
    data_dir: Path, model_id: str, stamp: str | None, water_stamp: float | None, cropland_stamp: float | None
) -> float | None:
    whole = _whole(data_dir, stamp, water_stamp)
    if whole is None:
        return None
    maps, w = whole
    land = regions.land(w)
    found = cropland.load(data_dir)
    weights = found.share(None, "cultivated", w).astype(np.float64) if found is not None else np.ones(w.shape)
    if found is not None and not np.nansum(np.where(land, weights, 0)) > 0:
        weights = np.ones(w.shape)  # the store doesn't reach the normals' area
    return weighted_percentile(maps[model_id][land], weights[land], REGION_PERCENTILE)


class _Crossing:
    """The first slot at which a running total, counted from a start slot (each cell's, or a fixed one), reaches a
    target, fed one slot at a time in order."""

    def __init__(self, *, start: np.ndarray, target: float, shape: tuple[int, ...]):
        self.start = np.broadcast_to(start, shape)
        self.target = target
        self.base = np.where(self.start <= 0, 0.0, np.nan)  # the total at the end of the day before the start
        self.found = np.full(shape, np.nan)

    def add(self, s: int, total: np.ndarray, before: np.ndarray | None) -> None:
        if before is not None:
            self.base = np.where(self.start == s, before, self.base)
        with np.errstate(invalid="ignore"):
            reached = np.isnan(self.found) & (self.start <= s) & (total - self.base >= self.target)
        self.found[reached] = s

    def finish(self, known: np.ndarray) -> np.ndarray:
        """The slots, `NEVER` where the normal is known (`known`) and the total never got there, NaN where unknown."""
        return np.where(np.isnan(self.found) & known & np.isfinite(self.start), NEVER, self.found)


def compute(data_dir: Path, specs: list[ModelSpec], window: Window) -> dict[str, np.ndarray]:
    """Each spec's opening slots over `window` (float (y, x), NaN where the normal is missing), all from one pass over
    the normal's days: each cube is read a day at a time, each rule's first day found per cell, then averaged over the
    area (`springfreeze.smooth`) and moved by its lead."""
    found = normals._opened(data_dir, PERIOD)
    if found is None:
        return {s.id: np.full(window.shape, np.nan) for s in specs}
    group, attrs = found
    shape = window.shape
    plans: list[tuple[ModelSpec, list[tuple[_Crossing, Cubes | None, Any]]]] = []
    wanted: set[str] = set()
    for spec in specs:
        rule = spec.opens
        crossings = []
        if isinstance(rule, OpensOnDegreeDays):
            parts = cubes(rule.method, rule.base_f, rule.upper_f)
            start = np.array(float(_slot(rule.start)))
            setting = DegreeDays(method=rule.method, base_f=rule.base_f, upper_f=rule.upper_f)  # type: ignore[arg-type]
            targets = [rule.dd] + ([rule.form_dd] if rule.form_dd is not None else [])
            crossings = [(_Crossing(start=start, target=t, shape=shape), parts, setting) for t in targets]
        elif isinstance(rule, OpensOnCropStage):
            setting, dd = crop_stage_dd(rule)
            parts = cubes(setting.method, setting.base_f, setting.upper_f)
            start = (
                potatoplanting.slots(data_dir, rule.planting, window) if rule.planting is not None else np.array(0.0)
            )
            crossings = [(_Crossing(start=start, target=dd, shape=shape), parts, setting)]
        for _, parts, _ in crossings:
            wanted.update(name for name, _ in parts or ())
        plans.append((spec, crossings))

    def read(name: str, s: int) -> np.ndarray:
        """Slot `s` of a statistic, from blocks of `BLOCK_SLOTS` read at once."""
        k = s // BLOCK_SLOTS
        if blocks.get(name, (None,))[0] != k:
            first = k * BLOCK_SLOTS
            last = min(first + BLOCK_SLOTS, climatology.SLOTS)
            try:
                values = normals.slots_within(group, attrs, name=name, first=first, last=last, window=window)
            except KeyError:  # a store without the statistic (a test's): the rules that read it have no map
                values = np.full((last - first, *shape), np.nan, dtype=np.float32)
            blocks[name] = (k, values)
        return blocks[name][1][s % BLOCK_SLOTS].astype(np.float64)

    blocks: dict[str, tuple[int, np.ndarray]] = {}
    capped = {setting for _, cs in plans for _, parts, setting in cs if parts is None}
    running = {setting: np.zeros(shape) for setting in capped}  # methods no cube keeps, from the daily normals
    previous: dict[Any, np.ndarray] = {}
    known = np.ones(shape, dtype=bool)  # cells the normal has every day so far
    for s in range(climatology.SLOTS):
        totals = {name: read(f"{name}/mean", s) for name in sorted(wanted)}
        if capped:
            tmin = read("air_temperature_min/mean", s) * 1.8 + 32
            tmax = read("air_temperature_max/mean", s) * 1.8 + 32
            for setting in capped:
                assert setting.upper_f is not None
                running[setting] = running[setting] + degree_days_average_capped_mean(
                    tmin, tmax, setting.base_f, setting.upper_f
                )
        current: dict[Any, np.ndarray] = {}
        for _, crossings in plans:
            for crossing, parts, setting in crossings:
                key = parts if parts is not None else setting
                if key not in current:
                    current[key] = sum(sign * totals[n] for n, sign in parts) if parts is not None else running[setting]
                crossing.add(s, current[key], previous.get(key))
        for total in current.values():
            known &= np.isfinite(total)
        previous = current
        if known.any() and all(
            np.isfinite(c.found[known & np.isfinite(c.start)]).all() for _, cs in plans for c, _, _ in cs
        ):
            break  # every cell has reached every event
    land = ~regions.water(window)
    out = {}
    for spec, crossings in plans:
        rule = spec.opens
        assert isinstance(rule, OpensOnDegreeDays | OpensOnCropStage)
        smoothed = [springfreeze.smooth(c.finish(known), land) for c, _, _ in crossings]
        value = smoothed[0]
        if isinstance(rule, OpensOnDegreeDays) and rule.form_normal is not None and rule.form_below is not None:
            normal = normals.place_normal(data_dir, rule.form_normal, window)
            with np.errstate(invalid="ignore"):
                value = np.where(np.isfinite(normal) & (normal < rule.form_below), smoothed[1], value)
        out[spec.id] = np.maximum(np.round(value) - rule.lead_days, 0.0)
    return out
