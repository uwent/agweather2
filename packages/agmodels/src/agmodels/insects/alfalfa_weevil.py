"""Alfalfa weevil, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage

INSECT = Insect(
    id="alfalfa-weevil",
    name="Alfalfa weevil",
    crops=("Alfalfa",),
    base_f=48.2,  # 9 °C
    upper_f=86,  # 30 °C
    biofix="01-01",
    criteria="Alfalfa weevil egg hatch begins around 300 FDD. Light feeding damage expected during 1st and 2nd "
    "instar life stages (350-500 FDD). Heavy feeding damage expected during 3rd and 4th instar development, "
    "approx. 400-600 FDD.",
    stages=(
        Stage(start=300, severity=1, label="Egg hatch, begin scouting"),
        Stage(start=370, severity=2, label="2nd instar larvae"),
        Stage(start=440, severity=3, label="3rd instar larvae"),
        Stage(start=505, severity=4, label="4th instar larvae"),
        Stage(start=595, severity=2, label="Pupal stage, end scouting"),
        Stage(start=815, severity=1, label="Adult emergence"),
        Stage(start=1000, severity=0, label="Adult diapause"),
    ),
    source=CRT,
)
