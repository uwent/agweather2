"""Parity with the Crop Risk Tool for the field-crop models, over its recorded 2025 at Eau Claire."""

import numpy as np
import pytest

from agmodels.models import (
    don,
    frogeye,
    gray_leaf_spot,
    red_crown_rot,
    soybean_cercospora,
    tar_spot,
    wheat_scab,
    white_mold,
)
from agmodels.probability import risk_level


@pytest.fixture
def inputs(crt):
    daily, more = crt("daily_eau_claire_2025"), crt("daily_more_eau_claire_2025")
    return {
        "air_temperature_min": daily["temperature_min"],
        "air_temperature_max": daily["temperature_max"],
        "air_temperature_mean": more["temperature_mean"],
        "relative_humidity_min": more["relative_humidity_min"],
        "relative_humidity_mean": more["relative_humidity_mean"],
        "relative_humidity_max": more["relative_humidity_max"],
        "dew_point_min": more["dew_point_min"],
        "dew_point_depression_mean": more["dew_point_depression_mean"],
        "dew_point_depression_max": more["dew_point_depression_max"],
        "wind_speed_max": more["wind_speed_max"] / 3.6,  # the tool's km/h to v2's m/s
        "hours_rh_over_80": daily["hours_rh_over_80"],
        "hours_rh_over_90": daily["hours_rh_over_90"],
        "hours_rh_over_90_night": daily["hours_rh_over_90_night"],
        "precipitation_sum": daily["precipitation_daily"],
    }


@pytest.mark.parametrize(
    ("module", "fixture", "options"),
    [
        (tar_spot, "tar_spot_eau_claire_2025", {}),
        (gray_leaf_spot, "gray_leaf_spot_eau_claire_2025", {}),
        (frogeye, "frogeye_eau_claire_2025", {}),
        (white_mold, "white_mold_dry_eau_claire_2025", {"irrigation": "dry"}),
        (white_mold, "white_mold_irrigated_30_eau_claire_2025", {"irrigation": "irrigated", "row_spacing": "30"}),
        (white_mold, "white_mold_irrigated_15_eau_claire_2025", {"irrigation": "irrigated", "row_spacing": "15"}),
    ],
)
def test_probability_matches(crt, inputs, module, fixture, options):
    np.testing.assert_allclose(module.outputs(inputs, **options)["probability"], crt(fixture)["probability"], atol=1e-9)


def test_don_matches_after_its_lag(crt, inputs):
    ours = don.outputs(inputs)["probability"]
    assert np.isnan(ours[:7]).all()  # the 21-to-7-day window doesn't exist yet (the tool drops those rows)
    np.testing.assert_allclose(ours[7:], crt("don_eau_claire_2025")["probability"], atol=1e-9)


def test_soybean_cercospora_species_match(crt, inputs):
    theirs = crt("soybean_cercospora_eau_claire_2025")
    ours = soybean_cercospora.outputs(inputs)
    for name, column in [
        ("probability_flagellaris", "C. flagellaris"),
        ("probability_sigesbeckiae", "C. sigesbeckiae"),
        ("probability_kikuchii", "C. kikuchii"),
    ]:
        np.testing.assert_allclose(ours[name], theirs[column], atol=1e-9)


def test_wheat_scab_resistance_classes_match(crt, inputs):
    theirs = crt("wheat_scab_eau_claire_2025")
    for key, (label, _) in wheat_scab.RESISTANCE.items():
        out = wheat_scab.outputs(inputs, resistance=key)
        np.testing.assert_allclose(out["probability"], theirs[label], atol=1e-9)


def test_red_crown_rot_matches_from_r1(crt, inputs):
    theirs = crt("red_crown_rot_r1_2025_07_01_eau_claire_2025")
    out = red_crown_rot.outputs(inputs, biofix_index=181)  # July 1
    np.testing.assert_allclose(out["incidence"], theirs["incidence"], atol=1e-9, equal_nan=True)
    np.testing.assert_allclose(out["precipitation_vegetative"], theirs["precipitation_veg"], atol=1e-9, equal_nan=True)
    np.testing.assert_allclose(
        out["temperature_mean_reproductive"], theirs["temperature_mean_rep"], atol=1e-9, equal_nan=True
    )


def test_red_crown_rot_counts_missing_rain_as_none(inputs):
    full = red_crown_rot.outputs(inputs, biofix_index=181)
    assert np.all(full["precipitation_days_missing"][150:] == 0)

    precip = inputs["precipitation_sum"].copy()
    precip[[160, 170, 190]] = np.nan  # two days before R1, one after
    out = red_crown_rot.outputs({**inputs, "precipitation_sum": precip}, biofix_index=181)
    rain = inputs["precipitation_sum"]
    np.testing.assert_allclose(out["precipitation_vegetative"][181], np.sum(rain[150:181]) - rain[160] - rain[170])
    after = 181 + red_crown_rot.WINDOW
    np.testing.assert_allclose(out["precipitation_reproductive"][after - 1 :], np.sum(rain[181:after]) - rain[190])
    assert out["precipitation_days_missing"][175] == 2
    assert out["precipitation_days_missing"][185] == 2
    assert out["precipitation_days_missing"][-1] == 3
    assert np.isnan(out["precipitation_days_missing"][149])


def test_red_crown_rot_counts_the_window_before_the_series_as_missing(inputs):
    out = red_crown_rot.outputs(inputs, biofix_index=10)
    assert out["precipitation_days_missing"][0] == red_crown_rot.WINDOW - 10
    np.testing.assert_allclose(out["precipitation_vegetative"][10], np.sum(inputs["precipitation_sum"][:10]))


def test_probability_levels_match(crt):
    sweep = crt("risk_from_prob_sweep")
    np.testing.assert_array_equal(risk_level(sweep["probability"], 1, 20, 35), sweep["risk_1_20_35"])
    np.testing.assert_array_equal(risk_level(sweep["probability"], 1, 5, 10), sweep["risk_1_5_10"])
