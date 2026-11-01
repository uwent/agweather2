from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from agdata import ingest
from agdata.grid import NDFD, Window
from agdata.ingest import (
    HOURLY_VARIABLES,
    SOIL,
    Hour,
    blocks,
    era5land_through,
    hour_runs,
    ingest_block,
    open_or_create_hourly,
    stale_hours,
    write_soil,
)
from agdata.sources import era5land
from agmodels.weather import solar_elevation_deg

WINDOW = Window(j0=900, j1=904, i0=1400, i1=1405)  # 4 x 5 cells near Madison
START = datetime(2025, 7, 15, 6, tzinfo=UTC)  # 1 am CDT


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    monkeypatch.setattr(ingest, "RETRY_SECONDS", 0)


def fake_fetch(missing_hour: int | None = None, spike: tuple[int, int, int] | None = None):
    lat, lon = NDFD.window_latlon(WINDOW)

    def fetch(when, window, session):
        n = int((when - START) / timedelta(hours=1))
        if n == missing_hour:
            raise ConnectionError("simulated outage")
        local = (when.hour - 5) % 24
        temp = np.full(window.shape, 22 + 8 * np.sin((local - 9) / 24 * 2 * np.pi))
        if spike and spike[0] == n:
            temp[spike[1], spike[2]] += 25
        mid = np.datetime64(when.replace(tzinfo=None) - timedelta(minutes=30), "s")
        sun = solar_elevation_deg(mid, lat, lon)
        values = {
            "air_temperature": temp,
            "dew_point": temp - 8,
            "wind_speed": np.full(window.shape, 3.0),
            "wind_gust": np.full(window.shape, 6.0),
            "wind_direction": np.full(window.shape, 180.0),
            "surface_pressure": np.full(window.shape, 98.0),
            "cloud_cover": np.full(window.shape, 20.0),
            "precipitation": np.full(window.shape, 2.0 if n == 10 else 0.0),
            "shortwave_radiation_hrrr": np.clip(800 * np.sin(np.radians(np.maximum(sun, 0))), 0, None),
            "soil_temperature_4cm": temp - 2,
            "soil_temperature_10cm": temp - 4,
        }
        sources = {name: ("hrrr" if name.startswith(("shortwave", "soil")) else "urma") for name in values}
        return Hour(values=values, sources=sources)

    return fetch


def test_a_day_through_qc_derivation_and_the_store(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    report = ingest_block(store, START, 24, fetch=fake_fetch(missing_hour=5, spike=(12, 1, 1)), workers=4)

    t0 = store.index_of(START)
    temp = store.read_point("air_temperature", 901, 1401, t0, t0 + 24)
    assert np.isnan(temp[[5, 12]]).all() and np.isfinite(np.delete(temp, [5, 12])).all()  # the gap and the spike
    assert report.missing["air_temperature"] == 1
    assert report.spikes["air_temperature"] == 1

    rain = store.read_point("precipitation", 901, 1401, t0, t0 + 24)
    assert np.isnan(rain[5])  # precip gaps are never filled
    assert rain[10] == pytest.approx(2.0) and np.nansum(rain) == pytest.approx(2.0)

    rh = store.read_point("relative_humidity", 900, 1400, t0, t0 + 24)
    assert 50 < np.nanmean(rh) < 65
    et0 = store.read_point("et0", 900, 1400, t0, t0 + 24)
    assert 3 < np.nansum(et0) < 8  # mm for a sunny July day

    sources = store.sources("air_temperature")[t0 : t0 + 24]
    assert sources.count("urma") == 23 and sources[5] is None
    assert store.sources("shortwave_radiation")[t0] == "hrrr"
    assert store.sources("et0")[t0 + 12] == "derived"


def test_reopening_checks_the_window(tmp_path):
    open_or_create_hourly(tmp_path, 2025, WINDOW)
    assert open_or_create_hourly(tmp_path, 2025, WINDOW).window == WINDOW
    with pytest.raises(ValueError):
        open_or_create_hourly(tmp_path, 2025, Window(j0=0, j1=4, i0=0, i1=5))


def test_month_blocks():
    assert blocks(datetime(2024, 12, 20, tzinfo=UTC), datetime(2025, 2, 10, tzinfo=UTC)) == [
        (datetime(2024, 12, 20, tzinfo=UTC), 12 * 24),
        (datetime(2025, 1, 1, tzinfo=UTC), 31 * 24),
        (datetime(2025, 2, 1, tzinfo=UTC), 9 * 24),
    ]
    assert [hours for _, hours in blocks(datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 2, 1, tzinfo=UTC), 10)] == [
        240,
        240,
        240,
        24,
    ]


def test_a_failing_hour_is_retried_then_left_missing(tmp_path):
    calls = {"n": 0}
    good = fake_fetch()

    def flaky(when, window, session):
        if when == START + timedelta(hours=2):
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("reset")
        if when == START + timedelta(hours=4):
            raise ConnectionError("down")
        return good(when, window, session)

    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    report = ingest_block(store, START, 6, fetch=flaky, workers=1)
    assert calls["n"] == 3  # recovered on the third try
    assert report.failed == [START + timedelta(hours=4)]


def test_a_refetch_that_fails_keeps_what_the_store_had(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    ingest_block(store, START, 6, fetch=fake_fetch(), workers=1)
    good = fake_fetch()

    def partial(when, window, session):
        if when == START + timedelta(hours=1):
            raise ConnectionError("down")  # the whole hour fails
        hour = good(when, window, session)
        hour.sources.pop("precipitation")  # and precip isn't out for any hour
        hour.values.pop("precipitation")
        return hour

    t0 = store.index_of(START)
    kept = store.read_steps("air_temperature", t0, t0 + 6)
    rain = store.read_steps("precipitation", t0, t0 + 6)
    report = ingest_block(store, START, 6, fetch=partial, workers=1)
    assert report.failed == [START + timedelta(hours=1)]
    np.testing.assert_allclose(store.read_steps("air_temperature", t0, t0 + 6), kept)
    np.testing.assert_allclose(store.read_steps("precipitation", t0, t0 + 6), rain)
    assert store.sources("air_temperature")[t0 + 1] == "urma"
    assert np.isfinite(store.read_steps("et0", t0 + 1, t0 + 2)).all()  # derived from the kept hour


def test_progress_counts_every_hour_including_failed_ones(tmp_path):
    def fetch(when, window, session):
        if when == START + timedelta(hours=1):
            raise ConnectionError("down")
        return fake_fetch()(when, window, session)

    seen = []
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    ingest_block(store, START, 4, fetch=fetch, workers=2, progress=seen.append)
    assert sorted(seen) == [1, 2, 3, 4]


def test_every_hourly_variable_is_in_the_store(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    assert set(store.variables) == {v.name for v in HOURLY_VARIABLES}


def test_stale_hours_are_missing_incomplete_or_rtma_with_urma_out(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    shape = (1, *WINDOW.shape)
    for n, analysis in enumerate(["urma", "rtma", "rtma", "urma", None]):
        when = START + timedelta(hours=n)
        if analysis:
            store.write(when, {"air_temperature": np.zeros(shape)}, source=analysis)
        store.write(when, {"shortwave_radiation": np.zeros(shape)}, source="hrrr")
        if n != 3:
            store.write(when, {"precipitation": np.zeros(shape)}, source=analysis or "rtma")
    published = {START + timedelta(hours=2)}  # URMA is out for hour 2, not hour 1
    asked = []

    def urma_published(when):
        asked.append(when)
        return when in published

    stale = stale_hours(tmp_path, WINDOW, START, START + timedelta(hours=6), urma_published)
    assert stale == [START + timedelta(hours=n) for n in (2, 3, 4, 5)]  # 3: no precip; 4: no analysis; 5: nothing
    assert asked == [START + timedelta(hours=1), START + timedelta(hours=2)]  # only RTMA hours cost a request


def test_hour_runs_split_at_gaps_and_years():
    new_year = datetime(2026, 1, 1, tzinfo=UTC)
    hours = [new_year + timedelta(hours=n) for n in (-2, -1, 0, 1, 5)]
    assert hour_runs(hours) == [(new_year - timedelta(hours=2), 2), (new_year, 2), (new_year + timedelta(hours=5), 1)]


def test_a_spike_at_the_edge_of_a_block_is_caught_using_the_stored_neighbours(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    ingest_block(store, START, 6, fetch=fake_fetch(), workers=2)
    ingest_block(store, START + timedelta(hours=3), 1, fetch=fake_fetch(spike=(3, 1, 1)), workers=1)
    t0 = store.index_of(START)
    assert np.isnan(store.read_point("air_temperature", 901, 1401, t0 + 3, t0 + 4)).all()


def test_refetching_precip_keeps_hours_neither_source_has(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from agdata.ingest import refetch_precipitation

    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    store.write(START, {"precipitation": np.full((3, *WINDOW.shape), 0.1)}, source="urma")
    urma_hours = {START: 0.03, START + timedelta(hours=1): 0.12}
    urma = SimpleNamespace(
        name="urma",
        fetch_precip=lambda when, window, s: np.full(window.shape, urma_hours[when]) if when in urma_hours else None,
    )
    rtma = SimpleNamespace(name="rtma", fetch_precip=lambda when, window, s: None)
    monkeypatch.setattr(ingest, "URMA", urma)
    monkeypatch.setattr(ingest, "RTMA", rtma)
    assert refetch_precipitation(store, START, 3, workers=2) == 2  # the third hour kept what it had
    t0 = store.index_of(START)
    np.testing.assert_allclose(store.read_point("precipitation", 900, 1400, t0, t0 + 3), [0.03, 0.12, 0.1])


def test_a_store_from_before_a_new_soil_level_opens_with_it_empty(tmp_path):
    from agdata.store import HOURLY, GridStore

    older = [v for v in HOURLY_VARIABLES if v.name != "soil_temperature_30cm"]
    GridStore.create(tmp_path, HOURLY, 2025, WINDOW, older)
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    t0 = store.index_of(START)
    assert np.isnan(store.read_point("soil_temperature_30cm", 900, 1400, t0, t0 + 3)).all()
    assert store.sources("soil_temperature_30cm")[t0] is None


def soil_hours(start: datetime, count: int, soil_c: float = 1.5) -> era5land.Hours:
    shape = (count, *WINDOW.shape)
    values = {name: np.full(shape, soil_c) for name in SOIL}
    values["snow_depth"] = np.full(shape, 12.0)
    return era5land.Hours(times=[start + timedelta(hours=n) for n in range(count)], values=values)


def test_the_hourly_ingest_leaves_soil_and_snow_to_their_jobs(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    write_soil(store, soil_hours(START, 24), "era5land")
    ingest_block(store, START, 24, fetch=fake_fetch(), workers=4)  # its fetch still offers HRRR-like soil
    t0 = store.index_of(START)
    np.testing.assert_allclose(store.read_point("soil_temperature_10cm", 901, 1401, t0, t0 + 24), 1.5)
    assert store.sources("snow_depth")[t0 : t0 + 24] == ["era5land"] * 24


def test_ifs_fills_in_but_never_over_era5land(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    assert write_soil(store, soil_hours(START, 12), "era5land") == 12
    assert era5land_through(store) == START + timedelta(hours=11)
    assert write_soil(store, soil_hours(START, 24, soil_c=4.0), "ifs") == 12
    t0 = store.index_of(START)
    soil = store.read_point("soil_temperature_10cm", 901, 1401, t0, t0 + 24)
    np.testing.assert_allclose(soil, [1.5] * 12 + [4.0] * 12)
    sources = store.sources("soil_temperature_10cm")[t0 : t0 + 24]
    assert sources == ["era5land"] * 12 + ["ifs"] * 12
    # ERA5-Land arriving later replaces the provisional hours
    write_soil(store, soil_hours(START + timedelta(hours=12), 12, soil_c=2.0), "era5land")
    assert store.sources("snow_depth")[t0 : t0 + 24] == ["era5land"] * 24
    assert era5land_through(store) == START + timedelta(hours=23)


def test_soil_hours_outside_the_year_are_left_to_its_store(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    new_year = datetime(2026, 1, 1, tzinfo=UTC)
    assert write_soil(store, soil_hours(new_year - timedelta(hours=2), 4), "era5land") == 2
    assert era5land_through(store) == new_year - timedelta(hours=1)
    assert era5land_through(open_or_create_hourly(tmp_path, 2026, WINDOW)) is None
