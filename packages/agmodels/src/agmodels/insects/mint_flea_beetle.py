"""Flea Beetle (Mint), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="mint-flea-beetle",
    name="Flea Beetle (Mint)",
    crops=("Mint",),
    base_f=41,
    upper_f=None,
    biofix="01-01",
    generations=((1475, 1675, 1880),),
)
