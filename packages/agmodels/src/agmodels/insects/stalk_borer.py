"""Stalk Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="stalk-borer",
    name="Stalk Borer",
    crops=("corn", "sweet-corn"),
    base_f=41,
    upper_f=86,
    biofix="01-01",
    generations=((1110, 1400, 1700),),
)
