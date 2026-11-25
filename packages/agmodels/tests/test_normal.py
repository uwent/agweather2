"""The Numba kernel for the normal CDF (`agmodels.normal`) gives the `math.erf` reference's values exactly."""

import numpy as np

from agmodels.normal import PARALLEL_SIZE, _cdf_kernel, normal_cdf, normal_cdf_reference


def test_the_kernel_matches_the_reference_to_the_bit():
    rng = np.random.default_rng(7)
    z = np.concatenate([rng.normal(0, 3, 20_000), [np.nan, np.inf, -np.inf, 0.0, -40.0, 40.0]])
    assert z.size >= PARALLEL_SIZE  # through the kernel
    expected = normal_cdf_reference(z)
    np.testing.assert_array_equal(normal_cdf(z), expected)
    np.testing.assert_array_equal(_cdf_kernel(z[:10]), expected[:10])  # finite values: no warning
    assert np.isnan(expected[-6:-3]).all()  # not finite: missing


def test_a_few_values_go_through_the_reference():
    found = normal_cdf(np.array([0.0, 1.959963984540054]))
    np.testing.assert_allclose(found, [0.5, 0.975], atol=1e-12)
