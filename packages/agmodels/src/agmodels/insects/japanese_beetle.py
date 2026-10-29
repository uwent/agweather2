"""Japanese Beetle, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="japanese-beetle",
    name="Japanese Beetle",
    crops=(
        "Asparagus",
        "Bean",
        "Beet",
        "Blackberry",
        "Cole Crops",
        "Eggplant",
        "Hops",
        "Horseradish",
        "Leafy Greens",
        "Melon",
        "Mint",
        "Pea",
        "Pepper",
        "Potato",
        "Pumpkin and Squash",
        "Raspberry",
        "Tomato",
    ),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=((970, 1600, 2150),),
)
