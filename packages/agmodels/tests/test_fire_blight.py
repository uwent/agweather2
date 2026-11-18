"""Fire blight against its sources' numbers: Cougarblight's table and thresholds, and MaryBlyt 7.1's degree-hour
totals on the three demonstration seasons of Turechek and Biggs (2015, Table 1)."""

import numpy as np
import pytest

from agmodels import features as f
from agmodels.degree_days import degree_days_sine
from agmodels.models import fire_blight as fb


def c(t_f):
    return (np.asarray(t_f, dtype=float) - 32) / 1.8


def test_cougarblight_hourly_values():
    np.testing.assert_allclose(
        fb.cougarblight_values(c([50, 51, 60, 70, 80, 88.6, 95, 96, 101])), [0, 0.05, 0.52, 4, 30, 52, 10, 0, 0]
    )


def test_cougarblight_levels_by_history():
    assert [float(fb.level(v)) for v in (149, 150, 349, 350)] == [0, 1, 1, 2]
    assert float(fb.level(299, "none")) == 0 and float(fb.level(800, "none")) == 2
    assert float(fb.level(80, "active")) == 1 and float(fb.level(200, "active")) == 2


def test_features_over_a_day():
    t = c(np.r_[np.full(12, 50.0), np.full(12, 70.0)])
    rh = np.r_[np.full(3, 95.0), np.full(21, 60.0)]
    rain = np.zeros(24)
    rain[10] = 0.3
    out = f.fire_blight_features(t, rh, rain)
    assert out["cougarblight_risk_values"] == pytest.approx(48.0)  # 12 hours at 70 °F, 4 each
    assert out["degree_hours_over_65f"] * 1.8 == pytest.approx(60.0)  # 12 hours 5 °F above
    assert out["hours_wet"] == 4


# Turechek and Biggs (2015) Table 1: daily high and low (°F) and MaryBlyt 7.1's cumulative degree hours above 65 °F
SEASONS = {
    "ex1": (
        [(81, 53), (85, 53), (63, 52), (60, 48), (63, 42), (67, 43), (64, 40), (55, 39), (79, 37)],
        [144, 312, 208, 104, 0, 0, 0, 0, 96],
    ),
    "ex2": (
        [(64, 46), (50, 35), (54, 30), (69, 30), (71, 45), (79, 40), (85, 46), (79, 49), (77, 54), (80, 44), (77, 54), (56, 39)],
        [0, 0, 0, 0, 24, 120, 264, 360, 432, 432, 384, 192],
    ),
    "ex3": (
        [(65, 53), (70, 51), (64, 38), (80, 46), (86, 69), (88, 63), (88, 58), (87, 65), (84, 65), (74, 50), (68, 49), (82, 53), (81, 58), (70, 56), (71, 42), (80, 49), (81, 58)],
        [0, 24, 16, 112, 400, 648, 768, 744, 720, 552, 312, 456, 360, 336, 192, 312, 312],
    ),
}  # fmt: skip


@pytest.mark.parametrize("name", sorted(SEASONS))
def test_maryblyt_reproduces_turechek_and_biggs_table_1(name):
    days, expected = SEASONS[name]
    hi, lo = (np.array([d[k] for d in days], dtype=float) for k in (0, 1))
    n = len(days)
    # The program's degree hours: 24 × the day's whole sine degree days above 65 °F (ours are summed hour by hour)
    dh_f = 24 * np.round(degree_days_sine(lo, hi, 65.0, 90.0))
    inputs = {
        "air_temperature_min": c(lo),
        "air_temperature_max": c(hi),
        "precipitation_sum": np.zeros(n),
        "cougarblight_risk_values": np.zeros(n),
        "degree_hours_over_65f": dh_f / 1.8,
        "hours_wet": np.zeros(n),
        "day_of_year": np.arange(111, 111 + n, dtype=float),  # not January 1: the first day is the first blossom
        "year": np.full(n, 2025.0),
    }
    out = fb.outputs(inputs, biofix_index=0)
    total = out["degree_hours"] * 1.8
    shown = np.isfinite(total)  # until petal fall (348 DD43 after first blossom)
    assert shown.sum() >= 9
    np.testing.assert_allclose(total[shown], np.array(expected, dtype=float)[shown], atol=1.0)
    np.testing.assert_allclose(out["eip"][shown], total[shown] / 198 * 100)


def season(n=60, t=(10.0, 24.0), values=50.0, rain=0.0):
    return {
        "air_temperature_min": np.full(n, t[0]),
        "air_temperature_max": np.full(n, t[1]),
        "precipitation_sum": np.full(n, rain),
        "cougarblight_risk_values": np.full(n, values),
        "degree_hours_over_65f": np.full(n, 20.0),
        "hours_wet": np.zeros(n),
        "day_of_year": np.arange(1, n + 1, dtype=float) + 90,
        "year": np.full(n, 2025.0),
    }


def test_bloom_runs_from_first_blossom_to_petal_fall_by_degree_days():
    inputs = season(150)
    inputs["day_of_year"] = np.arange(1, 151, dtype=float)  # from January 1
    inputs["air_temperature_min"] = np.full(150, 2.0)
    inputs["air_temperature_max"] = np.full(150, 14.0)  # 46.4 °F mean: 3.4 DD43 a day
    out = fb.outputs(inputs, biofix_index=0)
    first = int(np.argmax(out["bloom"] == 1))
    last = int(np.flatnonzero(out["bloom"] == 1)[-1])
    dd = np.cumsum(degree_days_sine(np.full(150, 35.6), np.full(150, 57.2), 43.0))
    assert dd[first] >= 230 > dd[first - 1]
    assert last == min(int(np.argmax(dd >= 578)), 165 - 1)  # June 15 is day 166: petal fall's own day still blooms
    assert np.isnan(out["cougarblight"][:first]).all() and np.isnan(out["eip"][last + 1 :]).all()


def test_cougarblight_four_days_and_infection_possible():
    inputs = season(10, values=50.0, rain=0.5)
    out = fb.outputs(inputs, biofix_index=0)
    assert out["cougarblight"][5] == 200  # four days of 50: High with blight nearby last year
    assert fb.risk(out)[5] == 1 and out["infection_possible"][5] == 1
    assert fb.risk(out, blight_history="none")[5] == 0


def test_maryblyt_infection_and_symptoms():
    inputs = season(20, t=(14.0, 26.0), rain=1.0)  # 68 °F mean, rain daily
    inputs["degree_hours_over_65f"][:] = 100 / 1.8  # 100 °F·h a day: EIP over 100 on the second day
    inputs["precipitation_sum"][2:] = 0  # dry after it (1 mm isn't the 0.10 in the day before that counts)
    out = fb.outputs(inputs, biofix_index=0)
    assert out["maryblyt"][0] == 2 and out["maryblyt"][1] == 3  # Infection once EIP reaches 100
    assert out["maryblyt"][2] == 2
    daily55 = float(degree_days_sine(57.2, 78.8, 55.0, 90.0))
    assert out["symptoms_dd"][1] == 0 and out["symptoms_dd"][3] == pytest.approx(2 * daily55)
