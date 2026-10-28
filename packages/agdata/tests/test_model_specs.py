"""Every model spec against the data layer: units the units module knows (agmodels can't import agdata)."""

import pytest

from agdata.units import unit
from agmodels.registry import all_models


@pytest.mark.parametrize("model_id", list(all_models()))
def test_spec_units_are_known(model_id):
    spec = all_models()[model_id].SPEC
    for quantity in (*spec.inputs, *spec.outputs, *spec.explorer):
        unit(quantity.unit)
