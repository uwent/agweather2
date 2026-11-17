"""Black Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="black-cutworm",
    name="Black Cutworm",
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
        "melon",
        "mint",
        "pea",
        "potato",
        "tomato",
    ),
    base_f=50,
    upper_f=86,
    biofix="05-15",
    generations=((300, 700, 1000),),
)
