"""A model at any US point (PLAN.md Phase 4 C, E): in the box, from the archive and the NBM forecast, with soil past
HRRR's 48 hours from Open-Meteo (D44); outside it, or before the archive, from Open-Meteo through the cell cache."""

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
    """Models' three layers at a point, each day marked observed, partial or forecast; their inputs are read once,
    all from the archive or all from Open-Meteo."""
    if planting_default:
        runs = [series.with_planting(run, latitude, longitude, start) for run in runs]
    first, _ = series.days_needed(runs, start)
    if in_archive(latitude, longitude, first, end):

        def fill_soil(first_hour: datetime, last_hour: datetime, names: list[str]) -> dict[str, np.ndarray]:
            values, _, _ = openmeteo.cell_hours(latitude, longitude, first_hour, last_hour, now)  # soil only
            return {name: values[name] for name in names if name in values}

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
        )

    def read_days(first: date, last: date, names: list[str]) -> series.DailySeries:
        return openmeteo.point_days(latitude, longitude, first, last, names, now)

    return series.runs_at_point(read_days, latitude, longitude, runs, start, end, planting_default=False)


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
