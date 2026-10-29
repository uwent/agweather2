"""Imported Cabbageworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "imported-cabbageworm",
    "Imported Cabbageworm",
    ("Cole Crops",),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    criteria=(
        "First generation adult flight starts around 150 FDD, peaks around 240 FDD, with larval feeding expected "
        "through 630 FDD. Second generation adult flight starts around 830 FDD, peaks around 1030 FDD, with "
        "larval feeding expected through around 2000 FDD."
    ),
    generations=(
        (150, 240, 630),
        (830, 1030, 2000),
    ),
)
