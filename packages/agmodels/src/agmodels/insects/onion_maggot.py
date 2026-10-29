"""Onion Maggot, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "onion-maggot",
    "Onion Maggot",
    ("Onion",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "First generation adult flight peaks around 680 FDD and second generation adult flight peaks around 1950."
        " Controlling adults is the best way to protect against damage from this pest."
    ),
    generations=(
        (510, 680, 850),
        (1460, 1950, 2435),
    ),
)
