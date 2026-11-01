"""Every model spec against the data layer: units the units module knows (agmodels can't import agdata)."""

import pytest

from agdata.units import unit
from agmodels.registry import all_models


@pytest.mark.parametrize("model_id", list(all_models()))
def test_spec_units_are_known(model_id):
    spec = all_models()[model_id].SPEC
    for quantity in (*spec.inputs, *spec.outputs, *spec.explorer):
        assert unit(quantity.unit).symbol == quantity.unit  # raises for a unit the units module doesn't know


@pytest.mark.parametrize("model_id", list(all_models()))
def test_inputs_are_in_the_daily_store(model_id):
    from agdata.catalog import DAILY_VARIABLES

    spec = all_models()[model_id].SPEC
    assert {q.name for q in spec.inputs} <= set(DAILY_VARIABLES), "the grid can only run models on stored days"
    assert spec.lookback_days >= 0


def test_every_insect_has_degree_day_cubes():
    """Maps of an insect come from the running-total cubes: one per threshold, a pair being their difference (D26)."""
    from agdata.catalog import DD_SINE_THRESHOLDS_F
    from agmodels.registry import all_insects

    for insect in all_insects():
        if insect.dd_method != "sine":  # an average needs only the day's min and max, computed on read
            continue
        thresholds = {insect.base_f} | ({insect.upper_f} if insect.upper_f is not None else set())
        assert thresholds <= set(DD_SINE_THRESHOLDS_F), insect.id


def test_regions_are_states():
    """Region masks come from the county grid's states (`agdata.places`), so every state a model names must be in it."""
    from agdata.places import counties

    states = {c.state for c in counties() if c}
    for model in all_models().values():
        assert set(model.SPEC.region) <= states, model.SPEC.id
