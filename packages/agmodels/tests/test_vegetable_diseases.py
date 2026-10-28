"""Parity with the Crop Risk Tool for the vegetable disease indices (late blight has its own file)."""

import numpy as np
import pytest

from agmodels import features as f
from agmodels.models import botcast, carrot_foliar, cercospora_beet, early_blight


def crt_inputs(daily):
    """The tool's daily columns under our input names, with its pairing (calendar-day humid hours)."""
    return {
        "air_temperature_min": daily["temperature_min"],
        "air_temperature_max": daily["temperature_max"],
        "hours_rh_over_90_from_8pm": daily["hours_rh_over_90"],
        "temperature_mean_rh_over_90_from_8pm": daily["temperature_mean_rh_over_90"],
        "hours_temperature_over_30c": daily["hours_temp_over_30"],
        "hours_rh_under_70": daily["hours_rh_under_70"],
        "precipitation_sum": daily["precipitation_daily"],
    }


def our_inputs(crt):
    h = crt("hourly_eau_claire_2025")
    local = h["local_time"].astype("datetime64[h]")
    _, daily = f.daily_features(
        local, h["temperature"], h["relative_humidity"], h["precipitation"], midnight_ends_day=False
    )
    return daily


# Tables


def test_pdays_match_with_the_tools_last_term(crt):
    sweep = crt("early_blight_pdays_sweep")
    np.testing.assert_allclose(
        early_blight.pdays(sweep["tmin"], sweep["tmax"], last_term="tmin"), sweep["pdays"], atol=1e-9
    )


def test_pdays_weigh_the_max_in_the_last_term():
    assert early_blight.pdays(10, 28) != early_blight.pdays(10, 28, last_term="tmin")
    p = early_blight.development_rate
    assert early_blight.pdays(21, 21) == pytest.approx(10) and p(21) == 10 and p(6.9) == 0 and p(30.1) == 0


def fast_differs(t, h):
    """Where FAST's table (v2) and the Crop Risk Tool's differ: the tool's first step at 13–17 and 18–20 °C is an hour
    late, and it puts 18, 21 and 26 °C in the band below. Drop once the tool's fix lands and its fixtures are rebuilt.
    """
    t, h = np.asarray(t), np.asarray(h)
    late_step = ((t >= 13) & (t < 18) & (h == 7)) | ((t >= 18) & (t <= 21) & (h == 4))
    edge = np.isclose(t, 18) | np.isclose(t, 21) | np.isclose(t, 26)
    return late_step | (edge & (h > 0))


def test_tomcast_table_matches_except_where_fast_differs(crt):
    sweep = crt("alternaria_dsv_sweep")
    ours = carrot_foliar.dsv(sweep["t"], sweep["h"])
    differs = fast_differs(sweep["t"], sweep["h"])
    np.testing.assert_array_equal(ours[~differs], sweep["dsv"][~differs])
    assert (ours[differs] != sweep["dsv"][differs]).any()


def test_tomcast_table_is_fasts():
    # Madden et al. (1978), Table 1: the hours at which each band reaches 1, 2, 3 and 4
    table = {13: (7, 16, 21, None), 18: (4, 9, 16, 23), 21: (3, 6, 13, 21), 26: (4, 9, 16, 23)}
    for low, steps in table.items():
        for t in (low, low + 0.5, {13: 17, 18: 20, 21: 25, 26: 29}[low] + 0.9):
            expected = [sum(h >= s for s in steps if s is not None) for h in range(25)]
            assert carrot_foliar.dsv(t, np.arange(25)).tolist() == expected, t
    assert not carrot_foliar.dsv(12.9, np.arange(25)).any()


def test_cercospora_table_matches(crt):
    sweep = crt("cercospora_div_sweep")
    ours = cercospora_beet.div(sweep["t"], sweep["h"])
    # Where hours are 0 the tool can give 1 (warm bands start at 1); with no humid hours there's no temperature,
    # so the tool's pairing never reaches it, and v2 gives 0
    some = sweep["h"] > 0
    np.testing.assert_array_equal(ours[some], sweep["div"][some])


def test_botcast_tables_match(crt):
    sweep = crt("botcast_dinfv_sweep")
    np.testing.assert_array_equal(botcast.infection(sweep["t"], sweep["h"]), sweep["dinfv"])
    sweep = crt("botcast_dinov_sweep")
    np.testing.assert_array_equal(botcast.inoculum(sweep["hot"], sweep["dry"], sweep["h"]), sweep["dinov"])


# A season, from the tool's own inputs


def test_early_blight_season(crt):
    theirs = crt("early_blight_eau_claire_2025")
    daily = crt("daily_eau_claire_2025")
    values = early_blight.pdays(daily["temperature_min"], daily["temperature_max"], last_term="tmin")
    np.testing.assert_allclose(values, theirs["pdays"], atol=1e-9)
    np.testing.assert_array_equal(early_blight.risk({"pdays": values}), theirs["severity"])


def test_carrot_foliar_season(crt):
    daily, theirs = crt_inputs(crt("daily_eau_claire_2025")), crt("alternaria_eau_claire_2025")
    daily["temperature_mean_rh_over_90_from_8pm"] = np.nan_to_num(daily["temperature_mean_rh_over_90_from_8pm"])
    out = carrot_foliar.outputs(daily)
    t, h = daily["temperature_mean_rh_over_90_from_8pm"], daily["hours_rh_over_90_from_8pm"]
    differs = fast_differs(t, h)
    np.testing.assert_array_equal(out["dsv"][~differs], theirs["dsv"][~differs])
    # Given the tool's daily values, the totals and risk are the tool's
    tool_values = {"dsv": np.where(differs, theirs["dsv"], out["dsv"])}
    np.testing.assert_array_equal(carrot_foliar.risk(tool_values), theirs["severity"])


def test_cercospora_season(crt):
    daily, theirs = crt_inputs(crt("daily_eau_claire_2025")), crt("cercospora_eau_claire_2025")
    # A day with calendar humid hours but none from 8 pm has no temperature: the tool scores 0, as 0 °C does here
    daily["temperature_mean_rh_over_90_from_8pm"] = np.nan_to_num(daily["temperature_mean_rh_over_90_from_8pm"])
    out = cercospora_beet.outputs(daily)
    np.testing.assert_array_equal(out["div"], theirs["div"])
    np.testing.assert_allclose(out["div_7_day_mean"], theirs["avg7"], atol=1e-9)
    np.testing.assert_array_equal(cercospora_beet.risk(out), theirs["severity"])


def test_botcast_season(crt):
    daily, theirs = crt_inputs(crt("daily_eau_claire_2025")), crt("botcast_eau_claire_2025")
    out = botcast.outputs(daily)
    # The tool scores days with humid hours but no temperature (its pairing) by falling through its conditions;
    # those are the only days v2 leaves missing
    unknown = np.isnan(out["dsi"])
    assert unknown.sum() == np.sum(
        np.isnan(daily["temperature_mean_rh_over_90_from_8pm"]) & (daily["hours_rh_over_90_from_8pm"] > 6)
    )
    np.testing.assert_array_equal(out["dsi"][~unknown], theirs["dsi"][~unknown])


# The window change (humid hours and their temperature from the same day from 8 pm), measured


@pytest.mark.parametrize(
    ("module", "name", "theirs_file", "column"),
    [
        (carrot_foliar, "dsv", "alternaria_eau_claire_2025", "dsv"),
        (cercospora_beet, "div", "cercospora_eau_claire_2025", "div"),
        (botcast, "dsi", "botcast_eau_claire_2025", "dsi"),
    ],
)
def test_pairing_changes_little_over_a_season(crt, module, name, theirs_file, column):
    ours = module.outputs(our_inputs(crt))[name]
    theirs = crt(theirs_file)[column]
    season = slice(134, 273)  # May 15 to Sep 30
    a, b = np.nansum(ours[season]), np.nansum(theirs[season])
    assert abs(a - b) <= 0.2 * b, (a, b)
