"""Japanese Beetle, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="japanese-beetle",
    name="Japanese Beetle",
    crops=(
        "asparagus",
        "beans",
        "beet",
        "blackberry",
        "cole-crops",
        "eggplant",
        "hops",
        "horseradish",
        "leafy-greens",
        "melon",
        "mint",
        "pea",
        "pepper",
        "potato",
        "pumpkin-squash",
        "raspberry",
        "tomato",
    ),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=((970, 1600, 2150),),
)
