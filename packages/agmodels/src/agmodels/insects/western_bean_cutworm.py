"""Western Bean Cutworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "western-bean-cutworm",
    "Western Bean Cutworm",
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
        "Potato",
        "Tomato",
    ),
    base_f=50,
    upper_f=None,
    biofix="05-01",
    criteria=(
        "25% adult moth emergence expected around 1320 FDD, peaking around 1420 FDD, and ending around 1535 FDD."
    ),
    generations=((1320, 1420, 1535),),
)
