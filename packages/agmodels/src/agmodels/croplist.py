"""The crops: one vocabulary of ids for models, topic pages, degree-day presets and typical planting dates (
Phase 6 step 2, "A crop vocabulary"; D93).

A crop is a plain noun (`soybean`, `sweet-corn`). A group is a crop with members (`cole-crops` holds cabbage,
broccoli and the rest): a model that names a group applies to each member, and one that names a member applies to
it within the group, so asking for broccoli finds the cole crop models and asking for wheat finds spring wheat's.
Names are public text.
"""

from dataclasses import dataclass
from typing import Literal

Category = Literal["field", "forage", "vegetable", "fruit", "specialty", "tree"]

CATEGORIES: dict[Category, str] = {  # public names, in the order a list shows them
    "field": "Field crops",
    "forage": "Forage and cover crops",
    "vegetable": "Vegetables",
    "fruit": "Fruit and nuts",
    "specialty": "Specialty crops",
    "tree": "Trees",
}


@dataclass(frozen=True, kw_only=True)
class Crop:
    id: str
    name: str
    category: Category
    members: tuple[str, ...] = ()  # a group's crops


CROPS: dict[str, Crop] = {
    c.id: c
    for c in (
        Crop(id="corn", name="Corn", category="field"),
        Crop(id="soybean", name="Soybean", category="field"),
        Crop(id="wheat", name="Wheat", category="field", members=("spring-wheat", "winter-wheat")),
        Crop(id="spring-wheat", name="Spring wheat", category="field"),
        Crop(id="winter-wheat", name="Winter wheat", category="field"),
        Crop(id="barley", name="Barley", category="field"),
        Crop(id="sorghum", name="Sorghum", category="field"),
        Crop(id="sunflower", name="Sunflower", category="field"),
        Crop(id="sugarbeet", name="Sugarbeet", category="field"),
        Crop(id="dry-bean", name="Dry bean", category="field"),
        Crop(id="cotton", name="Cotton", category="field"),
        Crop(id="alfalfa", name="Alfalfa", category="forage"),
        Crop(id="rye", name="Rye", category="forage"),
        Crop(id="asparagus", name="Asparagus", category="vegetable"),
        Crop(id="beans", name="Beans", category="vegetable", members=("snap-bean", "dry-bean")),
        Crop(id="snap-bean", name="Snap bean", category="vegetable"),
        Crop(id="beet", name="Table beet", category="vegetable"),
        Crop(id="carrot", name="Carrot", category="vegetable"),
        Crop(id="celery", name="Celery", category="vegetable"),
        Crop(
            id="cole-crops",
            name="Cole crops",
            category="vegetable",
            members=("cabbage", "broccoli", "cauliflower", "brussels-sprouts", "kale", "collards"),
        ),
        Crop(id="cabbage", name="Cabbage", category="vegetable"),
        Crop(id="broccoli", name="Broccoli", category="vegetable"),
        Crop(id="cauliflower", name="Cauliflower", category="vegetable"),
        Crop(id="brussels-sprouts", name="Brussels sprouts", category="vegetable"),
        Crop(id="kale", name="Kale", category="vegetable"),
        Crop(id="collards", name="Collards", category="vegetable"),
        Crop(id="cucumber", name="Cucumber", category="vegetable"),
        Crop(id="eggplant", name="Eggplant", category="vegetable"),
        Crop(id="horseradish", name="Horseradish", category="vegetable"),
        Crop(id="leafy-greens", name="Leafy greens", category="vegetable", members=("lettuce", "spinach")),
        Crop(id="lettuce", name="Lettuce", category="vegetable"),
        Crop(id="spinach", name="Spinach", category="vegetable"),
        Crop(id="melon", name="Melon", category="vegetable"),
        Crop(id="onion", name="Onion", category="vegetable"),
        Crop(id="pea", name="Pea", category="vegetable"),
        Crop(id="pepper", name="Pepper", category="vegetable"),
        Crop(id="potato", name="Potato", category="vegetable"),
        Crop(id="pumpkin-squash", name="Pumpkin and squash", category="vegetable", members=("pumpkin", "squash")),
        Crop(id="pumpkin", name="Pumpkin", category="vegetable"),
        Crop(id="squash", name="Squash", category="vegetable"),
        Crop(id="sweet-corn", name="Sweet corn", category="vegetable"),
        Crop(id="tomato", name="Tomato", category="vegetable"),
        Crop(id="apple", name="Apple", category="fruit"),
        Crop(id="blackberry", name="Blackberry", category="fruit"),
        Crop(id="raspberry", name="Raspberry", category="fruit"),
        Crop(id="cherry", name="Cherry", category="fruit"),
        Crop(id="pecan", name="Pecan", category="fruit"),
        Crop(id="hops", name="Hops", category="specialty"),
        Crop(id="mint", name="Mint", category="specialty"),
        Crop(id="oak", name="Oak", category="tree"),
    )
}


def crop(crop_id: str) -> Crop:
    return CROPS[crop_id]


def names(crop_ids: tuple[str, ...] | list[str]) -> list[str]:
    return [CROPS[c].name for c in crop_ids]


def groups_of(crop_id: str) -> list[str]:
    """The groups a crop is a member of."""
    return [c.id for c in CROPS.values() if crop_id in c.members]


def related(crop_id: str) -> set[str]:
    """The crop, the groups it's in and its members: what a model may name to apply to it."""
    return {crop_id, *groups_of(crop_id), *CROPS[crop_id].members}


def applies(crop_ids: tuple[str, ...] | list[str], crop_id: str) -> bool:
    """Whether something naming `crop_ids` applies to `crop_id`."""
    return bool(related(crop_id) & set(crop_ids))
