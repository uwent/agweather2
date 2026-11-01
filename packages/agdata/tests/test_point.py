"""A point and the grid give the same answer (Phase 3 exit): the point path's days match the rollup's, and
every model run over the grid gives each cell what it gives that cell's series alone."""

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import daily
from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.daily import open_or_create_daily, rollup_days
from agdata.grid import NDFD, Window
from agdata.point import daily_at_point
from agdata.store import HOURLY, GridStore
from agmodels.registry import all_models

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)  # 2 x 3 cells near Madison
ZONES = ["America/Detroit", "America/Chicago"]
START = datetime(2025, 5, 1, tzinfo=UTC)
HOURS = 62 * 24
FIRST, LAST = date(2025, 5, 2), date(2025, 6, 30)
GAP = slice(30 * 24 + 7, 30 * 24 + 12)  # five hours missing on May 31


def weather(rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Two months of plausible hours over the window: daily cycles, a humid spell, rain, cold soil."""
    shape = (HOURS, *WINDOW.shape)
    h = np.arange(HOURS)[:, None, None]
    cycle = np.sin(2 * np.pi * (h - 15) / 24)
    noise = rng.normal(0, 1, shape)
    temperature = 14 + h / HOURS * 10 + 9 * cycle + noise
    dew_point = temperature - np.clip(6 + 5 * cycle + rng.normal(0, 2, shape), 0, None)
    dew_point[20 * 24 : 26 * 24] = temperature[20 * 24 : 26 * 24] - 0.3  # a humid week
    rain = np.where(rng.random(shape) < 0.05, rng.exponential(1.5, shape), 0.0)
    sun = np.clip(850 * np.sin(2 * np.pi * (h - 11) / 24), 0, None)
    out = {
        "air_temperature": temperature,
        "dew_point": dew_point,
        "relative_humidity": np.clip(100 * np.exp(0.06 * (dew_point - temperature)), 0, 100),
        "wind_speed": np.abs(3 + 2 * cycle + noise),
        "wind_gust": np.abs(5 + 3 * cycle + noise),
        "wind_direction": rng.uniform(0, 359, shape),
        "surface_pressure": 98 + 0 * noise,
        "cloud_cover": rng.uniform(0, 100, shape),
        "precipitation": rain,
        "shortwave_radiation": sun,
        "soil_temperature_4cm": temperature * 0.6 - 4,  # crosses 27 °F on cool nights
        "soil_temperature_10cm": temperature * 0.4 + 2,
        "soil_temperature_30cm": 10 + 0 * noise,
        "et0": sun / 1500,
    }
    out = {name: np.broadcast_to(values, shape).copy() for name, values in out.items()}
    for values in out.values():
        values[GAP] = np.nan
    return out


@pytest.fixture(scope="module")
def stores(tmp_path_factory):
    """Two months of hours and their rollup, built once for the module (the tests only read); column 0 is Eastern
    time, the rest Central."""
    index = np.ones(WINDOW.shape, dtype=np.uint8)
    index[:, 0] = 0
    path = tmp_path_factory.mktemp("point")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(daily, "window_timezones", lambda window: (ZONES, index))
        hourly = GridStore.create(path, HOURLY, 2025, WINDOW, VARIABLES.values())
        hourly.write(START, weather(np.random.default_rng(1)), source="test")
        rollup_days(path, WINDOW, FIRST, LAST)
    return hourly, open_or_create_daily(path, 2025, WINDOW)


def cells():
    for y, x in np.ndindex(WINDOW.shape):
        yield y, x, ZONES[0 if x == 0 else 1]


def test_point_days_match_the_rollup(stores):
    hourly, days = stores
    d0, d1 = days.index_of(FIRST), days.index_of(LAST) + 1
    # Whole blocks read once: point reads of these small stores take ~60 ms each
    t0 = hourly.index_of(START)
    hourly_block = {name: hourly.read_steps(name, t0, t0 + HOURS) for name in VARIABLES}
    daily_block = {name: days.read_steps(name, d0, d1) for name in DAILY_VARIABLES}
    for y, x, zone in cells():
        hours = {name: values[:, y, x] for name, values in hourly_block.items()}
        point = daily_at_point(START, hours, zone, FIRST, LAST)
        assert set(point) | {"et0_sum_estimate"} == set(DAILY_VARIABLES)
        for name, values in point.items():
            stored = daily_block[name][:, y, x]
            assert np.array_equal(np.isnan(values), np.isnan(stored)), (name, zone)
            # The daily store rounds to its scale
            np.testing.assert_allclose(values, stored, atol=DAILY_VARIABLES[name].scale * 0.51, err_msg=name)
    may_31 = daily_block["air_temperature_min"][(date(2025, 5, 31) - FIRST).days, 0, 1]
    assert np.isnan(may_31)  # 19 of 24 hours is too few (D25)


def test_points_in_one_zone_roll_up_together(stores):
    hourly, _ = stores
    t0 = hourly.index_of(START)
    block = {name: hourly.read_steps(name, t0, t0 + HOURS) for name in VARIABLES}
    zone = next(zone for _, _, zone in cells())
    together = daily_at_point(START, {name: values[:, 0, :] for name, values in block.items()}, zone, FIRST, LAST)
    for x in range(WINDOW.shape[1]):
        alone = daily_at_point(START, {name: values[:, 0, x] for name, values in block.items()}, zone, FIRST, LAST)
        for name, values in alone.items():
            assert together[name].shape == (len(values), WINDOW.shape[1])
            np.testing.assert_allclose(together[name][:, x], values, rtol=1e-12, err_msg=name)  # nanmean's order


def test_every_model_gives_a_cell_what_it_gives_its_series(stores):
    _, days = stores
    d0, d1 = days.index_of(FIRST), days.index_of(LAST) + 1
    dates = np.arange(np.datetime64(FIRST), np.datetime64(LAST) + np.timedelta64(1, "D"))
    day_of_year = (dates - dates.astype("datetime64[Y]")).astype(int) + 1.0
    lat, _ = NDFD.window_latlon(WINDOW)
    for model_id, m in all_models().items():
        names = [q.name for q in m.SPEC.inputs]
        grid = {name: days.read_steps(name, d0, d1) for name in names}
        context = {"day_of_year": day_of_year[:, None, None], "latitude": lat, "year": np.array(2025.0)}
        grid |= {name: context[name] for name in m.SPEC.context}
        grid_out = m.outputs(grid)
        grid_risk = None if m.SPEC.risk is None else m.risk(grid_out)
        for y, x, _ in cells():
            point = {name: values[:, y, x] for name, values in grid.items() if name in names}
            context = {"day_of_year": day_of_year, "latitude": lat[y, x], "year": np.array(2025.0)}
            point |= {name: context[name] for name in m.SPEC.context}
            out = m.outputs(point)
            for name, values in out.items():
                cell = np.asarray(grid_out[name])[(slice(None), y, x)]
                np.testing.assert_allclose(values, cell, rtol=1e-6, atol=1e-9, err_msg=f"{model_id} {name}")
            if grid_risk is not None:
                np.testing.assert_array_equal(m.risk(out), np.asarray(grid_risk)[:, y, x], err_msg=model_id)


def test_hours_outside_the_series_are_missing():
    start = datetime(2025, 7, 1, 5, tzinfo=UTC)  # the first Central hour of July 1 ends at 06:00Z
    hours = {"air_temperature": np.full(48, 20.0), "precipitation": np.zeros(48)}
    point = daily_at_point(start, hours, "America/Chicago", date(2025, 6, 30), date(2025, 7, 2))
    assert np.isnan(point["air_temperature_max"][0])  # no hours on June 30
    assert point["air_temperature_max"][1] == 20.0 and point["precipitation_sum"][1] == 0.0
    assert np.isnan(point["precipitation_sum"][2])  # July 2 runs past the series: a sum needs every hour
    assert np.isnan(point["wind_speed_max"][1])  # not given


def test_hours_start_on_the_hour():
    with pytest.raises(ValueError, match="on the hour"):
        daily_at_point(START + timedelta(minutes=30), {}, "America/Chicago", FIRST, FIRST)
