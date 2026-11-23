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

    def archive_run(data_dir, lat, lon, runs, start, end, now, fill_soil, **kwargs):
        calls.update(data_dir=data_dir, runs=runs, kwargs=kwargs, fill_soil=fill_soil)
        return ["archive result"]

    monkeypatch.setattr(points.series, "models_at_point", archive_run)
    monkeypatch.setattr(
        points.series, "runs_at_point", lambda *a, **k: pytest.fail("used Open-Meteo for the whole run")
    )
    asked = []

    def cell_hours(lat, lon, first, last, now):
        asked.append((lat, lon, first, last, now))
        return {"soil_temperature_10cm": np.array([1.0, 2.0]), "air_temperature": np.array([9.0, 9.0])}, [], ()

    monkeypatch.setattr(points.openmeteo, "cell_hours", cell_hours)
    result = points.model_at_point(
        *MADISON, "custom-degree-days", date(2025, 7, 5), date(2025, 7, 10), NOW, biofix=date(2025, 7, 1)
    )
    assert result == "archive result"
    assert calls["data_dir"] == archive
    assert [(run.model_id, run.biofix) for run in calls["runs"]] == [("custom-degree-days", date(2025, 7, 1))]
    first, last = datetime(2025, 7, 1, tzinfo=UTC), datetime(2025, 7, 2, tzinfo=UTC)
    filled = calls["fill_soil"](first, last, ["soil_temperature_10cm", "snow_depth"])
    assert list(filled) == ["soil_temperature_10cm"]  # only the names asked for, and only those Open-Meteo has
    np.testing.assert_array_equal(filled["soil_temperature_10cm"], [1.0, 2.0])
    assert asked == [(*MADISON, first, last, NOW)]


def test_a_point_before_the_archive_runs_wholly_on_open_meteo(archive, monkeypatch):
    monkeypatch.setattr(points.series, "models_at_point", lambda *a, **k: pytest.fail("used the archive"))
    seen = {}

    def runs_at_point(read_days, lat, lon, runs, start, end, **kwargs):
        seen.update(lat=lat, runs=runs)
        monkeypatch.setattr(points.openmeteo, "point_days", lambda *args, **kwargs: ("days", args, kwargs))
        return [read_days(date(2024, 5, 1), date(2024, 5, 3), ["air_temperature_max"])]

    monkeypatch.setattr(points.series, "runs_at_point", runs_at_point)
    days = points.model_at_point(
        *MADISON, "custom-degree-days", date(2024, 5, 1), date(2024, 6, 1), NOW, biofix=date(2024, 5, 1)
    )
    asked = (*MADISON, date(2024, 5, 1), date(2024, 5, 3), ["air_temperature_max"], NOW)
    assert days == ("days", asked, {"zone": "Etc/GMT+6"})  # in the box, Open-Meteo's days are grid days too (D74)
    assert [(run.model_id, run.biofix) for run in seen["runs"]] == [("custom-degree-days", date(2024, 5, 1))]


def test_runs_reaching_before_the_archive_read_open_meteo_and_the_rest_the_archive(archive, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        points,
        "_archive_runs",
        lambda lat, lon, runs, *a: seen.setdefault("archive", runs) and [f"a:{r.model_id}" for r in runs],
    )
    monkeypatch.setattr(
        points,
        "_openmeteo_runs",
        lambda lat, lon, runs, *a: seen.setdefault("om", runs) and [f"o:{r.model_id}" for r in runs],
    )
    runs = [points.series.RunSpec(model_id=m) for m in ("tar-spot", "potato-volunteer", "custom-degree-days")]
    runs[1] = points.series.RunSpec(model_id="potato-volunteer", biofix=date(2024, 11, 1))  # last winter's start
    found = points.models_at_point(*MADISON, runs, date(2025, 7, 1), date(2025, 7, 10), NOW, planting_default=False)
    assert found == ["a:tar-spot", "o:potato-volunteer", "a:custom-degree-days"]  # in the order asked
    assert [r.model_id for r in seen["om"]] == ["potato-volunteer"]  # its biofix is before the archive


def test_under_the_launch_coverage_a_point_in_its_window_but_outside_its_mask_is_outside(settings):
    """D105: Toronto lies inside `upper_midwest`'s window but outside its mask, so it's outside the box (Open-Meteo,
    its own days); Madison and Windsor, within 50 km of Michigan, are inside."""
    settings.SERVICE_BOX = "upper_midwest"
    toronto, windsor = (43.65, -79.38), (42.31, -83.04)
    assert service_window("upper_midwest").contains(*points.NDFD.cell_of(*toronto))  # type: ignore[misc]
    assert not points.in_box(*toronto) and points.day_basis(*toronto) == "local"
    assert points.in_box(*MADISON) and points.in_box(*windsor)
    covered = points.coverage.of("upper_midwest")
    r = next(r for r in range(covered.mask.shape[0]) if covered.mask[r].any() and np.argmax(covered.mask[r]) >= 20)
    edge = (covered.window.j0 + r, covered.window.i0 + int(np.argmax(covered.mask[r])))  # on the mask's western edge
    lat, lng = (float(v) for v in points.NDFD.latlon(*edge))
    area = points.AreaAsk(radius_km=15).at(lat, lng)  # an area takes only covered cells
    assert len(area.cells) > 1 and all(covered.contains(*c) for c in area.cells)
