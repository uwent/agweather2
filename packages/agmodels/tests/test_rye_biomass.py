import numpy as np


def test_biomass_stays_0_after_a_very_wet_fall():
    from agmodels.models.rye_biomass import biomass

    values = biomass(2000, 300, np.array([0.0, 200.0, 395.0, 500.0, 800.0]))
    assert (np.diff(values) <= 0).all() and values[-1] == 0
