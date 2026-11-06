"""A model at any US point (PLAN.md Phase 4 C, E): in the box, from the archive and the NBM forecast, with the forecast
soil hours the run lacks from Open-Meteo (D44); outside it, or before the archive, from Open-Meteo through the cell
cache."""

from collections.abc import Sequence
from datetime import date, datetime

import numpy as np
from django.conf import settings

from agdata import series
from agdata.grid import NDFD, service_window
from agdata.store import DAILY
from agmodels.runner import ModelRun
from ops import openmeteo


def in_archive(latitude: float, longitude: float, first: date, last: date) -> bool:
    """Whether the archive covers a point and every year of first..last (each year's daily store exists)."""
    cell = NDFD.cell_of(latitude, longitude)
    if cell is None or not service_window(settings.SERVICE_BOX).contains(*cell):
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
) -> list[ModelRun]:
    """Models' three layers at a point, each day marked observed, partial or forecast, in the order of `runs`. The
    runs whose days the archive covers read it once; any that reach before it (or a point outside the box) read
    Open-Meteo once, so one model's long lookback doesn't move the others off the archive."""
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
            _archive_runs(latitude, longitude, chosen, start, end, now)
            if from_archive
            else _openmeteo_runs(latitude, longitude, chosen, start, end, now)
        )
        for k, result in zip(group, found, strict=True):
            results[k] = result
    return [r for r in results if r is not None]


def _archive_runs(latitude, longitude, runs, start, end, now) -> list[ModelRun]:
    def fill_soil(first_hour: datetime, last_hour: datetime, names: list[str]) -> dict[str, np.ndarray]:
        values, _, _ = openmeteo.cell_hours(latitude, longitude, first_hour, last_hour, now)  # soil only
        return {name: values[name] for name in names if name in values}

    return series.models_at_point(
        settings.DATA_DIR, latitude, longitude, runs, start, end, now=now, fill_soil=fill_soil, planting_default=False
    )


def _openmeteo_runs(latitude, longitude, runs, start, end, now) -> list[ModelRun]:
    def read_days(first: date, last: date, names: list[str]) -> series.DailySeries:
        return openmeteo.point_days(latitude, longitude, first, last, names, now)

    return series.runs_at_point(read_days, latitude, longitude, runs, start, end, planting_default=False)


def projected_at_point(
    latitude: float,
    longitude: float,
    runs: Sequence[series.RunSpec],
    start: date,
    end: date,
    now: datetime,
) -> series.Projected | None:
    """Runs carried past the forecast on each earlier archive year (D63); None for a point outside the archive (no
    projection there yet: Ben, 2026-11-03)."""
    first, names = series.days_needed(runs, start)
    if not in_archive(latitude, longitude, first, min(end, now.date())):
        return None
    cell = NDFD.cell_of(latitude, longitude)
    assert cell is not None
    stores = series.Stores(series.hourly_needed(names))

    def fill_soil(first_hour: datetime, last_hour: datetime, wanted: list[str]) -> dict[str, np.ndarray]:
        values, _, _ = openmeteo.cell_hours(latitude, longitude, first_hour, last_hour, now)  # soil only
        return {name: values[name] for name in wanted if name in values}

    def read_days(a: date, b: date, wanted: list[str]) -> series.DailySeries:
        return series.point_days(settings.DATA_DIR, *cell, a, b, wanted, now=now, fill_soil=fill_soil, stores=stores)

    return series.projected_runs(
        read_days,
        series.past_reader(settings.DATA_DIR, *cell, stores=stores),
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
