"""The parallel decode (`agdata.fastdecode`) gives NumPy's float64 decode rounded to float32, exactly."""

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
