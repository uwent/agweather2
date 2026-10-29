"""Black Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="black-cutworm",
    name="Black Cutworm",
    crops=(
        "Asparagus",
        "Bean",
        "Beet",
        "Carrot",
        "Celery",
        "Corn (Field and Sweet)",
        "Cucumber",
        "Hops",
        "Melon",
        "Mint",
        "Pea",
        "Potato",
        "Tomato",
    ),
    base_f=50,
    upper_f=86,
    biofix="05-15",
    generations=((300, 700, 1000),),
)
