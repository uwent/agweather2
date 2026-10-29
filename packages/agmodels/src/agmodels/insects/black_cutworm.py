"""Black Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "black-cutworm",
    "Black Cutworm",
    (
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
    criteria=(
        "Egg hatch begins around 180 FDD, with leaf cutting and larval development starting around 300 FDD and "
        "extending through 1000 FDD."
    ),
    generations=((300, 700, 1000),),
)
