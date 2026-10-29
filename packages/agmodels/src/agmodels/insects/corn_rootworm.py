"""Corn Rootworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="corn-rootworm",
    name="Corn Rootworm",
    crops=("Corn (Field and Sweet)",),
    base_f=52,
    upper_f=None,
    biofix="01-01",
    generations=((329, 472, 636),),
)
