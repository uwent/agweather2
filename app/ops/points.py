"""A model at any US point (Phase 4 C, E): in the box, from the archive and the NBM forecast, with the forecast
soil hours the run lacks from Open-Meteo (D44), and Open-Meteo's forecast in place of a stale or missing run (D114);
outside it, or before the archive, from Open-Meteo through the cell cache."""

import time
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta

import numpy as np
from django.conf import settings

from agdata import areas, coverage, series, terrain
from agdata.areas import Area, Place, Weighting
from agdata.grid import NDFD
from agdata.sources import openmeteo as openmeteo_source
from agdata.store import DAILY
from agdata.timezones import DayBasis, basis_zone
from agmodels.runner import ModelRun
from ops import openmeteo

HOUR = timedelta(hours=1)
FALLBACK_SECONDS = 10.0  # one request's time for starting Open-Meteo fetches in the box (D114)


@dataclass(frozen=True, kw_only=True)
class AreaAsk:
    """A request's `radius` (in km) and `weighting`: each point's weather is the area's around it
    (`agdata.areas`)."""

    radius_km: float
    weighting: Weighting = "equal"
    land_only: bool = False  # leave out cells all open water (`agdata.terrain`, D6)

    def at(self, latitude: float, longitude: float) -> Area:
        covered = coverage.of(settings.SERVICE_BOX)
        water_keep = _not_all_water() if self.land_only else None

        def keep(jj: np.ndarray, ii: np.ndarray) -> np.ndarray:  # covered cells (D105), and not all water if asked
            w = covered.window
            inside = (jj >= w.j0) & (jj < w.j1) & (ii >= w.i0) & (ii < w.i1)
            ok = inside & covered.mask[np.clip(jj - w.j0, 0, w.shape[0] - 1), np.clip(ii - w.i0, 0, w.shape[1] - 1)]
            return ok if water_keep is None else ok & water_keep(jj, ii)

        found = areas.around(latitude, longitude, self.radius_km, self.weighting, window=covered.window, keep=keep)
        if found is None:
            if NDFD.cell_of(latitude, longitude) is not None and self.land_only:
                raise AllWater(f"every cell within {self.radius_km:g} km of ({latitude}, {longitude}) is open water")
            raise ValueError(f"({latitude}, {longitude}) is off the grid")
        return found


class AllWater(ValueError):
    """`land_only` left no cell in a point's area."""


def _not_all_water():
    """For `areas.around`'s `keep`: a cell isn't all open water by the terrain store (cells outside it count)."""
    t = terrain.load(settings.DATA_DIR)
    if t is None:
        raise terrain.NotBuilt("the terrain store isn't built: run manage.py terrain")
    w = t.window

    def keep(jj: np.ndarray, ii: np.ndarray) -> np.ndarray:
        inside = (jj >= w.j0) & (jj < w.j1) & (ii >= w.i0) & (ii < w.i1)
        share = t.cells["water_share"][np.clip(jj - w.j0, 0, w.shape[0] - 1), np.clip(ii - w.i0, 0, w.shape[1] - 1)]
        return ~inside | (share < 100)

    return keep


def place_at(latitude: float, longitude: float, area: AreaAsk | None) -> Place:
    """The cell a point reads, or the area around it."""
    if area is not None:
        return area.at(latitude, longitude)
    cell = NDFD.cell_of(latitude, longitude)
    if cell is None:
        raise ValueError(f"({latitude}, {longitude}) is off the grid")
    return cell


def in_box(latitude: float, longitude: float) -> bool:
    """Whether the archive covers a point's cell: inside the service box, or the launch coverage's mask (D105)."""
    cell = NDFD.cell_of(latitude, longitude)
    return cell is not None and coverage.of(settings.SERVICE_BOX).contains(*cell)


def day_basis(latitude: float, longitude: float, basis: DayBasis | None = None) -> DayBasis:
    """Whose clock sets a point's days (D74): `basis`, or by default the grid's (CST) inside the box, so a point
    agrees with its map, and the point's own outside it."""
    if basis is not None:
        return basis
    return "central" if in_box(latitude, longitude) else "local"


def day_zone(latitude: float, longitude: float, basis: DayBasis | None = None) -> str:
    """The zone of `day_basis`'s clock."""
    return basis_zone(day_basis(latitude, longitude, basis), latitude, longitude)


def in_archive(latitude: float, longitude: float, first: date, last: date) -> bool:
    """Whether the archive covers a point and every year of first..last (each year's daily store exists)."""
    if not in_box(latitude, longitude):
        return False
    # A store is renamed into place only once it's whole (`GridStore.create`), so its path existing is enough
    return all(DAILY.path(settings.DATA_DIR, year).exists() for year in range(first.year, last.year + 1))


@dataclass(kw_only=True)
class FallbackBudget:
    """One request's allowance for fetching Open-Meteo for points in the box (the soil past the run's, D44, and the
    forecast in place of a stale run, D114): fetches start only within `seconds` of its making (the request's first read) and until one fails,
    after which the rest of the request's points go without (their answers say so) rather than each waiting out
    Open-Meteo's timeout. The cell cache's answers cost nothing and are always read."""

    seconds: float = FALLBACK_SECONDS
    started: float = field(default_factory=time.monotonic)
    failed: bool = False

    def allows(self) -> bool:
        return not self.failed and time.monotonic() - self.started < self.seconds


def fallback_on() -> bool:
    """Whether points in the box take Open-Meteo's forecast while ours is stale (`OPEN_METEO_FALLBACK`, D114)."""
    return bool(getattr(settings, "OPEN_METEO_FALLBACK", False))


def models_at_point(
    latitude: float,
    longitude: float,
    runs: Sequence[series.RunSpec],
    start: date,
    end: date,
    now: datetime,
    planting_default: bool = True,
    zone: str | None = None,
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> list[ModelRun]:
    """Models' three layers at a point (on the weather of `area` around it, if given), each day marked observed,
    partial or forecast, in the order of `runs`. The runs whose days the archive covers read it once; any that reach
    before it (or a point outside the box) read Open-Meteo once, so one model's long lookback doesn't move the others
    off the archive. Days follow `zone`'s clock (default `day_zone`'s)."""
    zone = zone or day_zone(latitude, longitude)
    budget = budget or FallbackBudget()
    if planting_default:
        runs = [series.with_planting(run, latitude, longitude, start) for run in runs]
    archived = [in_archive(latitude, longitude, series.days_needed([run], start)[0], end) for run in runs]
    results: list[ModelRun | None] = [None] * len(runs)
    for from_archive in (True, False):
        group = [k for k, a in enumerate(archived) if a == from_archive]
        if not group:
            continue
        chosen = [runs[k] for k in group]
        found = (
            _archive_runs(latitude, longitude, chosen, start, end, now, zone, area, budget)
            if from_archive
            else _openmeteo_runs(latitude, longitude, chosen, start, end, now, zone)
        )
        for k, result in zip(group, found, strict=True):
            results[k] = result
    return [r for r in results if r is not None]


def models_at_points(
    sites: Sequence[tuple[float, float]],
    runs: Sequence[Sequence[series.RunSpec]],
    start: date,
    end: date,
    now: datetime,
    zones: Sequence[str],
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> list[list[ModelRun]]:
    """`models_at_point` (without typical planting dates) at each point, with its own runs (`runs[k]`) on its own
    zone's days (`zones[k]`): the runs the archive covers, at every point, on one read of their cells
    (`series.cells_days`); the rest from Open-Meteo a point at a time. Each point's results are the same as its own
    request's, but for the order of a mean's sums (~1e-16) and `sources`, which name the sources of the hours read
    for every point's runs (from the earliest day any of them needs)."""
    results: list[list[ModelRun | None]] = [[None] * len(own) for own in runs]
    budget = budget or FallbackBudget()
    archived = {
        (k, m)
        for k, (lat, lng) in enumerate(sites)
        for m, run in enumerate(runs[k])
        if in_archive(lat, lng, series.days_needed([run], start)[0], end)
    }
    batched = sorted({k for k, _ in archived})
    if batched:
        chosen = {k: [m for m in range(len(runs[k])) if (k, m) in archived] for k in batched}
        first, names = series.days_needed([runs[k][m] for k in batched for m in chosen[k]], start)
        places = [place_at(*sites[k], area) for k in batched]
        found = series.cells_days(
            settings.DATA_DIR,
            places,
            first,
            end,
            names,
            now=now,
            fill_soil=[_soil_filler(*sites[k], now, budget) for k in batched],
            zones=[zones[k] for k in batched],
            fill_forecast=[forecast_filler(*sites[k], now, budget) for k in batched],
        )
        for k, days in zip(batched, found, strict=True):
            own = series.runs_at_point(
                _slicer(days),
                *sites[k],
                [runs[k][m] for m in chosen[k]],
                start,
                end,
                planting_default=False,
                data_dir=settings.DATA_DIR,
            )
            for m, result in zip(chosen[k], own, strict=True):
                results[k][m] = result
    for k, (lat, lng) in enumerate(sites):
        rest = [m for m in range(len(runs[k])) if results[k][m] is None]
        if rest:
            own = _openmeteo_runs(lat, lng, [runs[k][m] for m in rest], start, end, now, zones[k])
            for m, result in zip(rest, own, strict=True):
                results[k][m] = result
    return [[r for r in own if r is not None] for own in results]


def _slicer(days: series.DailySeries):
    """`runs_at_point`'s `read_days` from days already read (from as early as any point needed): the days it asks
    for, with the corrections those days went through, as a read of just them would give."""

    def read_days(first: date, last: date, names: list[str]) -> series.DailySeries:
        own = series.sliced(days, first, names)
        corrections = series.in_box_corrections(own.kinds, days.forecast, series.hourly_needed(names))
        return replace(own, corrections=corrections)

    return read_days


def _soil_filler(latitude: float, longitude: float, now: datetime, budget: FallbackBudget) -> series.FillSoil:
    """Forecast soil hours the run lacks, from Open-Meteo's ECMWF IFS through the cell cache (D44); None (the soil
    stays missing, with a warning) when Open-Meteo can't be reached or the request's `budget` is spent."""

    def fill_soil(first_hour: datetime, last_hour: datetime, names: list[str]) -> dict[str, np.ndarray] | None:
        found = _fetch(latitude, longitude, first_hour, last_hour, now, budget)
        if found is None:
            return None
        values, _, _ = found  # soil only
        return {name: values[name] for name in names if name in values}

    return fill_soil


def forecast_filler(
    latitude: float, longitude: float, now: datetime, budget: FallbackBudget
) -> series.FillForecast | None:
    """A point's forecast from Open-Meteo through the cell cache while our run is stale or missing (D114), as for a
    point outside the box (`ops.openmeteo.cell_hours`: NBM then best_match, IFS soil, D51's corrections), from the
    forecast endpoint's first hour on; None with the fallback off. It gives None (no forecast, with a warning) when
    Open-Meteo can't be reached or the request's `budget` is spent."""
    if not fallback_on():
        return None

    def fill(first_hour: datetime, last_hour: datetime, names: list[str]) -> series.FallbackHours | None:
        recent = now.date() - timedelta(days=openmeteo_source.RECENT_DAYS)  # the forecast endpoint's first day
        lo = max(first_hour, datetime(recent.year, recent.month, recent.day, tzinfo=UTC) + HOUR)
        if lo > last_hour:
            return series.FallbackHours(values={}, first_hour=None, last_hour=None)
        found = _fetch(latitude, longitude, lo, last_hour, now, budget)
        if found is None:
            return None
        values, kinds, applied = found
        n = (last_hour - first_hour) // HOUR + 1
        skip = (lo - first_hour) // HOUR
        placed = {}
        for name in names:
            row = np.full(n, np.nan)
            if name in values:
                row[skip:] = values[name]
            placed[name] = row
        covered = [k for k, kind in enumerate(kinds) if kind is not None]
        if not covered:
            return series.FallbackHours(values=placed, first_hour=None, last_hour=None, corrections=applied)
        return series.FallbackHours(
            values=placed, first_hour=lo + covered[0] * HOUR, last_hour=lo + covered[-1] * HOUR, corrections=applied
        )

    return fill


def _fetch(latitude: float, longitude: float, start: datetime, end: datetime, now: datetime, budget: FallbackBudget):
    """`ops.openmeteo.cell_hours`, or None when the request's budget is spent or Open-Meteo can't be reached (which
    spends it)."""
    if not budget.allows():
        return None
    try:
        return openmeteo.cell_hours(latitude, longitude, start, end, now)
    except openmeteo.Unavailable:
        budget.failed = True
        return None


def _archive_runs(
    latitude, longitude, runs, start, end, now, zone: str, area: AreaAsk | None, budget: FallbackBudget
) -> list[ModelRun]:
    fill_soil = _soil_filler(latitude, longitude, now, budget)
    return series.models_at_point(
        settings.DATA_DIR,
        latitude,
        longitude,
        runs,
        start,
        end,
        now=now,
        fill_soil=fill_soil,
        planting_default=False,
        zone=zone,
        area=area.at(latitude, longitude) if area is not None else None,
        fill_forecast=forecast_filler(latitude, longitude, now, budget),
    )


def _openmeteo_runs(latitude, longitude, runs, start, end, now, zone: str) -> list[ModelRun]:
    def read_days(first: date, last: date, names: list[str]) -> series.DailySeries:
        return openmeteo.point_days(latitude, longitude, first, last, names, now, zone=zone)

    return series.runs_at_point(
        read_days, latitude, longitude, runs, start, end, planting_default=False, data_dir=settings.DATA_DIR
    )


def projected_at_point(
    latitude: float,
    longitude: float,
    runs: Sequence[series.RunSpec],
    start: date,
    end: date,
    now: datetime,
    zone: str | None = None,
    area: AreaAsk | None = None,
    budget: FallbackBudget | None = None,
) -> series.Projected | None:
    """Runs carried past the forecast on each earlier archive year (D63); None for a point outside the archive (no
    projection there yet: Ben, 2026-11-03). This year's days follow `zone`; the past years' are grid days (their
    copies, `agdata.pastyears`), an hour apart at most from a point's own."""
    zone = zone or day_zone(latitude, longitude)
    first, names = series.days_needed(runs, start)
    if not in_archive(latitude, longitude, first, min(end, now.date())):
        return None
    cell = NDFD.cell_of(latitude, longitude)
    assert cell is not None
    stores = series.Stores(series.hourly_needed(names))

    budget = budget or FallbackBudget()
    fill_soil = _soil_filler(latitude, longitude, now, budget)
    fill_forecast = forecast_filler(latitude, longitude, now, budget)
    around = area.at(latitude, longitude) if area is not None else None

    def read_days(a: date, b: date, wanted: list[str]) -> series.DailySeries:
        return series.point_days(
            settings.DATA_DIR,
            *cell,
            a,
            b,
            wanted,
            now=now,
            fill_soil=fill_soil,
            stores=stores,
            zone=zone,
            area=around,
            fill_forecast=fill_forecast,
        )

    return series.projected_runs(
        read_days,
        series.past_reader(settings.DATA_DIR, *cell, stores=stores, area=around),
        latitude,
        longitude,
        runs,
        start,
        end,
        years=series.archive_years(settings.DATA_DIR),
        data_dir=settings.DATA_DIR,
    )


def model_at_point(
    latitude: float,
    longitude: float,
    model_id: str,
    start: date,
    end: date,
    now: datetime,
    biofix: date | None = None,
    planting: date | None = None,
    options: dict[str, str] | None = None,
    crop_options: dict[str, str] | None = None,
) -> ModelRun:
    """One model's three layers at a point (`models_at_point`)."""
    run = series.RunSpec(
        model_id=model_id, biofix=biofix, planting=planting, options=options or {}, crop_options=crop_options or {}
    )
    return models_at_point(latitude, longitude, [run], start, end, now)[0]
