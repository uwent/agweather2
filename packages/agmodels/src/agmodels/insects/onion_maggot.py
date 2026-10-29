"""Onion Maggot, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="onion-maggot",
    name="Onion Maggot",
    crops=("Onion",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    generations=(
        (510, 680, 850),
        (1460, 1950, 2435),
    ),
)
