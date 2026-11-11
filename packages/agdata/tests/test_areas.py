"""Areas around a point (`agdata.areas`): which cells and weights, the average across them (gaps, wind direction),
and an area read (`series.cells_hours`, `cells_days`, the past-years copies) against its cells read one by one."""

import math
from datetime import date

import numpy as np
import pytest

from agdata import areas, pastyears, series, testing
from agdata.areas import Area
from agdata.grid import NDFD, Window

CYCLE, NOW, START = testing.CELLS_CYCLE, testing.CELLS_NOW, testing.CELLS_START

LAT, LNG = 43.17, -89.50


@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    return testing.differing_cells(tmp_path_factory.mktemp("areas"))


def test_the_cells_within_a_radius():
    found = areas.around(LAT, LNG, areas.MAX_RADIUS_KM)
    assert found is not None and found.center == NDFD.cell_of(LAT, LNG) == found.cells[0]
    assert sum(found.weights) == pytest.approx(1.0) and len(set(found.weights)) == 1
    j, i = found.center
    (lat0, lng0), (lat1, lng1) = NDFD.latlon(j, i), NDFD.latlon(j, i + 1)
    spacing = float(areas._km(float(lat0), float(lng0), np.array(lat1), np.array(lng1)))  # ~2.37 km at 43°N, not 2.54
    assert len(found.cells) == pytest.approx(math.pi * areas.MAX_RADIUS_KM**2 / spacing**2, rel=0.05)  # 145 cells
    for j, i in found.cells:
        lat, lng = NDFD.latlon(j, i)
        assert areas._km(LAT, LNG, np.array(lat), np.array(lng)) <= areas.MAX_RADIUS_KM
    small = areas.around(LAT, LNG, 1.0)
    assert small is not None and small.cells == (found.center,)  # no other cell's center within 1 km
    with pytest.raises(ValueError):
        areas.around(LAT, LNG, 20.0)


def test_center_weighting_falls_off_and_a_window_clips():
    found = areas.around(LAT, LNG, 8.0, "center")
    assert found is not None and found.weights[0] == max(found.weights)
    assert found.weights[-1] < found.weights[0] * math.exp(-1.5)  # the edge, ~2σ out
    j, i = found.center
    clipped = areas.around(LAT, LNG, 8.0, "center", window=Window(j0=j, j1=j + 10, i0=i, i1=i + 10))
    assert clipped is not None and all(cj >= j and ci >= i for cj, ci in clipped.cells)
    assert sum(clipped.weights) == pytest.approx(1.0)


def test_the_average_skips_missing_cells_and_turns_directions_as_vectors():
    cells = [(0, 0), (0, 1), (0, 2)]
    area = Area(center=(0, 0), cells=tuple(cells), weights=(0.5, 0.25, 0.25), radius_km=5, weighting="center")
    values = np.array([[10.0, 20.0, 30.0], [10.0, np.nan, 30.0], [np.nan, np.nan, np.nan]])
    found = areas.combine(values, cells, [area, (0, 1)], "air_temperature")
    assert found[0, 0] == pytest.approx(17.5) and found[1, 0] == pytest.approx((5 + 7.5) / 0.75)
    assert np.isnan(found[2, 0]) and np.isnan(found[1, 1]) and found[0, 1] == 20.0
    wind = areas.combine(np.array([[350.0, 10.0, 10.0]]), cells, [area], "wind_direction")
    assert wind[0, 0] == pytest.approx(0.0, abs=1e-9) or wind[0, 0] == pytest.approx(360.0)


def _area(cells, weights) -> Area:
    w = np.asarray(weights, dtype=float)
    return Area(center=cells[0], cells=tuple(cells), weights=tuple(w / w.sum()), radius_km=5, weighting="center")


def test_an_area_s_hours_are_its_cells_hours_averaged(mixed):
    cells = [(900, 1401), (900, 1400), (901, 1402), (901, 1401)]  # (901, 1402) has gaps
    area = _area(cells, [4, 2, 1, 1])
    end = CYCLE + 20 * series.HOUR  # into the forecast
    names = ["air_temperature", "precipitation", "wind_direction"]
    found = series.cells_hours(mixed, [area], START, end, names, now=NOW)[0]
    each = series.cells_hours(mixed, cells, START, end, names, now=NOW)
    for name in names:
        stacked = np.stack([f.values[name] for f in each], axis=1)
        np.testing.assert_allclose(found.values[name], areas.combine(stacked, cells, [area], name)[:, 0])
    assert found.kinds == each[0].kinds and np.isfinite(found.values["air_temperature"]).all()


def test_an_area_s_daily_means_are_its_cells_means_where_none_has_gaps(mixed):
    cells = [(900, 1401), (900, 1400), (901, 1401)]
    area = _area(cells, [2, 1, 1])
    first, last = date(2024, 12, 29), date(2025, 1, 3)
    found = series.cells_days(mixed, [area], first, last, ["air_temperature_mean"], now=NOW)[0]
    each = series.cells_days(mixed, cells, first, last, ["air_temperature_mean"], now=NOW)
    expected = sum(w * d.values["air_temperature_mean"] for w, d in zip(area.weights, each, strict=True))
    np.testing.assert_allclose(found.values["air_temperature_mean"], expected, rtol=1e-6)
    single = series.point_days(mixed, *cells[0], first, last, ["air_temperature_mean"], now=NOW, area=area)
    np.testing.assert_allclose(single.values["air_temperature_mean"], found.values["air_temperature_mean"])


def test_the_past_years_copies_read_an_area(mixed):
    pastyears.build(mixed, 2024)
    reader = pastyears.Reader(mixed)
    cells = [(900, 1401), (900, 1400), (901, 1402)]
    area = _area(cells, [3, 1, 1])
    names = ["air_temperature_min", "precipitation_sum"]
    first, last = date(2024, 12, 28), date(2024, 12, 31)
    found = reader.read_area(area, first, last, names)
    assert found is not None
    for name in names:
        each = [reader.read(j, i, first, last, [name]) for j, i in cells]
        stacked = np.stack([e[name] for e in each if e is not None], axis=1)
        np.testing.assert_allclose(found[name], areas.combine(stacked, cells, [area], name)[:, 0], equal_nan=True)
    assert testing.WINDOW.contains(*area.center)
