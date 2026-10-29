"""Cabbage Maggot, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="cabbage-maggot",
    name="Cabbage Maggot",
    crops=("Cole Crops",),
    base_f=42.8,
    upper_f=86,
    biofix="01-01",
    generations=(
        (360, 600, 1521),
        (1881, 2121, 3042),
    ),
)
