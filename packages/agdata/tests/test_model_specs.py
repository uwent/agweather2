"""Every model spec against the data layer: units the units module knows (agmodels can't import agdata)."""

import numpy as np
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


def _degree_day_ingredients():
    return [(m.SPEC.id, i) for m in all_models().values() for i in m.SPEC.ingredients if i.degree_days is not None]


@pytest.mark.parametrize(("model_id", "ingredient"), _degree_day_ingredients(), ids=lambda x: getattr(x, "name", x))
def test_degree_day_ingredients_are_the_shared_running_totals(model_id, ingredient):
    """A map reads a model's degree days from the cumulative store's totals (D26), so each setting a model declares
    must be one, and summing the model's own daily values must give it (to float precision; stored to 0.5)."""
    from agdata.cumulative import MAX_BRIDGE_DAYS, running_totals
    from agdata.grids import cube_terms
    from agdata.units import convert
    from agmodels.registry import model
    from agmodels.testing import WEATHER

    dd = ingredient.degree_days
    terms = cube_terms(dd.method, dd.base_f, dd.upper_f)
    assert terms is not None, f"{model_id}: no running total for {dd}"
    pad = np.full(MAX_BRIDGE_DAYS, np.nan)
    tmin, tmax = (
        np.r_[pad, WEATHER[n][:365], pad][:, None, None] for n in ("air_temperature_min", "air_temperature_max")
    )
    nan = np.full_like(tmin, np.nan)
    totals = running_totals(tmin, tmax, nan, nan)
    cube = totals[terms[0]] - (totals[terms[1]] if terms[1] else 0.0)
    m = model(model_id)
    inputs = {
        "air_temperature_min": tmin[MAX_BRIDGE_DAYS:-MAX_BRIDGE_DAYS],
        "air_temperature_max": tmax[MAX_BRIDGE_DAYS:-MAX_BRIDGE_DAYS],
    }
    inputs |= {"day_of_year": np.arange(1, 366, dtype=float), "year": np.full(365, 2025.0)}
    inputs |= {q.name: np.zeros_like(inputs["air_temperature_min"]) for q in m.SPEC.inputs if q.name not in inputs}
    own = np.cumsum(m.ingredients(inputs)[ingredient.name], axis=0)  # type: ignore[attr-defined]
    np.testing.assert_allclose(convert(cube[:, 0, 0], "degF_day", ingredient.unit), own[:, 0, 0], atol=0.01)


def test_regions_are_states():
    """Region masks come from the county grid's states (`agdata.places`), so every state a model names must be in it."""
    from agdata.places import counties

    states = {c.state for c in counties() if c}
    for model in all_models().values():
        assert set(model.SPEC.region) <= states, model.SPEC.id


def test_names_are_current():
    """`agmodels/names.py` types model specs' names from the catalog; regenerate it with `bin/types`."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "scripts/generate_names.py"
    spec = importlib.util.spec_from_file_location("generate_names", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.TARGET.read_text() == module.render(), "agmodels/names.py is stale: run bin/types"
