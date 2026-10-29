"""Alfalfa weevil, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage

INSECT = Insect(
    "alfalfa-weevil",
    "Alfalfa weevil",
    ("Alfalfa",),
    base_f=48.2,  # 9 °C
    upper_f=86,  # 30 °C
    biofix="01-01",
    criteria="Alfalfa weevil egg hatch begins around 300 FDD. Light feeding damage expected during 1st and 2nd "
    "instar life stages (350-500 FDD). Heavy feeding damage expected during 3rd and 4th instar development, "
    "approx. 400-600 FDD.",
    stages=(
        Stage(300, 1, "Egg hatch, begin scouting"),
        Stage(370, 2, "2nd instar larvae"),
        Stage(440, 3, "3rd instar larvae"),
        Stage(505, 4, "4th instar larvae"),
        Stage(595, 2, "Pupal stage, end scouting"),
        Stage(815, 1, "Adult emergence"),
        Stage(1000, 0, "Adult diapause"),
    ),
    source=CRT,
)
