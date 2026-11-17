"""Degree-day presets: each is a setting the calculator can run, and a crop with a stage model gets that model's."""

from agmodels.models import spring_wheat_stages
from agmodels.presets import CROP_PRESETS, all_presets, insect_presets
from agmodels.registry import all_models


def test_ids_are_unique_and_each_has_a_source():
    presets = all_presets()
    assert len({p.id for p in presets}) == len(presets)
    for p in presets:
        assert p.citations, p.id
        assert p.freeze is None or p.freeze.citations, p.id


def test_settings_are_ones_the_calculator_runs():
    for p in all_presets():
        s = p.setting
        assert s.method in ("sine", "modified", "average"), p.id
        assert 25 <= s.base_f <= 60, p.id  # the API's usual range of bases
        assert s.upper_f is None or s.base_f < s.upper_f <= 104, p.id


def test_a_crop_with_a_stage_model_has_that_models_setting():
    models = all_models()
    for p in CROP_PRESETS:
        if p.model is None or p.model == spring_wheat_stages.SPEC.id:
            continue
        settings = [i.degree_days for i in models[p.model].SPEC.ingredients if i.degree_days is not None]
        assert settings == [p.setting], p.id
    wheat = next(p for p in CROP_PRESETS if p.model == spring_wheat_stages.SPEC.id)
    # The wheat model's GDD aren't a stored setting: its base, and the cap it keeps after Haun 2.0
    assert (wheat.setting.base_f, wheat.setting.upper_f) == (spring_wheat_stages.BASE_F, spring_wheat_stages.LATE_CAP_F)


def test_each_insect_model_gives_a_preset_with_its_setting_and_biofix():
    insects = {p.id: p for p in insect_presets()}
    weevil = insects["alfalfa-weevil"]
    assert (weevil.setting.method, weevil.setting.base_f, weevil.setting.upper_f) == ("sine", 48.2, 86)
    assert weevil.group == "insect" and weevil.starts == "biofix" and weevil.biofix == "01-01"
    assert insects["corn-earworm"].biofix == "08-01"
    # The beetle's adults and larvae models count as the beetle does: one preset
    assert "colorado-potato-beetle" in insects and "colorado-potato-beetle-adults" not in insects
    modelled = {m for m, mod in all_models().items() if mod.SPEC.group == "insect"}
    assert set(insects) <= modelled and len(insects) == len(modelled) - 2
