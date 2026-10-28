"""Potato volunteer survival (MSU's rule and the Wisconsin tool's 8 in, on HRRR's soil temperature)."""

import numpy as np

from agmodels import features
from agmodels.models import potato_volunteer as pv


def level(h4, h10, h8):
    return pv.explore(killing_hours_4cm=h4, killing_hours_10cm=h10, killing_hours_8in=h8)["risk"]


def test_risk_by_depths_past_120_hours():
    assert level(120, 120, 120) == 0  # Low: at least 120 hours (the tool's)
    assert level(120, 120, 119) == 1
    assert level(0, 500, 0) == 2
    assert level(60, 60, 60) == 3  # Very high
    assert pv.SPEC.risk is not None and pv.SPEC.risk.levels[3] == "Very high"


def inputs(days, *per_day):
    return {f"hours_soil_{d}_below_27f": np.full(days, h, dtype=float) for d, h in zip(pv.DEPTHS, per_day, strict=True)}


def test_the_count_runs_the_season_and_holds_into_summer():
    days = inputs(365, 2.0, 1.0, 0.0)
    for d in pv.DEPTHS:
        days[f"hours_soil_{d}_below_27f"][200:] = 0  # spring thaw: the counts stop growing and the winter's risk holds
    out = pv.outputs(days, biofix_index=10)
    total = out["killing_hours_4cm"]
    assert np.isnan(total[:10]).all() and total[10] == 2 and total[-1] == 2 * 190
    risk = pv.risk(out, biofix_index=10)
    assert risk[20] == 3 and risk[80] == 2 and risk[-1] == 1  # 4 cm reaches 120 hours on day 69, 10 cm on day 129


def test_a_day_missing_hours_adds_nothing():
    days = inputs(5, 30.0, 30.0, 30.0)
    days["hours_soil_4cm_below_27f"][2] = np.nan
    out = pv.outputs(days)
    assert out["killing_hours_4cm"][-1] == 120 and out["killing_hours_8in"][-1] == 150 and pv.risk(out)[-1] == 0


def test_killing_hours_from_hourly_soil_temperature():
    soil = np.array([-2.7, -2.8, -3.5, 0.0])  # 27 °F is −2.78 °C
    out = features.soil_features(soil, soil, soil)
    assert out["hours_soil_4cm_below_27f"] == 2 and out["hours_soil_8in_below_27f"] == 2
    # 8 in (20.3 cm) is about halfway from 10 to 30 cm
    deep = features.soil_features(soil, np.full(4, -4.0), np.full(4, -2.0))
    assert deep["hours_soil_8in_below_27f"] == 4 and features.soil_between(20.32, 10, -4.0, 30, -2.0) < -2.78
    assert np.isnan(features.soil_features(soil, soil, np.array([0, 0, 0, np.nan]))["hours_soil_8in_below_27f"])
