"""Asparagus Beetle (Common), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="common-asparagus-beetle",
    name="Asparagus Beetle (Common)",
    crops=("Asparagus",),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=((105, 250, 405),),
)
