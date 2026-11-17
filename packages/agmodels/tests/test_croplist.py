"""The crop vocabulary: every crop a model, topic page, preset or planting table names is in it, and groups hold
crops."""

from pathlib import Path

import yaml

from agmodels import croplist
from agmodels.presets import all_presets
from agmodels.registry import all_models

ROOT = Path(__file__).parents[3]


def test_groups_hold_single_crops():
    for c in croplist.CROPS.values():
        for member in c.members:
            assert member in croplist.CROPS and not croplist.CROPS[member].members, (c.id, member)


def test_models_presets_and_planting_name_known_crops():
    from agdata.planting import CROPS as PLANTING

    for model_id, module in all_models().items():
        assert all(c in croplist.CROPS for c in module.SPEC.crops), model_id
    for p in all_presets():
        assert all(c in croplist.CROPS for c in p.crops), p.id
    assert set(PLANTING) <= set(croplist.CROPS)


def test_topic_pages_name_known_crops():
    for path in (ROOT / "content" / "topics").glob("*.md"):
        front = yaml.safe_load(path.read_text().split("\n---\n", 1)[0].removeprefix("---\n"))
        assert all(c in croplist.CROPS for c in front.get("crops") or []), path.name


def test_a_crop_finds_its_groups_models_and_a_group_its_crops():
    assert croplist.applies(("cole-crops",), "broccoli")
    assert croplist.applies(("broccoli",), "cole-crops")
    assert croplist.applies(("wheat",), "spring-wheat") and croplist.applies(("spring-wheat",), "wheat")
    assert not croplist.applies(("corn",), "sweet-corn")
    assert croplist.groups_of("dry-bean") == ["beans"]
