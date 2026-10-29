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
    criteria=(
        "Egg-laying peaks around 900 FDD with larval populations active from around 1150 FDD through 1900 FDD, "
        "with end of larval stage around 2100 FDD."
    ),
    generations=((900, 1450, 2100),),
)
