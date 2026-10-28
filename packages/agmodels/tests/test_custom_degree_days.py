"""Custom degree days: any thresholds, method and unit, over the same functions as the models."""

import numpy as np
import pytest

from agmodels.degree_days import degree_days_modified, degree_days_sine
from agmodels.models import custom_degree_days as cdd

LO, HI = np.array([5.0, 12.0, 20.0, np.nan]), np.array([18.0, 28.0, 35.0, 30.0])  # °C
INPUTS = {"air_temperature_min": LO, "air_temperature_max": HI}


def test_defaults_are_sine_50_86_f():
    out = cdd.outputs(INPUTS)
    np.testing.assert_allclose(out["dd"][:3], degree_days_sine(LO[:3] * 1.8 + 32, HI[:3] * 1.8 + 32, 50, 86))
    assert np.isnan(out["dd"][3]) and out["dd_total"][-1] == out["dd_total"][-2]  # a missing day adds nothing


def test_celsius_thresholds_give_the_same_degree_days_in_f():
    f = cdd.outputs(INPUTS, base="50", upper="86", unit="F")["dd"]
    c = cdd.outputs(INPUTS, base="10", upper="30", unit="C")["dd"]
    np.testing.assert_allclose(c, f)
    np.testing.assert_allclose(c[:3] * 5 / 9, degree_days_sine(LO[:3], HI[:3], 10, 30))  # °C·d are 5/9 of °F·d


def test_methods_options_and_biofix():
    out = cdd.outputs(INPUTS, method="modified", base="50", upper="86", unit="F")
    np.testing.assert_allclose(out["dd"][:3], degree_days_modified(LO[:3] * 1.8 + 32, HI[:3] * 1.8 + 32, 50, 86))
    no_upper = cdd.outputs(INPUTS, method="sine", base="41", upper="none")["dd"]
    assert no_upper[2] > cdd.outputs(INPUTS, method="sine", base="41", upper="86")["dd"][2]
    assert np.isnan(cdd.outputs(INPUTS, biofix_index=2)["dd_total"][:2]).all()
    with pytest.raises(ValueError, match="upper"):
        cdd.outputs(INPUTS, method="average", upper="86")
    with pytest.raises(ValueError, match="base"):
        cdd.outputs(INPUTS, base="warm")
