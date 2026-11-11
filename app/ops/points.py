"""A model at any US point (PLAN.md Phase 4 C, E): in the box, from the archive and the NBM forecast, with the forecast
soil hours the run lacks from Open-Meteo (D44); outside it, or before the archive, from Open-Meteo through the cell
cache."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime

import numpy as np
from django.conf import settings

from agdata import areas, series
from agdata.areas import Area, Place, Weighting
from agdata.grid import NDFD, service_window
from agdata.store import DAILY
from agdata.timezones import DayBasis, basis_zone
from agmodels.runner import ModelRun
from ops import openmeteo


@dataclass(frozen=True, kw_only=True)
class AreaAsk:
    """A request's `radius` (in km) and `weighting`: each point's weather is the area's around it
    (`agdata.areas`)."""

    radius_km: float
    weighting: Weighting = "equal"

    def at(self, latitude: float, longitude: float) -> Area:
        found = areas.around(
            latitude, longitude, self.radius_km, self.weighting, window=service_window(settings.SERVICE_BOX)
        )
        if found is None:
            raise ValueError(f"({latitude}, {longitude}) is off the grid")
        return found


def place_at(latitude: float, longitude: float, area: AreaAsk | None) -> Place:
    """The cell a point reads, or the area around it."""
    if area is not None:
        return area.at(latitude, longitude)
    cell = NDFD.cell_of(latitude, longitude)
    if cell is None:
        raise ValueError(f"({latitude}, {longitude}) is off the grid")
    return cell


def in_box(latitude: float, longitude: float) -> bool:
    cell = NDFD.cell_of(latitude, longitude)
    return cell is not None and service_window(settings.SERVICE_BOX).contains(*cell)


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
) -> list[ModelRun]:
    """Models' three layers at a point (on the weather of `area` around it, if given), each day marked observed,
    partial or forecast, in the order of `runs`. The runs whose days the archive covers read it once; any that reach
    before it (or a point outside the box) read Open-Meteo once, so one model's long lookback doesn't move the others
    off the archive. Days follow `zone`'s clock (default `day_zone`'s)."""
    zone = zone or day_zone(latitude, longitude)
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
            _archive_runs(latitude, longitude, chosen, start, end, now, zone, area)
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
) -> list[list[ModelRun]]:
    """`models_at_point` (without typical planting dates) at each point, with its own runs (`runs[k]`) on its own
    zone's days (`zones[k]`): the runs the archive covers, at every point, on one read of their cells
    (`series.cells_days`); the rest from Open-Meteo a point at a time. Each point's results are the same as its own
    request's, but for the order of a mean's sums (~1e-16) and `sources`, which name the sources of the hours read
    for every point's runs (from the earliest day any of them needs)."""
    results: list[list[ModelRun | None]] = [[None] * len(own) for own in runs]
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
            fill_soil=[_soil_filler(*sites[k], now) for k in batched],
            zones=[zones[k] for k in batched],
        )
        for k, days in zip(batched, found, strict=True):
            own = series.runs_at_point(
                _slicer(days), *sites[k], [runs[k][m] for m in chosen[k]], start, end, planting_default=False
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


def _soil_filler(latitude: float, longitude: float, now: datetime):
    """Forecast soil hours the run lacks, from Open-Meteo's ECMWF IFS through the cell cache (D44)."""

    def fill_soil(first_hour: datetime, last_hour: datetime, names: list[str]) -> dict[str, np.ndarray]:
        values, _, _ = openmeteo.cell_hours(latitude, longitude, first_hour, last_hour, now)  # soil only
        return {name: values[name] for name in names if name in values}

    return fill_soil


def _archive_runs(latitude, longitude, runs, start, end, now, zone: str, area: AreaAsk | None) -> list[ModelRun]:
    fill_soil = _soil_filler(latitude, longitude, now)
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
    )


def _openmeteo_runs(latitude, longitude, runs, start, end, now, zone: str) -> list[ModelRun]:
    def read_days(first: date, last: date, names: list[str]) -> series.DailySeries:
        return openmeteo.point_days(latitude, longitude, first, last, names, now, zone=zone)

    return series.runs_at_point(read_days, latitude, longitude, runs, start, end, planting_default=False)


def projected_at_point(
    latitude: float,
    longitude: float,
    runs: Sequence[series.RunSpec],
    start: date,
    end: date,
    now: datetime,
    zone: str | None = None,
    area: AreaAsk | None = None,
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

    fill_soil = _soil_filler(latitude, longitude, now)
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
