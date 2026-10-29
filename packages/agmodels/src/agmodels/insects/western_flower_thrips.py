"""Western Flower Thrips, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "western-flower-thrips",
    "Western Flower Thrips",
    ("Cucumber", "Eggplant", "Onion", "Pepper", "Tomato"),
    base_f=45,
    upper_f=None,
    biofix="01-01",
    criteria=(
        "Thrips typically have several overlapping generations per year in Wisconsin, with peaks occurring around"
        " 675, 1350, 2025, and 2700 FDD."
    ),
    generations=(
        (340, 675, 1010),
        (1010, 1350, 1685),
        (1685, 2025, 2360),
        (2360, 2700, 3375),
    ),
)
