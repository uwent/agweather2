"""Variegated Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="variegated-cutworm",
    name="Variegated Cutworm",
    crops=(
        "asparagus",
        "beans",
        "beet",
        "carrot",
        "celery",
        "corn",
        "sweet-corn",
        "cucumber",
        "hops",
        "leafy-greens",
        "melon",
        "mint",
        "potato",
        "tomato",
    ),
    base_f=45,
    upper_f=80.1,
    biofix="05-01",
    generations=((900, 1450, 2100),),
)
