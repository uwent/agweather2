import numpy as np

from agmodels import features as f
from agmodels.models import late_blight as lb
from agmodels.registry import model


def test_the_dsv_table_matches_the_crop_risk_tool(crt):
    sweep = crt("late_blight_dsv_sweep")
    np.testing.assert_array_equal(lb.dsv(sweep["t"], sweep["h"]), sweep["dsv"])


def test_a_season_matches_the_crop_risk_tool_from_its_inputs(crt):
    daily, theirs = crt("daily_eau_claire_2025"), crt("late_blight_eau_claire_2025")
    # The tool's own pairing (calendar-day hours with 8 pm temperatures), to check the accumulation and risk. Where
    # the calendar day has humid hours but the 8 pm window none, the tool scores 0 for want of a temperature; a
    # temperature below the table's first band gives the same here
    temperature = np.where(np.isnan(daily["temperature_mean_rh_over_90"]), 0.0, daily["temperature_mean_rh_over_90"])
    out = lb.outputs(
        {"temperature_mean_rh_over_90_from_8pm": temperature, "hours_rh_over_90_from_8pm": daily["hours_rh_over_90"]}
    )
    np.testing.assert_array_equal(out["dsv"], theirs["dsv"])
    np.testing.assert_array_equal(out["dsv_total"], theirs["total"])
    np.testing.assert_array_equal(out["dsv_14_day"], theirs["total14"])
    np.testing.assert_array_equal(lb.risk(out), theirs["severity"])


def test_pairing_hours_with_their_own_window_changes_few_days(crt):
    h = crt("hourly_eau_claire_2025")
    _, daily = f.daily_features(
        h["local_time"].astype("datetime64[h]"), h["temperature"], h["relative_humidity"], h["precipitation"]
    )
    ours = lb.outputs(daily)["dsv"]
    theirs = crt("late_blight_eau_claire_2025")["dsv"]
    # 2025 at Eau Claire (PLAN.md Phase 3 D): 27 days differ, the May 15-Sep 30 total is 53 against 47, and both
    # reach the 18-DSV spray threshold on July 16
    assert int((ours != theirs).sum()) == 27
    season = slice(134, 273)
    assert (np.sum(ours[season]), np.sum(theirs[season])) == (53, 47)


def test_missing_inputs_give_no_dsv_and_no_humid_hours_give_zero():
    np.testing.assert_array_equal(lb.dsv([np.nan, 20.0, np.nan], [10.0, np.nan, 0.0]), [np.nan, np.nan, 0.0])


def test_risk_starts_at_the_biofix_and_skips_missing_days():
    values = np.full(40, 2.0)
    values[5] = np.nan
    levels = lb.risk({"dsv": values}, biofix_index=10)
    assert np.isnan(levels[:10]).all()
    assert levels[10] == 1 and levels[-1] == 4  # 2 a day: 14 days = 28 ≥ 21 once 30 are in


def test_the_grid_shape_works():
    shape = (30, 3, 4)
    out = lb.outputs(
        {
            "temperature_mean_rh_over_90_from_8pm": np.full(shape, 16.0),
            "hours_rh_over_90_from_8pm": np.full(shape, 20.0),
        }
    )
    assert out["dsv"].shape == shape and (out["dsv"] == 4).all()  # 20 h at 16 °C exceeds all four steps
    assert lb.risk(out).shape == shape


def test_the_registry_and_explorer():
    assert model("late-blight-dsv") is lb
    assert lb.explore(temperature=16, hours=20) == {"dsv": 4.0}
