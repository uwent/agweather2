"""Parity with the Crop Risk Tool for pecan scab and cotton planting (D6), and intended differences. Rye biomass left
the tool's model in 0.3 (`test_rye_biomass.py`)."""

import numpy as np

from agmodels import features as f
from agmodels.models import cotton_planting as cotton
from agmodels.models import pecan_scab as pecan

# Pecan scab


def test_scab_hours_by_the_tools_thresholds_match_it(crt):
    # The tool counts RH ≥ 92% and temperature > 21.1 °C over each calendar day (00:00–23:00)
    h, theirs = crt("hourly_eau_claire_2025"), crt("pecan_scab_eau_claire_2025")
    days = np.array([t[:10] for t in h["local_time"]])
    scab = (h["relative_humidity"] >= 92) & (h["temperature"] > 21.1)
    ours = np.array([scab[days == d].sum() for d in theirs["date"]], dtype=float)
    np.testing.assert_array_equal(ours, theirs["daily_scab_hours"])
    np.testing.assert_array_equal(
        pecan.outputs({"hours_rh_over_90_temperature_over_70f": ours})["scab_hours_total"], theirs["scab_hours"]
    )


def test_v2_counts_the_mesonets_scab_hours(crt):
    h, theirs = crt("hourly_eau_claire_2025"), crt("pecan_scab_eau_claire_2025")
    local = h["local_time"].astype("datetime64[h]")
    _, daily = f.daily_features(
        local, h["temperature"], h["relative_humidity"], h["precipitation"], midnight_ends_day=False
    )
    ours = daily["hours_rh_over_90_temperature_over_70f"]
    # RH from 90% rather than 92% counts more hours; the temperature edges (≥ 70 °F, > 21.1 °C) differ by 0.01 °C
    assert np.nansum(ours) > theirs["daily_scab_hours"].sum()
    assert np.all(f.hours_humid_and_warm(np.array([21.1, 21.2, 25]), np.array([95, 95, 89.9]), 90, f.SCAB_C) == 1)


def _pecan_season(hours, biofix_index=0, **options):
    """Daily scab hours from March 1, 2025, with the runner's context: (outputs, risk)."""
    n = len(hours)
    inputs = {
        "hours_rh_over_90_temperature_over_70f": np.asarray(hours, dtype=float),
        "day_of_year": np.arange(60, 60 + n, dtype=float),
        "year": np.full(n, 2025.0),
    }
    out = pecan.outputs(inputs, biofix_index=biofix_index, **options)
    return out, pecan.risk(out, biofix_index=biofix_index, **options)


def test_pecan_threshold_within_the_wait_from_march_1_is_moderate():
    # One scab hour a day from day 11: 5 hours (half of 10) on day 15, 10 on day 20, then the wait ends on day 30
    hours = np.where(np.arange(45) >= 11, 1.0, 0.0)
    out, level = _pecan_season(hours)
    assert out["scab_hours_total"][20] == 10 and out["wait_days_left"][20] == 10
    assert level[:15].tolist() == [0] * 15
    assert level[15:30].tolist() == [1] * 15  # from half the threshold, and at it within the 30-day wait
    assert level[30:].tolist() == [2] * 15  # spray advised
    assert out["days_since_start"][30] == 30 and out["wait_days_left"][30] == 0


def test_pecan_from_a_spray_waits_its_protection_days():
    hours = np.full(60, 2.0)  # 10 hours 5 days after the spray
    for days in ("5", "7", "10", "14"):
        out, level = _pecan_season(hours, biofix_index=40, protection_days=days)
        wait = int(days)
        assert np.isnan(level[:40]).all() and np.isnan(out["days_since_start"][:40]).all()
        assert level[40:43].tolist() == [0, 0, 1]  # 2, 4, then 6 hours: from half of 10
        advised = np.flatnonzero(level == 2)
        assert advised[0] == 40 + wait, days  # the threshold was reached on day 4, so the wait decides
        assert out["wait_days_left"][40].item() == wait


def test_pecan_susceptibility_sets_the_threshold():
    hours = np.where(np.arange(90) >= 31, 1.0, 0.0)  # from the end of the wait, a scab hour a day
    for susceptibility, threshold in (("high", 10), ("moderate", 20), ("low", 30)):
        out, level = _pecan_season(hours, susceptibility=susceptibility)
        first = int(np.flatnonzero(level == 2)[0])
        assert out["scab_hours_total"][first] == threshold, susceptibility
        assert out["scab_hours_total"][int(np.flatnonzero(level == 1)[0])] == threshold / 2


def test_pecan_explorer_levels():
    # Low below half the threshold, Moderate from half or at it within the wait, High at it once the wait is over
    assert [pecan.explore(h, 0)["risk_high"] for h in (0, 4, 5, 9, 10, 30)] == [0, 0, 1, 1, 2, 2]
    assert [pecan.explore(h, 3)["risk_high"] for h in (4, 5, 10, 30)] == [0, 1, 1, 1]
    assert [pecan.explore(h, 0)["risk_low"] for h in (14, 15, 29, 30)] == [0, 1, 1, 2]
    assert [pecan.explore(h, 0)["risk_moderate"] for h in (9, 10, 19, 20)] == [0, 1, 1, 2]


# Cotton planting


def test_cotton_model_matches_the_tool(crt):
    # The tool's probability rests on the emergence model and its standard error, which v2's stand interval uses
    s = crt("cotton_planting_sweep")
    p, _ = cotton.probability_below(s["precip"], s["tmin"], s["pythium"], s["pop"], s["limit"], s["year"])
    np.testing.assert_allclose(p, s["probability"], rtol=1e-9, atol=1e-12)


def test_cotton_windows_match_the_tools(crt):
    daily, theirs = crt("daily_eau_claire_2025"), crt("cotton_planting_eau_claire_2025")
    inputs = {"precipitation_sum": daily["precipitation_daily"], "air_temperature_min": daily["temperature_min"]}
    found = cotton.ingredients(inputs)
    rain, cold = found["precipitation_3_day_ahead"], found["air_temperature_min_9_day_ahead"]
    full = np.arange(daily["date"].size) <= daily["date"].size - cotton.COLD_DAYS  # both windows inside the year
    np.testing.assert_allclose(rain[full], theirs["precip_3day_forward"][full], atol=1e-9)
    np.testing.assert_allclose(cold[full], theirs["mean_min_temp_9day_forward"][full], atol=1e-9)
    p, _ = cotton.probability_below(rain, cold, 1.0, 45000, 15000, 2025)
    np.testing.assert_allclose(p[full], theirs["probability"][full], rtol=1e-9, atol=1e-12)
    # The tool shrinks the windows at the end of the series; v2 leaves those days without a value
    assert np.isnan(cold[~full]).all() and np.isfinite(theirs["probability"][~full]).all()


def test_cotton_stand_and_interval():
    out = cotton.outputs(
        {
            "precipitation_sum": np.full(12, 10 / 3),
            "air_temperature_min": np.full(12, 12.0),
            "year": np.full(12, 2025.0),
        },
        planting_population="40000",
    )
    emergence, low, high = cotton.emergence_interval(rain_3day=10.0, min_temp_9day=12.0, pythium=1.0, year=2025)
    np.testing.assert_allclose(out["stand"][0], emergence * 40000)
    np.testing.assert_allclose(out["emergence"][0], emergence * 100)
    np.testing.assert_allclose([out["stand_low"][0], out["stand_high"][0]], [low * 40000, high * 40000])
    assert out["stand_low"][0] < out["stand"][0] < out["stand_high"][0]
    # The audit's case: SE 0.026 at Pythium, 10 mm and 12 °C, so the interval is about ±5 points of emergence
    assert 0.04 < high - emergence < 0.06


def test_cotton_year_is_held_at_the_fits_last_year():
    inputs = {"precipitation_sum": np.full(12, 3.0), "air_temperature_min": np.full(12, 15.0)}
    at = {y: cotton.outputs(inputs | {"year": np.full(12, float(y))})["stand"][0] for y in (2024, 2025, 2026, 2040)}
    assert at[2024] < at[2025] == at[2026] == at[2040]
    assert cotton.LAST_FIT_YEAR == 2025


def test_cotton_needs_7_of_9_minimum_temperatures():
    cold = np.full(12, 15.0)
    two_gaps, three_gaps = cold.copy(), cold.copy()
    two_gaps[[1, 5]] = np.nan
    three_gaps[[1, 5, 7]] = np.nan
    rain = np.full(12, 3.0)
    for temps, known in ((two_gaps, True), (three_gaps, False)):
        found = cotton.ingredients({"precipitation_sum": rain, "air_temperature_min": temps})
        assert np.isfinite(found["air_temperature_min_9_day_ahead"][0]) == known


def test_cotton_risk_levels():
    # High below the limit, Moderate from it to under 25% above, Low from 25% above
    stands = np.array([14999, 15000, 18749, 18750, np.nan])
    assert np.array_equal(cotton.risk({"stand": stands}), [2, 1, 1, 0, np.nan], equal_nan=True)
    assert cotton.risk({"stand": np.array([19999, 24999, 25000])}, limiting_population="20000").tolist() == [2, 1, 0]
