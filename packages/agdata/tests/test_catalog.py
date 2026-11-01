import numpy as np
import pytest

from agdata.catalog import FILL, VARIABLES, Variable, variable


def test_encode_decode_round_trip_within_precision():
    temp = variable("air_temperature")
    values = np.array([-40.0, 0.0, 21.234, np.nan, 59.96])
    packed = temp.encode(values)
    assert packed.dtype == np.int16
    assert packed[3] == FILL
    np.testing.assert_allclose(temp.decode(packed), values, atol=temp.scale / 2)


def test_pressure_encoding():
    pressure = variable("surface_pressure")
    np.testing.assert_allclose(pressure.decode(pressure.encode(np.array([98.76, 101.3]))), [98.76, 101.3], atol=0.05)


def test_zero_is_not_missing():
    rain = variable("precipitation")
    assert rain.decode(rain.encode(np.array([0.0])))[0] == 0.0


def test_encoding_refuses_values_it_cant_hold():
    with pytest.raises(ValueError, match="air_temperature: values outside what int16 can hold"):
        variable("air_temperature").encode(np.array([4000.0]))


def test_every_variable_can_hold_its_qc_range():
    for v in VARIABLES.values():
        np.testing.assert_allclose(
            v.decode(v.encode(np.array([v.valid_min, v.valid_max]))), [v.valid_min, v.valid_max], atol=v.scale
        )


def test_a_variable_that_cant_hold_its_range_is_rejected():
    with pytest.raises(ValueError, match=r"bad: int16 .* can't hold 0\.\.1000"):
        Variable(name="bad", long_name="Too narrow", unit="mm", scale=0.001, valid_min=0, valid_max=1000)
    with pytest.raises(ValueError, match="unknown unit 'furlongs'"):
        Variable(name="bad", long_name="Unknown unit", unit="furlongs", scale=1)


def test_every_daily_variable_says_how_a_missing_day_is_estimated():
    from agdata.catalog import DAILY_VARIABLES, GAP_FILL

    assert set(GAP_FILL) == set(DAILY_VARIABLES)
    assert GAP_FILL["precipitation_sum"] == "zero"  # never estimated (D45)
