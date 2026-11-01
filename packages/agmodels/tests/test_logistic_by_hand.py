"""The logistic field-crop models at chosen inputs, computed here with `math` from the published coefficients
(Willbur et al. 2018 for white mold; Smith et al. and Webster for tar spot, gray leaf spot and frogeye leaf spot: the
numbers printed in each model's module), independent of `agmodels.probability.logistic` and of the Crop Risk Tool's
fixtures."""

import math

import numpy as np
import pytest

from agmodels.models import frogeye, gray_leaf_spot, tar_spot, white_mold
from agmodels.probability import attenuate_for_cold


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def test_white_mold_dry_averages_three_logistic_models():
    # 30-day mean max 25 °C, max wind 3 m/s, max RH 90 %: the three logits worked out by hand
    m1 = -0.47 * 25 - 1.01 * 3 + 16.65  # 1.87
    m2 = -0.68 * 25 + 17.19  # 0.19
    m3 = -0.86 * 25 + 0.1 * 90 - 0.75 * 3 + 8.2  # -6.55
    assert (m1, m2, m3) == pytest.approx((1.87, 0.19, -6.55))
    expected = (sigmoid(m1) + sigmoid(m2) + sigmoid(m3)) / 3
    assert float(white_mold.probability_dry(25, 3, 90)) == pytest.approx(expected)
    assert expected == pytest.approx(0.4717, abs=1e-4)


@pytest.mark.parametrize(("spacing", "row"), [("30", 1), ("15", 0)])
def test_white_mold_irrigated_by_hand(spacing, row):
    logit = -52.65 - 2.38 * row + 0.65 * 30 + 0.38 * 90
    assert float(white_mold.probability_irrigated(30, 90, spacing)) == pytest.approx(sigmoid(logit))
    assert sigmoid(logit) == pytest.approx(0.2092 if row else 0.7408, abs=1e-4)


def test_white_mold_in_a_cold_spell_is_scaled_down_by_the_21_day_minimum():
    # A warm, humid 30 days whose 21-day mean minimum is 4 °C: the probability is multiplied by 4 / 10
    n = 40
    inputs = {
        "air_temperature_max": np.full(n, 25.0),
        "air_temperature_min": np.full(n, 4.0),
        "relative_humidity_max": np.full(n, 90.0),
        "wind_speed_max": np.full(n, 3.0),
    }
    raw = float(white_mold.probability_dry(25, 3, 90))
    out = white_mold.outputs(inputs)["probability"]
    assert out[-1] == pytest.approx(raw * 0.4)
    colder = white_mold.outputs(inputs | {"air_temperature_min": np.full(n, -2.0)})["probability"]
    assert colder[-1] == 0  # at or under 0 °C nothing
    assert float(attenuate_for_cold(0.5, 12)) == 0.5  # over 10 °C unscaled


def test_white_mold_irrigated_risk_uses_its_own_cutoffs():
    # irrigated: Low from 1 %, Moderate from 5 %, High from 10 %; dry: Low from 1 %, Moderate from 20 %, High from 35 %
    outputs = {"probability": np.array([0.005, 0.04, 0.06, 0.12, 0.25])}
    np.testing.assert_array_equal(white_mold.risk(outputs, irrigation="irrigated"), [0, 1, 2, 3, 3])
    np.testing.assert_array_equal(white_mold.risk(outputs), [0, 1, 1, 1, 2])


def test_tar_spot_averages_two_logistic_models():
    # 30-day mean temperature 20 °C, max RH 95 %, 14-day mean night hours with RH ≥ 90 % of 8
    a = 32.06987 - 0.89471 * 20 - 0.14373 * 95  # 0.5213
    b = 20.35950 - 0.91093 * 20 - 0.29240 * 8
    expected = (sigmoid(a) + sigmoid(b)) / 2
    assert float(tar_spot.probability(20, 95, 8)) == pytest.approx(expected)
    assert expected == pytest.approx(0.5390, abs=1e-4)


def test_gray_leaf_spot_and_frogeye_by_hand():
    assert float(gray_leaf_spot.probability(14, 12)) == pytest.approx(sigmoid(-2.9467 - 0.03729 * 14 + 0.6534 * 12))
    assert float(frogeye.probability(27, 12)) == pytest.approx(sigmoid(-5.92485 + 0.12208 * 27 + 0.17326 * 12))
    assert sigmoid(-5.92485 + 0.12208 * 27 + 0.17326 * 12) == pytest.approx(0.3660, abs=1e-4)
