"""Seasonal products on the grid (PLAN.md Phase 4 H, D68): a once-a-season model's map for a season, whether the
season is final, and its end projected from the archive's earlier seasons.

A seasonal model (`ModelSpec.seasonal`; potato volunteer's winter) is finished from its stored ingredients like
any model map (`agdata.modelgrid`): its season's map is the model on the season's last day counted, `through`, the
season's last day or the archive's last observed day before it. It counts observed days only (Q16), never the
forecast run. A season is final once its last day is in and none of the hours behind that day are provisional
(`store.PROVISIONAL`: ERA5-Land's soil has replaced IFS's, ~5 days after).

The projection carries each accumulation from a day to its end (the season's last day, or its `until`) on each
earlier season the archive holds (D63, every year counted the same, D67): the day's total plus that season's total
over the same calendar days, a difference of its running totals, so ten winters cost a few reads each. Each
season's totals are finished and given a risk as the model's own, and a cell's projection is their median and the
share of seasons ending at each risk level.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from agdata import modelgrid, series
from agdata.grid import Window
from agdata.projection import source_day
from agdata.store import HOURLY, PROVISIONAL
from agmodels.ingredients import until_day
from agmodels.registry import model as find_model
from agmodels.seasons import Season, season_of, season_starting
from agmodels.spec import ModelSpec

# The hours behind a day in every zone of the lower 48: its local midnight-to-midnight, UTC−5 to UTC−8, and the
# 8 pm day from the evening before
DAY_HOURS_BEFORE, DAY_HOURS_AFTER = 4, 8
PROJECTED, CHANCE = "projected_", "chance_"


def seasonal_spec(model_id: str) -> ModelSpec | None:
    """The model's spec if it's a seasonal product, else None."""
    spec = find_model(model_id).SPEC
    return spec if spec.seasonal is not None else None


def through(season: Season, last_observed_day: date) -> date | None:
    """The season's last day counted: its last, or the archive's last observed day before then; None before it
    starts."""
    day = min(season.last, last_observed_day)
    return day if day >= season.first else None


def is_final(data_dir: Path, spec: ModelSpec, season: Season, last_observed_day: date) -> bool:
    """Whether the season's last day is observed and none of the hours behind it is from a provisional source (a
    missing hour doesn't hold it open: a gap still there after the season may never fill)."""
    if last_observed_day < season.last:
        return False
    names = series.hourly_needed([q.name for q in spec.inputs])
    midnight = datetime(season.last.year, season.last.month, season.last.day, tzinfo=UTC)
    first, last = midnight - timedelta(hours=DAY_HOURS_BEFORE), midnight + timedelta(hours=24 + DAY_HOURS_AFTER)
    stores = series.Stores(names)
    for name in names:
        t = first
        while t < last:
            stop = min(last, datetime(t.year + 1, 1, 1, tzinfo=UTC))
            store = stores.get(data_dir, HOURLY, t.year)
            if store is None:
                return False
            k = store.index_of(t)
            if PROVISIONAL & set(store.sources(name, k, k + (stop - t) // timedelta(hours=1))):
                return False
            t = stop
    return True


def held(spec: ModelSpec, years: list[int], last_observed_day: date) -> list[Season]:
    """The seasons the archive holds (its years: each a season touches, but those not reached yet), oldest
    first. A season reaching before the archive's first year isn't one: its count would be short."""
    found = []
    for year in sorted(years):
        season = season_starting(spec, year)
        whole = season.last.year in years or season.last.year > max(years)
        if whole and through(season, last_observed_day) is not None:
            found.append(season)
    return found


@dataclass(kw_only=True)
class Projection:
    """A day's season carried to its end on each earlier season: per output, (y, x) maps."""

    years: list[int]  # each earlier season's first year, newest first
    medians: dict[str, np.ndarray]  # `projected_<output>` and `projected_risk_level`
    chances: dict[str, np.ndarray]  # `chance_<level>`: the percent of seasons ending at that risk level
    counted: np.ndarray  # (y, x): the seasons each cell has


def level_key(level: str) -> str:
    return level.lower().replace(" ", "_")


def project(
    data_dir: Path,
    model_id: str,
    day: date,
    window: Window,
    found: modelgrid.ModelDays,
    years: list[int],
    stores: series.Stores | None = None,
    now=None,
) -> Projection:
    """The season `day` falls in, carried from `found` (the model's map on `day`) to its end on each earlier
    season among the archive's `years`."""
    m = find_model(model_id)
    spec = m.SPEC
    season = season_of(spec, day)
    if season is None:
        raise ValueError(f"{day} isn't in a {model_id} season")
    current = {a.name: found.accumulated[a.name][0] for a in spec.accumulations}
    ends = {a.name: until_day(a.until, season.first) if a.until else season.last for a in spec.accumulations}
    back = [
        k
        for k in range(1, season.first.year - min(years, default=season.first.year) + 1)
        if season.first.year - k in years and season.last.year - k in years
    ]
    if all(day >= end for end in ends.values()):
        back = []  # nothing left to count: the season's own totals
    _, reader = modelgrid._base(data_dir, spec, day, day, window, now, stores, modelgrid.read_names(model_id))
    scenarios: dict[str, list[np.ndarray]] = {a.name: [] for a in spec.accumulations}
    for k in back:
        for a in spec.accumulations:
            ingredient = next(i for i in spec.ingredients if i.name == a.of)
            end = ends[a.name]
            if day >= end:
                scenarios[a.name].append(current[a.name])
                continue
            span = (source_day(day + timedelta(days=1), k), source_day(end, k))
            rest = modelgrid._spans(lambda days, i=ingredient: reader.total(i, spec.id, days), [span], window)[0]
            scenarios[a.name].append(current[a.name] + rest)
    if not back:
        scenarios = {name: [v] for name, v in current.items()}
    stacked = {name: np.stack(v) for name, v in scenarios.items()}  # (seasons, y, x)
    n = next(iter(stacked.values())).shape[0]
    end_day = max(ends.values())
    values: dict[str, np.ndarray] = {i.name: np.full((n, *window.shape), np.nan) for i in spec.ingredients}
    values |= stacked
    values["day_of_year"] = np.full((n, 1, 1), float(end_day.timetuple().tm_yday))
    values["year"] = np.full((n, 1, 1), float(end_day.year))
    values["biofix_day_of_year"] = np.full((n, 1, 1), float(season.first.timetuple().tm_yday))
    outputs = {k: np.broadcast_to(v, (n, *window.shape)) for k, v in m.finish(values, **found.options).items()}  # type: ignore[attr-defined]
    known = np.all([np.isfinite(v) for v in stacked.values()], axis=0)  # (seasons, y, x)
    counted = known.sum(axis=0)
    medians = {f"{PROJECTED}{name}": _median(v, known) for name, v in outputs.items()}
    chances: dict[str, np.ndarray] = {}
    if spec.risk is not None:
        risk = np.broadcast_to(
            np.asarray(m.risk(outputs | stacked, biofix_index=0, **found.options), dtype=float), known.shape
        )
        thresholds = spec.risk.thresholds
        level = np.searchsorted(np.asarray(thresholds), risk, side="right").astype(float) if thresholds else risk
        level = np.where(known & np.isfinite(risk), level, np.nan)
        # An even count's median level is the higher of the middle two: the riskier, as a warning should lean
        medians[f"{PROJECTED}risk_level"] = _median(level, known, method="higher")
        with np.errstate(invalid="ignore", divide="ignore"):
            for k, name in enumerate(spec.risk.levels):
                share = 100.0 * (level == k).sum(axis=0) / counted
                chances[f"{CHANCE}{level_key(name)}"] = np.where(counted > 0, share, np.nan)
    if found.in_region is not None:
        for v in (*medians.values(), *chances.values()):
            v[~found.in_region] = np.nan
    return Projection(years=[season.first.year - k for k in back], medians=medians, chances=chances, counted=counted)


def _median(values: np.ndarray, known: np.ndarray, method: str = "linear") -> np.ndarray:
    v = np.where(known, values, np.nan)
    out = np.full(v.shape[1:], np.nan)
    has = known.any(axis=0)
    if has.any():
        out[has] = np.nanquantile(v[:, has], 0.5, axis=0, method=method)  # type: ignore[call-overload]
    return out


def describe(data_dir: Path, spec: ModelSpec, season: Season, last: date, observed_day: date) -> dict[str, Any]:
    """A season as responses summarize it: its days, when it's shown, through which day it's counted (`last`, the
    response's last day, within the season) and whether it's final."""
    return {
        "name": season.name,
        "label": season.label,
        "first": season.first,
        "last": season.last,
        "appears": season.appears,
        "through": min(last, season.last),
        "final": is_final(data_dir, spec, season, observed_day),
    }
