"""Western Flower Thrips, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="western-flower-thrips",
    name="Western Flower Thrips",
    crops=("Cucumber", "Eggplant", "Onion", "Pepper", "Tomato"),
    base_f=45,
    upper_f=None,
    biofix="01-01",
    generations=(
        (340, 675, 1010),
        (1010, 1350, 1685),
        (1685, 2025, 2360),
        (2360, 2700, 3375),
    ),
)
