"""Squash Vine Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="squash-vine-borer",
    name="Squash Vine Borer",
    crops=("cucumber", "melon", "pumpkin-squash"),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=((750, 900, 1000),),
)
