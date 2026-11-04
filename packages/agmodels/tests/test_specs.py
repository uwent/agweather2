"""What every model's spec must carry (CLAUDE.md, "One model, one file"), over the whole registry."""

import inspect
import re

import pytest

from agmodels.registry import all_models, page_path
from agmodels.spec import Model

MODELS = sorted(all_models().items())
IDS = [model_id for model_id, _ in MODELS]


@pytest.mark.parametrize(("model_id", "m"), MODELS, ids=IDS)
def test_a_spec_has_its_required_elements(model_id, m: Model):
    spec = m.SPEC
    assert spec.id == model_id and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", spec.id)
    assert re.fullmatch(r"0\.\d+", spec.version), f"{model_id}: versions stay 0.x until launch (D46)"
    assert spec.status in ("beta", "stable", "retired")
    assert spec.name and spec.summary and spec.outputs and spec.inputs
    assert spec.citations, f"{model_id} cites nothing"
    assert all(c.text for c in spec.citations)
    assert spec.sweep, f"{model_id} has no sweep"
    assert spec.changelog and spec.changelog[-1].version == spec.version, f"{model_id}: changelog ends at its version"
    assert page_path(model_id).exists()
    if spec.season is not None:
        assert all(re.fullmatch(r"\d\d-\d\d", day) for day in spec.season)
    if spec.biofix is not None:
        assert re.fullmatch(r"\d\d-\d\d", spec.biofix.default)
    assert all(re.fullmatch(r"[A-Z]{2}", state) for state in spec.region)


@pytest.mark.parametrize(("model_id", "m"), MODELS, ids=IDS)
def test_the_sweep_runs_the_explorer_inputs_through_explore(model_id, m: Model):
    spec = m.SPEC
    explorer = {e.name: e for e in spec.explorer}
    assert set(spec.sweep) <= set(explorer), f"{model_id}: sweep names inputs the explorer lacks"
    for name, values in spec.sweep.items():
        assert values == tuple(sorted(set(values))), f"{model_id}: sweep of {name} should be ascending and distinct"
    for e in spec.explorer:
        assert e.minimum <= e.default <= e.maximum and e.step > 0, f"{model_id}: {e.name}"
    accepted = set(inspect.signature(m.explore).parameters)
    assert accepted == set(explorer) or "values" in accepted, f"{model_id}: explore() takes {accepted}"
    defaults = {e.name: e.default for e in spec.explorer}
    assert m.explore(**defaults), model_id


@pytest.mark.parametrize(("model_id", "m"), MODELS, ids=IDS)
def test_risk_and_options_are_consistent(model_id, m: Model):
    spec = m.SPEC
    assert (spec.risk is None) == (spec.group in ("crop", "degree_days")), (
        f"{model_id}: only growth-stage and degree-day models have no risk"
    )
    for option in spec.options:
        if option.choices:
            assert option.default in {value for value, _ in option.choices}, f"{model_id}: {option.name}"
    if spec.risk is not None and spec.risk.thresholds:
        assert len(spec.risk.thresholds) == len(spec.risk.levels) - 1
        assert list(spec.risk.thresholds) == sorted(spec.risk.thresholds)


def test_citations_with_a_doi_are_the_journal_articles_and_the_rest_name_a_source():
    """Citations without a DOI are extension pages, tools and reports (their URL is the copy to read); a citation
    with neither a DOI nor a URL must say whose work it is (a tool, a person or "unpublished")."""
    for m in all_models().values():
        for c in m.SPEC.citations:
            if not c.doi and not c.url:
                assert re.search(r"Crop Risk Tool|VDIFN|unpublished|Unpublished|\(\d{4}\)", c.text), (m.SPEC.id, c.text)


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_every_explore_output_is_declared_with_a_unit(model_id):
    """`POST /models/{id}/evaluate` shows explore()'s values in the request's units, so each needs one."""
    m = all_models()[model_id]
    declared = {q.name for q in (*m.SPEC.outputs, *m.SPEC.explorer_outputs)}
    values = m.explore(**{e.name: e.default for e in m.SPEC.explorer})
    assert set(values) <= declared, f"undeclared: {sorted(set(values) - declared)}"
    assert not {q.name for q in m.SPEC.explorer_outputs} & {q.name for q in m.SPEC.outputs}
