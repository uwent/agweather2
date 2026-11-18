"""Apple scab against its sources' numbers and NEWA's rules, on hand-made seasons."""

import numpy as np
import pytest

from agmodels import features as f
from agmodels.models import apple_scab as scab

C_55F = (55 - 32) / 1.8


def hours(n, rh=50.0, t=C_55F, rain=0.0):
    return np.full(n, t), np.full(n, rh), np.full(n, rain)


def test_revised_mills_table():
    assert scab.hours_needed(34) == 41 and scab.hours_needed(55) == 8 and scab.hours_needed(70) == 6
    assert scab.hours_needed(79) == 11 and scab.hours_needed(33) == np.inf and scab.hours_needed(80) == np.inf
    assert scab.hours_needed(54.5) == 8  # rounded half up, as NEWA's toFixed


def test_maturity_matches_stensvands_milestones():
    # Stensvand et al. 2005 (p. 198), Gadoury and MacHardy's model: 50, 95 and 99 % at 250, 420 and 490 DD°C
    np.testing.assert_allclose(scab.maturity_percent([250, 420, 490]), [50, 95.6, 99.2], atol=0.5)


def test_a_dry_spell_stops_maturity_after_seven_days():
    rain = np.array([1.0] + [0.0] * 9 + [0.5, 0.0])
    np.testing.assert_array_equal(scab.counted_days(rain), [True] * 8 + [False, False, True, True])


def test_an_infection_when_wet_hours_reach_the_table():
    t, rh, rain = hours(48)
    rain[30] = 1.0  # rain starts the period
    rh[30:38] = 95  # 8 wet hours at 55 °F: the table's 8
    out = scab.infection_periods(t, rh, rain)
    assert out["infection"] == 1 and out["wet_hours"] == 8 and out["wet_temperature"] == pytest.approx(C_55F)
    rh[37] = 50  # 7 hours: none
    assert scab.infection_periods(t, rh, rain)["infection"] == 0


def test_wetness_without_rain_starts_nothing():
    t, rh, rain = hours(48, rh=95.0)
    assert scab.infection_periods(t, rh, rain)["infection"] == 0


def test_periods_under_24_hours_apart_join():
    t, rh, rain = hours(72)
    rain[[30, 45]] = 1.0
    rh[30:34] = 95  # 4 hours
    rh[45:49] = 95  # 4 more, 11 hours after the first ended: 8 together
    out = scab.infection_periods(t, rh, rain)
    assert out["infection"] == 1 and out["wet_hours"] == 8
    rain[45], rain[57] = 0, 1.0
    rh[45:49], rh[57:61] = 50, 95  # 24 hours after: apart
    out = scab.infection_periods(t, rh, rain)
    assert out["infection"] == 0 and out["wet_hours"] == 4


def test_an_infection_counts_on_the_day_it_happens():
    t, rh, rain = hours(120)
    rain[60] = 1.0
    rh[60:70] = 95  # reached at hour 67, three days before the window's last day
    assert scab.infection_periods(t, rh, rain)["infection"] == 0
    rh[60:110] = 95  # still wet into the last day, but it reached the table days before
    out = scab.infection_periods(t, rh, rain)
    assert out["infection"] == 0 and out["wet_hours"] == 50 and out["truncated"] == 0


def test_a_missing_hour_leaves_the_day_missing():
    t, rh, rain = hours(48)
    rh[3] = np.nan
    assert np.isnan(scab.infection_periods(t, rh, rain)["infection"])


def test_features_split_the_days_and_nights_rain():
    n = f.SCAB_HOURS
    local_hour = (np.arange(n) + 1) % 24  # readings 01:00 … 24:00 (0), five days
    t, rh, rain = hours(n)
    rain[local_hour == 7] = 1.0  # 07:00 readings: day rain
    rain[local_hour == 21] = 2.0  # 21:00 readings: the night before's
    rain[local_hour == 6] = 0.5  # 06:00 readings: night
    out = f.scab_features(t, rh, rain, local_hour)
    assert out["precipitation_7am_to_7pm"] == pytest.approx(1.0)
    assert out["precipitation_8pm_to_6am"] == pytest.approx(2.5)
    assert out["temperature_mean_rain_7am_to_7pm"] == pytest.approx(C_55F)


def season(days, rain_day=0.0, rain_t=np.nan, infection=0.0, t=15.0):
    return {
        "air_temperature_min": np.full(days, t - 5),
        "air_temperature_max": np.full(days, t + 5),
        "precipitation_sum": np.full(days, 5.0),
        "precipitation_7am_to_7pm": np.full(days, rain_day),
        "precipitation_8pm_to_6am": np.zeros(days),
        "temperature_mean_rain_7am_to_7pm": np.full(days, rain_t),
        "scab_infection": np.full(days, infection),
        "scab_wet_hours": np.zeros(days),
        "scab_wet_temperature": np.full(days, np.nan),
    }


def test_the_season_ends_with_a_warm_day_rain_after_95_percent():
    inputs = season(60, rain_day=3.0, rain_t=12.0, infection=1.0)
    out = scab.outputs(inputs, biofix_index=5)
    assert np.isnan(out["maturity"][:5]).all()
    first_95 = int(np.argmax(out["maturity"] >= 95))  # 15 DD°C a day: 420 DD on day 28 from green tip
    assert out["season"][first_95] == 0 and out["season"][first_95 + 1] == 1
    risk = scab.risk(out)
    assert risk[first_95] == 1 and np.isnan(risk[first_95 + 1 :]).all()
    assert (
        out["released"][first_95] > 0.99 * out["maturity"][first_95]
    )  # 90 % of the mature remainder each warm wet day


def test_the_backstop_ends_a_season_without_rain():
    out = scab.outputs(season(120), biofix_index=0)
    ended = int(np.argmax(out["season"] == 1))
    assert ended == int(np.ceil(scab.BACKSTOP_DD_C / 15))  # the day after 1,300 DD°C
    assert out["released"][-1] == 0


def test_release_shares():
    inputs = season(3, rain_day=1.0, rain_t=8.0)  # light and cool: 25 %
    inputs["precipitation_8pm_to_6am"][:] = 1.0  # night rain first: 5 %
    out = scab.outputs(inputs, biofix_index=0)
    mature = out["maturity"][0]
    assert out["released_today"][0] == pytest.approx(mature * 0.05 + mature * 0.95 * 0.25)
