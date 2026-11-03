"""A model at any US point (PLAN.md Phase 4 C, E): in the box, from the archive and the NBM forecast, with soil past
HRRR's 48 hours from Open-Meteo (D44); outside it, or before the archive, from Open-Meteo through the cell cache."""

from datetime import date, datetime

import numpy as np
from django.conf import settings

from agdata import series
from agdata.grid import NDFD, service_window
from agdata.store import DAILY
from agmodels.registry import model as find_model
from agmodels.runner import ModelRun, first_day_needed
from ops import openmeteo


def in_archive(latitude: float, longitude: float, first: date, last: date) -> bool:
    """Whether the archive covers a point and every year of first..last (each year's daily store exists)."""
    cell = NDFD.cell_of(latitude, longitude)
    if cell is None or not service_window(settings.SERVICE_BOX).contains(*cell):
        return False
    # A store is renamed into place only once it's whole (`GridStore.create`), so its path existing is enough
    return all(DAILY.path(settings.DATA_DIR, year).exists() for year in range(first.year, last.year + 1))


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
    """A model's three layers at a point, each day marked observed, partial or forecast."""
    first = first_day_needed(find_model(model_id), start, biofix=biofix, planting=planting)
    kwargs = {"biofix": biofix, "planting": planting, "options": options, "crop_options": crop_options}
    if in_archive(latitude, longitude, first, end):

        def fill_soil(first_hour: datetime, last_hour: datetime, names: list[str]) -> dict[str, np.ndarray]:
            values, _, _ = openmeteo.cell_hours(latitude, longitude, first_hour, last_hour, now)  # soil only
            return {name: values[name] for name in names if name in values}

        return series.model_at_point(
            settings.DATA_DIR, latitude, longitude, model_id, start, end, now=now, fill_soil=fill_soil, **kwargs
        )

    def read_days(first: date, last: date, names: list[str]) -> series.DailySeries:
        return openmeteo.point_days(latitude, longitude, first, last, names, now)

    return series.run_at_point(read_days, latitude, longitude, model_id, start, end, **kwargs)
