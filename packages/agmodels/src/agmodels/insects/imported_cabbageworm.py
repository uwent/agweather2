"""Imported Cabbageworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="imported-cabbageworm",
    name="Imported Cabbageworm",
    crops=("Cole Crops",),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=(
        (150, 240, 630),
        (830, 1030, 2000),
    ),
)
