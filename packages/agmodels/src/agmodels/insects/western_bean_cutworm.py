"""Western Bean Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="western-bean-cutworm",
    name="Western Bean Cutworm",
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
        "potato",
        "tomato",
    ),
    base_f=50,
    upper_f=None,
    biofix="05-01",
    generations=((1320, 1420, 1535),),
)
