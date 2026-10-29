"""Variegated Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="variegated-cutworm",
    name="Variegated Cutworm",
    crops=(
        "Asparagus",
        "Bean",
        "Beet",
        "Carrot",
        "Celery",
        "Corn (Field and Sweet)",
        "Cucumber",
        "Hops",
        "Leafy Greens",
        "Melon",
        "Mint",
        "Potato",
        "Tomato",
    ),
    base_f=45,
    upper_f=80.1,
    biofix="05-01",
    generations=((900, 1450, 2100),),
)
