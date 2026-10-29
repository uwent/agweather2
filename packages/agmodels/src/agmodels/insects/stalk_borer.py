"""Stalk Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "stalk-borer",
    "Stalk Borer",
    ("Corn (Field and Sweet)",),
    base_f=41,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "Adult flight begins around 1110 FDD and peaks around 1650 FDD. Control is best between 1400 and 1700 FDD."
    ),
    generations=((1110, 1400, 1700),),
)
