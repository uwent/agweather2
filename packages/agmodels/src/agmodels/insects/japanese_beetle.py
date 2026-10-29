"""Japanese Beetle, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "japanese-beetle",
    "Japanese Beetle",
    (
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
    criteria=(
        "Adults emerge starting around 970 FDD, with peak feeding around 1600 FDD, and end of feeding by around "
        "2150 FDD."
    ),
    generations=((970, 1600, 2150),),
)
