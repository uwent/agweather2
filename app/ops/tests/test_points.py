from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata.daily import open_or_create_daily
from agdata.grid import service_window
from ops import points

BOX = "43.05,-89.45,43.1,-89.4"
MADISON = (43.07, -89.42)
FLORIDA = (28.5, -81.4)
NOW = datetime(2025, 7, 15, 18, tzinfo=UTC)


@pytest.fixture
def archive(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    settings.SERVICE_BOX = BOX
    open_or_create_daily(tmp_path, 2025, service_window(BOX))
    return tmp_path


def test_a_point_is_in_the_archive_when_it_is_in_the_box_and_every_year_has_a_daily_store(archive):
    assert points.in_archive(*MADISON, date(2025, 6, 1), date(2025, 7, 1))
    assert not points.in_archive(*MADISON, date(2024, 12, 1), date(2025, 7, 1))  # 2024 has no store
    assert not points.in_archive(*MADISON, date(2025, 6, 1), date(2026, 1, 5))  # nor 2026


def test_a_point_outside_the_box_or_the_grid_is_not_in_the_archive(archive):
    assert not points.in_archive(*FLORIDA, date(2025, 6, 1), date(2025, 7, 1))
    assert not points.in_archive(48.0, 2.0, date(2025, 6, 1), date(2025, 7, 1))  # Paris: off the NDFD grid


def test_an_archive_point_runs_on_the_archive_with_open_meteo_filling_only_soil(archive, monkeypatch):
    calls = {}

    def archive_run(data_dir, lat, lon, model_id, start, end, now, fill_soil, **kwargs):
        calls.update(data_dir=data_dir, model_id=model_id, kwargs=kwargs, fill_soil=fill_soil)
        return "archive result"

    monkeypatch.setattr(points.series, "model_at_point", archive_run)
    monkeypatch.setattr(points.series, "run_at_point", lambda *a, **k: pytest.fail("used Open-Meteo for the whole run"))
    asked = []

    def cell_hours(lat, lon, first, last, now):
        asked.append((lat, lon, first, last, now))
        return {"soil_temperature_10cm": np.array([1.0, 2.0]), "air_temperature": np.array([9.0, 9.0])}, [], ()

    monkeypatch.setattr(points.openmeteo, "cell_hours", cell_hours)
    result = points.model_at_point(
        *MADISON, "degree-days", date(2025, 7, 5), date(2025, 7, 10), NOW, biofix=date(2025, 7, 1)
    )
    assert result == "archive result"
    assert calls["data_dir"] == archive and calls["model_id"] == "degree-days"
    assert calls["kwargs"]["biofix"] == date(2025, 7, 1)
    first, last = datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 2, tzinfo=UTC)
    filled = calls["fill_soil"](first, last, ["soil_temperature_10cm", "snow_depth"])
    assert list(filled) == ["soil_temperature_10cm"]  # only the names asked for, and only those Open-Meteo has
    np.testing.assert_array_equal(filled["soil_temperature_10cm"], [1.0, 2.0])
    assert asked == [(*MADISON, first, last, NOW)]


def test_a_point_before_the_archive_runs_wholly_on_open_meteo(archive, monkeypatch):
    monkeypatch.setattr(points.series, "model_at_point", lambda *a, **k: pytest.fail("used the archive"))
    seen = {}

    def run_at_point(read_days, lat, lon, model_id, start, end, **kwargs):
        seen.update(lat=lat, model_id=model_id, kwargs=kwargs)
        monkeypatch.setattr(points.openmeteo, "point_days", lambda *args: ("days", args))
        return read_days(date(2024, 5, 1), date(2024, 5, 3), ["air_temperature_max"])

    monkeypatch.setattr(points.series, "run_at_point", run_at_point)
    days = points.model_at_point(
        *MADISON, "degree-days", date(2024, 5, 1), date(2024, 6, 1), NOW, biofix=date(2024, 5, 1)
    )
    assert days == ("days", (*MADISON, date(2024, 5, 1), date(2024, 5, 3), ["air_temperature_max"], NOW))
    assert seen["model_id"] == "degree-days" and seen["kwargs"]["biofix"] == date(2024, 5, 1)
