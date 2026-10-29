"""Mint Root Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="mint-root-borer",
    name="Mint Root Borer",
    crops=("Mint",),
    base_f=50,
    upper_f=None,
    biofix="04-01",
    generations=((430, 1280, 2150),),
)
