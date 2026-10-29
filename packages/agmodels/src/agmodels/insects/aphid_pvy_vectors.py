"""Aphid PVY Vectors, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="aphid-pvy-vectors",
    name="Aphid PVY Vectors",
    crops=("Potato",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    generations=((1838, 2515, 3228),),
)
