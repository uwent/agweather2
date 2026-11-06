import numpy as np
import pytest

from agmodels import features as f

# Our names for the Crop Risk Tool's build_daily columns
CRT_NAMES = {
    "hours_temperature_over_20c": "hours_temp_over_20",
    "hours_temperature_over_30c": "hours_temp_over_30",
    "hours_rh_under_70": "hours_rh_under_70",
    "hours_rh_over_80": "hours_rh_over_80",
    "hot_past_5_days": "hot_past_5_days",
    "dry": "dry",
    "precipitation_sum": "precipitation_daily",
    "air_temperature_min": "temperature_min",
    "air_temperature_max": "temperature_max",
}
# Not compared: the tool's RH ≥ 90% counts, which v2 counts on gridded RH at 88% (D50; tested below), and its days
# from 8 pm, which v2 starts at 6 pm (D74). Tar spot's night is the tool's (below).


@pytest.fixture
def ours(crt):
    h = crt("hourly_eau_claire_2025")
    local = h["local_time"].astype("datetime64[h]")
    return f.daily_features(
        local, h["temperature"], h["relative_humidity"], h["precipitation"], midnight_ends_day=False
    )


@pytest.mark.parametrize("name", list(CRT_NAMES))
def test_daily_features_match_the_crop_risk_tool(ours, crt, name):
    days, daily = ours
    theirs = crt("daily_eau_claire_2025")
    assert [str(d) for d in days] == theirs["date"].tolist()
    np.testing.assert_allclose(daily[name], theirs[CRT_NAMES[name]], atol=1e-9, equal_nan=True)


def test_rh_90_features_count_gridded_rh_at_88():
    temperature = np.full((24,), 20.0)
    rh = np.array([87.9, 88.0, 89.0, 90.0] * 6)
    local = np.datetime64("2025-07-01T00", "h") + np.arange(24)
    _, daily = f.daily_features(local, temperature, rh, np.zeros(24), midnight_ends_day=False)
    assert daily["hours_rh_over_90"][0] == 18  # 88, 89 and 90 count; 87.9 doesn't
    days = f.evening_features(temperature, rh, np.arange(24))
    assert days["hours_rh_over_90_from_6pm"] == 18
    # Night is readings 19:00-06:00 (12), tar spot's 20:00-06:00 (11); the hours h with h % 4 == 0 read 87.9
    assert days["hours_rh_over_90_night"] == 9 and days["hours_rh_over_90_7pm_to_6am"] == 8
    hot = f.hours_humid_and_warm(np.full(24, 25.0), rh, 90, f.SCAB_C)
    assert hot == 6  # pecan scab keeps the Mesonet's 90%


def test_a_missing_hour_makes_counts_missing_but_not_other_days():
    temperature = np.full((48,), 25.0)
    rh = np.full((48,), 95.0)
    rh[30] = np.nan
    local = np.datetime64("2025-07-01T00", "h") + np.arange(48)
    _, daily = f.daily_features(local, temperature, rh, np.zeros(48), midnight_ends_day=False)
    assert daily["hours_rh_over_90"].tolist()[0] == 24
    assert np.isnan(daily["hours_rh_over_90"][1])
    assert np.isnan(daily["temperature_mean_rh_over_90_from_6pm"][1])


def test_tar_spots_night_matches_the_crop_risk_tool(crt):
    # The tool's night is the readings 20:00-06:00 of its day from 8 pm, which v2's day from 6 pm holds whole under the
    # same date; counted at the tool's 90% here (v2 counts gridded RH at 88%, D50)
    h = crt("hourly_eau_claire_2025")
    local = h["local_time"].astype("datetime64[h]")
    evening = (local + np.timedelta64(23 - f.EVENING_HOUR, "h")).astype("datetime64[D]")
    hour = (local - local.astype("datetime64[D]")).astype(int)
    theirs = crt("daily_eau_claire_2025")
    for k, day in enumerate(theirs["date"]):
        mine = evening == np.datetime64(day)
        found = f.evening_features(h["temperature"][mine], h["relative_humidity"][mine], hour[mine], rh_90_at=90)
        expected = theirs["hours_rh_over_90_night"][k]
        assert found["hours_rh_over_90_7pm_to_6am"] == expected or (np.isnan(expected) and mine.sum() < 24), day


def test_windows_hold_the_readings_after_their_start_through_their_end():
    local = np.datetime64("2025-07-01T01", "h") + np.arange(72)  # hours ending July 1 01:00 .. July 4 00:00
    temperature = np.arange(72, dtype=float)
    days, daily = f.daily_features(local, temperature, np.full(72, 95.0), np.zeros(72))
    k = [str(d) for d in days].index("2025-07-02")
    # July 2 from 6 pm: readings July 1 19:00 .. July 2 18:00 (24 of them)
    assert daily["hours_rh_over_90_from_6pm"][k] == 24 and daily["hours_rh_over_90_night"][k] == 12
    # Noon to noon: readings July 1 13:00 .. July 2 12:00; the coldest is the first (index 12)
    assert daily["air_temperature_min_overnight"][k] == 12.0


def test_no_qualifying_hours_leaves_the_mean_missing_not_zero():
    rh = np.full((3, 2), 50.0)
    assert np.isnan(f.mean_where(np.full((3, 2), 20.0), rh >= 90)).all()


def test_the_grid_shape_works():
    temperature = np.full((24, 3, 4), 31.0)
    rh = np.full((24, 3, 4), 92.0)
    out = f.calendar_features(temperature, rh)
    assert out["hours_temperature_over_30c"].shape == (3, 4) and (out["hours_rh_over_90"] == 24).all()


def test_v2_days_close_at_midnight():
    local = np.datetime64("2025-07-01T01", "h") + np.arange(24)  # hours ending 01:00 .. 24:00
    days, daily = f.daily_features(local, np.full(24, 25.0), np.full(24, 95.0), np.ones(24))
    assert [str(d) for d in days] == ["2025-07-01"]
    assert daily["precipitation_sum"].tolist() == [24.0]


def test_dew_point_depression_matches_the_crop_risk_tool(crt):
    h = crt("hourly_eau_claire_2025")
    local = h["local_time"].astype("datetime64[h]")
    _, daily = f.daily_features(
        local,
        h["temperature"],
        h["relative_humidity"],
        h["precipitation"],
        midnight_ends_day=False,
        dew_point_c=h["dew_point"],
    )
    more = crt("daily_more_eau_claire_2025")
    np.testing.assert_allclose(daily["dew_point_depression_mean"], more["dew_point_depression_mean"], atol=1e-9)
    np.testing.assert_allclose(daily["dew_point_depression_max"], more["dew_point_depression_max"], atol=1e-9)


def test_soil_hours_below_27f_count_each_depth_and_interpolate_8_inches():
    local = np.datetime64("2025-01-10T01", "h") + np.arange(24)
    kill = (27 - 32) / 1.8  # −2.78 °C
    first = np.arange(24)
    soil_4cm = np.where(first < 5, kill - 0.5, kill + 0.5)  # 5 h below
    soil_10cm = np.where(first < 6, kill - 0.5, kill + 0.5)  # 6 h below
    soil_30cm = np.full(24, kill + 0.6)  # never
    _, daily = f.daily_features(
        local,
        np.full(24, -5.0),
        np.full(24, 80.0),
        np.zeros(24),
        soil_4cm_c=soil_4cm,
        soil_10cm_c=soil_10cm,
        soil_30cm_c=soil_30cm,
    )
    assert daily["hours_soil_4cm_below_27f"].tolist() == [5]
    assert daily["hours_soil_10cm_below_27f"].tolist() == [6]
    # 8 in (20.32 cm) is 51.6% of the way from 10 to 30 cm: 0.484 (kill − 0.5) + 0.516 (kill + 0.6) is above the line,
    # so the 6 hours under it at 10 cm aren't under it at 8 in
    assert daily["hours_soil_8in_below_27f"].tolist() == [0]
    colder = f.soil_between(f.EIGHT_INCHES_CM, 10, -4.0, 30, -2.0)
    assert colder == pytest.approx(-4.0 + 0.516 * 2.0, abs=1e-3)


def test_the_soil_features_need_all_three_levels():
    local = np.datetime64("2025-01-10T01", "h") + np.arange(24)
    _, daily = f.daily_features(local, np.full(24, -5.0), np.full(24, 80.0), np.zeros(24), soil_4cm_c=np.full(24, -5.0))
    assert "hours_soil_4cm_below_27f" not in daily
