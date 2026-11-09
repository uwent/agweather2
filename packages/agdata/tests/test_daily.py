from datetime import UTC, date, datetime, timedelta

import numpy as np

from agdata.catalog import VARIABLES
from agdata.daily import cell_timezones, on_grid_days, open_or_create_daily, rollup_days
from agdata.grid import Window
from agdata.store import HOURLY, GridStore
from agdata.timezones import GRID_ZONE, day_bounds, evening_bounds, overnight_bounds

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)  # 2 x 3 cells near Madison
HOUR = timedelta(hours=1)


def hourly_store(tmp_path, year, start, hours, temperature=None, precip=1.0):
    """Hours from `start`: temperature counts up 0.1 °C an hour from 0 at `start` unless given; precip 1 mm."""
    store = GridStore.create(tmp_path, HOURLY, year, WINDOW, VARIABLES.values())
    n = np.arange(hours, dtype=float)
    temps = (n * 0.1 if temperature is None else np.full(hours, temperature))[:, None, None]
    store.write(start, {"air_temperature": np.broadcast_to(temps, (hours, *WINDOW.shape))}, source="test")
    store.write(start, {"precipitation": np.full((hours, *WINDOW.shape), precip)}, source="test")
    return store


def read(tmp_path, name, day):
    store = open_or_create_daily(tmp_path, day.year, WINDOW)
    return store.read_block(name, store.index_of(day))


def test_day_bounds_follow_the_zones_clock():
    # Grid days are CST all year: readings 07:00Z .. 06:00Z (06:00 to 06:00 UTC), 24 of them on every day
    assert day_bounds(date(2025, 7, 1), GRID_ZONE) == (
        datetime(2025, 7, 1, 7, tzinfo=UTC),
        datetime(2025, 7, 2, 6, tzinfo=UTC),
    )
    # A point's local days follow daylight saving (`day_basis=local`)
    assert day_bounds(date(2025, 7, 1), "America/Chicago") == (
        datetime(2025, 7, 1, 6, tzinfo=UTC),
        datetime(2025, 7, 2, 5, tzinfo=UTC),
    )
    for day, zone, hours in [
        (date(2025, 3, 9), GRID_ZONE, 24),
        (date(2025, 11, 2), GRID_ZONE, 24),
        (date(2025, 3, 9), "America/Chicago", 23),
        (date(2025, 11, 2), "America/Chicago", 25),
        (date(2025, 1, 15), "America/Detroit", 24),
    ]:
        begin, end = day_bounds(day, zone)
        assert (end - begin) // HOUR + 1 == hours


def test_windows_hold_the_readings_after_their_start_through_their_end():
    day = date(2025, 7, 2)
    # 6 pm CST the evening before to 6 pm: readings 19:00 .. 18:00 CST (01:00Z .. 00:00Z)
    assert evening_bounds(day, GRID_ZONE) == (datetime(2025, 7, 2, 1, tzinfo=UTC), datetime(2025, 7, 3, 0, tzinfo=UTC))
    # Noon to noon: readings 13:00 .. 12:00 CST (19:00Z .. 18:00Z)
    assert overnight_bounds(day, GRID_ZONE) == (
        datetime(2025, 7, 1, 19, tzinfo=UTC),
        datetime(2025, 7, 2, 18, tzinfo=UTC),
    )


def test_every_cell_shares_the_grid_day(tmp_path):
    start = datetime(2025, 7, 1, tzinfo=UTC)
    hourly_store(tmp_path, 2025, start, 72)
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 1))
    # Readings 07:00Z .. 06:00Z the next day, in every cell (the window reaches into Eastern time nowhere here, but
    # the rule is the same for cells that do)
    np.testing.assert_allclose(read(tmp_path, "air_temperature_min", date(2025, 7, 1)), 0.7)
    np.testing.assert_allclose(read(tmp_path, "air_temperature_max", date(2025, 7, 1)), 3.0)
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 7, 1)), 24)


def test_grid_days_have_24_hours_across_daylight_saving(tmp_path):
    hourly_store(tmp_path, 2025, datetime(2025, 1, 1, tzinfo=UTC), 8760, temperature=5.0)
    rollup_days(tmp_path, WINDOW, date(2025, 3, 9), date(2025, 3, 9))
    rollup_days(tmp_path, WINDOW, date(2025, 11, 2), date(2025, 11, 2))
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 3, 9)), 24)
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 11, 2)), 24)


def test_incomplete_days_are_missing(tmp_path):
    start = datetime(2025, 7, 1, 7, tzinfo=UTC)  # the grid day's first reading
    store = hourly_store(tmp_path, 2025, start - timedelta(days=1), 96, temperature=20.0)
    store.write(start, {"air_temperature": np.full((4, *WINDOW.shape), np.nan)}, source="test")  # 20 hours left
    store.write(start + 10 * HOUR, {"precipitation": np.full((1, *WINDOW.shape), np.nan)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 2))
    np.testing.assert_allclose(read(tmp_path, "air_temperature_mean", date(2025, 7, 1)), 20)
    assert np.isnan(read(tmp_path, "precipitation_sum", date(2025, 7, 1))).all()  # one hour short
    store.write(start + 4 * HOUR, {"air_temperature": np.full((1, *WINDOW.shape), np.nan)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 1))
    assert np.isnan(read(tmp_path, "air_temperature_mean", date(2025, 7, 1))).all()  # 19 hours
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 7, 2)), 24)


def test_a_day_without_values_isnt_marked_rolled_up(tmp_path):
    start = datetime(2025, 7, 1, 7, tzinfo=UTC)
    hourly_store(tmp_path, 2025, start, 30, temperature=20.0)  # July 1 and 6 hours of July 2
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 3))
    store = open_or_create_daily(tmp_path, 2025, WINDOW)
    t = store.index_of(date(2025, 7, 1))
    assert store.sources("air_temperature_min")[t : t + 3] == ["derived", None, None]
    assert store.sources("precipitation_sum")[t : t + 3] == ["derived", None, None]


def test_new_years_eve_reads_the_next_years_hours(tmp_path):
    hourly_store(tmp_path, 2025, datetime(2025, 12, 31, tzinfo=UTC), 24)
    rollup_days(tmp_path, WINDOW, date(2025, 12, 31), date(2025, 12, 31))
    assert np.isnan(read(tmp_path, "precipitation_sum", date(2025, 12, 31))).all()  # 2026's hours missing
    hourly_store(tmp_path, 2026, datetime(2026, 1, 1, tzinfo=UTC), 24)
    rollup_days(tmp_path, WINDOW, date(2025, 12, 31), date(2026, 1, 1))
    np.testing.assert_allclose(read(tmp_path, "precipitation_sum", date(2025, 12, 31)), 24)
    assert read(tmp_path, "precipitation_sum", date(2026, 1, 1)).shape == WINDOW.shape


def test_a_year_without_hours_gets_no_daily_store(tmp_path):
    """A backfill rolls up from the day before its first: December 31 of the year before the archive isn't made."""
    hourly_store(tmp_path, 2016, datetime(2016, 1, 1, tzinfo=UTC), 48)
    rollup_days(tmp_path, WINDOW, date(2015, 12, 31), date(2016, 1, 1))
    assert not (tmp_path / "daily" / "2015.zarr").exists()
    assert (tmp_path / "daily" / "2016.zarr").exists()


def test_a_new_store_is_on_grid_days(tmp_path):
    store = open_or_create_daily(tmp_path, 2025, WINDOW)
    zones, index = cell_timezones(store)
    assert zones == [GRID_ZONE] and (index == 0).all() and on_grid_days(store)


def test_a_day_missing_et0_hours_gets_an_estimate_beside_the_raw_total(tmp_path):
    start = datetime(2025, 7, 1, tzinfo=UTC)
    store = hourly_store(tmp_path, 2025, start, 96, temperature=25.0)
    shape = (96, *WINDOW.shape)
    store.write(
        start,
        {
            "dew_point": np.full(shape, 15.0),
            "wind_speed": np.full(shape, 3.0),
            "surface_pressure": np.full(shape, 98.5),
            "shortwave_radiation": np.full(shape, 0.0),  # stays dark, so the missing hour's ET0 is small
            "et0": np.full(shape, 0.1),
        },
        source="test",
    )
    store.write(start + 31 * HOUR, {"et0": np.full((1, *WINDOW.shape), np.nan)}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 1), date(2025, 7, 2))
    assert np.isnan(read(tmp_path, "et0_sum", date(2025, 7, 2))).all()  # 07:00Z, July 2's first reading
    estimate = read(tmp_path, "et0_sum_estimate", date(2025, 7, 2))
    assert np.all((estimate > 2.3) & (estimate < 2.6))  # 23 × 0.1 plus the estimated hour
    np.testing.assert_allclose(read(tmp_path, "et0_sum", date(2025, 7, 1)), 2.4)
    assert np.isnan(read(tmp_path, "et0_sum_estimate", date(2025, 7, 1))).all()  # only where the raw is missing


def test_grid_features_match_the_point_path(tmp_path):
    from zoneinfo import ZoneInfo

    from agmodels import features
    from agmodels.weather import relative_humidity_percent

    start = datetime(2025, 7, 1, tzinfo=UTC)
    n = 96
    hour = np.arange(n)
    temperature = np.round(20 + 8 * np.sin(2 * np.pi * (hour - 15) / 24), 1)  # a daily cycle, at stored precision
    dew_point = 17 + 0 * hour  # humid at night, dry by day
    soil = {  # one depth crossing 27 °F (−2.8 °C) each day, one always above
        "soil_temperature_4cm": np.round(-3 + 1.5 * np.sin(2 * np.pi * hour / 24), 1),
        "soil_temperature_10cm": np.full(n, -1.0),
        "soil_temperature_30cm": np.full(n, -5.0),  # so 8 in, between them, is below 27 °F
    }
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())
    grid = (n, *WINDOW.shape)
    store.write(start, {"air_temperature": np.broadcast_to(temperature[:, None, None], grid)}, source="test")
    store.write(start, {"dew_point": np.broadcast_to(dew_point[:, None, None], grid)}, source="test")
    store.write(start, {k: np.broadcast_to(v[:, None, None], grid) for k, v in soil.items()}, source="test")
    rollup_days(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 3))

    # The point path over the same hours, on the grid's clock (CST)
    local = np.array(
        [(start + k * HOUR).astimezone(ZoneInfo(GRID_ZONE)).replace(tzinfo=None) for k in range(n)],
        dtype="datetime64[h]",
    )
    rh = relative_humidity_percent(temperature, dew_point)
    days, point = features.daily_features(
        local,
        temperature,
        rh,
        np.zeros(n),
        soil_4cm_c=soil["soil_temperature_4cm"],
        soil_10cm_c=soil["soil_temperature_10cm"],
        soil_30cm_c=soil["soil_temperature_30cm"],
    )
    for day in (date(2025, 7, 2), date(2025, 7, 3)):
        k = [str(d) for d in days].index(str(day))
        for name in (
            "hours_rh_over_90",
            "hours_temperature_over_20c",
            "hours_rh_over_80_from_6pm",
            "hours_rh_over_90_night",
            "hours_rh_over_90_7pm_to_6am",
            "temperature_mean_rh_over_80_from_6pm",
            "air_temperature_min_overnight",
            "hours_soil_4cm_below_27f",
            "hours_soil_10cm_below_27f",
            "hours_soil_8in_below_27f",
        ):
            grid_value = read(tmp_path, name, day)
            np.testing.assert_allclose(grid_value, point[name][k], atol=0.05, err_msg=f"{name} {day}")
    assert read(tmp_path, "hours_rh_over_80_from_6pm", date(2025, 7, 2))[0, 1] > 0  # the test has humid hours
    assert 0 < read(tmp_path, "hours_soil_4cm_below_27f", date(2025, 7, 2))[0, 1] < 24
    assert read(tmp_path, "hours_soil_10cm_below_27f", date(2025, 7, 2))[0, 1] == 0
    assert read(tmp_path, "hours_soil_8in_below_27f", date(2025, 7, 2))[0, 1] == 24


def test_a_store_from_before_new_features_opens_with_them_stale(tmp_path):
    from dataclasses import replace

    from agdata.catalog import DAILY_FEATURES, DAILY_VARIABLES
    from agdata.store import DAILY

    old = [v for name, v in DAILY_VARIABLES.items() if name not in DAILY_FEATURES]
    GridStore.create(tmp_path, DAILY, 2025, WINDOW, old)
    store = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values(), add_missing=True)
    assert store.stale == set(DAILY_FEATURES)
    store.mark_current(DAILY_FEATURES)
    assert GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values()).stale == set()
    bumped = [
        replace(v, version=v.version + 1) if v.name == "hours_rh_over_90" else v for v in DAILY_VARIABLES.values()
    ]
    assert GridStore.open(tmp_path, DAILY, 2025, bumped).stale == {"hours_rh_over_90"}
