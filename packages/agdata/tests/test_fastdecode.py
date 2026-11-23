"""The parallel decode (`agdata.fastdecode`) gives NumPy's float64 decode rounded to float32, exactly; the parallel
encode gives NumPy's encode exactly."""

import numpy as np

from agdata.catalog import DAILY_VARIABLES, FILL


def test_a_parallel_float32_decode_is_float64s_values_rounded():
    rng = np.random.default_rng(2)
    for name in ("air_temperature_min", "precipitation_sum", "et0_sum"):
        v = DAILY_VARIABLES[name]
        packed = rng.integers(-32767, 32767, (50, 60, 70)).astype(np.int16)
        packed[rng.random(packed.shape) < 0.1] = FILL
        found = v.decode(packed, dtype=np.float32)  # 210,000 values: the kernel
        expected = v.decode(packed).astype(np.float32)
        assert found.dtype == np.float32
        np.testing.assert_array_equal(found, expected)
    from agdata import catalog, fastdecode

    assert packed.size > catalog.DECODE_PARALLEL  # the test went through the kernel
    np.testing.assert_array_equal(
        fastdecode.decode_float32(packed[:1, :1, :1], v.scale, v.offset), expected[:1, :1, :1]
    )


def _numpy_encode(v, values):
    """`Variable.encode`'s NumPy path, the reference."""
    values = np.asarray(values, dtype=np.float64)
    missing = ~np.isfinite(values)
    packed = np.round((np.where(missing, 0.0, values) - v.offset) / v.scale)
    packed[missing] = FILL
    return packed.astype(np.int16)


def test_a_parallel_encode_is_numpys_exactly():
    import pytest

    from agdata import catalog
    from agdata.catalog import VARIABLES

    rng = np.random.default_rng(3)
    for v in [VARIABLES["air_temperature"], DAILY_VARIABLES["precipitation_sum"]]:
        packed = rng.integers(-32767, 32767, (40, 60, 70)).astype(np.int16)
        values = v.decode(packed)
        values += rng.uniform(-0.6, 0.6, values.shape) * v.scale  # between codes, halves included below
        values.ravel()[:1000] = (packed.ravel()[:1000].astype(np.float64) + 0.5) * v.scale + v.offset
        values[rng.random(values.shape) < 0.1] = np.nan
        values = np.clip(values, *v.decode(np.array([FILL + 1, 32767], dtype=np.int16)))
        assert values.size > catalog.DECODE_PARALLEL
        for given in (values, values.astype(np.float32)):
            np.testing.assert_array_equal(v.encode(given), _numpy_encode(v, given))
    too_big = np.full((50, 50, 50), 1e9)
    with pytest.raises(ValueError, match="int16"):
        VARIABLES["air_temperature"].encode(too_big)
