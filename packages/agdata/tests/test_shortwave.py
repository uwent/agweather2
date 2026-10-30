from datetime import UTC, datetime, timedelta

import numpy as np

from agdata import shortwave
from agdata.catalog import VARIABLES
from agdata.gaps import clear_sky_shortwave_w_m2
from agdata.grid import NDFD, Window
from agdata.ingest import ingest_block, open_or_create_hourly
from agdata.rebuild import find_stale
from agdata.store import HOURLY, GridStore

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)
NOON = datetime(2025, 7, 15, 18, tzinfo=UTC)  # 1 pm CDT


def _rso() -> np.ndarray:
    lat, lon = NDFD.window_latlon(WINDOW)
    times = np.array([NOON.replace(tzinfo=None)], dtype="datetime64[s]")
    return clear_sky_shortwave_w_m2(times, lat, lon, np.full((1, *WINDOW.shape), 98.0))


def _correct(raw: np.ndarray) -> np.ndarray:
    lat, lon = NDFD.window_latlon(WINDOW)
    times = np.array([NOON.replace(tzinfo=None)], dtype="datetime64[s]")
    return shortwave.correct_w_m2(times, lat, lon, raw, np.full(raw.shape, 98.0))


def test_the_factor_follows_the_hours_clearness():
    rso = _rso()
    table = dict(zip(shortwave.TABLE["clearness"], shortwave.TABLE["factor"], strict=True))
    for clearness in (0.35, 0.75, 0.95):
        raw = clearness * rso
        np.testing.assert_allclose(_correct(raw), raw * table[clearness], rtol=1e-6)
    assert table[0.75] < 0.85  # cloudy hours come down most (HRRR dims too little under cloud)


def test_dark_and_missing_hours_stay_as_they_are():
    raw = np.array([[[0.0, np.nan, 0.0], [0.0, 0.0, 0.0]]])
    out = _correct(raw)
    assert out[0, 0, 0] == 0 and np.isnan(out[0, 0, 1])


def test_the_catalog_version_follows_the_table():
    assert VARIABLES["shortwave_radiation"].version == 1 + shortwave.VERSION
    assert VARIABLES["shortwave_radiation"].derived and not VARIABLES[shortwave.RAW].derived


def _fetch(raw_value: float):
    def fetch(when, window, session):
        from agdata.ingest import Hour

        values = {
            "air_temperature": np.full(window.shape, 25.0),
            "dew_point": np.full(window.shape, 15.0),
            "wind_speed": np.full(window.shape, 3.0),
            "wind_gust": np.full(window.shape, 6.0),
            "wind_direction": np.full(window.shape, 180.0),
            "surface_pressure": np.full(window.shape, 98.0),
            "cloud_cover": np.full(window.shape, 50.0),
            "precipitation": np.zeros(window.shape),
            shortwave.RAW: np.full(window.shape, raw_value),
        }
        sources = {name: "hrrr" if name == shortwave.RAW else "urma" for name in values}
        return Hour(values=values, sources=sources)

    return fetch


def test_ingest_keeps_hrrr_and_stores_it_corrected(tmp_path):
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    ingest_block(store, NOON, 1, fetch=_fetch(600.0), workers=1)
    t = store.index_of(NOON)
    raw = store.read_steps(shortwave.RAW, t, t + 1)
    stored = store.read_steps("shortwave_radiation", t, t + 1)
    np.testing.assert_allclose(raw, 600.0)
    np.testing.assert_allclose(stored, _correct(raw), atol=0.06)  # stored at 0.1 W/m²
    assert store.sources("shortwave_radiation")[t] == "hrrr" and store.sources(shortwave.RAW)[t] == "hrrr"


def test_the_archive_is_corrected_once_from_raw(tmp_path):
    # A store from before the correction: shortwave holds raw HRRR at version 1, and there's no raw variable
    old = [v for v in VARIABLES.values() if v.name != shortwave.RAW]
    old = [
        type(v)(**{**v.__dict__, "derived": False, "version": 1}) if v.name == "shortwave_radiation" else v for v in old
    ]
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, old)
    hours = [NOON + k * timedelta(hours=1) for k in range(3)]
    shape = (3, *WINDOW.shape)
    store.write(
        hours[0],
        {
            "shortwave_radiation": np.full(shape, 600.0),
            "air_temperature": np.full(shape, 25.0),
            "dew_point": np.full(shape, 15.0),
            "wind_speed": np.full(shape, 3.0),
            "surface_pressure": np.full(shape, 98.0),
            "et0": np.full(shape, 0.5),
        },
        source="hrrr",
    )
    assert "hourly/2025" in find_stale(tmp_path).stale

    assert shortwave.correct_archive(tmp_path, WINDOW, log=lambda _: None) == [2025]
    store = GridStore.open(tmp_path, HOURLY, 2025, VARIABLES.values())
    t = store.index_of(NOON)
    np.testing.assert_allclose(store.read_steps(shortwave.RAW, t, t + 3), 600.0)
    corrected = store.read_steps("shortwave_radiation", t, t + 1)
    np.testing.assert_allclose(corrected, _correct(np.full((1, *WINDOW.shape), 600.0)), atol=0.06)
    et0 = store.read_steps("et0", t, t + 1)
    assert np.all(et0 < 0.5) and np.all(et0 > 0.2)  # re-derived from the corrected shortwave
    assert store.sources("et0")[t] == "derived"
    assert "hourly/2025" not in find_stale(tmp_path).stale

    # Again: nothing is stale, so nothing changes (the raw isn't overwritten with corrected values)
    assert shortwave.correct_archive(tmp_path, WINDOW, log=lambda _: None) == []
    np.testing.assert_allclose(
        GridStore.open(tmp_path, HOURLY, 2025, VARIABLES.values()).read_steps(shortwave.RAW, t, t + 1), 600.0
    )


def test_a_stale_store_corrected_twice_keeps_the_first_raw(tmp_path):
    """A store whose shortwave is stale but already has raw HRRR (written by ingest) keeps that raw."""
    store = open_or_create_hourly(tmp_path, 2025, WINDOW)
    ingest_block(store, NOON, 1, fetch=_fetch(600.0), workers=1)
    store._array("shortwave_radiation").attrs["version"] = 1  # as if a refit left it stale before a raw copy
    shortwave.correct_archive(tmp_path, WINDOW, log=lambda _: None)
    store = GridStore.open(tmp_path, HOURLY, 2025, VARIABLES.values())
    t = store.index_of(NOON)
    np.testing.assert_allclose(store.read_steps(shortwave.RAW, t, t + 1), 600.0)  # raw kept, not the corrected value


def test_a_missing_pressure_doesnt_lose_the_sun():
    lat, lon = NDFD.window_latlon(WINDOW)
    times = np.array([NOON.replace(tzinfo=None)], dtype="datetime64[s]")
    with_nan = clear_sky_shortwave_w_m2(times, lat, lon, np.full((1, *WINDOW.shape), np.nan))
    typical = clear_sky_shortwave_w_m2(times, lat, lon, np.full((1, *WINDOW.shape), 97.0))
    np.testing.assert_allclose(with_nan, typical)
    assert np.all(typical > 500)


def test_lead_days_count_to_each_solar_noon():
    lon = np.array(-89.4)  # Madison: solar noon near 18Z
    hours = np.array([f"2025-07-{d}T18:00" for d in (15, 16, 25)], dtype="datetime64[s]")
    assert shortwave.lead_days(hours, lon, datetime(2025, 7, 15, 13, tzinfo=UTC)).ravel().tolist() == [0, 1, 10]
    assert shortwave.lead_days(hours, lon, datetime(2025, 7, 15, 1, tzinfo=UTC)).ravel().tolist() == [1, 2, 11]


def test_nbm_factors_follow_lead_and_clearness():
    rso = _rso()
    lat, lon = NDFD.window_latlon(WINDOW)
    times = np.array([NOON.replace(tzinfo=None)], dtype="datetime64[s]")
    table = shortwave.NBM_TABLE
    for cycle, group in ((NOON - timedelta(hours=5), 0), (NOON - timedelta(days=8, hours=5), len(table["factor"]) - 1)):
        raw = 0.75 * rso
        out = shortwave.correct_nbm_w_m2(times, lat, lon, raw, np.full(raw.shape, 98.0), cycle)
        expected = raw * np.interp(0.75, table["clearness"], table["factor"][group])
        np.testing.assert_allclose(out, expected, rtol=1e-6)
