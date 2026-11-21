"""A place inside or outside a model's training area (D101)."""

from agdata.places import County
from agdata.series import outside_training_area
from agmodels.registry import all_models


def _county(geoid: str, state: str) -> County:
    return County(geoid=geoid, name="Test County", state=state, land_m2=1, cells=1)


def test_a_place_is_outside_unless_its_county_or_state_is_listed():
    beetle = all_models()["colorado-potato-beetle"].SPEC
    assert not outside_training_area(beetle, _county("55001", "WI"))  # Adams County
    assert outside_training_area(beetle, _county("55079", "WI"))  # Milwaukee County
    assert outside_training_area(beetle, None)  # off the county grid
    assert not outside_training_area(all_models()["early-blight-pdays"].SPEC, None)  # no training area
