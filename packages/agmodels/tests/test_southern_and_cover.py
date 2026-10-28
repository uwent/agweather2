"""Parity with the Crop Risk Tool for pecan scab, cotton planting and rye biomass (D6), and intended differences."""

import numpy as np

from agmodels import features as f
from agmodels.models import cotton_planting as cotton
from agmodels.models import pecan_scab as pecan
from agmodels.models import rye_biomass as rye


def day_of_year(dates) -> np.ndarray:
    d = np.asarray(dates, dtype="datetime64[D]")
    return (d - d.astype("datetime64[Y]")).astype(int) + 1


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


def test_pecan_risk_levels():
    assert [pecan.explore(h)["risk"] for h in (0, 9, 10, 19, 20, 29, 30)] == [0, 0, 1, 1, 2, 2, 3]


# Cotton planting


def test_cotton_model_matches_the_tool(crt):
    s = crt("cotton_planting_sweep")
    p, _ = cotton.probability_below(s["precip"], s["tmin"], s["pythium"], s["pop"], s["limit"], s["year"])
    np.testing.assert_allclose(p, s["probability"], rtol=1e-9, atol=1e-12)


def test_cotton_season_with_full_forward_windows(crt):
    daily, theirs = crt("daily_eau_claire_2025"), crt("cotton_planting_eau_claire_2025")
    inputs = {
        "precipitation_sum": daily["precipitation_daily"],
        "air_temperature_min": daily["temperature_min"],
        "year": np.full(daily["date"].size, 2025.0),
    }
    out = cotton.outputs(inputs, pythium="present", planting_population="45000", limiting_population="15000")
    full = np.arange(daily["date"].size) <= daily["date"].size - cotton.COLD_DAYS  # both windows inside the year
    np.testing.assert_allclose(out["probability"][full] / 100, theirs["probability"][full], rtol=1e-9, atol=1e-12)
    # The tool shrinks the windows at the end of the series; v2 leaves those days without a value
    assert np.isnan(out["probability"][~full]).all() and np.isfinite(theirs["probability"][~full]).all()


def test_cotton_risk_levels():
    assert cotton.risk({"probability": np.array([0.5, 1, 20, 35])}).tolist() == [0, 1, 2, 3]


# Rye biomass


def test_rye_biomass_matches_the_tool(crt):
    s = crt("rye_biomass_sweep")
    np.testing.assert_allclose(rye.biomass(s["gdd"], s["plant_doy"], s["precip_fall"]), s["biomass"], rtol=1e-12)


def test_rye_season_from_a_fall_planting(crt):
    daily, theirs = crt("daily_eau_claire_2025"), crt("rye_biomass_eau_claire_2025_09_15")
    start = int(np.flatnonzero(daily["date"] == theirs["date"][0])[0])
    inputs = {
        "air_temperature_min": daily["temperature_min"][start:],
        "air_temperature_max": daily["temperature_max"][start:],
        "precipitation_sum": daily["precipitation_daily"][start:],
        "day_of_year": day_of_year(daily["date"][start:]),
    }
    out = rye.outputs(inputs)
    np.testing.assert_allclose(out["gdd_total"], theirs["gdd_total"], atol=1e-6)  # no fall day over 35 °C
    np.testing.assert_allclose(out["precipitation_fall"], theirs["precip_fall"], atol=1e-6)
    np.testing.assert_allclose(out["biomass"], theirs["biomass"], rtol=1e-9)


def test_rye_fall_precip_stops_at_new_year():
    days = 120  # Oct 1 to late January
    doy = (np.arange(days) + 273) % 365 + 1
    out = rye.outputs(
        {
            "air_temperature_min": np.zeros(days),
            "air_temperature_max": np.full(days, 10.0),
            "precipitation_sum": np.ones(days),
            "day_of_year": doy,
        }
    )
    new_year = int(np.flatnonzero(doy == 1)[0])
    assert out["precipitation_fall"][new_year - 1] == new_year and out["precipitation_fall"][-1] == new_year
    assert rye.risk({"biomass": np.array([1999, 2000, 4500])}).tolist() == [0, 1, 2]
