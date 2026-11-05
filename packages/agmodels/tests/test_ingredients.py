"""Every model's ingredients (D66): declared, composed into its outputs, and finished day by day, as a map does."""

import numpy as np
import pytest

from agmodels import runner
from agmodels.ingredients import CONTEXT, Accumulation, accumulate, with_accumulations
from agmodels.registry import all_models, model
from agmodels.testing import DATES, DAYS, LATITUDE, WEATHER

# Models a map can't finish from ingredients: day-by-day state machines (soybean stages; spring wheat's cap
# switches at Haun 2.0 on its own running total), red crown rot's windows either side of R1, and custom degree days,
# whose daily values depend on the options (any setting, served from min and max by `/grids`, D65)
WITHOUT_INGREDIENTS = {"soybean-stages", "spring-wheat-stages", "red-crown-rot", "degree-days"}

BIOFIX = 140  # inside the series, after its first New Year


def _inputs(m, shape=(2, 3)) -> dict[str, np.ndarray]:
    """The model's inputs from the year of weather, each cell warmed or cooled by a few degrees."""
    shifts = np.linspace(-4, 4, int(np.prod(shape))).reshape(shape)
    inputs = {}
    for q in m.SPEC.inputs:
        series = WEATHER[q.name][(slice(None), None, None)]
        inputs[q.name] = np.broadcast_to(series + (shifts if q.unit == "degC" else 0.0), (DAYS, *shape)).copy()
    context = runner._context(DATES, LATITUDE)
    return inputs | {name: context[name] for name in m.SPEC.context}


def _with_ingredients():
    return sorted(i for i, m in all_models().items() if m.SPEC.ingredients)


def test_every_model_but_the_listed_has_ingredients():
    assert set(all_models()) - set(_with_ingredients()) == WITHOUT_INGREDIENTS


@pytest.mark.parametrize("model_id", _with_ingredients())
def test_declared_ingredients_are_what_the_model_computes(model_id):
    m = model(model_id)
    values = m.ingredients(_inputs(m))  # type: ignore[attr-defined]
    assert set(values) == {i.name for i in m.SPEC.ingredients}, model_id
    names = set(values)
    for a in m.SPEC.accumulations:
        assert a.of in names, f"{model_id}: {a.name} accumulates an unknown ingredient {a.of}"
    assert not {a.name for a in m.SPEC.accumulations} & names, f"{model_id}: an accumulation shadows an ingredient"


@pytest.mark.parametrize("model_id", _with_ingredients())
def test_finish_is_day_by_day(model_id):
    """A day's outputs and risk from that day's ingredients, accumulations and context alone: a map finishes one
    day per cell from what it stored, without the season around it."""
    m = model(model_id)
    inputs = _inputs(m)
    values = m.ingredients(inputs)  # type: ignore[attr-defined]
    full = dict(values) | accumulate(values, m.SPEC.accumulations, BIOFIX, day_of_year=inputs.get("day_of_year"))
    full |= {name: np.asarray(inputs[name], dtype=float) for name in CONTEXT if name in inputs}
    if "day_of_year" in inputs:
        full["biofix_day_of_year"] = np.asarray(inputs["day_of_year"][BIOFIX])
    season = m.finish(full)  # type: ignore[attr-defined]
    assert set(season) == {q.name for q in m.SPEC.outputs}, model_id
    np.testing.assert_equal(m.outputs(inputs, biofix_index=BIOFIX), season)
    risk = m.risk(season | _accumulated(full, m.SPEC.accumulations)) if m.SPEC.risk else None
    for k in (0, BIOFIX - 1, BIOFIX, BIOFIX + 7, 300, DAYS - 1):
        day = {name: (v[k : k + 1] if np.ndim(v) and v.shape[0] == DAYS else v) for name, v in full.items()}
        one = m.finish(day)  # type: ignore[attr-defined]
        for name, v in season.items():
            np.testing.assert_allclose(one[name], v[k : k + 1], equal_nan=True, err_msg=f"{model_id} {name} day {k}")
        if risk is not None:
            r = m.risk(one | _accumulated(day, m.SPEC.accumulations))
            np.testing.assert_allclose(r, risk[k : k + 1], equal_nan=True, err_msg=f"{model_id} risk day {k}")


def _accumulated(values, accumulations: tuple[Accumulation, ...]):
    return {a.name: values[a.name] for a in accumulations}


def test_a_risk_given_only_daily_values_accumulates_them():
    acc = (Accumulation(name="t", of="x"), Accumulation(name="s", of="x", how="sum", days=2))
    x = np.array([1.0, np.nan, 2.0, 3.0])
    out = with_accumulations({"x": x}, acc, biofix_index=1)
    np.testing.assert_equal(out["t"], [np.nan, 0, 2, 5])
    np.testing.assert_equal(out["s"], [np.nan, 0, 2, 5])
    given = with_accumulations({"x": x, "t": np.zeros(4)}, acc)
    np.testing.assert_equal(given["t"], np.zeros(4))  # what's there is used as it is


def test_a_year_end_total_stops_at_december_31():
    doy = np.array([364.0, 365, 1, 2])
    acc = (Accumulation(name="fall", of="rain", year_end=True),)
    out = accumulate({"rain": np.ones(4)}, acc, biofix_index=0, day_of_year=doy)
    np.testing.assert_equal(out["fall"], [1, 2, 2, 2])
