import numpy as np
import pytest

from agmodels import features as f

# Our names for the Crop Risk Tool's build_daily columns
CRT_NAMES = {
    "hours_temperature_over_20c": "hours_temp_over_20",
    "hours_temperature_over_30c": "hours_temp_over_30",
    "hours_rh_under_70": "hours_rh_under_70",
    "hours_rh_over_80": "hours_rh_over_80",
    "hours_rh_over_90": "hours_rh_over_90",
    "hours_rh_over_80_night": "hours_rh_over_80_night",
    "hours_rh_over_90_night": "hours_rh_over_90_night",
    "temperature_mean_rh_over_80_from_8pm": "temperature_mean_rh_over_80",
    "temperature_mean_rh_over_90_from_8pm": "temperature_mean_rh_over_90",
    "hot_past_5_days": "hot_past_5_days",
    "dry": "dry",
    "precipitation_mm": "precipitation_daily",
}


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


def test_a_missing_hour_makes_counts_missing_but_not_other_days():
    temperature = np.full((48,), 25.0)
    rh = np.full((48,), 95.0)
    rh[30] = np.nan
    local = np.datetime64("2025-07-01T00", "h") + np.arange(48)
    _, daily = f.daily_features(local, temperature, rh, np.zeros(48), midnight_ends_day=False)
    assert daily["hours_rh_over_90"].tolist()[0] == 24
    assert np.isnan(daily["hours_rh_over_90"][1])
    assert np.isnan(daily["temperature_mean_rh_over_90_from_8pm"][1])


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
    assert daily["precipitation_mm"].tolist() == [24.0]
