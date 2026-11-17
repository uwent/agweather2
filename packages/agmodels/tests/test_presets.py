"""Degree-day presets: each is a setting the calculator can run, and a crop with a stage model gets that model's."""

from agmodels.models import spring_wheat_stages
from agmodels.presets import PRESETS
from agmodels.registry import all_models


def test_ids_are_unique_and_each_has_a_source():
    assert len({p.id for p in PRESETS}) == len(PRESETS)
    for p in PRESETS:
        assert p.citations, p.id
        assert p.freeze is None or p.freeze.citations, p.id


def test_settings_are_ones_the_calculator_runs():
    for p in PRESETS:
        s = p.setting
        assert s.method in ("sine", "modified", "average"), p.id
        assert 25 <= s.base_f <= 60, p.id  # the API's usual range of bases
        assert s.upper_f is None or s.base_f < s.upper_f <= 104, p.id


def test_a_crop_with_a_stage_model_has_that_models_setting():
    models = all_models()
    for p in PRESETS:
        if p.model is None or p.model == spring_wheat_stages.SPEC.id:
            continue
        settings = [i.degree_days for i in models[p.model].SPEC.ingredients if i.degree_days is not None]
        assert settings == [p.setting], p.id
    wheat = next(p for p in PRESETS if p.model == spring_wheat_stages.SPEC.id)
    # The wheat model's GDD aren't a stored setting: its base, and the cap it keeps after Haun 2.0
    assert (wheat.setting.base_f, wheat.setting.upper_f) == (spring_wheat_stages.BASE_F, spring_wheat_stages.LATE_CAP_F)
